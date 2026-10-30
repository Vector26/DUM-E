---
title: Schedules (cron, systemd units and timers)
scope: Everything that runs on a schedule or at boot on this machine, and what DUM-E's own schedule is (none)
last_verified: 2026-10-29
sources: crontab -l, systemctl --user list-units/list-timers, systemctl cat (zram, ollama, notion-export-watchdog, system-monitor-power), vault-backup/scripts/cron-daily.sh
---

# Schedules (cron, systemd units and timers)

## What it is
The owner's user crontab is the main scheduler for Homelab jobs. A few things run as systemd units (system or user). DUM-E itself has NO schedule: it never runs unless the owner starts it [V].

## How the owner refers to it
"cron", "the jobs", "what runs at night", "boot".

## Components
User crontab (cmd: crontab -l, 2026-10-29) [V]:
| When | Command | Purpose | Log |
|---|---|---|---|
| 05:00 daily | `cd homelab/personal-feed && bash run_learn.sh` | Feed learn pipeline (rebalance + backlog) | personal-feed/out/learn.log |
| 06:00 daily | `cd homelab/personal-feed && bash run_daily.sh` | Daily feed build; uses the local AI through pi | personal-feed/out/cron.log |
| @reboot +20 s | `homelab/control/fortress boot` | Apply Default profile (manual 04) | control/boot.log |
| every 15 min | `cd ~/kindle-dash && . ./.env && ... python3 render_dash.py` | Render Kindle dashboard PNG | ~/kindle-dash/render.log |
| every 10 min | `~/bin/wifi-safe-switch.sh guard` | Wi-Fi/Mesh VPN (e.g. Tailscale) guard (manual 29) | ~/wifi-scan-reports/wifi-guard-cron.log |
| hourly :00 | `homelab/control/fortress health --notify` | Health checks + Alert notifications | ~/.local/state/homelab/health-cron.log |
| 03:00 daily | `homelab/vault-backup/scripts/cron-daily.sh` | Off-site backup daily tier (flock, incident on failure); includes retention prune | /mnt/backup-volume/vault-backup/logs/cron-daily.log |
| 04:00 Sunday | `homelab/vault-backup/scripts/cron-photos.sh` | Off-site backup photos tier | see manual 23 |
| @reboot +120 s | `homelab/vault-backup/scripts/bootstrap-keepalive.sh` | Resume backup bootstrap | bootstrap-keepalive.log |
| 07:30 Sunday | `python3 homelab/control/docker-image-cleanup.py --apply` | Weekly Docker image cleanup: unused images and 7-day-stopped containers of registered stacks; images only, never volumes, skips cine-immich (DELETES; DUM-E only previews it or proposes a run) | ~/.local/state/homelab/docker-image-cleanup.log |

User systemd services running (cmd: systemctl --user list-units) [V]: `fortress-modelq.service` (:8181) and `fortress-agent-gateway.service` (:8190), both `Restart=always`, enabled, and started at boot because lingering is on; `kindle-dash.service` (Kindle PNG server), `system-monitor-power.service` (CPU RAPL + GPU power logger, restarts on failure), plus desktop/audio units (pipewire, wireplumber, filter-chain, dbus, keyring, portals, snapd integration).

User timers (cmd: systemctl --user list-timers) [V]:
- `notion-export-watchdog.timer`: 5 min after boot, then every 10 min; runs `affine/scripts/.venv/bin/python tools/export/watchdog.py` with working directory inside `NOTION-DATA [DO NOT REMOVE OR TOUCH]` (a "heartbeat check" for the Notion export). DUM-E must not look inside that folder.
- `fortress-agent-heal.timer`: 90 s after boot, then 2 minutes after each run finishes; runs `agents/scripts/agent-heal --fix --quiet` (self-heal for the agent platform; not DUM-E; log `~/.local/state/homelab/agent-heal.log`) [V].
- `snap.firmware-updater.firmware-notifier.timer` (daily), `launchpadlib-cache-clean.timer` (daily).

System units relevant to the homelab (cmd: systemctl is-active) [V]: `ollama` (active), `docker` (active), `zram` (active, oneshot at boot), `hd-idle` (active, spins down idle disks), `mesh-vpnd` (active).

Things started by Homelab Control, not by systemd: the AI brain, the VRAM watchdog, the Personal Feed API [V].

## Files and data
- Crontab: `crontab -l` (owner's). User units: `~/.config/systemd/user/`. System units: `/etc/systemd/system/` (ollama.service + override.conf, zram.service).

## Commands
- READ: `crontab -l`, `systemctl --user list-units --type=service`, `systemctl --user list-timers`, `systemctl status <unit>`.
- MUTATES (owner only): `crontab -e`, `systemctl [--user] enable|disable|start|stop`.

## Depends on
- 05:00/06:00 feed jobs need the AI brain on :8081 [I]; if the AI is paused, they fail or start it (start_backend.sh launches it if :8081 is down) [V].
- Hourly health needs the notifier for alerts.

## How to check it (read-only)
- DUM-E tool `schedules`; `log_tail` for each job's log (feed_cron, feed_learn, kindle_render, wifi_guard, health_cron, vault_cron_daily, vault_bootstrap, boot).

## Known problems and fixes
- Gap in hourly health logs from 2026-10-20 00:05 to 2026-10-29 (machine likely off or cron not running) [V/I].
- The backup daily job reported "restic exited 1" hourly via health on 2026-10-29 [V]; see runbook:backup-failing.

## Logs
See the table above.

## Rules for DUM-E here
- DUM-E never adds, removes or changes schedules, and is itself never scheduled.

## Open questions
- Whether the @reboot boot and the TTY-login boot both run on a console login [U].
