"""DUM-E core: paths, limits, redaction, path guard, audit log and a safe subprocess runner.

Everything here runs as the homelab owner, either from the owner's `dume` command or
from `dume-tool`, which the `dume` user may call only through one sudoers rule.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

OWNER = os.environ.get("DUME_OWNER", getpass.getuser())
AGENT_USER = "dume"
HOME = Path(os.environ.get("DUME_HOME", str(Path.home()))).expanduser()
HOMELAB = Path(os.environ.get("HOMELAB_ROOT", str(HOME / "homelab"))).expanduser()
ROOT = Path(os.environ.get("DUME_ROOT", str(HOMELAB / "DUM-E"))).expanduser()
CONFIG = ROOT / "config"
KNOWLEDGE = ROOT / "knowledge"
MANUALS = KNOWLEDGE / "manuals"
RUNBOOKS = KNOWLEDGE / "runbooks"
GLOSSARY = KNOWLEDGE / "glossary.md"
GRAPH_JSON = KNOWLEDGE / "graph.json"
HISTORY = KNOWLEDGE / ".history"
STATE = ROOT / "state"
PENDING = STATE / "pending"
RESULTS = STATE / "results"
CACHE = STATE / "cache"
AUDIT_LOG = STATE / "audit.log"

FORTRESS = HOMELAB
CONTROL = FORTRESS / "control"
LIBRARY = FORTRESS / "library"
CONTROL_PY = CONTROL / ".venv" / "bin" / "python"
STATUS_PY = CONTROL / "status.py"
FORTRESS_CLI = CONTROL / "fortress"
LLAMA_CTL = HOME / "bin" / "llama-server-ctl"
LLAMA_PIDFILE = HOME / ".local/state/llama-server-ctl.pid"
LLAMA_LOG = HOME / ".local/state/llama-server-ctl.log"
LLAMA_URL = "http://127.0.0.1:8081"
OLLAMA_URL = "http://127.0.0.1:11434"
WATCHDOG_SCRIPT = CONTROL / "vram-watchdog.sh"
WATCHDOG_DIR = HOME / ".local/state/homelab-vram-watchdog"
INCIDENTS_LOG = HOME / ".local/state/homelab/incidents.log"
VAULT_LOGS = Path("/mnt/backup-volume/vault-backup/logs")

MAX_OUTPUT = 12000  # characters returned to the model per tool call
PENDING_TTL_S = 30 * 60  # a proposal must be approved within 30 minutes


def _xdg_runtime_dir() -> str:
    run = Path(f"/run/user/{os.getuid()}")
    return str(run) if run.is_dir() else ""


SAFE_ENV = {
    "PATH": f"{HOME / 'bin'}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": str(HOME),
    "USER": OWNER,
    "LOGNAME": OWNER,
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    **({"XDG_RUNTIME_DIR": _xdg_runtime_dir()} if _xdg_runtime_dir() else {}),
}

# ---------------------------------------------------------------- redaction

_SECRET_WORDS = (
    r"token|secret|passw(?:or)?d|passwd|pwd|api[_-]?key|apikey|bearer|authorization|"
    r"private[_-]?key|access[_-]?key|client[_-]?secret|auth[_-]?key|cookie|session[_-]?id"
)
_REDACTIONS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "<redacted private key>"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 <redacted>"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:" + _SECRET_WORDS + r")[A-Z0-9_]*)([\"']?\s*[:=]\s*)([\"']?)"
                r"(?!(?:bearer|basic) <redacted>)[^\s\"',;}{]+"),
     r"\1\2\3<redacted>"),
    (re.compile(r"\bhf_[A-Za-z0-9]{20,}"), "<redacted>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "<redacted>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "<redacted>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "<redacted>"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "<redacted>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted>"),
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "<redacted>"),  # Telegram bot token
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "<redacted jwt>"),
    (re.compile(r"(://)[^/\s:@]+:[^/\s@]+@"), r"\1<redacted>@"),
]


def redact(text: str) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def cap(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... truncated {len(text) - limit} characters; ask for a narrower view ...]"


# ---------------------------------------------------------------- path guard

_PROTECTED_PREFIXES = [
    HOME / ".ssh", HOME / ".gnupg", HOME / ".aws", HOME / ".git-credentials", HOME / "gitToken",
    HOME / ".bash_history", HOME / ".python_history", HOME / ".lesshst",
    HOME / ".claude", HOME / ".claude.json", HOME / ".pi" / "agent" / "auth.json",
    HOME / ".openclaw", HOME / ".codex", HOME / ".gemini", HOME / ".cursor", HOME / ".cursor-server",
    HOME / ".pyicloud", HOME / ".spotiflac", HOME / ".docker",
    HOME / ".config" / "vault-backup", HOME / ".config" / "rclone", HOME / ".config" / "wifi-switch.conf",
    FORTRESS / "HumanReadableData", FORTRESS / "People-research", FORTRESS / "life-archive-data",
    FORTRESS / "vitalis", FORTRESS / "pi-cyber", FORTRESS / "nextplan.md",
    FORTRESS / "VIRTUAL_SELF_ARCHITECTURE_PLAN.md",
    FORTRESS / "extensions",  # syncer files hold plaintext Spotify/Navidrome credentials
    HOME / "mediastack" / "secrets",
    Path("/mnt/photos"), Path("/mnt/backup-volume/vault-backup"),
    STATE / "pending", STATE / "results",
]
_PROTECTED_GLOBS = ["NOTION-DATA*", "notion_html_export*"]  # directly under homelab/
_PROTECTED_NAMES = re.compile(
    r"(?i)^(\.env(\..*)?|.*\.env|.*\.key|.*\.pem|.*\.p12|id_[a-z0-9]+|auth\.json|credentials.*|access_info.*)$"
)
# Explicit exceptions inside protected trees (read-only use by registered tools).
_EXCEPTIONS = [VAULT_LOGS]


def is_protected(path: str | os.PathLike) -> bool:
    """True if DUM-E must not read this path. Resolves symlinks first."""
    try:
        real = Path(os.path.realpath(path))
    except Exception:
        return True
    name = real.name
    if _PROTECTED_NAMES.match(name) and not name.endswith(".example"):
        return True
    for exc in _EXCEPTIONS:
        if real == exc or exc in real.parents:
            return False
    for prefix in _PROTECTED_PREFIXES:
        if real == prefix or prefix in real.parents:
            return True
    for pattern in _PROTECTED_GLOBS:
        for match in FORTRESS.glob(pattern):
            m = Path(os.path.realpath(match))
            if real == m or m in real.parents:
                return True
    return False


def inside(path: str | os.PathLike, root: Path) -> bool:
    real = Path(os.path.realpath(path))
    root = Path(os.path.realpath(root))
    return real == root or root in real.parents


# ---------------------------------------------------------------- audit

def caller() -> str:
    """Who asked: 'dume' when called through sudo by the agent user, else the login user."""
    return os.environ.get("SUDO_USER") or os.environ.get("USER") or str(os.getuid())


def audit(event: str, **fields) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
             "caller": caller(), "event": event}
    for key, value in fields.items():
        text = value if isinstance(value, str) else json.dumps(value, default=str)
        entry[key] = redact(text)[:2000]
    fd = os.open(AUDIT_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------- subprocess

def run(argv: list[str], timeout: float = 30, stdin_text: str | None = None,
        cwd: str | None = None) -> tuple[int, str]:
    """Run a fixed argv (never through a shell). Returns (exit code, stdout+stderr)."""
    try:
        proc = subprocess.run(
            argv, input=stdin_text, capture_output=True, text=True, timeout=timeout,
            env=SAFE_ENV, cwd=cwd or str(HOME),
            stdin=None if stdin_text is not None else subprocess.DEVNULL,
        )
        out = proc.stdout + (("\n" + proc.stderr) if proc.stderr.strip() else "")
        return proc.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s: {' '.join(argv)}"
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read(200_000).decode(errors="replace")
    except Exception as exc:  # connection refused, timeout, HTTP error
        code = getattr(exc, "code", 0)
        return code, str(exc)


def tail_file(path: Path, lines: int = 50, contains: str | None = None,
              scan_bytes: int = 8 * 1024 * 1024) -> str:
    """Last `lines` lines of a possibly huge file, optionally only lines containing `contains`."""
    size = path.stat().st_size
    start = max(0, size - scan_bytes)
    with open(path, "rb") as fh:
        fh.seek(start)
        data = fh.read().decode(errors="replace")
    rows = data.splitlines()
    if start > 0 and rows:
        rows = rows[1:]  # first line is probably partial
    if contains:
        needle = contains.lower()
        rows = [r for r in rows if needle in r.lower()]
    return "\n".join(rows[-lines:])


def human_age(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 120:
        return f"{seconds}s"
    if seconds < 7200:
        return f"{seconds // 60} min"
    if seconds < 172800:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds / 86400:.1f} days"


def now() -> float:
    return time.time()


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default
