"""DUM-E read-only tools. Each takes a dict of arguments and returns plain text.

No tool here changes system state. The only writes are DUM-E's own cache, the audit log,
and proposal files (see actions.py / knowledge.py), all inside ~/homelab/DUM-E/state.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from . import core
from .core import run, http_get, human_age

# ---------------------------------------------------------------- helpers


def _arg_int(args: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(args.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _arg_str(args: dict, key: str, default: str = "", maxlen: int = 200) -> str:
    value = args.get(key, default)
    if value is None:
        return default
    return str(value)[:maxlen]


def _status_py(cmd: str, timeout: float = 60) -> dict | list | None:
    if cmd not in {"status", "catalog", "ai-catalog", "profile", "gpu", "running-ids", "health"}:
        raise ValueError("status.py subcommand not allowed")  # never 'snapshot-default'
    rc, out = run([str(core.CONTROL_PY), str(core.STATUS_PY), cmd], timeout=timeout,
                  cwd=str(core.CONTROL))
    starts = [i for i in (out.find("{"), out.find("[")) if i >= 0]
    if not starts:
        return None
    try:
        return json.loads(out[min(starts):])
    except Exception:
        return None


def _gpu_query() -> dict:
    rc, out = run(["nvidia-smi",
                   "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,"
                   "temperature.gpu,power.draw,power.limit",
                   "--format=csv,noheader,nounits"], timeout=10)
    if rc != 0 or not out:
        return {"error": out or "nvidia-smi failed (driver unloaded?)"}
    parts = [p.strip() for p in out.splitlines()[0].split(",")]
    keys = ["name", "total", "used", "free", "util", "temp", "power", "power_limit"]
    return dict(zip(keys, parts))


def _docker_id_names() -> dict:
    rc, out = run(["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Names}}"], timeout=15)
    mapping = {}
    for line in out.splitlines():
        if " " in line:
            cid, name = line.split(" ", 1)
            mapping[cid] = name
    return mapping


def _pid_owner(pid: str, id_names: dict) -> str:
    """Name the container (or host command) that owns a PID."""
    try:
        cgroup = Path(f"/proc/{pid}/cgroup").read_text()
        match = re.search(r"([0-9a-f]{64})", cgroup)
        if match and match.group(1) in id_names:
            return f"container {id_names[match.group(1)]}"
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return f"host process: {cmd[:120]}"
    except Exception:
        return "unknown (process gone or not readable)"


def _gpu_apps() -> list[dict]:
    rc, out = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory",
                   "--format=csv,noheader,nounits"], timeout=10)
    apps = []
    if rc != 0:
        return apps
    id_names = None
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        if id_names is None:
            id_names = _docker_id_names()
        apps.append({"pid": parts[0], "name": parts[1], "mib": parts[2],
                     "owner": _pid_owner(parts[0], id_names)})
    return apps


def _llama_process() -> dict | None:
    """Find the running llama-server and parse its real arguments (never trust the alias)."""
    pids = []
    try:
        pids.append(core.LLAMA_PIDFILE.read_text().strip())
    except Exception:
        pass
    rc, out = run(["pgrep", "-f", "build/bin/llama-server"], timeout=5)
    pids += out.split()
    for pid in pids:
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        except Exception:
            continue
        argv = [a.decode(errors="replace") for a in raw if a]
        if not argv or "llama-server" not in argv[0]:
            continue
        info = {"pid": pid}
        flags = {"-m": "model", "-c": "context", "--alias": "alias", "-ncmoe": "ncmoe",
                 "--cache-type-k": "kv_k", "--cache-type-v": "kv_v", "--host": "host", "--port": "port"}
        for i, arg in enumerate(argv[:-1]):
            if arg in flags:
                info[flags[arg]] = argv[i + 1]
        if "-cmoe" in argv:
            info["moe"] = "all experts on CPU (-cmoe)"
        rc, etimes = run(["ps", "-o", "etimes=", "-p", pid], timeout=5)
        if etimes.strip().isdigit():
            info["running_for"] = human_age(int(etimes.strip()))
        return info
    return None


def _watchdog_constants() -> dict:
    consts = {}
    try:
        for line in core.WATCHDOG_SCRIPT.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=([0-9]+)", line.strip())
            if m:
                consts[m.group(1)] = int(m.group(2))
    except Exception:
        pass
    return consts


def _watchdog_state() -> dict:
    state = {"running": False}
    try:
        pid = (core.WATCHDOG_DIR / "watchdog.pid").read_text().strip()
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
        state["running"] = "vram-watchdog.sh" in cmd
        state["pid"] = pid
    except Exception:
        pass
    flag = core.WATCHDOG_DIR / "ai-paused"
    if flag.exists():
        try:
            paused_at = int(flag.read_text().strip())
            state["paused_since"] = datetime.fromtimestamp(paused_at).isoformat(timespec="seconds")
            state["paused_for"] = human_age(core.now() - paused_at)
        except Exception:
            state["paused_since"] = "flag present (unreadable timestamp)"
    log = core.WATCHDOG_DIR / "watchdog.log"
    if log.exists() and log.stat().st_size:
        state["last_log"] = core.tail_file(log, 4)
    return state


def _ollama_ps() -> str:
    rc, out = run(["ollama", "ps"], timeout=10)
    lines = [l for l in out.splitlines() if l.strip()]
    if rc != 0:
        return f"ollama not reachable: {out[:200]}"
    if len(lines) <= 1:
        return "no Ollama model loaded in memory"
    return "\n".join(lines)


def _incidents(hours: float, source: str = "") -> tuple[int, list]:
    cutoff = datetime.now().astimezone() - timedelta(hours=hours)
    counts: Counter = Counter()
    first: dict = {}
    last: dict = {}
    total = 0
    path = core.INCIDENTS_LOG
    if not path.exists():
        return 0, []
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"])
            except Exception:
                continue
            if ts < cutoff:
                continue
            if source and source.lower() not in entry.get("source", "").lower():
                continue
            total += 1
            key = (entry.get("source", "?"), entry.get("severity", "?"), entry.get("summary", "")[:140])
            counts[key] += 1
            first.setdefault(key, entry["ts"])
            last[key] = entry["ts"]
    rows = [(n, k, first[k], last[k]) for k, n in counts.most_common(25)]
    return total, rows


# ---------------------------------------------------------------- tools


def snapshot(args: dict) -> str:
    """One-screen overview of the whole machine."""
    out = []
    rc, up = run(["uptime"], timeout=5)
    out.append(f"Uptime/load: {up}")
    rc, boot = run(["uptime", "-s"], timeout=5)
    out.append(f"Booted: {boot}")
    rc, mem = run(["free", "-h"], timeout=5)
    out.append("Memory:\n" + mem)
    rc, df = run(["df", "-h", "/", "/mnt/backup-volume", "/mnt/photos"], timeout=10)
    out.append("Disks:\n" + df)
    gpu = _gpu_query()
    if "error" in gpu:
        out.append(f"GPU: {gpu['error']}")
    else:
        out.append(f"GPU: {gpu['name']} | VRAM used {gpu['used']} / {gpu['total']} MiB, free {gpu['free']} MiB"
                   f" | util {gpu['util']}% | {gpu['temp']} C | {gpu['power']} W of {gpu['power_limit']} W")
        for app in _gpu_apps():
            out.append(f"  GPU user: PID {app['pid']} {app['name']} {app['mib']} MiB -> {app['owner']}")
    llama = _llama_process()
    code, body = http_get(core.LLAMA_URL + "/health")
    if llama:
        model = Path(llama.get("model", "?")).name
        out.append(f"AI brain: running (PID {llama['pid']}, {llama.get('running_for', '?')}), model file {model},"
                   f" ctx {llama.get('context', '?')}, health {'ok' if code == 200 else 'NOT ok: ' + body[:80]}")
    else:
        out.append("AI brain: NOT running (no llama-server process; :8081 "
                   + ("answers" if code == 200 else "closed") + ")")
    wd = _watchdog_state()
    wd_line = f"VRAM watchdog: {'running' if wd['running'] else 'NOT running'}"
    if "paused_since" in wd:
        wd_line += f"; AI PAUSED by watchdog since {wd['paused_since']} ({wd.get('paused_for', '?')})"
    out.append(wd_line)
    out.append("Ollama: " + _ollama_ps().replace("\n", "\n  "))
    status = _status_py("status")
    if isinstance(status, dict):
        off_defaults = [s["id"] for s in status["services"] if s["default"] and not s["running"]]
        out.append(f"Homelab services: {status['on']}/{status['total']} running."
                   f" Default services not running: {', '.join(off_defaults) or 'none'}")
    total, rows = _incidents(24)
    out.append(f"Incidents in last 24 h: {total}" + (
        "; top: " + "; ".join(f"{k[0]} x{n}" for n, k, _, _ in rows[:5]) if rows else ""))
    pending = sorted(core.PENDING.glob("*.json"))
    if pending:
        out.append(f"Proposals waiting for owner approval: {len(pending)} (owner runs: dume pending)")
    return "\n".join(out)


def gpu(args: dict) -> str:
    g = _gpu_query()
    if "error" in g:
        return f"GPU unavailable: {g['error']}"
    lines = [f"{g['name']}: VRAM total {g['total']} MiB, used {g['used']} MiB, free {g['free']} MiB",
             f"Utilisation {g['util']}%, temperature {g['temp']} C, power {g['power']} W (limit {g['power_limit']} W)"]
    apps = _gpu_apps()
    if not apps:
        lines.append("No compute processes on the GPU.")
    for app in apps:
        lines.append(f"PID {app['pid']} ({app['name']}) uses {app['mib']} MiB -> {app['owner']}")
    rc, clocks = run(["nvidia-smi", "--query-gpu=clocks.gr,clocks.mem,persistence_mode,pstate",
                      "--format=csv"], timeout=10)
    lines.append("Clocks/state:\n" + clocks)
    lines.append("Rules: only one GPU-heavy AI brain at a time (control/ai_models.yaml). The watchdog pauses the"
                 " AI below its pause threshold; see tool ai_brain for the live gates.")
    return "\n".join(lines)


def ai_brain(args: dict) -> str:
    lines = []
    llama = _llama_process()
    code, body = http_get(core.LLAMA_URL + "/health")
    if llama:
        lines.append(f"llama-server PID {llama['pid']}, up {llama.get('running_for', '?')}")
        lines.append(f"  model file: {llama.get('model', '?')}")
        lines.append(f"  context {llama.get('context', '?')}, KV {llama.get('kv_k', '?')}/{llama.get('kv_v', '?')},"
                     f" MoE on CPU: {llama.get('ncmoe') or llama.get('moe') or '?'} layers,"
                     f" bind {llama.get('host', '?')}:{llama.get('port', '?')}")
        lines.append(f"  alias reported to clients: {llama.get('alias', '?')} (alias is fixed in the start script;"
                     " the model file above is the truth)")
    else:
        lines.append("llama-server: NOT running.")
    lines.append(f"  /health: {code} {body[:120]}")
    if code == 200:
        scode, sbody = http_get(core.LLAMA_URL + "/slots")
        try:
            slots = json.loads(sbody)
            busy = sum(1 for s in slots if s.get("is_processing"))
            lines.append(f"  slots: {len(slots)} total, {busy} busy (shared by pi, Jarvis, Virtual Self, feed, DUM-E)")
        except Exception:
            pass
    wd = _watchdog_state()
    consts = _watchdog_constants()
    g = _gpu_query()
    lines.append(f"VRAM watchdog: {'running PID ' + wd.get('pid', '?') if wd['running'] else 'NOT running'}")
    if consts:
        lines.append(f"  rules (from vram-watchdog.sh): pause when free VRAM < {consts.get('FREE_PAUSE_MIB')} MiB;"
                     f" resume when free >= {consts.get('FREE_RESUME_MIB')} MiB AND GPU util <="
                     f" {consts.get('QUIET_UTIL_PCT', '?')}% for {consts.get('QUIET_POLLS_NEEDED', '?')} polls of"
                     f" {consts.get('POLL_S')} s AND paused >= {consts.get('MIN_PAUSE_S')} s")
    if "paused_since" in wd:
        lines.append(f"  AI is PAUSED since {wd['paused_since']} ({wd.get('paused_for')}). Live gates now:"
                     f" free {g.get('free', '?')} MiB, util {g.get('util', '?')}%.")
    else:
        lines.append("  not paused")
    if "last_log" in wd:
        lines.append("  last watchdog log lines:\n    " + wd["last_log"].replace("\n", "\n    "))
    lines.append("Ollama in memory: " + _ollama_ps().replace("\n", "\n  "))
    rc, olist = run(["ollama", "list"], timeout=10)
    lines.append("Ollama models on disk:\n  " + olist.replace("\n", "\n  "))
    brains = _status_py("ai-catalog")
    if isinstance(brains, list):
        lines.append("Brain menu (control/ai_models.yaml): " + "; ".join(
            f"{b['id']} ({b.get('backend')}, {b.get('quant', '')})" for b in brains))
    profile = _status_py("profile")
    if isinstance(profile, dict):
        lines.append(f"Default profile brain at boot: {profile.get('ai', '?')}")
    return "\n".join(lines)


def services(args: dict) -> str:
    sid = _arg_str(args, "id", "", 60)
    status = _status_py("status")
    if not isinstance(status, dict):
        return "Could not read Homelab Control status (control/status.py status failed)."
    profile = _status_py("profile") or {}
    in_profile = set(profile.get("services", [])) if isinstance(profile, dict) else set()
    catalog = _status_py("catalog") or []
    by_id = {c["id"]: c for c in catalog} if isinstance(catalog, list) else {}
    if sid:
        if sid not in by_id:
            return f"Unknown service id '{sid}'. Known: {', '.join(sorted(by_id))}"
        entry = by_id[sid]
        live = next((s for s in status["services"] if s["id"] == sid), {})
        dependents = [c["id"] for c in by_id.values() if sid in (c.get("depends_on") or [])]
        lines = [f"{entry.get('name')} ({sid}): {'RUNNING' if live.get('running') else 'not running'}",
                 f"  what: {entry.get('blurb', '')}",
                 f"  kind: {entry.get('kind')}; GPU: {bool(entry.get('gpu'))}; default in services.yaml:"
                 f" {bool(entry.get('default'))}; in boot profile: {sid in in_profile}"]
        for key in ("compose", "start", "stop", "detect_container", "detect_port", "detect_process", "depends_on"):
            if entry.get(key):
                lines.append(f"  {key}: {entry[key]}")
        lines.append(f"  services that depend on it: {', '.join(dependents) or 'none'}")
        return "\n".join(lines)
    lines = [f"{status['on']}/{status['total']} services running. AI: {status.get('ai', {}).get('label', '?')}",
             "id | state | default(yaml) | in boot profile | GPU | what"]
    for s in status["services"]:
        lines.append(f"{s['id']} | {'ON' if s['running'] else 'off'} | {'yes' if s['default'] else 'no'} |"
                     f" {'yes' if s['id'] in in_profile else 'no'} | {'GPU' if s['gpu'] else '-'} | {s['blurb']}")
    if status.get("ghost_count"):
        lines.append(f"Ghosts (expected detector missing): {json.dumps(status['ghosts'])[:600]}")
    lines.append("Note: hourly health alerts use 'default(yaml)'; boot uses 'in boot profile'."
                 " A service that is default but not in the profile raises 'not running (default service)'.")
    return "\n".join(lines)


def health(args: dict) -> str:
    refresh = bool(args.get("refresh"))
    cache = core.CACHE / "health.json"
    data = core.load_json(cache)
    age = core.now() - cache.stat().st_mtime if cache.exists() else None
    if refresh or data is None or (age is not None and age > 1800):
        core.CACHE.mkdir(parents=True, exist_ok=True)
        rc, out = run([str(core.CONTROL_PY), str(core.STATUS_PY), "health"], timeout=420,
                      cwd=str(core.CONTROL))
        try:
            data = json.loads(out[out.index("{"):])
        except Exception:
            return f"Health check failed to run (rc {rc}): {out[:400]}"
        cache.write_text(json.dumps(data))
        age = 0
    lines = [f"Health (Homelab Control checks, {human_age(age)} old): {data['checked']} checked,"
             f" {data['failed']} failing. This is a read-only run; it sends no Alert message."]
    for r in data["results"]:
        if not r["ok"]:
            lines.append(f"FAIL {r['kind']} {r['id']} ({r['name']}): {'; '.join(r['problems'])}")
    lines.append("OK: " + ", ".join(r["id"] for r in data["results"] if r["ok"]))
    lines.append("Slow: the restic check can take up to 5 minutes; results are cached for 30 minutes.")
    return "\n".join(lines)


def incidents(args: dict) -> str:
    hours = _arg_int(args, "hours", 24, 1, 24 * 90)
    source = _arg_str(args, "source", "", 60)
    total, rows = _incidents(hours, source)
    if not total:
        return f"No incidents in the last {hours} h" + (f" for '{source}'" if source else "") + \
               f" (log: {core.INCIDENTS_LOG})."
    lines = [f"{total} incident lines in the last {hours} h (grouped; the log repeats hourly):"]
    for n, (src, sev, summary), first, last in rows:
        lines.append(f"x{n} [{sev}] {src}: {summary} (first {first[:16]}, last {last[:16]})")
    return "\n".join(lines)


def containers(args: dict) -> str:
    name = _arg_str(args, "name", "", 120)
    log_lines = _arg_int(args, "log_lines", 0, 0, 100)
    if not name:
        rc, out = run(["docker", "ps", "-a", "--format",
                       "{{.Names}}\t{{.Status}}\t{{.Label \"com.docker.compose.project\"}}"], timeout=20)
        rows = sorted(out.splitlines())
        bad = [r for r in rows if "unhealthy" in r or "Exited" in r or "Restarting" in r]
        return (f"{len(rows)} containers (name, status, compose project):\n" + "\n".join(rows) +
                ("\n\nNeeds attention:\n" + "\n".join(bad) if bad else ""))
    rc, names = run(["docker", "ps", "-a", "--format", "{{.Names}}"], timeout=20)
    if name not in names.split():
        return f"No container named '{name}'. Use containers without a name to list them."
    fmt = ("status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"
           " restart_policy={{.HostConfig.RestartPolicy.Name}} restarts={{.RestartCount}}"
           " started={{.State.StartedAt}} project={{index .Config.Labels \"com.docker.compose.project\"}}"
           " workdir={{index .Config.Labels \"com.docker.compose.project.working_dir\"}}"
           " image={{.Config.Image}}")
    rc, info = run(["docker", "inspect", "--format", fmt, name], timeout=20)
    lines = [f"{name}: {info}"]
    rc, hc = run(["docker", "inspect", "--format",
                  "{{if .State.Health}}{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}|{{end}}{{end}}", name],
                 timeout=20)
    if hc.strip():
        last = [h for h in hc.split("|") if h.strip()][-2:]
        lines.append("Last health-check results: " + " || ".join(x.strip()[:300] for x in last))
    rc, ports = run(["docker", "port", name], timeout=10)
    if ports:
        lines.append("Ports: " + ports.replace("\n", "; "))
    if log_lines:
        rc, logs = run(["docker", "logs", "--tail", str(log_lines), name], timeout=30)
        lines.append(f"Last {log_lines} log lines:\n{logs}")
    return "\n".join(lines)


def schedules(args: dict) -> str:
    rc, cron = run(["crontab", "-l"], timeout=10)
    rc, units = run(["systemctl", "--user", "list-units", "--type=service", "--state=running", "--no-legend",
                     "--plain"], timeout=10)
    rc, timers = run(["systemctl", "--user", "list-timers", "--no-legend", "--plain"], timeout=10)
    sys_lines = []
    for unit in ("ollama", "docker", "zram", "hd-idle", "mesh-vpnd"):
        rc, state = run(["systemctl", "is-active", unit], timeout=5)
        sys_lines.append(f"{unit}: {state.strip()}")
    return ("User crontab (the only scheduler for Homelab jobs; DUM-E itself is never scheduled):\n" + cron +
            "\n\nUser systemd services running:\n" + units +
            "\n\nUser timers:\n" + (timers or "none") +
            "\n\nSystem units:\n" + "\n".join(sys_lines))


_KNOWN_PORTS = {
    "22": "ssh", "2283": "Immich (fortress-immich-server)", "3010": "AFFiNE", "3030": "Grafana",
    "3100": "Loki", "5678": "n8n", "6333": "Qdrant (rag-agent, when on)", "8000": "Portainer edge",
    "8001": "Alert notifier (container port 8000)", "8077": "Personal Feed API (uvicorn)",
    "7460": "ODA preview server (oda-preview.service)", "8081": "AI brain llama-server",
    "8181": "Model queue (fortress-modelq.service)", "8190": "Agent gateway (fortress-agent-gateway.service)",
    "8082": "Plane proxy http", "8098": "Virtual Self searxng",
    "8099": "Virtual Self knowledge gateway", "8100": "ChromaDB (n8n stack)", "8443": "Plane proxy https",
    "8800": "Jarvis gateway (Mesh VPN (e.g. Tailscale) IP only, when on)", "9010": "Portainer", "9090": "Prometheus",
    "9100": "node-exporter", "9122": "vault-backup exporter", "9400": "dcgm-exporter (when on)",
    "9443": "Portainer https", "11434": "Ollama", "39081": "LifePath API (when on)",
    "39082": "Vitalis (when on)", "6544": "Music service (when on)",
    "18765": "Kindle dashboard PNG server (kindle-dash.service)",
}


def ports(args: dict) -> str:
    rc, out = run(["ss", "-ltnH"], timeout=10)
    seen = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        port = local.rsplit(":", 1)[-1]
        addr = local.rsplit(":", 1)[0]
        seen.setdefault(port, set()).add(addr)
    lines = ["port | bound to | known as"]
    for port in sorted(seen, key=lambda p: int(p) if p.isdigit() else 0):
        addrs = ", ".join(sorted(seen[port]))
        lines.append(f"{port} | {addrs} | {_KNOWN_PORTS.get(port, 'unknown')}")
    lines.append("0.0.0.0 or * means reachable from the LAN (ufw is inactive). Containers reach the host"
                 " model servers through host.docker.internal, so do not rebind 8081/11434 to 127.0.0.1.")
    return "\n".join(lines)


_BIG_LOGS = [core.LLAMA_LOG, core.INCIDENTS_LOG, core.HOME / ".local/state/homelab/health-cron.log",
             core.VAULT_LOGS / "bootstrap-keepalive.log", core.VAULT_LOGS / "bootstrap-photos.log",
             core.VAULT_LOGS / "cron-daily.log", core.HOME / "wget-log"]


def disk_memory(args: dict) -> str:
    rc, df = run(["df", "-h", "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs", "-x", "overlay", "-x", "efivarfs"],
                 timeout=10)
    rc, mem = run(["free", "-h"], timeout=5)
    rc, swap = run(["swapon", "--show"], timeout=5)
    sizes = []
    for path in _BIG_LOGS:
        try:
            sizes.append(f"{path}: {path.stat().st_size / 1e6:.1f} MB")
        except Exception:
            pass
    return ("Filesystems:\n" + df + "\n\nMemory:\n" + mem + "\n\nSwap:\n" + swap +
            "\n\nLarge known log files (DUM-E cannot delete or rotate them; the owner decides):\n" + "\n".join(sizes))


def image_cleanup_preview(args: dict) -> str:
    # Dry run only: the script deletes nothing without --apply, and --apply is reachable only through
    # the owner-approved action docker_image_cleanup_run.
    rc, out = run(["/usr/bin/python3", str(core.CONTROL / "docker-image-cleanup.py")], timeout=90)
    return out if rc == 0 else f"Preview failed (exit {rc}):\n{out}"


LOGS = {
    "image_cleanup": core.HOME / ".local/state/homelab/docker-image-cleanup.log",
    "incidents": core.INCIDENTS_LOG,
    "agent_heal": core.HOME / ".local/state/homelab/agent-heal.log",
    "health_cron": core.HOME / ".local/state/homelab/health-cron.log",
    "boot": core.CONTROL / "boot.log",
    "llama": core.LLAMA_LOG,
    "watchdog": core.WATCHDOG_DIR / "watchdog.log",
    "feed_cron": core.FORTRESS / "personal-feed/out/cron.log",
    "feed_learn": core.FORTRESS / "personal-feed/out/learn.log",
    "feed_api": core.FORTRESS / "personal-feed/out/api.log",
    "feed_llama": core.FORTRESS / "personal-feed/out/llama-server.log",
    "kindle_render": core.HOME / "kindle-dash/render.log",
    "wifi_guard": core.HOME / "wifi-scan-reports/wifi-guard-cron.log",
    "wifi_switch": core.HOME / "wifi-scan-reports/wifi-switch.log",
    "vault_backup": core.VAULT_LOGS / "vault-backup.log",
    "vault_cron_daily": core.VAULT_LOGS / "cron-daily.log",
    "vault_bootstrap": core.VAULT_LOGS / "bootstrap-keepalive.log",
    "vault_bootstrap_photos": core.VAULT_LOGS / "bootstrap-photos.log",
    "restic_forget": core.VAULT_LOGS / "restic-forget.log",
    "dume_audit": core.AUDIT_LOG,
}


def log_tail(args: dict) -> str:
    name = _arg_str(args, "log", "", 40)
    lines = _arg_int(args, "lines", 40, 1, 200)
    contains = _arg_str(args, "contains", "", 80) or None
    if name not in LOGS:
        return "Unknown log. Registered logs: " + ", ".join(f"{k} ({v})" for k, v in LOGS.items())
    path = LOGS[name]
    if core.is_protected(path):
        return f"Refused: {path} is a protected path."
    if not path.exists():
        return f"{path} does not exist."
    size = path.stat().st_size
    age = human_age(core.now() - path.stat().st_mtime)
    body = core.tail_file(path, lines, contains)
    return f"{path} ({size / 1e6:.1f} MB, modified {age} ago), last {lines} lines" + \
        (f" containing '{contains}'" if contains else "") + f":\n{body or '(no matching lines)'}"


def backup(args: dict) -> str:
    # Deliberately NOT `vault-backup status`: it calls restic_ensure_repo, which can run `restic init`
    # on some errors (vault-backup/lib/restic.sh:91-110), so it is not read-only.
    lines = ["Off-site backup (vault-backup, restic -> Google Drive). Read from logs and incidents only."]
    lock = core.VAULT_LOGS.parent / "run.lock"
    rc, holders = run(["fuser", str(lock)], timeout=10)
    pids = re.findall(r"\b(\d+)\b", holders.replace(str(lock), ""))
    lines.append(f"run.lock {lock}: " + (f"held by PID(s) {', '.join(pids)} (a backup is running;"
                                          " cron-daily skips while it is held)" if rc == 0 and pids
                                          else "not held (or not visible to this user)"))
    vlog = core.VAULT_LOGS / "vault-backup.log"
    if vlog.exists():
        lines.append("Last lines of vault-backup.log:\n  " + core.tail_file(vlog, 12).replace("\n", "\n  "))
    try:
        logs = sorted(core.VAULT_LOGS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
        lines.append("Newest logs in /mnt/backup-volume/vault-backup/logs:")
        for p in logs:
            st = p.stat()
            lines.append(f"  {p.name}: {st.st_size / 1e6:.1f} MB, modified {human_age(core.now() - st.st_mtime)} ago")
    except Exception as exc:
        lines.append(f"Log folder not readable: {exc} (is /mnt/backup-volume mounted?)")
    total, rows = _incidents(24 * 7, "vault")
    lines.append(f"Backup incidents in the last 7 days: {total}")
    for n, (src, sev, summary), first, last in rows[:8]:
        lines.append(f"  x{n} {src}: {summary} (last {last[:16]})")
    rc, cron = run(["crontab", "-l"], timeout=10)
    lines.append("Schedule:\n  " + "\n  ".join(l for l in cron.splitlines() if "vault-backup" in l))
    lines.append("Retention on every run: restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune"
                 " (permanent deletion of older snapshots).")
    return "\n".join(lines)


def shell_index(args: dict) -> str:
    query = _arg_str(args, "query", "", 60).lower()
    bashrc = core.HOME / ".bashrc"
    entries = []
    comments: list[str] = []
    in_function = False
    text = bashrc.read_text(errors="replace")
    # Header blocks describe several functions at once: "# powersaver-lite  — CPU powersave + ..."
    described = {m.group(1): m.group(2).strip()
                 for m in re.finditer(r"(?m)^#\s*([\w-]+)\s+—\s*(.+)$", text)}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("#"):
            if not in_function:
                comments.append(line.lstrip("# ").strip())
            continue
        m = re.match(r"^alias\s+([\w.-]+)=(['\"])(.*)\2\s*(?:#\s*(.*))?$", line)
        f = re.match(r"^([\w-]+)\s*\(\)\s*\{(.*)$", line)
        if m:
            entries.append(("alias", m.group(1), number, m.group(4) or "", m.group(3)))
        elif f:
            name = f.group(1)
            # Prefer a comment line that describes this exact function ("# powersaver  — ...").
            own = [c for c in comments if re.match(rf"^{re.escape(name)}(\s|$)", c)]
            note = described.get(name) or (own[-1] if own else (comments[-1] if comments else ""))
            entries.append(("function", name, number, note, f.group(2).strip()))
            in_function = not f.group(2).strip().endswith("}")
        if raw.startswith("}"):
            in_function = False
        if line and not in_function:
            comments = []
    rows = []
    for kind, name, number, comment, body in entries:
        text = f"{kind} {name} (.bashrc:{number}): {comment} -> {body}"
        if query and query not in text.lower():
            continue
        rows.append(core.redact(text)[:400])
    head = (f"{len(rows)} of {len(entries)} aliases/functions" + (f" matching '{query}'" if query else "") +
            ". Exports and secret lines are never shown. Aliases do not exist in DUM-E's tools;"
            " DUM-E calls the underlying scripts.\n")
    return head + "\n".join(rows)


TOOLS = {
    "snapshot": snapshot,
    "gpu": gpu,
    "ai_brain": ai_brain,
    "services": services,
    "health": health,
    "incidents": incidents,
    "containers": containers,
    "schedules": schedules,
    "ports": ports,
    "disk_memory": disk_memory,
    "image_cleanup_preview": image_cleanup_preview,
    "log_tail": log_tail,
    "backup": backup,
    "shell_index": shell_index,
}
