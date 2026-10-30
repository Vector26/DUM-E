---
title: Off-site backups (vault-backup) and local state snapshots
scope: The vault-backup tool (restic to Google Drive), its cron jobs, bootstrap, retention, restore, logs; plus backup_state.sh and the homelab/backups folder.
last_verified: 2026-10-29
sources: homelab/vault-backup/vault-backup, homelab/vault-backup/lib/*.sh, homelab/vault-backup/scripts/*.sh, homelab/vault-backup/config/{paths.tsv,excludes.txt,vault.conf.example}, homelab/vault-backup/install.sh, homelab/backup_state.sh, homelab/backups/, homelab/control/host_jobs.yaml, homelab/control/lib/fc_incident.sh, homelab/control/status.py, crontab -l, /mnt/backup-volume/vault-backup/logs/*, ~/.local/state/homelab/{incidents.log,vault-backup/bootstrap.json}, journalctl
---

# Off-site backups (vault-backup) and local state snapshots

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
vault-backup copies important server data to Google Drive. It uses restic, so each run uploads only new or changed chunks, encrypted on this server. [V] (src: homelab/vault-backup/lib/restic.sh:4-5)
The restic repository is `rclone:remote:backup-repo`. [V] (src: homelab/vault-backup/lib/common.sh:33)
It is the only off-site copy of the homelab. It is NOT the same as vault-storage (MinIO), which receives backups from the MacBook. [V] (src: homelab/control/services.yaml:100; homelab/vault-storage/CONTEXT.md:9)
A first full upload ("bootstrap") started on 2026-09-29 and has not finished. While it runs, the nightly backup is skipped. [V] (cmd: vault-backup progress; src: /mnt/backup-volume/vault-backup/logs/cron-daily.log)
Separately, `backup_state.sh` makes a local copy of compose and `.env` files into `homelab/backups/`. It was last used on 2026-02-21. [V] (cmd: ls -la homelab/backups)

## How the owner refers to it
- "vault-backup", "off-site backup", "Google Drive backup", "restic". [V] (src: ~/.bashrc:494-502)
- Bash aliases: `vault-backup`, `vault-backup-menu`, `vault-backup-status`, `vault-backup-daily`, `vault-backup-photos`, `vault-backup-full`. [V] (src: ~/.bashrc:497-502)
- Health job id `vault_offsite`, name "Off-site backup (restic → GDrive)". [V] (src: homelab/control/host_jobs.yaml:6-7)
- Telegram label "Google Drive backup". [V] (src: homelab/control/lib/fc_incident.sh:33)
- "bootstrap" or "first-run" means the staged first upload. [V] (src: homelab/vault-backup/lib/bootstrap.sh:2)

## Components
- CLI: `/usr/local/bin/vault-backup`. It is a root-owned symlink to `~/homelab/vault-backup/vault-backup`. [V] (cmd: ls -la /usr/local/bin/vault-backup)
- Libraries in `homelab/vault-backup/lib/`: `common.sh` (config, logging), `paths.sh` (reads paths.tsv), `restic.sh` (backup, retention), `bootstrap.sh` (staged first run), `menu.sh` (interactive menu and pipeline), `rclone.sh` (Drive setup), `archive.sh`, `crypto.sh`, `restore.sh` (legacy tar+age engine). [V] (src: homelab/vault-backup/vault-backup:6-23)
- Engine is `restic`. The legacy "tar + zstd + age" engine exists but is not used. [V] (src: homelab/vault-backup/lib/common.sh:31; homelab/vault-backup/lib/menu.sh:8-11)
- No container and no listening port belong to vault-backup itself. [V] (cmd: docker ps; ss -ltnp)
- Required tools: whiptail, tar, zstd, docker, restic, rclone. [V] (src: homelab/vault-backup/vault-backup:111-117; homelab/vault-backup/lib/common.sh:87)
- Cron (user `(owner)`): [V] (cmd: crontab -l)
  - `0 3 * * *` → `homelab/vault-backup/scripts/cron-daily.sh` (runs `vault-backup run daily`).
  - `0 4 * * 0` → `homelab/vault-backup/scripts/cron-photos.sh` (runs `vault-backup run photos`, Sundays).
  - `@reboot sleep 120 && homelab/vault-backup/scripts/bootstrap-keepalive.sh` (keeps the bootstrap going).
- No systemd unit or timer runs backups. [V] (cmd: systemctl list-timers --all; systemctl list-units --all)
- Processes running at 22:42 on 2026-10-29: the keepalive script (PID 24119, since 21:08), `vault-backup run bootstrap`, `restic backup /mnt/photos/primary-immich --tag photos`, and its `rclone serve restic --stdio` child. [V] (cmd: ps -eo pid,etime,user,args)
- Health check: `fortress health` job `vault_offsite` checks the crontab marker `vault-backup run`, at least 1 snapshot, newest snapshot younger than 36 h (129600 s), and the word `Fatal:` in the newest `restic-*.log`. [V] (src: homelab/control/host_jobs.yaml:10-21)
- Monitoring: container `fortress-vault-backup-exporter` on port 9122 reports backup metrics to Prometheus. See manual 25. [V] (src: homelab/monitoring/docker-compose.yml:53-73)

### Tiers (groups in paths.tsv)
- `tier1`: 32 rows. Shell files, SSH keys, Gemini and Cursor config, `homelab/library`, `orchestration`, `core-orchestration`, the root compose file, most project repos, the Immich `.env`, the Immich Postgres folder and the Cine-Immich Postgres folder. [V] (src: homelab/vault-backup/config/paths.tsv:3-37,41)
- `tier1-volumes`: 7 Docker volumes: `fortress-portainer-data`, `plane_pgdata`, `plane_uploads`, `lifepath_lifepath_pgdata`, `onyx-rag-agent_postgres_data`, `onyx-rag-agent_minio_data`, `onyx-rag-agent_vespa_data`. [V] (src: homelab/vault-backup/config/paths.tsv:44-50)
- `tier1-photos`: 3 rows: `~/immich/library`, `/mnt/photos/primary-immich`, and `/mnt/photos` (the whole disk, which also contains primary-immich). [V] (src: homelab/vault-backup/config/paths.tsv:38-39,42)
- Excludes: `node_modules`, `.git`, `.venv`, caches, build folders, `*.zip`, `*.log`, `vault-backup/staging`, `vault-backup/logs`, `homelab/backups`, `homelab/archived`, `homelab/notion_html_export`, navidrome cache. [V] (src: homelab/vault-backup/config/excludes.txt:1-28)

### What each run mode does
- `run daily`: backs up `tier1` with tag `tier1-daily`, then `tier1-volumes` with tag `tier1-volumes`, then applies retention. [V] (src: homelab/vault-backup/vault-backup:64; lib/menu.sh:8-10; lib/restic.sh:254-257,275)
- `run photos`: backs up `tier1-photos` with tag `photos`, then applies retention. [V] (src: lib/restic.sh:258-260,275)
- `run full`: `tier1` (tag `tier1`), volumes, photos, then retention. [V] (src: lib/restic.sh:261-265,275)
- `run group NAME`: one group, tag NAME, then retention. [V] (src: lib/restic.sh:266-268,275)
- `run bootstrap`: staged batches (see below), then retention when all stages finish. [V] (src: lib/bootstrap.sh:364-384)
- After every non-bootstrap run, restic counts snapshots. If it finds 0, it reports an incident. [V] (src: lib/restic.sh:277-285)
- Groups `tier1` and `tier1-volumes`, and any unreadable path, make restic run as root through `sudo`. Root uses a separate cache at `/mnt/backup-volume/vault-backup/cache-root`. [V] (src: lib/restic.sh:26-38,171-180; lib/bootstrap.sh:197-200)

### Retention (permanent deletion)
- Function `restic_forget_prune` runs `restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune --verbose=2`. [V] (src: homelab/vault-backup/lib/restic.sh:214-225)
- The numbers come from `RESTIC_KEEP_DAILY/WEEKLY/MONTHLY`. Defaults are 14/8/12. [V] (src: lib/common.sh:35-37; config/vault.conf.example:20-22)
- The user file `~/.config/vault-backup/vault.conf` is sourced after the defaults and could change them. Its content was not read (protected folder). [U] (src: lib/common.sh:39-42)
- The command has no `--tag` and no `--group-by`. restic then groups snapshots by host and path set. [I] (restic default behaviour)
- It runs on `run daily`, `run photos`, `run full`, `run group`, and at the end of `run bootstrap`. [V] (src: lib/restic.sh:275; lib/bootstrap.sh:384)
- It has never run yet: `restic-forget.log` does not exist. [V] (cmd: ls /mnt/backup-volume/vault-backup/logs)
- The first successful run will forget and prune across the whole repository at once. On Google Drive this can take a long time and holds an exclusive repository lock. [I]

### Bootstrap (staged first upload)
- State file: `~/.local/state/homelab/vault-backup/bootstrap.json`. Also `bootstrap.pid` and `keepalive.pid` there. [V] (src: lib/bootstrap.sh:5-6; cmd: ls ~/.local/state/homelab/vault-backup)
- Lock: `/mnt/backup-volume/vault-backup/run.lock`, taken with `flock -n` on file descriptor 200. [V] (src: lib/bootstrap.sh:7,344-348)
- Order: `tier1` (tag `tier1-daily`, batches of 8), `tier1-volumes` (tag `tier1-volumes`, batches of 3), `tier1-photos` (tag `photos`, one item at a time). [V] (src: lib/bootstrap.sh:165-172,364-368)
- restic exit code 3 (some files unreadable) is treated as success. [V] (src: lib/bootstrap.sh:215-219)
- A failed batch marks its items `failed` and sends an incident. A missing path is marked `skipped`. [V] (src: lib/bootstrap.sh:221-229,257-271)
- Items in `skipped` count as done. The bootstrap never retries them. [V] (src: lib/bootstrap.sh:54-65)
- The keepalive script reruns `vault-backup run bootstrap` every 120 s after a failure until the state says COMPLETE. It raises restic HTTP timeouts to 7200 s and 1200 s. [V] (src: scripts/bootstrap-keepalive.sh:6-9,26-50)
- Current state: stage `tier1-photos`, 22 completed, 18 skipped, failed `immich_photos_hdd`, working on "Primary Immich originals + encoded video (HDD)", updated 2026-10-29 15:48 UTC. `cine_photos` (`/mnt/photos`) has not started. [V] (cmd: vault-backup progress; src: ~/.local/state/homelab/vault-backup/bootstrap.json)

### Restore flow
- vault-backup has no restic restore command. The usage text lists none. [V] (src: homelab/vault-backup/vault-backup:27-47)
- Menu item 10 "Restore from Google Drive" only handles legacy `.age` files in `vault-gdrive:vault-backup/`. It downloads, decrypts with the age key, and extracts into a folder (default `/mnt/backup-volume/vault-backup/staging/restore`). [V] (src: lib/restore.sh:4-31; lib/menu.sh:94)
- A restic restore must be run by the owner with restic directly, for example `restic restore <snapshot-id> --target <empty-folder>`, with `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE` and `RCLONE_CONFIG` set as in `restic_export_env`. [I] (src: lib/restic.sh:7-16)
- Restore needs two SECRET files: the restic password file and the rclone config. If the password file is lost, the backups cannot be decrypted. [V] (src: lib/restic.sh:246)
- Always restore into an empty folder first, then copy files by hand. The legacy wizard says the same. [V] (src: lib/restore.sh:31)

## Files and data
- `~/homelab/vault-backup/` — tool code, config, scripts. [V]
- `homelab/vault-backup/config/paths.tsv` — what is backed up (id, label, path, type, enabled, group). [V]
- `homelab/vault-backup/config/excludes.txt` — exclude patterns. [V]
- `homelab/vault-backup/config/vault.conf.example` — example settings (no secrets). [V]
- `~/.config/vault-backup/` — SECRET folder (mode 700). Holds `restic-password.txt` (SECRET), `rclone.conf` (SECRET, Google Drive token), `identity.txt` (SECRET, legacy age key), `vault.conf`. Never open. [V] (cmd: ls -la ~/.config/vault-backup, names only)
- `/mnt/backup-volume/vault-backup/` — data root on the USB "Expansion HDD" (exFAT, 1.9 TB, 16 % used). Holds `cache/` (129 MB), `cache-root/` (86 MB), `staging/`, `logs/`, `run.lock`. [V] (cmd: df -h; lsblk; du -sh)
- `/mnt/backup-volume` is exFAT, so every file there shows mode 755 and owner `(owner)`; Unix permissions do not protect the logs. [V] (cmd: lsblk; ls -la /mnt/backup-volume/vault-backup)
- `~/.local/state/homelab/vault-backup/bootstrap.json` — bootstrap progress. [V]
- `homelab/vault-backup/staging/tier1_20260530_154459.tar.zst.age` — legacy test archive, 213 bytes. [V] (cmd: ls -la)
- `homelab/vault-backup/logs/` — legacy logs from 2026-05-30. [V]
- Backed-up content includes PRIVATE data: photo libraries under `~/immich/library` and `/mnt/photos`. [V] (src: config/paths.tsv:38-42)
- Backed-up content includes SECRET data: `~/.ssh`, `~/.gemini`, `homelab/immich/.env`. They are encrypted by restic. [V] (src: config/paths.tsv:5-6,36)
- `~/homelab/backup_state.sh` — local snapshot script (see Commands). [V]
- `~/homelab/backups/` — 628 KB, three folders from 2026-02-21: [V] (cmd: find homelab/backups -type f; du -sh)
  - `fortress_state_20260221_120008/` — only `backup_file_list.txt`; empty `files/` and `compose-configs/`.
  - `fortress_state_20260221_120020/` — files and 7 resolved configs, no manifest.
  - `fortress_state_20260221_120030/` — complete: files, 17 resolved configs, `DATA_PATHS_MANIFEST.txt`, `FAILED_CONFIGS.log`.
  - SECRET: these folders contain copies of `.env` files (`cine-immich/.env`, `immich/.env`, `moltbot/.env`, `n8n/.env`, `n8n/.env.bak`, `notifier/telemon/.env`, `rag-agent/.env`) and resolved compose configs, which can contain secret values. Never open them. [V] (cmd: find, names only) [I] for resolved configs
  - `homelab/backups` is excluded from restic, so these copies are not off-site. [V] (src: config/excludes.txt:17,20)

## Commands
READ:
- `vault-backup progress` — bootstrap status from the state file, `pgrep`, and log tails. READ. [V] (src: lib/bootstrap.sh:117-163)
- `vault-backup paths` — table of configured paths. READ. [V] (src: lib/paths.sh:76-85)
- `vault-backup status` — setup check, latest 8 snapshots, repo stats, last 10 log lines. READ in normal use, but slow: it did not finish within 400 s on 2026-10-29 22:3x while an upload ran. [V] (cmd: timeout 400 vault-backup status)
  - Edge case: it calls `restic_ensure_repo`, which runs `restic init` if the error text looks like "repository does not exist". MUTATES in that case. [V] (src: lib/restic.sh:91-112,227-235)
- `vault-backup help` — usage text. READ. [V]
- `crontab -l | grep vault` — show schedules. READ.

MUTATES and DELETES (owner only, except `backup_run_daily`):
- `vault-backup run daily` — uploads tier1 and volumes, then `restic forget … --prune`. MUTATES + DELETES (old snapshots, permanent). [V] (src: lib/restic.sh:254-257,275,214-225)
  - It does not take `run.lock` itself. Only `cron-daily.sh`, `cron-photos.sh` and the bootstrap take it. [V] (src: vault-backup:49-76; scripts/cron-daily.sh:10-14)
- `vault-backup run photos` / `run full` / `run group NAME` — same as above with other groups. MUTATES + DELETES. [V]
- `vault-backup run bootstrap` — staged upload; runs retention at the end; may `rm -f run.lock` if no backup process is seen. MUTATES + DELETES. [V] (src: lib/bootstrap.sh:330-338,384)
- `scripts/cron-daily.sh` — lock + `run daily` + incident on failure. MUTATES + DELETES. [V] (src: scripts/cron-daily.sh:1-23)
- `scripts/cron-photos.sh` — lock + `run photos`. MUTATES + DELETES. [V] (src: scripts/cron-photos.sh:1-21)
- `scripts/bootstrap-keepalive.sh` — endless loop of `run bootstrap`; removes a stale `run.lock`. MUTATES + DELETES. [V] (src: scripts/bootstrap-keepalive.sh:14-22)
- `vault-backup setup restic` — creates the restic password file (refuses if it exists). MUTATES. [V] (src: lib/restic.sh:237-247)
- `vault-backup setup gdrive` — interactive; if you answer "y" it runs `rclone config delete vault-gdrive` before re-creating it. DELETES (remote config). [V] (src: lib/rclone.sh:24-29)
- `vault-backup setup crypto` — creates the legacy age key. MUTATES. [V] (src: lib/crypto.sh:4-18)
- `vault-backup menu` — interactive whiptail menu. Items 1-5 run backups (DELETES via retention). Item 5 (custom folder) fails under restic with "Unknown restic mode: path". Item 10 restores legacy archives and extracts into a folder, which can overwrite files there (DELETES). Item 11 rewrites the crontab. [V] (src: lib/menu.sh:64-191; lib/restic.sh:269-271) [I] for overwrite
  - Cron presets 1, 2, 3 and 5 remove every crontab line containing `# vault-backup`. The current daily and photos lines both contain that text, so choosing preset 1 deletes the photos schedule and preset 2 deletes the daily schedule. DELETES. [V] (src: lib/menu.sh:165,172,176,180,187; cmd: crontab -l)
- Legacy engine only (not active): `rm -f` of plaintext archives after encryption, `rm -f` of staging copies after upload, `rclone delete --min-age 90d` on `vault-gdrive:vault-backup/`, `rm -rf` of work folders. DELETES. [V] (src: lib/crypto.sh:35; lib/rclone.sh:83,102; lib/archive.sh:87,95,99,131)
- `install.sh` — `sudo apt-get install`, writes `~/.config/vault-backup/vault.conf`, creates the symlink, appends to `.bashrc`. MUTATES. [V] (src: homelab/vault-backup/install.sh:10-44)
- `bash ~/homelab/backup_state.sh` — creates `homelab/backups/fortress_state_<timestamp>/`, copies every `docker-compose*.yml` and `.env` under `homelab/` into it, and saves `docker compose config` output per stack. MUTATES. It creates new copies of secrets. [V] (src: homelab/backup_state.sh:6-51)
- Any direct `restic` or `rclone` command — not part of the tool; `restic forget`, `restic prune`, `rclone delete|purge|sync` DELETE. Owner only.

## Depends on
- Google Drive through the rclone remote `vault-gdrive` (SECRET config). Drive total 5.0 TiB, used 259 GB (4.7 %) at 22:4x. [V] (cmd: curl -s localhost:9122/metrics)
- The USB disk `/mnt/backup-volume` (Seagate Expansion HDD, exFAT). Logs, caches and the lock live there. If it disconnects, backups fail silently. [V] (src: lib/common.sh:21-24; journalctl -b -1 -k)
- Passwordless `sudo` for root restic runs. [V] (src: lib/restic.sh:26-38)
- Docker, to find volume paths. [V] (src: lib/paths.sh:66-71)
- The notifier on host port 8001, through `fc_incident.sh` (`FORTRESS_NOTIFIER_URL`, default `http://127.0.0.1:8001/notify`). [V] (src: homelab/control/lib/fc_incident.sh:12; lib/common.sh:14-16)
- python3 for state files and snapshot counting. [V] (src: lib/bootstrap.sh:37-52; lib/restic.sh:280)
- Not the GPU, not the AI brain on :8081, not Ollama. [V] (no references in the code)

## How to check it (read-only)
- DUM-E tool `backup` → runs `vault-backup status`. Allow more than 400 s, or expect a timeout while an upload runs. [V]
- DUM-E tool `schedules` → crontab lines for cron-daily, cron-photos and the keepalive. [V]
- DUM-E tool `incidents` → aggregate `source = vault_offsite`. [V]
- DUM-E tool `health` → `vault_offsite` check (slow: up to 300 s for restic). [V] (src: homelab/control/status.py:297-311)
- DUM-E tool `log_tail` → `/mnt/backup-volume/vault-backup/logs/*.log` (tail only).
- DUM-E tool `disk_memory` → is `/mnt/backup-volume` mounted and how full.
- Owner, read-only:
  - `vault-backup progress`
  - `tail -n 30 /mnt/backup-volume/vault-backup/logs/vault-backup.log`
  - `grep -E "cron daily|SKIP|Fatal" /mnt/backup-volume/vault-backup/logs/cron-daily.log | tail`
  - `curl -s localhost:9122/metrics | grep -v '^#'` (exporter numbers)
  - `findmnt /mnt/backup-volume` (is the USB disk there?)
  - `pgrep -af "restic backup"` (is an upload running?)

## Known problems and fixes
1. Nightly backups have not produced a snapshot since 2026-10-02.
   - Evidence: the last "snapshot … saved" in `cron-daily.log` is `bdfb10fb` at 2026-10-02 05:38. Later runs show "Setup incomplete" (Oct 3-5) and "SKIP: another backup holds lock" (Oct 6, 12-15). [V] (src: /mnt/backup-volume/vault-backup/logs/cron-daily.log)
   - Cause: the bootstrap holds `run.lock` for days, and `cron-daily.sh` skips when the lock is held. [V] (src: scripts/cron-daily.sh:10-14; lib/bootstrap.sh:344-348)
   - Fix: the owner decides whether to let the bootstrap finish first, or pause it to let a daily run through. DUM-E has no action for this; the owner runs: stop the keepalive and bootstrap processes by hand, then `~/homelab/vault-backup/scripts/cron-daily.sh`.
2. The bootstrap is stuck on the photo HDD.
   - Evidence: `immich_photos_hdd` is in `failed`; 161 `Fatal` lines in `bootstrap-photos.log`, 151 of them "unable to save snapshot: server response unexpected: 500 Internal Server Error". Keepalive rounds 12-18 on Oct 13-15 each ended with exit 1 after hours. [V] (src: bootstrap.json; logs/bootstrap-photos.log; logs/bootstrap-keepalive.log)
   - Cause: Google Drive returns HTTP 500 when restic saves the final snapshot of a very large path. [I]
   - Fix: [U]. Possible owner options: split `/mnt/photos/primary-immich` into smaller paths in `paths.tsv`, or use a different backend. DUM-E has no action for this.
3. Docker volumes are never backed up.
   - Evidence: all 7 `vol_*` items were skipped with "no resolved paths" on 2026-10-05 23:44. [V] (src: logs/vault-backup.log)
   - Cause: `/var/lib/docker` is mode 710 root, so the `-e` test run as the owner cannot see volume folders and drops them. [V] (cmd: ls -ld /var/lib/docker; test -e) (src: lib/restic.sh:149; lib/bootstrap.sh:263-266)
   - The same test runs in `run daily` before root is used, so `tier1-volumes` likely gets 0 paths there too, and the run may fail at that step before retention. [I] (src: lib/restic.sh:143-158,166-172)
   - Fix: code change by the owner (resolve volume paths as root). DUM-E has no action for this.
4. 11 other items are marked `skipped` with no log reason: `repo_monitoring`, `repo_notifier`, `repo_system_monitor`, `repo_vault_storage`, `repo_vault_backup`, `repo_extensions`, `repo_netwatch`, `repo_spot_spot`, `immich_env`, `immich_postgres`, `cine_postgres`.
   - Evidence: a batch with the first eight started at 2026-10-05 23:38:45; at 23:44:42 the stage reported "nothing left"; `bootstrap.sh` was modified at 23:44 that evening. [V] (src: logs/vault-backup.log:1166-1168; cmd: ls -la lib/bootstrap.sh)
   - Cause: [U]. Likely marked skipped by hand or by an edited script. [I]
   - Effect: the bootstrap will never upload them. They may exist in the 2026-10-02 daily snapshot. [I]
5. The USB data disk dropped on 2026-10-15 19:38.
   - Evidence: kernel "usb 2-3: USB disconnect" for the Seagate Expansion HDD; the systemd unmount failed; cron ran `cron-daily.sh` on Oct 16-19 but nothing was written to its log. [V] (cmd: journalctl -b -1 -k; journalctl -b -1 -t CRON)
   - Effect: backups failed silently for days; health then reported "restic timed out (300s)" from Oct 15 20:05. [V] (src: incidents.log)
   - Fix: owner checks the cable and power of the USB disk. DUM-E can report `findmnt /mnt/backup-volume`.
6. The health check keeps failing with "restic exited 1".
   - Evidence: 346 times from 2026-09-29 13:01 to 2026-10-29 22:01. [V] (src: incidents.log, aggregated)
   - Cause: [U]. Settle: the owner runs `vault-backup status` when no upload is running and reads the error.
7. Alert noise and broken dedupe.
   - Each health failure is written twice to `incidents.log` in the same second. [V] (src: incidents.log)
   - "newest snapshot is N h old" puts the hour count in the summary, so each hour has a new dedupe key and Telegram is sent each hour despite the 6 h cooldown. [I] (src: homelab/control/lib/fc_incident.sh:204)
8. `vault-backup progress` shows stale log lines.
   - It tails `bootstrap-tier1-daily.log` (last written 2026-10-05) before the photos log. [V] (src: lib/bootstrap.sh:160-162; cmd: ls -la logs)
9. A wrong-error path tried to create a new repository.
   - On 2026-10-02 05:52 rclone could not read `rclone.conf` ("permission denied") and the tool logged "Initializing restic repository" and ran `restic init`, which failed. [V] (src: logs/cron-daily.log)
   - Risk: an error that matches the "does not exist" patterns triggers `restic init`. [V] (src: lib/restic.sh:104-111)
10. Huge logs.
    - `bootstrap-keepalive.log` 927 MB and `bootstrap-photos.log` 339 MB, both still growing (restic `--verbose=2` prints every file). They are shipped to Loki (see manual 25). [V] (cmd: ls -la logs; src: homelab/monitoring/promtail/promtail.yml:50-61)
    - DUM-E must not delete or rotate them. The owner decides.
11. Legacy `homelab/backups` snapshots hold secret copies and are stale (Feb 2026). [V] Keep or delete is the owner's choice.

## Logs
All under `/mnt/backup-volume/vault-backup/logs/` unless noted. Use tail only. [V] (cmd: ls -la)
- `vault-backup.log` (154 KB) — main log: INFO/WARN/ERROR lines. Look for `[ERROR]`, "Bootstrap batch FAILED", "Google Drive hiccup", "Bootstrap skip".
- `cron-daily.log` (10 MB) — one block per night. Look for "cron daily start", "SKIP: another backup holds lock", "Fatal:", "cron daily OK".
- `cron-photos.log` (166 bytes) — only one run, 2026-10-04, "Setup incomplete".
- `restic-tier1-daily.log` (10 MB, last 2026-10-02) — per-file restic output for daily runs. Health and the exporter read the newest `restic-*.log`.
- `restic-forget.log` — retention output. Does not exist yet.
- `bootstrap-run.log` (12 KB, 2026-10-05), `bootstrap-tier1-daily.log` (589 MB, 2026-10-05), `bootstrap-photos.log` (339 MB, growing), `bootstrap-keepalive.log` (927 MB, growing).
- `~/.local/state/homelab/incidents.log` — JSON lines; `source = vault_offsite` (1,349 of 5,820 lines). [V]
- `~/.local/state/homelab/health-cron.log` — hourly "FAIL vault_offsite: …" lines. [V]
- `homelab/vault-backup/logs/` — legacy logs from 2026-05-30. [V]

Incident summary for `vault_offsite` (2026-09-29 → 2026-10-29), aggregated: [V] (src: incidents.log)
- "Setup incomplete…" 425× (Oct 2-5).
- "restic error: restic exited 1" 346× (Sep 29 → Oct 29, still firing).
- "restic error: restic timed out (300s)" 176× (Oct 15-20).
- "vault-backup run bootstrap failed (exit 1)" 84×; "Bootstrap failed on tier1-batch-1" 60×; "Bootstrap batch FAILED [tier1-batch-1] exit=3" 53×.
- "Another vault-backup run holds …run.lock" 21×.
- "Bootstrap failed on tier1-photos-batch-1" 18×; "…exit=1" 17×.
- "newest snapshot is N h old (limit 36h)" about 150 lines, Oct 11-18 (136 h to 154 h).
- "Scheduled daily vault-backup failed" 4×; "Scheduled photos vault-backup failed" 1×.

## Rules for DUM-E here
- Never run `vault-backup run …`, `cron-daily.sh`, `cron-photos.sh`, `bootstrap-keepalive.sh`, `restic` or `rclone` directly.
- The only backup action is `backup_run_daily`. It permanently deletes old snapshots through retention. It needs the owner's typed confirmation every time. State this before asking.
- Refuse `backup_run_daily` while `run.lock` is held. The file always exists, so test the lock (flock), not the file. Also refuse if `pgrep -f "restic backup"` finds a process. `vault-backup run daily` does not take the lock by itself.
- Refuse `backup_run_daily` if `/mnt/backup-volume` is not mounted.
- Never open `~/.config/vault-backup/` or any file in it. Never print the restic password, the rclone token or the age key.
- Never open files in `homelab/backups/` beyond their names.
- Never edit `bootstrap.json`, `paths.tsv`, `excludes.txt`, or the crontab.
- Never remove `run.lock`, pid files, caches, staging files or logs.
- Never run `vault-backup menu` or `vault-backup setup …`.
- Never run `backup_state.sh` (it makes new copies of secrets).
- DELETES operations that exist here (all owner-only except `backup_run_daily`):
  - `restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune` inside `run daily|photos|full|group|bootstrap` (lib/restic.sh:214-225,275; lib/bootstrap.sh:384).
  - `rm -f run.lock` in `bootstrap_clear_stale_lock` and in the keepalive (lib/bootstrap.sh:337; scripts/bootstrap-keepalive.sh:21).
  - `rclone config delete vault-gdrive` in `setup gdrive` (lib/rclone.sh:28).
  - Crontab line removal in menu item 11 (lib/menu.sh:172-187).
  - File overwrite by `tar -x` in the legacy restore (lib/restore.sh:22-27).
  - Legacy engine: `rm -f` plaintext and staging files, `rclone delete --min-age 90d`, `rm -rf` work folders (lib/crypto.sh:35; lib/rclone.sh:83,102; lib/archive.sh:87,95,99,131).
  - Temporary file removal in `restic_run_retry` (lib/restic.sh:59,69,72).

## Open questions
- Effective retention numbers: `~/.config/vault-backup/vault.conf` may override 14/8/12. Settle: the owner runs `grep KEEP ~/.config/vault-backup/vault.conf`. [U]
- Which snapshots exist now. Settle: the owner runs `vault-backup status` when no upload is running, or reads `vault_backup_restic_snapshots_total` from the exporter when `vault_backup_process_running` is 0. [U]
- Why the health check gets "restic exited 1". Settle: as above, read the restic error text. [U]
- Why 11 tier1 items are marked skipped. Settle: the owner remembers or checks file history. [U]
- Whether `run daily` fails at the volumes step every time. Settle: the next daily run's `cron-daily.log`. [I]
- Whether the photo HDD path can ever finish on Google Drive. [U]
- Whether a separate copy of the restic password exists off this server. Settle: ask the owner. [U]
