<div align="center">

# DUM-E

**A read-only homelab copilot — observe, explain, propose. Never execute alone.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pi Agent](https://img.shields.io/badge/Built_on-pi-111?style=flat-square)](https://github.com/mariozechner/pi)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-lightgrey?style=flat-square)](https://kernel.org/)

</div>

---

## Why it exists

Homelabs are powerful and fragile: GPUs, containers, backups, and schedules fail in ways that are hard to explain at 2 a.m. **DUM-E** is a **local, tool-restricted maintenance assistant** that reads machine state and your documentation, explains what is going on, and **proposes** fixes — while **destructive or state-changing work always waits for explicit human approval** in a separate terminal.

## Features

| | |
|---|---|
| **Read-only observability** | GPU, disks, services, containers, schedules, logs, backups |
| **Structured knowledge** | Manuals, runbooks, and a navigable graph under `knowledge/` |
| **Proposal gate** | `propose_action` → owner runs `dume approve <ID>` with confirmation |
| **Low-privilege runtime** | Dedicated `dume` system user — not your daily login |
| **Path guard & redaction** | Secrets, `.env`, SSH, and backup creds blocked from tools |
| **Deletion Mandate** | Every approvable action in `config/actions.json` declares what it deletes |

## Architecture

```
Owner terminal                    Agent user (dume)
─────────────                    ─────────────────
dume  ──sudo──► pi + DUM-E ext ──sudo──► dume-tool (gateway)
                      │                         │
                      │                         ├── tools.py (read-only probes)
                      │                         ├── knowledge/ (manuals, runbooks, graph)
                      │                         └── actions.py (proposals only)
dume approve <ID>  ──► runs approved command as owner
```

| Component | Role |
|-----------|------|
| `bin/dume` | Owner CLI — chat, doctor, approve/reject, manual search |
| `bin/dume-tool` | Gateway; sole sudo entry for the agent user |
| `lib/dume/` | Paths, redaction, tools, action catalog, graph builder |
| `config/actions.json` | Allowlisted approvable actions |
| `ext/dume.ts` | pi extension exposing only DUM-E tools |

Optional env: `HOMELAB_ROOT`, `DUME_ROOT`, `DUME_HOME`, `DUME_OWNER`, `DUME_MODEL`.

Bundled `knowledge/` describes a **generic homelab layout** (`~/homelab/…`). Adapt paths, service names, and manuals to your environment.

## Quick start

**Requirements:** Linux, Node ≥ 20, global `@mariozechner/pi-coding-agent`, passwordless sudo for install steps, local OpenAI-compatible endpoint (default `http://127.0.0.1:8181/v1`).

```bash
git clone https://github.com/Vector26/DUM-E.git ~/homelab/DUM-E
cd ~/homelab/DUM-E
bash install.sh
```

`install.sh` creates `/opt/dume`, `/etc/sudoers.d/dume`, symlinks `~/bin/dume`, and runs smoke tests. Customize model id and paths via environment variables and `config/actions.json`.

**Uninstall:** `bash uninstall.sh` (keeps repo and knowledge; optional history purge).

```bash
dume doctor          # deterministic health scan
dume rebuild-graph   # refresh knowledge/graph.json from ~/homelab/control/*.yaml
```

## Safety model

1. **Separate user** — `dume` has no login shell; sessions live under `/var/lib/dume`.
2. **Single sudo rule** — only `bin/dume-tool` as the homelab owner.
3. **No shell for the model** — pi built-ins disabled; only registered DUM-E tools.
4. **Human approval** — proposals expire after 30 minutes; permanent deletes need a typed phrase (e.g. `PRUNE`).
5. **Knowledge edits** — owner-directed; proposals show a diff before apply.

Details: `knowledge/manuals/09-security-and-boundaries.md`, `knowledge/manuals/11-dume.md`.

> **What makes it different**
>
> Most “AI ops” demos give the model a shell. DUM-E inverts that: **read everything, change nothing without a second human in the loop** — with a dedicated UNIX user, allowlisted actions, and redaction baked in.

## Status

| Area | State |
|------|--------|
| Install / doctor | Production-oriented for personal homelabs |
| Knowledge base | Generic templates — you customize to your stack |
| Tests | `cd tests && python3 -m pytest` when present |
| Design notes | [DUM-E.md](./DUM-E.md) (historical plan; examples illustrative) |

---

<div align="center">

**MIT** — see [LICENSE](./LICENSE)

Built by **[Vector26](https://github.com/Vector26)** · Safety-first homelab AI

</div>
