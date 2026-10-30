---
title: Repeated health alerts
symptom: Alerts or the incident log keeps repeating "not running (default service)" or other health problems
last_verified: 2026-10-30
related: 04-fortress-control, 13-logs-and-incidents, 26-notifier
---

# Repeated health alerts

## Symptom
- The owner gets Alert notifications about services, or `incidents` fills with the same lines. [V]
- Many lines read "<service>: not running (default service)". [V]

## Quick check
1. `incidents {"hours":24}` - look for: the sources that repeat.
2. `services {}` - look for: services with default yes, boot profile no, state off.

## Diagnosis
1. Hourly cron runs `fortress health --notify`. [V]
2. Alert notifications are deduplicated for 6 hours. The incident log is not, so it repeats every hour. [V]
3. A service with `default: true` in `services.yaml` that is off fails health, even if it is not in the boot profile -> cause A: services.yaml and the boot profile disagree. [V]
4. The source is `vault_offsite` -> runbook:backup-failing.
5. The source is `ai_llama` -> runbook:ai-down.
6. The source starts with `agent-heal:` -> runbook:agent-heal. Those are written by the 2-minute self-heal timer; a Alert message is sent only after repeated failure. [V]

## Fix
The owner picks one per service. DUM-E edits neither file.
- Start it: `propose_action {"action":"service_start","args":{"service_id":"<id>"}}`. Tell the owner: dume approve <ID>.
- Or add it to the boot profile: the owner edits `~/.config/fortress-control/profiles/default.json`.
- Or set `default: false` in `~/homelab/control/services.yaml` (owner edit).

## Verify
- `health {"refresh":true}` shows the service OK. It can take minutes because the backup check calls restic with a 300 s limit. [V]

## Do not
- Do not run `fortress health` in a loop. The restic check is slow.
- Do not use `fortress save-default` during boot.

## Sources
- `crontab -l` (hourly `fortress health --notify`)
- `~/homelab/control/lib/fc_incident.sh` (dedupe cooldown 21600 s)
- `~/homelab/control/status.py` (health checks)
- manual 04-fortress-control, 13-logs-and-incidents
