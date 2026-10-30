---
title: Backup failing
symptom: The backup failed, restic reports an error, or vault_offsite is unhealthy
last_verified: 2026-10-30
related: 23-backups, 24-vault-storage
---

# Backup failing

## Symptom
- `dume doctor` lists "Health: vault_offsite: newest snapshot is 426h old (limit 36h)". [V]
- The incident log shows restic errors or timeouts for `vault_offsite`. [V]

## Quick check
1. `backup {}` - look for: newest snapshot age, last run, locks.
2. `incidents {"hours":168,"source":"vault"}` - look for: the error text.
3. `log_tail {"log":"vault_cron_daily","lines":60}` - look for: "Fatal" or "error".

## Diagnosis
1. The schedule: cron daily 03:00, photos on Sundays 04:00, a bootstrap keepalive 120 s after reboot. [V]
2. The health check wants at least 1 snapshot, the newest under 36 hours, and no "Fatal:" in the newest restic log. [V]
3. "Setup incomplete" -> cause A: credentials are not set up. [I]
4. "timed out (300s)" -> cause B: the health check's restic call is slow because the remote is Google Drive via rclone. This is not proof the backup failed. Compare with the cron log. [V]
5. "restic exited 1" -> cause C: read the newest log lines with "Fatal" or "error" (`log_tail {"log":"vault_cron_daily","contains":"Fatal"}`).
6. A lock is held -> cause D: another run (bootstrap keepalive or a photo backup) is active. Wait. A restic photo backup was running on 2026-10-30. [V]
7. `/mnt/backup-volume` is not mounted -> cause E. It was mounted on 2026-10-30. [V]

## Fix
- A: owner runs `vault-backup setup restic && vault-backup setup gdrive`.
- B, D: wait and compare logs.
- C: `propose_action {"action":"backup_run_daily"}`. **DELETES:** old restic snapshots by retention (permanent). The owner types PRUNE. Tell the owner: dume approve <ID>.
- E: the owner mounts the Expansion drive.

## Verify
- `backup {}` shows a snapshot newer than 36 hours.

## Do not
- Do not run restic or rclone yourself.
- Do not read `~/.config/vault-backup` (it holds the password).
- Do not start a second backup while one is running.

## Sources
- `crontab -l` (vault-backup entries)
- `~/homelab/control/status.py` (restic check, 300 s limit)
- manual 23-backups, 24-vault-storage
