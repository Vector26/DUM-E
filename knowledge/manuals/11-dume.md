---
title: DUM-E itself
scope: How DUM-E works, how the owner uses it, its tools and actions, approvals, learning, files, install and removal
last_verified: 2026-10-29
sources: ~/homelab/DUM-E/{bin,lib,config,ext,prompts,install.sh}, DUM-E.md
---

# DUM-E itself

## What it is
DUM-E is the homelab maintenance assistant. It is the local AI brain (manual 02) running inside the pi agent (manual 12) with every built-in pi tool switched off and only DUM-E's own tools switched on. It reads the machine, explains, and proposes. It never acts on its own and never runs unless the owner starts it [V].

## How the owner refers to it
"DUM-E", "dume", "the maintenance bot".

## Components
- Owner command: `dume` (`~/bin/dume` -> `~/homelab/DUM-E/bin/dume`) [V].
- Gateway: `~/homelab/DUM-E/bin/dume-tool` + Python package `~/homelab/DUM-E/lib/dume/` (core, tools, actions, knowledge, graph) [V].
- Action catalog: `~/homelab/DUM-E/config/actions.json` [V].
- Agent runtime (root-owned): `/opt/dume/node/bin/node` (Node v20.20.0 copy), `/opt/dume/pi/` (pi 0.67.1 copy), `/opt/dume/ext/dume.ts` (the extension) [V after install].
- Agent user `dume`, home `/var/lib/dume` (pi settings, provider config, sessions) [V after install].
- System prompt: `~/homelab/DUM-E/prompts/system.md` (passed at launch) [V].

Tools (all read-only) [V]: snapshot, gpu, ai_brain, services, health, incidents, containers, schedules, ports, disk_memory, log_tail, backup, shell_index, manual, graph, action_status.
Proposal tools: propose_action, propose_knowledge_edit.

Actions DUM-E can propose (src: config/actions.json) [V]:
| Action | Does | Deletes | Approval |
|---|---|---|---|
| llama_start | start the AI brain | nothing | y |
| llama_stop | stop the AI brain | its pid file | y (named) |
| llama_restart | restart the AI brain | its pid file | y (named) |
| ollama_unload | unload Ollama models from VRAM | nothing | y |
| service_start <id> | `fortress start <id>` (not ai_llama, vram_watchdog, immich, mediastack) | nothing | y |
| service_stop <id> | `fortress stop <id>` (not ai_llama, vram_watchdog, orchestration, notifier, monitoring) | nothing | y |
| watchdog_restart | restart the VRAM watchdog | nothing | y |
| watchdog_clear_pause | remove the pause flag and start the AI | the pause flag | y (named) |
| backup_run_daily | `vault-backup run daily` | old restic snapshots (retention, PERMANENT) | type PRUNE |

## Files and data
- `~/homelab/DUM-E/knowledge/` - manuals, runbooks, glossary, graph, `.history/` (old versions).
- `~/homelab/DUM-E/state/` (owner-only, mode 700): `audit.log`, `pending/` (proposals waiting), `results/` (finished proposals and their output), `cache/health.json`.
- `/var/lib/dume/sessions/` - conversation history (readable only by the `dume` user and root).

## Commands
Owner (`dume help` prints this) [V]:
- `dume` - talk to DUM-E. `dume -c` continues the last conversation. Extra pi flags pass through.
- `dume ask "question"` - one question and answer.
- `dume status` - machine overview without the AI.
- `dume doctor` - known-problem scan without the AI; names the runbook for each finding.
- `dume pending`, `dume show <ID>`, `dume approve <ID>`, `dume reject <ID>`.
- `dume manual [name [section]]`, `dume search <words>`.
- `dume tool <name> [json]` - run one read-only tool yourself.
- `dume rebuild-graph`, `dume audit [N]`.

How a change happens [V]:
1. The owner asks DUM-E for something that changes state.
2. DUM-E calls `propose_action`; nothing runs; it gets an ID like `4ED19A`.
3. The owner runs `dume approve 4ED19A` in a separate terminal (or after leaving the chat). The screen shows the action, the exact commands, and every deletion. The owner types `y` (or `PRUNE` for permanent deletions).
4. It runs in the owner's terminal; the result is saved; DUM-E can read it with `action_status`.
5. Proposals expire after 30 minutes. An approved, rejected or expired proposal cannot be reused.

How learning works (owner-directed only) [V]:
1. The owner says "improve/correct/remember ... in <part>".
2. DUM-E proposes a change to exactly ONE section of ONE knowledge file (`propose_knowledge_edit`): replace_section, add_section, or glossary_add.
3. The owner sees the diff with `dume approve <ID>` and types `y`. The old file is saved in `knowledge/.history/`.
4. The edit is refused if the file changed since the proposal, if the text looks like it contains a secret, or if it tries to add headings that would spill into other sections.

## Depends on
- The AI brain on :8081 for conversation (status/doctor/manual/search work without it).
- sudo rule `/etc/sudoers.d/dume`.

## How to check it (read-only)
- `dume doctor`, `dume audit`, `log_tail log=dume_audit`.

## Known problems and fixes
- "DUM-E is not installed yet" -> run `bash ~/homelab/DUM-E/install.sh`.
- "The AI brain (:8081) is not answering" -> `dume` offers to start it; or see runbook:ai-down.
- Chat fails with "connection refused" while the brain is fine -> the model queue (:8181) is down. DUM-E's provider talks to :8181, not :8081. `dume` now restarts it on launch; see runbook:model-queue-down. (Found 2026-10-30.)
- Chat ends with "terminated" right after launch, with the queue up -> the queue's streaming path was broken (`RuntimeError: Cannot send a request, as the client has been closed.` in the modelq journal). Fixed 2026-10-30 in `modelq/modelq/app.py`; `agent-heal` now probes a streamed completion every 10 minutes. See runbook:dume-trouble. [V]
- `dume doctor` also runs `agent-heal --check --json` (read-only) and lists its findings with the right runbook. [V]
- Gateway errors in chat -> runbook:dume-trouble.

## Logs
- `~/homelab/DUM-E/state/audit.log` (every tool call, proposal, approval, result).

## Rules for DUM-E here
- DUM-E is never scheduled and never runs in the background.
- DUM-E does not edit its own code, config, prompt or catalog.

## Open questions
None.
