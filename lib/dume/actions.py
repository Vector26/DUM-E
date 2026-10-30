"""DUM-E actions: the model may only PROPOSE; the owner approves and runs them.

Flow:
  1. dume-tool propose_action  -> validates against config/actions.json, writes state/pending/<ID>.json
  2. owner runs `dume approve <ID>` in their own terminal -> re-validates, shows exactly what will
     happen (including every deletion), asks for confirmation, runs it, writes state/results/<ID>.json
Nothing the model says counts as approval (Deletion Mandate, plan section 12.0).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import core

ACTIONS_FILE = core.CONFIG / "actions.json"
CLASSES = {"mutates", "housekeeping", "permanent_delete"}


class ActionError(Exception):
    pass


def load_catalog() -> dict:
    data = json.loads(ACTIONS_FILE.read_text())
    catalog = {k: v for k, v in data.items() if not k.startswith("_")}
    for name, spec in catalog.items():
        if "deletes" not in spec:
            raise ActionError(f"actions.json: '{name}' has no 'deletes' field (Deletion Mandate M4)")
        if spec["deletes"] != "none" and not (isinstance(spec["deletes"], list) and spec["deletes"]):
            raise ActionError(f"actions.json: '{name}' deletes must be 'none' or a non-empty list")
        if spec.get("class") not in CLASSES:
            raise ActionError(f"actions.json: '{name}' has invalid class")
        if spec["deletes"] != "none" and spec["class"] == "mutates":
            raise ActionError(f"actions.json: '{name}' deletes something but is classed 'mutates'")
        if spec["class"] == "permanent_delete" and not spec.get("typed_phrase"):
            raise ActionError(f"actions.json: '{name}' is permanent_delete without typed_phrase")
        if bool(spec.get("argv")) == bool(spec.get("builtin")):
            raise ActionError(f"actions.json: '{name}' needs exactly one of argv/builtin")
    return catalog


def _service_ids() -> list[str]:
    rc, out = core.run([str(core.CONTROL_PY), str(core.STATUS_PY), "catalog"], timeout=30,
                       cwd=str(core.CONTROL))
    try:
        return [s["id"] for s in json.loads(out[out.index("["):])]
    except Exception:
        return []


def validate(action: str, args: dict, catalog: dict | None = None) -> tuple[dict, dict, list[str]]:
    """Return (spec, clean_args, rendered command lines) or raise ActionError."""
    catalog = catalog or load_catalog()
    if action not in catalog:
        raise ActionError(f"Unknown action '{action}'. Allowed: {', '.join(catalog)}")
    spec = catalog[action]
    args = args or {}
    clean = {}
    unknown = set(args) - set(spec.get("args", {}))
    if unknown:
        raise ActionError(f"Unexpected argument(s) for {action}: {', '.join(sorted(unknown))}")
    for key, rule in spec.get("args", {}).items():
        value = str(args.get(key, "")).strip()
        if not value:
            raise ActionError(f"{action} needs argument '{key}'")
        if rule.get("type") == "service_id":
            ids = _service_ids()
            if value not in ids:
                raise ActionError(f"'{value}' is not a Homelab service id. Known: {', '.join(ids)}")
            if value in rule.get("exclude", []):
                raise ActionError(f"{action} is not allowed for '{value}'."
                                  " Use the dedicated action (llama_*/watchdog_*) or ask the owner.")
        clean[key] = value
    if spec.get("argv"):
        argv = [_expand_argv_part(part, clean) for part in spec["argv"]]
        rendered = [" ".join(argv)]
    else:
        rendered = BUILTIN_DESCRIPTIONS[spec["builtin"]]
    return spec, clean, rendered


def _expand_argv_part(part: str, clean: dict) -> str:
    text = part.format(home=str(core.HOME), homelab=str(core.FORTRESS), **clean)
    if text.startswith("~/"):
        return str(core.HOME / text[2:])
    return text


BUILTIN_DESCRIPTIONS = {
    "ollama_unload": ["for each model in `ollama ps`: POST http://127.0.0.1:11434/api/generate"
                      " {\"model\": <name>, \"keep_alive\": 0}"],
    "watchdog_restart": [f"{core.FORTRESS_CLI} stop vram_watchdog",
                         f"{core.FORTRESS_CLI} start vram_watchdog"],
    "watchdog_clear_pause": [f"remove {core.WATCHDOG_DIR / 'ai-paused'}",
                             f"{core.LLAMA_CTL} start"],
}


def _fingerprint(record: dict) -> str:
    material = json.dumps({k: record.get(k) for k in ("kind", "action", "args", "commands", "file", "op",
                                                      "section", "new_text", "new_content", "base_sha256",
                                                      "deletes", "class", "typed_phrase")},
                          sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def new_id() -> str:
    while True:
        pid = secrets.token_hex(3).upper()
        if not (core.PENDING / f"{pid}.json").exists() and not (core.RESULTS / f"{pid}.json").exists():
            return pid


def save_pending(record: dict) -> dict:
    core.PENDING.mkdir(parents=True, exist_ok=True)
    record["fingerprint"] = _fingerprint(record)
    # Return an identical open proposal instead of piling up duplicates.
    for existing in core.PENDING.glob("*.json"):
        old = core.load_json(existing, {})
        if old.get("fingerprint") == record["fingerprint"] and old.get("expires", 0) > core.now():
            return old
    record["id"] = new_id()
    record["created"] = core.now()
    record["expires"] = core.now() + core.PENDING_TTL_S
    record["status"] = "pending"
    record["requested_by"] = core.caller()
    path = core.PENDING / f"{record['id']}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(record, fh, indent=2)
    core.audit("proposed", id=record["id"], kind=record["kind"],
               what=record.get("action") or f"{record.get('op')} {record.get('file')}#{record.get('section')}")
    return record


def propose(action: str, args: dict) -> str:
    spec, clean, rendered = validate(action, args)
    record = save_pending({"kind": "action", "action": action, "args": clean, "commands": rendered,
                           "summary": spec["summary"], "deletes": spec["deletes"], "class": spec["class"],
                           "typed_phrase": spec.get("typed_phrase"), "warnings": spec.get("warnings", [])})
    lines = [f"Proposal {record['id']} created. NOTHING HAS RUN YET.",
             f"Action: {action} {json.dumps(clean) if clean else ''}",
             f"What it does: {spec['summary']}",
             "Commands: " + " ; ".join(rendered)]
    if spec["deletes"] != "none":
        lines.append("Deletes: " + "; ".join(spec["deletes"]))
    for w in spec.get("warnings", []):
        lines.append(f"Warning: {w}")
    lines.append(f"Tell the owner to approve it in a separate terminal with:  dume approve {record['id']}")
    lines.append("It expires in 30 minutes. Check the outcome later with action_status.")
    return "\n".join(lines)


def status(proposal_id: str) -> str:
    pid = proposal_id.strip().upper()
    if not pid.isalnum() or len(pid) > 12:
        return "Invalid proposal id."
    for folder in (core.RESULTS, core.PENDING):
        record = core.load_json(folder / f"{pid}.json")
        if record:
            state = record.get("status")
            if state == "pending" and record.get("expires", 0) < core.now():
                state = "expired (never approved)"
            lines = [f"Proposal {pid}: {state}",
                     f"  what: {record.get('action') or record.get('op')} {json.dumps(record.get('args') or record.get('section') or '')}"]
            if record.get("rc") is not None:
                lines.append(f"  exit code: {record['rc']}")
            if record.get("output_tail"):
                lines.append("  output (tail):\n" + core.redact(record["output_tail"])[-3000:])
            return "\n".join(lines)
    return f"No proposal {pid}."


# ---------------------------------------------------------------- owner side

def owner_check() -> None:
    import pwd
    if os.getuid() != pwd.getpwnam(core.OWNER).pw_uid or os.environ.get("SUDO_USER"):
        raise SystemExit(f"Only the owner, logged in as '{core.OWNER}' (not through sudo), can approve.")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SystemExit("Approval needs an interactive terminal. Nothing was run.")


def list_pending() -> list[dict]:
    rows = []
    for path in sorted(core.PENDING.glob("*.json"), key=lambda p: p.stat().st_mtime):
        record = core.load_json(path, {})
        if record:
            rows.append(record)
    return rows


def _finish(record: dict, status: str, rc=None, output: str = "") -> None:
    record.update({"status": status, "rc": rc, "output_tail": output[-6000:], "finished": core.now()})
    core.RESULTS.mkdir(parents=True, exist_ok=True)
    (core.RESULTS / f"{record['id']}.json").write_text(json.dumps(record, indent=2))
    pending = core.PENDING / f"{record['id']}.json"
    if pending.exists():
        pending.unlink()  # DUM-E's own proposal file; the full record now lives in results/
    core.audit("finished", id=record["id"], status=status, rc=rc)


def _run_logged(argv: list[str], timeout, stream: bool, log_path: Path) -> tuple[int, str]:
    if stream:
        print(f"--- running: {' '.join(argv)} (output below) ---")
        proc = subprocess.run(argv, env=core.SAFE_ENV, cwd=str(core.HOME), stdin=subprocess.DEVNULL,
                              timeout=timeout)
        return proc.returncode, "(output was shown in the owner's terminal)"
    with open(log_path, "w") as log:
        try:
            proc = subprocess.run(argv, env=core.SAFE_ENV, cwd=str(core.HOME), stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = 124
    return rc, log_path.read_text(errors="replace")


def _builtin(name: str, log_path: Path, timeout) -> tuple[int, str]:
    if name == "ollama_unload":
        rc, out = core.run(["ollama", "ps"], timeout=15)
        models = [l.split()[0] for l in out.splitlines()[1:] if l.strip()]
        if not models:
            return 0, "No Ollama model was loaded; nothing to unload."
        done = []
        for model in models:
            body = json.dumps({"model": model, "keep_alive": 0}).encode()
            req = urllib.request.Request(core.OLLAMA_URL + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=30).read()
                done.append(f"unloaded {model}")
            except Exception as exc:
                done.append(f"failed {model}: {exc}")
        return 0, "\n".join(done)
    if name == "watchdog_restart":
        rc1, out1 = _run_logged([str(core.FORTRESS_CLI), "stop", "vram_watchdog"], timeout, False, log_path)
        time.sleep(2)
        rc2, out2 = _run_logged([str(core.FORTRESS_CLI), "start", "vram_watchdog"], timeout, False,
                                log_path.with_suffix(".2.log"))
        time.sleep(3)
        alive = core.run(["pgrep", "-f", "vram-watchdog.sh$"], timeout=5)[1].split()
        return (0 if rc2 == 0 and len(alive) == 1 else 1), \
            f"{out1}\n{out2}\nwatchdog processes now: {len(alive)}"
    if name == "watchdog_clear_pause":
        flag = core.WATCHDOG_DIR / "ai-paused"
        note = "pause flag was not present"
        if flag.exists():
            flag.unlink()
            note = "removed pause flag"
        rc, out = _run_logged([str(core.LLAMA_CTL), "start"], timeout, False, log_path)
        return rc, f"{note}\n{out}"
    raise ActionError(f"unknown builtin {name}")


def approve(proposal_id: str) -> int:
    """Owner-only, interactive. Returns a process exit code."""
    from . import knowledge
    owner_check()
    pid = proposal_id.strip().upper()
    path = core.PENDING / f"{pid}.json"
    record = core.load_json(path)
    if not record:
        print(f"No pending proposal {pid}. (dume pending lists them.)")
        return 1
    if record.get("expires", 0) < core.now():
        _finish(record, "expired")
        print(f"Proposal {pid} expired; nothing was run. Ask DUM-E to propose it again.")
        return 1
    if record.get("fingerprint") != _fingerprint(record):
        _finish(record, "rejected: record was altered")
        print("Proposal record does not match its fingerprint. Refused.")
        return 1

    if record["kind"] == "knowledge_edit":
        return knowledge.approve_edit(record, _finish)

    try:
        spec, clean, rendered = validate(record["action"], record["args"])
    except ActionError as exc:
        _finish(record, f"rejected: {exc}")
        print(f"Refused: {exc}")
        return 1
    if rendered != record["commands"] or spec["deletes"] != record["deletes"]:
        _finish(record, "rejected: catalog changed since proposal")
        print("The action definition changed since DUM-E proposed it. Refused; ask for a new proposal.")
        return 1

    print("=" * 72)
    print(f"DUM-E proposal {pid}  (requested by {record.get('requested_by')})")
    print(f"Action : {record['action']} {json.dumps(clean) if clean else ''}")
    print(f"Does   : {spec['summary']}")
    for line in rendered:
        print(f"Runs   : {line}")
    if spec["deletes"] == "none":
        print("Deletes: nothing")
    else:
        for item in spec["deletes"]:
            print(f"DELETES: {item}")
    for w in spec.get("warnings", []):
        print(f"Warning: {w}")
    print("=" * 72)
    if spec["class"] == "permanent_delete":
        phrase = spec["typed_phrase"]
        answer = input(f"This PERMANENTLY deletes data. Type {phrase} to run it, anything else cancels: ").strip()
        ok = answer == phrase
    else:
        answer = input("Run it? Type y to run, anything else cancels: ").strip().lower()
        ok = answer == "y"
    if not ok:
        _finish(record, "rejected by owner")
        print("Cancelled. Nothing was run.")
        return 1

    core.audit("approved", id=pid, action=record["action"], args=clean)
    log_path = core.RESULTS / f"{pid}.log"
    core.RESULTS.mkdir(parents=True, exist_ok=True)
    try:
        if spec.get("argv"):
            argv = [_expand_argv_part(part, clean) for part in spec["argv"]]
            rc, output = _run_logged(argv, spec.get("timeout"), bool(spec.get("stream")), log_path)
        else:
            rc, output = _builtin(spec["builtin"], log_path, spec.get("timeout"))
    except subprocess.TimeoutExpired:
        rc, output = 124, "timed out"
    _finish(record, "done" if rc == 0 else "failed", rc, output)
    print(output[-4000:])
    print(f"--- {pid}: {'done' if rc == 0 else 'FAILED'} (exit {rc}). DUM-E can read this with action_status.")
    return 0 if rc == 0 else 1


def reject(proposal_id: str) -> int:
    owner_check()
    pid = proposal_id.strip().upper()
    record = core.load_json(core.PENDING / f"{pid}.json")
    if not record:
        print(f"No pending proposal {pid}.")
        return 1
    _finish(record, "rejected by owner")
    print(f"Rejected {pid}. Nothing was run.")
    return 0
