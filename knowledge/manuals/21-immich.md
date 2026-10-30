---
title: Immich (standard photo backup)
scope: The standard Immich stack (containers fortress-immich-*), its compose files, its data on /mnt/photos/primary-immich and ~/immich, and the root helper scripts immich-post-rsync.sh and immich-migration-notify-watchdog.sh.
last_verified: 2026-10-29
sources: homelab/orchestration/stacks/immich/docker-compose.yml, homelab/immich/docker-compose.yml, ~/immich-post-rsync.sh, ~/immich-migration-notify-watchdog.sh, homelab/control/services.yaml:52-59, homelab/control/lib/actions.sh:38-50, ~/.config/fortress-control/profiles/default.json, crontab -l, /mnt/backup-volume/vault-backup/logs/cron-photos.log, docker ps/inspect/logs, ss, df, lsblk
---

# Immich (standard photo backup)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Immich is the owner's main self-hosted photo and video backup, like Google Photos. Phones upload to it on port 2283. [V] (src: homelab/control/services.yaml:52-59; homelab/orchestration/stacks/immich/docker-compose.yml:1-4)
It is the plain Immich, without the B-roll AI. The custom version is Cine-Immich (manual 20-cine-immich). [V] (src: library/08-orchestration/guides/USAGE_GUIDE.md:35-36)
In late September 2026 its originals and transcoded videos were moved from the NVMe disk to the HDD at `/mnt/photos/primary-immich`. Thumbnails stayed on fast storage. [V] (src: ~/immich-post-rsync.sh:100; cmd: docker inspect --format Mounts fortress-immich-server)

## How the owner refers to it
- "Immich", "Immich photos", "photo backup", "plain Immich", "2283". [V] (src: services.yaml:53-54; homelab/control/lib/fc_incident.sh:37; library/01-cine-immich/repo-root-docs/GUIDE.md:598)
- Homelab service id: `immich`. [V] (src: services.yaml:52)
- Compose project name: `immich`. [V] (src: stacks/immich/docker-compose.yml:12; cmd: docker compose ls)
- Related aliases: `vault-backup-photos` (back up `/mnt/photos`), `share-media` / `expose` (public Cloudflare tunnel to a local URL "Immich, etc."). [V] (src: ~/.bashrc:457-460,501)
- Old docs say `fortress deploy immich`. That command does not exist in Homelab Control. [V] (src: library/08-orchestration/guides/QUICK_REFERENCE.md:39; DUM-E.md section 8.2; cmd: grep deploy homelab/control/fortress lib/actions.sh → no match)

## Components
Active compose file: `~/homelab/orchestration/stacks/immich/docker-compose.yml`. It was started with env file `~/homelab/immich/.env`. [V] (cmd: docker inspect --format '{{json .Config.Labels}}' fortress-immich-server → project.environment_file)
Live state on 2026-10-29 (all started 21:06 IST at boot). [V] (cmd: docker ps; docker inspect --format State)

- `fortress-immich-server` (service `immich-server`). Web UI, API and background jobs. Image `ghcr.io/immich-app/immich-server:release`, running version **v2.4.1**. Port `0.0.0.0:2283` and `[::]:2283`. Restart `always`. Health: healthy. Networks `immich-internal` and `fortress-network`. [V] (src: stacks/immich/docker-compose.yml:15-40; cmd: docker logs fortress-immich-server → "listening ... [v2.4.1]"; ss -ltnp)
- `fortress-immich-ml` (service `immich-machine-learning`). CLIP search and faces. Image `ghcr.io/immich-app/immich-machine-learning:release` (CPU image, no `-cuda`, no GPU reservation). Volume `immich-model-cache`. Healthy. [V] (src: stacks/immich/docker-compose.yml:42-56)
- `fortress-immich-redis` (service `redis`). Valkey 8. Health check `redis-cli ping`. Healthy. Data in an anonymous Docker volume at `/data`. [V] (src: stacks/immich/docker-compose.yml:58-68; cmd: docker inspect --format Mounts)
- `fortress-immich-postgres` (service `database`). Postgres 14 with vectorchord/pgvectors. Label `com.fortress.backup=critical`. Healthy. Port 5432 inside the network only. [V] (src: stacks/immich/docker-compose.yml:70-86)
- Networks: `immich-internal` (bridge) and external `fortress-network`. [V] (src: stacks/immich/docker-compose.yml:95-101)
- Named volume `immich-model-cache`. [V] (src: stacks/immich/docker-compose.yml:88-93)
- It IS in the default boot profile. Boot logs show "Already on: immich". [V] (src: ~/.config/fortress-control/profiles/default.json; homelab/control/boot.log)
- GPU: none. [V] (src: services.yaml:58; compose has no GPU settings)
- No cron job or systemd unit for Immich itself. The weekly photo backup reads its data (see Depends on). [V] (cmd: crontab -l; systemctl --user list-unit-files)
- The two helper scripts in `~/` are one-time migration tools. They are not scheduled and not running. [V] (cmd: crontab -l; ls /tmp/immich-primary-finish.log → missing)

Second compose file: `~/homelab/immich/docker-compose.yml`. This is the original upstream-style file. Container names `immich_server`, `immich_machine_learning`, `immich_redis`, `immich_postgres`. Same project name `immich`. No `fortress-network`. Not running. [V] (src: homelab/immich/docker-compose.yml:10-73; cmd: docker ps -a)

## Files and data
- `~/homelab/immich/.env` — **SECRET**. DB password and paths. Never open it. Variable names used (values not read): `UPLOAD_LOCATION`, `ORIGINALS_LOCATION`, `ENCODED_VIDEO_LOCATION`, `THUMB_LOCATION`, `DB_DATA_LOCATION`, `DB_PASSWORD`, `DB_USERNAME`, `DB_DATABASE_NAME`, `IMMICH_VERSION`. Docs say `IMMICH_SOURCE_API_KEY` may also be in it. [V] (src: stacks/immich/docker-compose.yml:17-79; library/01-cine-immich/repo-root-docs/GUIDE.md:611-615)
- Resolved mounts of `fortress-immich-server` (from docker, not from .env): [V] (cmd: docker inspect --format Mounts fortress-immich-server)
  - `~/immich/library` → `/usr/src/app/upload` (the `UPLOAD_LOCATION` root, on `/home`, NVMe). **PRIVATE**.
  - `/mnt/photos/primary-immich/upload` → `/usr/src/app/upload/upload` (originals, HDD). **PRIVATE**.
  - `/mnt/photos/primary-immich/encoded-video` → `/usr/src/app/upload/encoded-video` (transcodes, HDD). **PRIVATE**.
  - `~/immich/library/thumbs` → `/usr/src/app/upload/thumbs` (thumbnails, NVMe). **PRIVATE**.
  - an anonymous Docker volume → `/data`.
- `~/immich/postgres` — Postgres data (`DB_DATA_LOCATION`). Owned by another uid. **PRIVATE**. [V] (cmd: docker inspect --format Mounts fortress-immich-postgres; ls -la)
- Sizes under `~/immich/library` on 2026-10-29: `thumbs` 8.8G, `backups` 2.4G, `profile` 240K, leftover `upload.nvme-stub-*` and `encoded-video.nvme-stub-*` folders about 29 MB total. `upload` and `encoded-video` are now empty mount points. [V] (cmd: du -sh ~/immich/library/*) [I] `backups` holds Immich's automatic database dumps.
- `/mnt/photos` — HDD `/dev/sdb1`, ext4, 1.8T, 992G used (58%), mounted by fstab UUID with `nofail`. systemd shows `mnt-immich_data.mount`. **PRIVATE: personal photos. Never list it.** It is shared with Cine-Immich, which uses the top level (`upload`, `library`, `encoded-video`, `thumbs`, `ai_cache`). [V] (cmd: df -h; lsblk; grep /etc/fstab; systemctl list-unit-files)
- Helper scripts: [V] (cmd: ls -la)
  - `~/immich-post-rsync.sh` (3,477 bytes, 2026-09-30).
  - `~/immich-migration-notify-watchdog.sh` (1,993 bytes, 2026-09-29).
- Their state files were in `/tmp`: `/tmp/immich-primary-finish.log`, `/tmp/immich-primary-rsync.log`, `/tmp/immich-primary-finish.lock`, `/tmp/immich-migration-notified`. None exist now (cleared by reboot). [V] (src: ~/immich-post-rsync.sh:5-7; cmd: ls)
- Grafana dashboard: `homelab/monitoring/grafana/provisioning/dashboards/json/immich-logs.json`. [V] (cmd: grep -rl)

## Commands
Read-only:
- `docker ps --filter name=fortress-immich` — container state. READ.
- `docker logs --tail 50 fortress-immich-server` — server log. READ.
- `curl -sf http://127.0.0.1:2283/api/server/ping` — API alive check (used by both helper scripts). READ. (src: ~/immich-post-rsync.sh:85)
- `vault-backup status` (`vault-backup-status`) — backup setup and snapshot summary. READ. (src: ~/.bashrc:499)

Mutating:
- `cd ~/homelab/orchestration/stacks/immich && docker compose --env-file ~/homelab/immich/.env up -d` — the documented way to start or update the stack. MUTATES. (src: stacks/immich/docker-compose.yml:7-9; ~/immich-post-rsync.sh:76-77)
- `fortress start immich` — runs `docker compose up -d` in the stack folder **without** `--env-file`. MUTATES. [I] It will fail (empty volume paths) or, worse, mount wrong paths. See Known problems 1. (src: homelab/control/lib/actions.sh:38-45)
- `fortress stop immich` — runs `docker compose stop`. MUTATES (containers kept). (src: homelab/control/lib/actions.sh:47-50)
- `docker compose pull` then `up -d` (upgrade). MUTATES. [I] Tag is `release`, so a pull would jump from v2.4.1 to the newest major release (logs say v3.3.5 exists). (cmd: docker logs → "Found v3.3.5")
- `bash ~/immich-post-rsync.sh` — waits for any `rsync` of `~/immich/library/` to stop; if `/tmp/immich-primary-rsync.log` has no `all_done` line, runs `sudo rsync -aH` of `upload/` and `encoded-video/` from NVMe to `/mnt/photos/primary-immich/`; then `docker compose --env-file ... up -d`; waits up to 5 min for `/api/server/ping`; sends a Alert message via `http://localhost:8001/notify`. MUTATES. Uses sudo. No `--delete`, so it does not remove files. [V] (src: ~/immich-post-rsync.sh:51-100)
- `bash ~/immich-migration-notify-watchdog.sh` — polls every 120 s for up to 24 h and sends exactly one success or failure Alert message; writes `/tmp/immich-migration-notified`. MUTATES (notification + temp file only). [V] (src: ~/immich-migration-notify-watchdog.sh:1-45)
- `vault-backup run photos` (`vault-backup-photos`) — restic backup of `/mnt/photos`. MUTATES (backup repo). (src: ~/.bashrc:501)
- `share-media` / `expose` = `~/.local/bin/proxy-share.sh` — opens a public Cloudflare tunnel to a local URL. MUTATES. Exposes private photos to the internet if pointed at Immich. (src: ~/.bashrc:457-460)
- `bash ~/homelab/cine-immich/scripts/run_immich_migrate.sh -y` — see Deleting.

Deleting:
- `bash ~/homelab/cine-immich/scripts/run_immich_migrate.sh -y` (and `migrate_immich_large_videos.py`, `run_immich_migrate_in_screen.sh`, `run_overnight_reliability.sh`) — copies large videos (>100 MiB, >90 s) to Cine-Immich, then moves them to the trash of THIS Immich (`DELETE /api/assets`, `force: false`). DELETES (soft). [V] (src: homelab/cine-immich/scripts/migrate_immich_large_videos.py:6,870-891; library/01-cine-immich/repo-root-docs/GUIDE.md:603)
- `cd ~/homelab/immich && docker compose up -d` — starts the OLD compose file with the same project name `immich`. [I] Compose would treat the running `fortress-immich-*` containers as the same services and recreate them under new names and without `fortress-network`. Treat as DELETES (containers replaced). (src: homelab/immich/docker-compose.yml:10-14)
- `docker compose down` in either Immich folder — removes containers. DELETES containers. [I] The Redis volume is anonymous, so the job queue state is lost.
- `docker compose down -v` — also removes the `immich-model-cache` volume and the anonymous volumes. DELETES.
- Removing `~/immich/library/*.nvme-stub-*` or the old NVMe copies — the finisher message says "NVMe copies are still present until cleanup is confirmed". DELETES. Only the owner may do this, by hand. (src: ~/immich-post-rsync.sh:100)
- Emptying the trash in the Immich UI — permanent delete of trashed assets. DELETES. [I]

## Depends on
- GPU: no. [V] (src: services.yaml:58)
- AI brain :8081 and Ollama :11434: no. [V] (src: compose files)
- Notifier :8001: only the two helper scripts use it (`NOTIFIER_URL` default `http://localhost:8001`). [V] (src: ~/immich-post-rsync.sh:8)
- Disks: `/mnt/photos` (originals, transcodes) and `/home` (thumbnails, DB). If `/mnt/photos` is not mounted at boot (`nofail`), Docker would bind an empty folder on the root disk. [I] (cmd: grep /etc/fstab)
- Docker network `fortress-network` must exist. [V] (src: stacks/immich/docker-compose.yml:99-101)
- Env file `~/homelab/immich/.env`. [V]
- Cine-Immich depends on THIS stack as the source for large-video migration. [V] (src: homelab/cine-immich/scripts/run_immich_migrate.sh:17)
- Backup: `vault-backup` group `photos` (cron `0 4 * * 0` → `homelab/vault-backup/scripts/cron-photos.sh`). [V] (cmd: crontab -l line 11)

## How to check it (read-only)
- DUM-E tools: `services` (Homelab status of `immich`), `containers`, `health`, `ports` (2283), `disk_memory` (`/mnt/photos`, `/home`), `log_tail` (`fortress-immich-server`), `backup` (photos backup state), `incidents` (source `immich`), `schedules` (cron-photos), `manual`, `graph`.
- Owner commands:
  - `docker ps --format 'table {{.Names}}\t{{.Status}}' | grep fortress-immich`
  - `docker inspect --format '{{.State.Health.Status}}' fortress-immich-server`
  - `curl -sf http://127.0.0.1:2283/api/server/ping`
  - `df -h /mnt/photos /home`
  - `findmnt /mnt/photos`
  - `tail -20 /mnt/backup-volume/vault-backup/logs/cron-photos.log`
- Healthy looks like: four `fortress-immich-*` containers "Up (healthy)", port 2283 listening, ping returns `{"res":"pong"}` [I], `/mnt/photos` mounted from `/dev/sdb1`.

## Known problems and fixes
1. **`fortress start immich` (and DUM-E `service_start immich`) omits the env file.** [V] + [I]
   - Homelab runs `cd <dir> && docker compose up -d`. The stack folder has no `.env`. The compose file says: "Deploy ONLY with: docker compose --env-file ~/homelab/immich/.env up -d". (src: homelab/control/lib/actions.sh:44; stacks/immich/docker-compose.yml:7-9; cmd: ls -la stacks/immich)
   - [I] Without it, `UPLOAD_LOCATION` and the other paths are blank, so compose fails or mounts the wrong paths.
   - It has not bitten yet because boot only says "Already on: immich". (src: homelab/control/boot.log)
   - Fix: DUM-E has no safe action for a cold start; the owner runs: `cd ~/homelab/orchestration/stacks/immich && docker compose --env-file ~/homelab/immich/.env up -d`. Long-term: add a symlink `.env` in the stack folder or teach `fc_compose_up` about env files.
2. **Photo backup is not set up.** [V]
   - The only logged weekly run (2026-10-04 04:00) failed: "Setup incomplete. Run: vault-backup setup restic && vault-backup setup gdrive". (src: /mnt/backup-volume/vault-backup/logs/cron-photos.log)
   - [I] The photo originals on `/mnt/photos` have no working off-site copy.
   - Fix: DUM-E has no action for this; the owner runs: `vault-backup setup restic && vault-backup setup gdrive`, then `vault-backup run photos`.
3. **Two compose files share project name `immich`.** [V] + [I]
   - Running the old file in `~/homelab/immich` would replace the live containers. Use only the stacks file. (src: both compose files, `name: immich`)
4. **Both stacks register the DNS alias `immich-server` on `fortress-network`.** [V]
   - `fortress-immich-server` and `cine_immich_server` both answer to `immich-server` there. [I] Any container on that network that calls `immich-server` may hit either one. Use container names instead. (cmd: docker inspect --format Networks)
5. **Version tag `release` floats.** [V] + [I]
   - Running v2.4.1; Immich reports v3.3.5 available. A pull would do a major upgrade. Cine-Immich is pinned to v2.5.6, and the migrator warns on version skew. Pin `IMMICH_VERSION` before any pull. (cmd: docker logs; src: migrate_immich_large_videos.py `--i-know-version-mismatch`)
6. **Anonymous `/data` volume on the server.** [V] + [U]
   - Immich v2 images use `/data` as the default media folder, but this compose mounts the old `/usr/src/app/upload` path. An anonymous volume sits at `/data`. [U] Whether any new uploads land in that anonymous volume (inside `/var/lib/docker` on the 91%-full root disk) is not verified.
7. **Port 2283 is open on all interfaces.** [V]
   - Bound to `0.0.0.0` and `[::]`. DUM-E.md finding F9 says the firewall is off. (cmd: ss -ltnp)
8. **Both Immich stacks run at once.** [V]
   - The orchestration guide warns against it. Together they use a lot of RAM. (src: library/08-orchestration/guides/QUICK_REFERENCE.md:115)
9. **Helper scripts are stale one-shot tools.** [V] + [I]
   - Their `/tmp` logs are gone. Running `immich-post-rsync.sh` now would find no `all_done` line and run `sudo rsync` again before `compose up`. [I] With empty NVMe `upload/` it copies nothing. Keep them for reference; do not schedule them.
10. **Migration may have trashed assets here.** [V] + [U]
    - The cine migrator moves verified large videos to this Immich's trash. [U] Whether any were trashed and when the trash auto-empties. Settle: check the Trash page in the Immich UI.

## Logs
- `docker logs --tail 50 fortress-immich-server` — look for `listening on ... [vX]`, `Machine learning server became unhealthy`, `PostgresError`, `ENOENT` (missing files after the HDD move). [V] (cmd: docker logs)
- `docker logs --tail 50 fortress-immich-ml`, `fortress-immich-postgres`, `fortress-immich-redis`.
- Helper script logs (gone now): `/tmp/immich-primary-finish.log`, `/tmp/immich-primary-rsync.log`. [V] (src: ~/immich-post-rsync.sh:5-6)
- Photo backup log: `/mnt/backup-volume/vault-backup/logs/cron-photos.log`. [V]
- Homelab incidents: `~/.local/state/homelab/incidents.log`, source `immich` (none in the recent tail). [V] (cmd: grep incidents.log)
- Grafana "immich-logs" dashboard (Loki). [V]

## Rules for DUM-E here
- Never open `~/homelab/immich/.env`. Never print API keys or DB passwords.
- Never list or read `/mnt/photos`, `~/immich/library` contents, or `~/immich/postgres`. Folder sizes are fine; file names are not.
- Do not propose `service_start immich` when the containers are stopped; it skips the env file (Known problem 1). Give the owner the full command instead. `service_stop immich` (compose stop) is allowed with approval, but warn that phone backups stop.
- Never run the helper scripts, `share-media`/`expose`, or any migration script.
- DELETES operations that exist here (never run them; only name them):
  - `run_immich_migrate.sh -y` / `migrate_immich_large_videos.py` / `run_immich_migrate_in_screen.sh` / `run_overnight_reliability.sh` (trash assets here)
  - `docker compose up -d` in `~/homelab/immich` (replaces live containers)
  - `docker compose down` and `docker compose down -v`
  - deleting `~/immich/library/*.nvme-stub-*` or old NVMe copies
  - emptying the Immich trash

## Open questions
- [U] Exact `.env` values (paths, `IMMICH_VERSION`). Settle: owner reads the file; DUM-E must not.
- [U] Does Immich v2.4.1 store anything in the anonymous `/data` volume? Settle: owner runs `docker inspect --format '{{range .Mounts}}{{.Name}} {{.Destination}}{{"\n"}}{{end}}' fortress-immich-server`, then `sudo du -sh /var/lib/docker/volumes/<name>`.
- [U] Is it safe to delete the NVMe stub folders? Settle: owner confirms in the Immich UI that old photos and videos play.
- [U] Why did the photo backup cron leave only one log entry (2026-10-04)? Settle: check whether the host is off at Sunday 04:00 and run `vault-backup status`.
- [U] Who, if anyone, calls `http://immich-server:2283` on `fortress-network`? Settle: `grep -rn 'immich-server:2283' ~/homelab --include=*.yml --include=*.py`.
