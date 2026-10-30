---
title: After a reboot
symptom: The machine just rebooted and the owner asks whether everything is OK
last_verified: 2026-10-30
related: 04-fortress-control, 06-schedules
---

# After a reboot

## Symptom
- "The machine just rebooted, is everything OK?" [V]

## Quick check
Wait 5 minutes after boot first. Then, in order:
1. `snapshot {}` - look for: uptime, GPU, service count.
2. `ai_brain {}` - look for: the brain started and is not paused.
3. `services {}` - look for: every profile service ON.
4. `containers {}` - look for: the "Needs attention" list.
5. `disk_memory {}` - look for: `/mnt/backup-volume` and `/mnt/photos` mounted.
6. `incidents {"hours":2}` - look for: new errors.
7. `log_tail {"log":"agent_heal","lines":30}` - look for: DETECT and FIX lines right after boot.

## Diagnosis
1. Boot order. [V]
   - User systemd units start first (lingering is on): `fortress-modelq`, `fortress-agent-gateway`, `fortress-agent-heal.timer` (first run 90 s after boot).
   - `oda-preview.service` is a system unit and starts with the system.
   - Cron `@reboot` runs `fortress boot` after 20 s: compose stacks, the brain, then modelq and gateway (already on), the watchdog.
   - `fortress boot` ends with `agent-heal --fix --quiet`.
   - Cron `@reboot` starts the vault bootstrap keepalive after 120 s. [V]
2. The watchdog can pause the brain shortly after boot if VRAM is tight. It resumes when the GPU is quiet. -> runbook:ai-down.
3. A profile service is off -> runbook:boot-profile.
4. An agent check fails in the heal log -> runbook:agent-heal.
5. `Linger=no` would mean the user units wait for desktop login. It is `yes` now. [V]

## Fix
- Follow the runbook named in each branch. Do not fix several things at once.

## Verify
- `dume doctor` shows only known, unrelated findings.
- Owner runs `~/homelab/agents/scripts/agent-heal --check --quiet` - expected: no output and exit 0.

## Do not
- Do not run `fortress boot` again by hand. It restarts the brain. [V]
- Do not restart containers that are still starting; wait 5 minutes.

## Sources
- `crontab -l`, `~/homelab/control/fortress`, `control/boot.log`
- `systemctl --user list-unit-files 'fortress-*'`
- manual 04-fortress-control, 06-schedules
