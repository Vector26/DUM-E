---
title: Homelab Control (the `fortress` command)
scope: Whole-service start/stop, AI brain picker, boot profile, health checks, incident log and alerts
last_verified: 2026-10-29
sources: control/fortress, control/lib/{common,actions,gpu,menu,fc_incident}.sh, control/status.py, control/services.yaml, control/host_jobs.yaml, control/ai_models.yaml, control/README.md, control/boot.log, ~/.config/fortress-control/profiles/default.json
---

# Homelab Control (the `fortress` command)

## What it is
The owner's single switchboard for the homelab. It starts and stops whole services (a whole Docker stack or a host program, not single containers), picks which AI brain uses the GPU, applies a "Default profile" at boot, and runs functional health checks that log incidents and send Alert notifications. Code lives in `~/homelab/control/` [V].

## How the owner refers to it
`fortress` or `f` (bashrc aliases, .bashrc:550-551) [V], "Homelab Control", "the menu", "the boot profile", "default profile", "health check". PlainTop shows a "Homelab services" pane; pressing `s` there opens this menu (src: control/README.md) [V].

## Components
- `control/fortress` - bash entry point. Subcommands (src: control/fortress) [V]:
  - `fortress` / `fortress menu` - interactive whiptail menu.
  - `fortress status` - ON/OFF list.
  - `fortress boot [--prompt-if-tty]` - apply the Default profile.
  - `fortress start <id>` / `fortress stop <id>` - one service.
  - `fortress ai <brain-id>` - switch AI brain.
  - `fortress wizard` - first-time setup.
  - `fortress save-default [ai-id]` - save currently running services as the Default profile.
  - `fortress health [--notify]` - functional health checks; with --notify also Telegram.
- `control/status.py` (Python, venv `control/.venv`) - JSON subcommands: status, catalog, ai-catalog, snapshot-default (WRITES the profile), profile, gpu, running-ids, health [V].
- `control/lib/actions.sh` - start/stop/AI/profile logic; `lib/gpu.sh` - GPU guard (manual 03); `lib/menu.sh` - menu and boot prompt; `lib/fc_incident.sh` - incident log + Telegram; `lib/common.sh` - paths [V].
- Config: `services.yaml` (22 services), `host_jobs.yaml` (2 host jobs), `ai_models.yaml` (5 brains) [V].

How "running" is detected (src: status.py is_running) [V]: by Docker container name in `docker ps`, or by a TCP connect to 127.0.0.1:<port>, or by `pgrep -f <pattern>`.

How start/stop work (src: lib/actions.sh) [V]:
- compose service: `docker compose up -d` in the compose directory / stop uses `docker compose stop` (containers and data stay).
- host service: runs the `start`/`stop` string from services.yaml with `bash -c` (so services.yaml is effectively code).
- GPU services first pass the GPU guard; `ai_llama` first unloads Ollama.
- Failures are written to the incident log.

How `fortress ai <id>` works (src: fc_start_ai) [V]: `none` stops llama and unloads Ollama; `llama` brains unload Ollama, set HAUHAUCS_MODEL to the brain's file and restart the server; `ollama` brains stop llama, run `sudo systemctl start ollama` and preload the model with keep_alive -1. Then the brain id is written into the Default profile.

Boot (src: crontab; control/boot.log) [V]:
- Cron `@reboot sleep 20 && fortress boot >> control/boot.log` applies the profile: starts each listed service that is not already on, then applies the profile's AI brain (restarting llama-server).
- `.bashrc` also runs `fortress boot --prompt-if-tty` once per local console (tty1-6) login.
- `boot.log` has no timestamps; it shows 8 profile runs, the last two back-to-back [V].

Default profile (src: ~/.config/fortress-control/profiles/default.json) [V]:
- Since 2026-10-29 22:13 (restored by the owner's decision): services orchestration, n8n, monitoring, notifier, immich, plane, vault, personal_feed, ai_llama, vram_watchdog; ai hauhaucs_q4.
- At 21:07:57 the same day it had been overwritten with what happened to be running 2 minutes after boot and `ai: hauhaucs_iq3`; the backup is `default.json.bak-20261029-2215` [V]. `save-default` saves only services running at that moment, and its AI detection cannot tell Q4 from IQ3 (it reports hauhaucs_q4 whenever port 8081 is open) [V].

Health (src: status.py run_health_checks) [V]:
- Services: a service with `default: true` in services.yaml that is not running fails as "not running (default service)". Optional http/container health checks.
- Host jobs (host_jobs.yaml): `vault_offsite` (cron entry present; restic has >= 1 snapshot, newest < 36 h; newest restic log has no "Fatal:") and `vault_backup_exporter` (container running).
- The restic check can take up to 300 s.
- Hourly cron runs `fortress health --notify`.

## Files and data
- `~/homelab/control/` - code and YAML.
- `~/.config/fortress-control/profiles/default.json` - boot profile; `first_run_done` marker.
- `~/.local/state/homelab/incidents.log` - JSON lines (ts, source, severity, summary, detail, exit_code) [V].
- `~/.local/state/homelab/notify_dedupe.tsv` - alert fingerprint + epoch; 6 h cooldown (FORTRESS_NOTIFY_COOLDOWN_SEC=21600) [V].
- `~/.local/state/homelab/health-cron.log` - output of the hourly health cron.
- `control/boot.log` - boot output.

## Commands
- READ: `fortress status`, `status.py status|catalog|ai-catalog|profile|gpu|running-ids|health`.
- MUTATES: `fortress start|stop <id>` (DUM-E actions `service_start`/`service_stop`), `fortress ai <id>` (owner only), `fortress boot` (owner only), `fortress health --notify` (sends Telegram).
- WRITES the profile (owner only; DUM-E must never run): `fortress save-default`, `fortress wizard`, `status.py snapshot-default`, menu item 5 in the boot prompt.

## Depends on
Docker, the notifier (:8001) for alerts, `/usr/local/bin/vault-backup`/restic for the backup check.

## How to check it (read-only)
- `services` (all services: running, default, in profile, GPU; with id for details and dependents).
- `health` (cached; `refresh=true` to rerun, ~5 min).
- `incidents` (grouped).
- `log_tail log=boot` / `log=health_cron`.

## Known problems and fixes
- Endless "not running (default service)" alerts for services that are `default: true` in services.yaml but not in the boot profile (on 2026-10-29: anytype, jarvis, mediastack) [V]. Fix (owner's choice): either start them, add them to the profile, or set `default: false` in services.yaml. See runbook:health-alerts.
- Profile overwritten during boot -> runbook:boot-profile.
- `fortress start ai_llama` refused by the GPU guard while cine holds the GPU [V] -> use `llama_start`.

## Logs
- `log_tail log=boot`, `log=health_cron`, `log=incidents`.

## Rules for DUM-E here
- DUM-E may propose `service_start`/`service_stop` for listed ids only; never for ai_llama, vram_watchdog (dedicated actions), and never stop orchestration, notifier or monitoring (they carry alerting).
- Never run save-default, wizard, snapshot-default, boot or `fortress ai`.
- Never edit services.yaml, host_jobs.yaml or ai_models.yaml.

## Open questions
- Whether boot runs twice (cron + TTY hook) [U]: add timestamps to boot.log to settle.
