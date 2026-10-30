# DUM-E

**DUM-E** is a local, tool-restricted maintenance assistant for a personal homelab. It runs a small agent (built on [pi](https://github.com/mariozechner/pi)) that can **read** machine state and homelab documentation, **explain** what is going on, and **propose** maintenance actions. It never executes destructive or state-changing work on its own.

## What it is

- A **read-only observability layer**: GPU, disks, services, containers, schedules, logs, backups, and a structured knowledge base (manuals + runbooks).
- A **proposal gate**: state changes go through `propose_action` → owner runs `dume approve <ID>` in a separate terminal with explicit confirmation (including typed phrases for permanent deletes).
- A **dedicated low-privilege runtime user** (`dume`) so the model is not the same UNIX user as the operator.

Bundled `knowledge/` content describes a **generic homelab layout** (`~/homelab/…`). You are expected to adapt paths, service names, and manuals to your environment.

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

- **`bin/dume`**: owner CLI (chat, doctor, approve/reject, manual search).
- **`bin/dume-tool`**: gateway; the only entry point the agent user may invoke via sudo.
- **`lib/dume/`**: core paths, redaction, tools, action catalog, graph builder.
- **`config/actions.json`**: allowlisted approvable actions (Deletion Mandate: every action declares what it deletes).
- **`prompts/system.md`**: agent system prompt.
- **`ext/dume.ts`**: pi extension exposing only DUM-E tools.

Environment overrides (optional): `HOMELAB_ROOT`, `DUME_ROOT`, `DUME_HOME`, `DUME_OWNER`, `DUME_MODEL`.

## Safety model

1. **Separate user**: install creates system user `dume` with no login shell; agent sessions live under `/var/lib/dume`.
2. **Single sudo rule**: `dume` may run only `bin/dume-tool` as the homelab owner—nothing else.
3. **No shell for the model**: pi built-in tools are disabled; only registered DUM-E tools are available.
4. **Path guard + redaction**: protected paths (secrets, `.env`, SSH, backup credentials) are blocked; tool output is scanned for tokens/passwords.
5. **Human approval**: proposals expire after 30 minutes; permanent deletes require an extra typed phrase (e.g. `PRUNE`).
6. **Knowledge edits**: owner-directed only; proposals show a diff before apply.

See `knowledge/manuals/09-security-and-boundaries.md` and `knowledge/manuals/11-dume.md` for the full model.

## Install

**Requirements**: Linux, Node ≥ 20, global `@mariozechner/pi-coding-agent`, passwordless sudo for install steps, a local OpenAI-compatible model endpoint (default config points at `http://127.0.0.1:8181/v1`).

```bash
git clone https://github.com/Vector26/DUM-E.git ~/homelab/DUM-E
cd ~/homelab/DUM-E
bash install.sh
```

`install.sh` creates `/opt/dume`, `/etc/sudoers.d/dume`, symlinks `~/bin/dume`, and runs smoke tests. Customize model id and paths before or after install via environment variables and `config/actions.json`.

**Uninstall**: `bash uninstall.sh` (keeps the repo and knowledge; optional history purge).

## Development

```bash
cd tests && python3 -m pytest   # when present
dume doctor                     # deterministic health scan
dume rebuild-graph              # refresh knowledge/graph.json from ~/homelab/control/*.yaml
```

Long-form design notes: [DUM-E.md](./DUM-E.md) (historical plan; homelab-specific examples are illustrative).

## License

MIT — see [LICENSE](./LICENSE).
