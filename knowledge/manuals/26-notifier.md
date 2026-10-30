---
title: Alert notifier (telemon) and the incident log
scope: The notifier container and its HTTP API, the Telegram bot inside it, who calls it, the stale port in the docs, and control/lib/fc_incident.sh (incident log, dedupe, cooldown).
last_verified: 2026-10-29
sources: homelab/notifier/{docker-compose.yml,.env.example}, homelab/notifier/telemon/{Dockerfile,.env.example,config.yaml.example,requirements-api.txt,deploy/telemon.service,telemon/api.py,telemon/main.py,telemon/config.py,telemon/notifiers/telegram.py,telemon/vself_client.py}, homelab/library/04-notifier/*, homelab/library/00-meta/fortress-repository-root/AGENT_INTEGRATION.md, homelab/control/lib/fc_incident.sh, homelab/control/services.yaml, ~/.local/state/homelab/{incidents.log,notify_dedupe.tsv,health-cron.log}, docker ps, docker inspect --format, docker logs --tail/--since (filtered), curl localhost:8000/health, curl localhost:8001/health, ss -ltnp
---

# Alert notifier (telemon) and the incident log

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
The notifier is a small web service that forwards messages to the owner's Telegram chat. Other scripts send it a POST request; it sends the text through a Telegram bot. [V] (src: homelab/notifier/telemon/telemon/api.py:38-56)
It listens on host port 8001. Host port 8000 is Portainer, not the notifier. [V] (src: homelab/notifier/docker-compose.yml:10-11; cmd: curl -s localhost:8001/health; curl -s localhost:8000/health)
The same container also runs a Telegram bot that accepts a few commands from the owner, including approving Virtual Self proposals. [V] (src: telemon/notifiers/telegram.py:297-315; telemon/main.py:15-40)
Homelab Control, vault-backup and other scripts first write problems to a local incident log, then notify through this service, with a 6-hour repeat block. That logic lives in `control/lib/fc_incident.sh`. [V] (src: homelab/control/lib/fc_incident.sh:1-12)

## How the owner refers to it
- "Alert notifier", "Alert notifications", "phone alerts", "notifier", "telemon". Homelab Control id `notifier`. [V] (src: homelab/control/services.yaml:34-41; homelab/control/lib/fc_incident.sh:39)
- "incidents", "incident log", "health alerts". [V] (src: homelab/control/lib/fc_incident.sh:2)

## Components
- Compose file: `~/homelab/notifier/docker-compose.yml`, project `notifier`. [V] (src: docker-compose.yml:1; cmd: docker compose ls)
- Container `notifier-notifier-1`, image `notifier-notifier` built from `notifier/telemon/Dockerfile` (python:3.12-slim; runs `python -m telemon.main`). [V] (cmd: docker ps; src: telemon/Dockerfile:1,26)
- Port: host `0.0.0.0:8001` → container 8000 (`NOTIFIER_PORT=8000`). [V] (src: docker-compose.yml:10-13; cmd: ss -ltnp; docker ps)
- Restart policy `unless-stopped`. Started 2026-10-29 15:36 UTC. [V] (cmd: docker inspect --format)
- Volume `notifier_notifier_logs` → `/app/logs` (8.95 MB). [V] (src: docker-compose.yml:17-18; cmd: docker system df -v)
- Network: only `notifier_default`. It is not on `fortress-network` (those lines are commented out). [V] (src: docker-compose.yml:19-29; cmd: docker inspect --format Networks)
- Environment: `env_file: telemon/.env` (SECRET) plus `NOTIFIER_PORT=8000` and `VSELF_API_URL=http://host.docker.internal:8090`. [V] (src: docker-compose.yml:5-14)
- HTTP API (no authentication): [V] (src: telemon/api.py)
  - `GET /health` → `{"status":"ok"}`. (api.py:32-35)
  - `POST /notify` with JSON `{"message": "...", "source": "..."}` → sends "[source] message" to Telegram; returns `{"ok": true}`; 503 if token or chat id missing; 502 on Telegram error. (api.py:38-56)
  - `POST /notify/file` (multipart: `file`, optional `message`, `source`) → sends a document. (api.py:59-88)
  - `POST /convert/pdf` with `{"markdown": "..."}` → returns a PDF. (api.py:95-122)
- Telegram bot (polling): started when `TELEMON_ENABLE_BOT` is true (default) and `TELEGRAM_USER_ID` is set. The logs show `getUpdates` calls, so the bot is on. [V] (src: telemon/main.py:15-40; cmd: docker logs --tail 200 | grep -c getUpdates) [I] that `TELEGRAM_USER_ID` is set
  - Commands, only from the user id in `TELEGRAM_USER_ID`: `/help`, `/ping`, `/status`, `/temps`, `/reminders`, `/remind_in`, `/remind_at`, `/remind_daily`, `/remind_weekly`, `/remind_delete`, `/approve <id>`, `/reject <id>`, `/edit`. [V] (src: telemon/notifiers/telegram.py:85,297-315)
  - `/approve`, `/reject`, `/edit` call the Virtual Self API at `VSELF_API_URL` with `VSELF_API_TOKEN`. [V] (src: telemon/vself_client.py:13-56)
  - Free-text chat and voice handlers are commented out. [V] (src: telemon/notifiers/telegram.py:303,319)
- Homelab Control: `kind: compose`, `detect_container: notifier-notifier-1`, `default: true`. [V] (src: homelab/control/services.yaml:34-41)
- Not installed: the old systemd unit `deploy/telemon.service` (root, `/opt/telemon`). No `telemon` unit exists. [V] (src: telemon/deploy/telemon.service; cmd: systemctl list-units --all)

### Who sends to the notifier (and which URL they use)
All found by searching code under `homelab/` and `~/bin`. [V] (cmd: grep -rnoE ':800[01]|NOTIFIER_URL')
- `control/lib/fc_incident.sh` → `http://127.0.0.1:8001/notify` (env `FORTRESS_NOTIFIER_URL`). (fc_incident.sh:12)
- `control/vram-watchdog.sh` → `http://localhost:8001/notify`. (vram-watchdog.sh:20)
- vault-backup (through `fc_incident.sh`). (homelab/vault-backup/lib/common.sh:14-16)
- `personal-feed/config.py` → `127.0.0.1:8001/notify`. (config.py:50)
- `affine/scripts/notion_data_import/paths.py` → `127.0.0.1:8001/notify`. (paths.py:66)
- `virtual-self-memory/compose.yaml` → `host.docker.internal:8001/notify`; `src/virtual_self/observability/notify.py` default `127.0.0.1:8001/notify`; `scripts/overnight-run.sh` → `127.0.0.1:8001/notify`. (compose.yaml:19; notify.py:48-49; overnight-run.sh:28)
- `core-orchestration/notify_ceo.sh`, `notify_fortress_alert.sh` → `http://host.docker.internal:8001` (`/notify` and `/notify/file`). (notify_ceo.sh:15,28,46; notify_fortress_alert.sh:25,30)
- `research-digest/research-digest-cli.sh` → `http://127.0.0.1:8001/notify`. (research-digest-cli.sh:7)
- `cine-immich/broll_agent/trigger_full_scan.py` → default `http://notifier:8000`. That name only works on a shared Docker network, and the notifier is not on one, so it needs `NOTIFIER_URL` set. [V] (trigger_full_scan.py:55,85,468) [I] for reachability

### fc_incident.sh (incident log and notification helper)
File: `~/homelab/control/lib/fc_incident.sh`. Sourced by `fortress` (control CLI), vault-backup (`lib/common.sh`), `cron-daily.sh`, `cron-photos.sh`. [V] (src: fc_incident.sh:2; homelab/vault-backup/lib/common.sh:14-16; homelab/vault-backup/scripts/cron-daily.sh:16)
- Loads once per shell (guard `_FC_INCIDENT_SH`). [V] (fc_incident.sh:5-6)
- Settings (each can be overridden by an environment variable of the same name): [V] (fc_incident.sh:8-12)
  - State dir: `${XDG_STATE_HOME:-$HOME/.local/state}/fortress`.
  - `FORTRESS_INCIDENTS_LOG` = `~/.local/state/homelab/incidents.log`.
  - `FORTRESS_NOTIFY_DEDUPE` = `~/.local/state/homelab/notify_dedupe.tsv`.
  - `FORTRESS_NOTIFY_COOLDOWN_SEC` = 21600 (6 hours).
  - `FORTRESS_NOTIFIER_URL` = `http://127.0.0.1:8001/notify`.
- `fc_incident_log source severity summary [detail] [exit_code]` — appends one JSON line `{"ts","source","severity","summary","detail"?,"exit_code"?}`. Time is local ISO (+05:30). [V] (fc_incident.sh:155-166)
- `fc_notify_label source` — friendly prefix, e.g. `vault_offsite` → "Google Drive backup", `ai_llama` → "Local AI", others → "Fortress". [V] (fc_incident.sh:31-54)
- `fc_format_telegram_message` — turns the technical summary into one plain-English line. It never adds paths, log tails or exit codes. [V] (fc_incident.sh:58-153)
- `fc_incident_notify source summary [detail]` — POSTs `{"message","source"}` to the notifier with an 8 s timeout; message cut to 900 characters. [V] (fc_incident.sh:169-181)
- `fc_incident_dedupe_check fingerprint` — true if the same fingerprint was sent less than 6 h ago. [V] (fc_incident.sh:183-193)
- `fc_incident_report source severity summary [detail] [exit_code]` — logs the incident, then notifies unless the fingerprint `source|summary` is inside the cooldown. It records the fingerprint only if the send succeeded. [V] (fc_incident.sh:201-212)
- `fc_incident_notify_progress source summary` — progress message only, no incident line; fingerprint `source|progress|summary`. [V] (fc_incident.sh:215-224)

## Files and data
- `~/homelab/notifier/docker-compose.yml` — the stack. [V]
- `~/homelab/notifier/.env.example` — names `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (empty). Not used by compose. [V]
- `~/homelab/notifier/docs` — symlink to `homelab/library/04-notifier/docs`. [V] (cmd: ls -la)
- `~/homelab/notifier/telemon/` — app source (a git repo). [V]
  - `.env` — SECRET. Mode 664 (readable by any local user). Never open. [V] (cmd: ls -la)
  - `.env.example` — variable names: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `NOTIFIER_PORT`, `TELEMON_ENABLE_BOT`, `TELEGRAM_USER_ID`, `VSELF_API_URL`, `VSELF_API_TOKEN`, `STATE_PATH`, `TELEMON_LLM_BACKEND`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`. [V] (src: telemon/.env.example:1-20)
  - `data/google_token.json` — SECRET (Google OAuth token). Never open. [V] (cmd: ls -la)
  - `data/reminders.json` — PRIVATE (owner's reminders). [V] (cmd: ls -la)
  - `telemon_openrouter_extension/openrouter.env` — SECRET. [V] (cmd: ls -la)
  - `state.json`, `config.yaml` — app state and old monitor config; content not read. [U]
  - `logs/telemon.log*` (2025) — old logs; may contain the bot token (see problem 2). Treat as SECRET. [I]
  - `telemon/api.py`, `main.py`, `config.py`, `notifiers/telegram.py`, `vself_client.py`, `ai_actions.py`, `reminders.py`, `checks/`, `integrations/gcal.py`. [V]
  - `requirements-api.txt` — fastapi, uvicorn, python-telegram-bot, weasyprint, google API client, and others. [V]
- `~/.local/state/homelab/incidents.log` — 863 KB, 5,820 JSON lines, 2026-09-29 12:07 → 2026-10-29 22:01. [V] (cmd: wc -l; head; tail)
- `~/.local/state/homelab/notify_dedupe.tsv` — 450 lines, 33.8 KB; `fingerprint<TAB>epoch`. Only appended, never cleaned. [V] (cmd: wc -l; src: fc_incident.sh:195-199) [I] for never cleaned
- `~/.local/state/homelab/health-cron.log` — 135 KB, output of the hourly `fortress health --notify`. [V]
- Docs: `homelab/library/04-notifier/README.md`, `telemon-README.md`, `telemon-ext-README.md`, `docs/AGENT_INTEGRATION.md`; and `homelab/library/00-meta/fortress-repository-root/AGENT_INTEGRATION.md` (the main notifier API guide). [V]

## Commands
READ:
- `curl -s localhost:8001/health` → `{"status":"ok"}`. [V]
- `docker ps --filter name=notifier` — state and port. [V]
- `docker logs --tail 50 notifier-notifier-1` — never copy it raw; it can contain the bot token. Filter first, for example `| sed -E 's#bot[0-9]+:[A-Za-z0-9_-]+#bot<REDACTED>#g'`. [V]
- `tail -n 20 ~/.local/state/homelab/incidents.log` — latest incidents. [V]
- `tail -n 40 ~/.local/state/homelab/health-cron.log` — latest health runs. [V]

MUTATES (owner only unless noted):
- `curl -X POST localhost:8001/notify -H 'Content-Type: application/json' -d '{"message":"…","source":"…"}'` — sends a real Alert message. MUTATES. DUM-E must not call it during checks. [V] (src: api.py:38-56)
- `POST /notify/file` — sends a file to Telegram. MUTATES. [V]
- `~/homelab/control/fortress health --notify` — runs all checks, writes incidents, may send Telegram. MUTATES. Runs hourly from cron. [V] (cmd: crontab -l; src: homelab/control/fortress:65-95)
- `source homelab/control/lib/fc_incident.sh; fc_incident_report …` — writes to `incidents.log`, may send Telegram, appends to `notify_dedupe.tsv`. MUTATES. [V]
- `fortress start notifier` / `fortress stop notifier` (control CLI, full path) → `docker compose up -d` / `docker compose stop`. DUM-E action `service_start notifier` is allowed with confirmation; `service_stop notifier` is excluded because it carries alerts. MUTATES. [V] (src: homelab/control/lib/actions.sh:38-50; DUM-E.md 15.2)
- Telegram bot commands `/remind_*`, `/approve`, `/reject`, `/edit` — change reminders or Virtual Self proposals. MUTATES. Owner only, from the phone. [V]
- `cd homelab/notifier && docker compose up -d --build` — rebuild after code changes. MUTATES. [I]

DELETES (owner only):
- Telegram `/remind_delete` — deletes a reminder. DELETES. [V] (src: telegram.py:311,679)
- `docker compose down` in `homelab/notifier` — removes the container. DELETES. [I]
- `docker volume rm notifier_notifier_logs` — removes the app logs. DELETES. [I]
- Clearing or rotating `incidents.log` or `notify_dedupe.tsv`. Removing dedupe lines makes old alerts resend. DELETES. [I]

## Depends on
- Internet and DNS to reach `api.telegram.org`. [V] (cmd: docker logs, "Temporary failure in name resolution")
- The Telegram bot token, chat id and user id in `telemon/.env` (SECRET). [V]
- The Virtual Self API on host port 8090 for `/approve`, `/reject`, `/edit`. [V] (src: docker-compose.yml:14)
- Docker. [V]
- Not the GPU, not the AI brain :8081. The bot code can use Ollama or OpenRouter for chat, but chat is disabled. [V] (src: telegram.py:319; library/04-notifier/telemon-README.md:93-96)
- Everything that alerts depends on the notifier: Homelab Control health, vault-backup, the VRAM watchdog, Personal Feed, Virtual Self, research digest. [V] (see "Who sends")

## How to check it (read-only)
- DUM-E tool `health` → `curl localhost:8001/health` style check; expect `{"status":"ok"}`.
- DUM-E tool `containers` → `notifier-notifier-1` up.
- DUM-E tool `ports` → 8001 listening (notifier) and 8000 listening (Portainer).
- DUM-E tool `incidents` → aggregated `incidents.log` (count by source and summary, first and last time). Never dump it raw.
- DUM-E tool `services` → id `notifier`.
- Owner, read-only: `curl -s localhost:8001/health`; `tail -n 20 ~/.local/state/homelab/incidents.log`.

## Known problems and fixes
1. The docs give the wrong port.
   - Evidence: `library/00-meta/fortress-repository-root/AGENT_INTEGRATION.md` lines 16-20 say `http://localhost:8000` (host) and `http://notifier:8000` (Docker); `library/04-notifier/docs/AGENT_INTEGRATION.md` lines 18-20, 73-79, 106, 121 say the same; `library/04-notifier/telemon-README.md` line 10 uses `localhost:8000/notify`. [V]
   - Reality: host port 8001 maps to container 8000. Host 8000 is Portainer's edge port: `curl localhost:8000/health` returns plain `OK` from Portainer; `curl localhost:8001/health` returns `{"status":"ok"}`. [V] (src: docker-compose.yml:10-11; cmd: curl)
   - The name `notifier` does not resolve from other stacks, because the notifier is not on `fortress-network`. [V] (src: docker-compose.yml:19-29) [I]
   - Fix: owner updates the docs to `http://127.0.0.1:8001` (host) and `http://host.docker.internal:8001` (containers). DUM-E always uses 8001.
2. The container log leaks the Telegram bot token.
   - Evidence: the first log lines include `httpx | HTTP Request: POST https://api.telegram.org/bot<token>/…`. [V] (cmd: docker logs notifier-notifier-1 | head -3; value not copied)
   - Effect: the token sits in Docker's JSON log, in the `notifier_notifier_logs` volume, and Promtail ships it to Loki (manual 25), where Grafana and port 3100 can show it. [I]
   - Fix: owner sets the `httpx` logger to WARNING, rotates the bot token with BotFather, and decides what to do with stored logs. DUM-E has no action for this.
3. `telemon/.env` is world-readable (mode 664). [V] (cmd: ls -la) Fix: owner runs `chmod 600 ~/homelab/notifier/telemon/.env`. DUM-E has no action for this.
4. DNS failures at boot.
   - Evidence: 28 `NetworkError: … Temporary failure in name resolution` between 15:40 and 16:00 UTC (21:10-21:30 IST) on 2026-10-29. Afterwards 18 `POST /notify` calls returned 200 in 3 hours. [V] (cmd: docker logs --since 3h, filtered)
   - Effect: alerts sent in the first minutes after boot may be lost. fc_incident does not record a failed send, so the next run retries. [V] (src: fc_incident.sh:208-210) [I]
5. Every log line appears twice. [V] (cmd: docker logs --tail 50) Cause: two log handlers. [I]
6. Incident noise and dedupe gaps.
   - Each `fortress health` failure is written twice to `incidents.log` with the same second. [V] (src: incidents.log)
   - Summaries that contain changing numbers (for example "newest snapshot is 137h old") make a new fingerprint every hour, so the 6 h cooldown does not apply. [V] (src: incidents.log) [I] for the Telegram effect
   - `notify_dedupe.tsv` only grows. [V] (src: fc_incident.sh:195-199)
   - The health check compares against `services.yaml` `default: true` (15 services) while boot uses the saved profile, so some services are reported "not running (default service)" forever. [V] (DUM-E.md F6)
7. The bot can approve Virtual Self proposals from Telegram. DUM-E's design says Telegram is notification-only for DUM-E; that rule is about DUM-E, not this bot. [V] (src: telegram.py:313-315; DUM-E.md 12.0 M2.3)
8. The notifier has no authentication. Any device that can reach port 8001 (firewall off) can send messages to the owner's Telegram. [V] (src: AGENT_INTEGRATION.md:192-196; DUM-E.md F9)

Incident log summary (all sources, 2026-09-29 → 2026-10-29), aggregated: [V] (cmd: python3 count over incidents.log)
- By source: `vault_offsite` 1,349; `anytype` 737; `jarvis` 737; `mediastack` 737; `cine_immich` 735; `personal_feed` 735; `n8n` 402; `vram_watchdog` 327; `ai_llama` 31; `affine` 21; `immich` 6; `fortress-verify` 2; `virtual_self_archive` 1.
- No lines from `notifier`, `monitoring`, `orchestration` or `vault`.
- Gaps: no entries 2026-10-20 00:05 → 2026-10-29 21:05 (host off; boot list shows the previous boot ended 2026-10-20 00:26). [V] (cmd: journalctl --list-boots)
- Still firing at 22:01 today: `vault_offsite` "restic exited 1"; `anytype`, `jarvis`, `mediastack`, `ai_llama` "not running (default service)". [V] (src: notify_dedupe.tsv tail; health-cron.log tail)

## Logs
- `docker logs notifier-notifier-1` — API hits ("API hit: POST /notify", "API response: /notify → 200"), Telegram errors ("Failed to send Telegram notification", `NetworkError`). Redact tokens before showing. Log times are UTC. [V]
- Volume `notifier_notifier_logs` (`/app/logs/telemon.log` inside the container). [V] (src: Dockerfile:20-21)
- `~/.local/state/homelab/incidents.log` — JSON lines; look at `source`, `summary`, `ts`. [V]
- `~/.local/state/homelab/notify_dedupe.tsv` — what was sent and when (epoch). [V]
- `~/.local/state/homelab/health-cron.log` — "Health: N check(s) failed" and "FAIL id: reason" lines. [V]

## Rules for DUM-E here
- Never POST to `/notify`, `/notify/file` or `/convert/pdf` while checking. Only `GET /health`.
- Always use port 8001. Never use 8000 for the notifier. Trust this manual over `AGENT_INTEGRATION.md`.
- Never open `telemon/.env`, `data/google_token.json`, `openrouter.env`, `reminders.json`, `state.json`, or old `telemon/logs/*`.
- Never print raw notifier logs; redact `bot<digits>:<token>` first. Never print a token, chat id or user id.
- Never run `fortress health --notify` (it sends Telegram). Use the read-only health tool.
- Never edit, truncate or rotate `incidents.log` or `notify_dedupe.tsv`.
- Never treat a Alert message as approval for a DUM-E action.
- `service_stop notifier` is not allowed. `service_start notifier` is allowed with confirmation.
- DELETES operations that exist here: Telegram `/remind_delete`; `docker compose down` (container); `docker volume rm notifier_notifier_logs`; clearing `incidents.log` or `notify_dedupe.tsv`.

## Open questions
- Is `TELEGRAM_USER_ID` set (bot on) on purpose? The logs suggest yes. Settle: the owner checks `telemon/.env` personally. [I]
- Do the 2025 files in `telemon/logs/` contain the bot token? Settle: owner runs `grep -c "api.telegram.org/bot" telemon/logs/*` (count only). [U]
- Does Virtual Self actually send proposals for `/approve`? Settle: Virtual Self manual. [U]
- Does `cine-immich` have `NOTIFIER_URL` set in its `.env`? Settle: owner checks `grep -c NOTIFIER_URL homelab/cine-immich/.env`. [U]
