---
title: Cine-Immich (photo library + B-roll AI)
scope: The cine-immich Docker stack in ~/homelab/cine-immich, its B-roll workers, Redis queues, GPU use, import and migration scripts, and its docs in library/01-cine-immich.
last_verified: 2026-10-29
sources: homelab/cine-immich/docker-compose.yml, homelab/cine-immich/broll_agent/*.py, homelab/cine-immich/scripts/*, library/01-cine-immich/**/*.md, ~/.bashrc:135-163, homelab/control/services.yaml:43-50, homelab/control/lib/{actions,gpu}.sh, homelab/control/vram-watchdog.sh, monitoring/docker-compose.yml, monitoring/prometheus/prometheus.yml, docker ps/inspect/logs, nvidia-smi, ss
---

# Cine-Immich (photo library + B-roll AI)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Cine-Immich is a second, customised Immich photo and video library. It is built for cinematic B-roll footage. [V] (src: homelab/cine-immich/docker-compose.yml:1-9)
On top of Immich it adds an AI pipeline. A watcher finds new videos. A GPU worker runs the Florence-2 vision model to write tags and a description into an XMP sidecar file. A face worker extracts frames and sends them to Immich for face detection. [V] (src: library/01-cine-immich/repo-root-docs/GUIDE.md:105-121)
It uses the NVIDIA GPU, so it competes with the local AI brain for VRAM. [V] (src: homelab/control/services.yaml:43-50; homelab/control/vram-watchdog.sh:1-8)
It is a separate install from the standard Immich on port 2283 (see manual 21-immich). Both write to the same disk, `/mnt/photos`. [V] (cmd: docker inspect --format Mounts)

## How the owner refers to it
- "cine", "cine-immich", "Cine photos", "Cine photos + AI tags", "B-roll", "the b-roll pipeline". [V] (src: ~/.bashrc:136-139; homelab/control/services.yaml:44; homelab/control/lib/fc_incident.sh:36)
- Homelab service id: `cine_immich`. [V] (src: homelab/control/services.yaml:43)
- Bash aliases (all in ~/.bashrc). [V] (src: ~/.bashrc:139-163)
  - `cine` = cd to the stack folder.
  - `cineImport` = guided import from a USB drive or SSD.
  - `mount_immich_ssd` = `sudo mount -t exfat /dev/sda2 /mnt/cine-immich-source`.
  - `cinelogs`, `cinelogsml`, `cinelogsworker` = follow logs.
  - `cinestats` = docker stats. `cinegpu` = watch nvidia-smi. `cinehealth` = docker ps filtered to `cine_`.
  - `triggerReindex`, `checkReindexStatus` = run `trigger_full_scan.py` in the face worker.
  - `migrateCine`, `migrateCineDry` = copy media from `/mnt/cine-immich-source`.
  - `rediscli`, `clearRedisQueues`, `checkBrollQueue`, `checkFaceQueue` = Redis queue tools.
  - `startCine`, `stopCine`, `restartCine`, `restartCineAll` = compose up / down / restart / force-recreate.
- Docs also mention `triggerReindexNotify`, `pauseReindex`, `emptyReindexQueues`. These aliases do NOT exist in ~/.bashrc. [V] (cmd: grep -n 'triggerReindexNotify|pauseReindex|emptyReindexQueues' ~/.bashrc → no match; src: library/01-cine-immich/repo-root-docs/REINDEX_IMPROVEMENTS.md:43-47)

## Components
Compose file: `~/homelab/cine-immich/docker-compose.yml`. Top-level `name: cine_immich`. [V] (src: docker-compose.yml:40)
Running containers carry compose project label `cine-immich` (with a hyphen). [V] (cmd: docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' cine_immich_server)
Live state was taken 2026-10-29 about 22:37 IST. [V] (cmd: docker ps -a)

- `cine_immich_server` (service `immich-server`). Web UI and API. Custom image `cine-immich/immich-server-patched:v2.5.6`, built from `./immich-server-patched`. Port `127.0.0.1:2285 -> 2283` (loopback only). GPU. RAM limit 8g, 4 CPUs. Restart `always`. Health: healthy. [V] (src: docker-compose.yml:53-97; cmd: docker ps)
- `cine_immich_gateway` (service `immich-gateway`). Front door for the UI and apps on host port `2284 -> 8080`. Routes `/api/search/smart` and `/api/search/metadata` to the search proxy when `USE_IMPROVED_SEARCH=true`. Upload timeout `IMMICH_GATEWAY_TIMEOUT_S` default 7200 s. Restart `unless-stopped`. **State: Exited (0) since 2026-09-01.** [V] (src: docker-compose.yml:108-141; cmd: docker inspect --format State cine_immich_gateway)
- `cine_immich_microservices` (service `immich-microservices`). Background jobs: transcoding (ffmpeg), metadata, thumbnails, face and smart-search coordination. Same patched image. `IMMICH_MEDIA_TRANSCODING_CONCURRENCY=1`. RAM limit 12g, 6 CPUs, pids 500. GPU. Restart `always`. Healthy. [V] (src: docker-compose.yml:155-198; cmd: docker ps)
- `cine_immich_machine_learning` (service `immich-machine-learning`). CLIP smart search and face models. Image `ghcr.io/immich-app/immich-machine-learning:v2.5.6-cuda`. Port 3003 inside the network only. Command overridden to gunicorn with `-t 900`. RAM 4g, pids 150, `OMP_NUM_THREADS=4`. GPU. Healthy. Unloads models after 300 s idle. [V] (src: docker-compose.yml:214-276; cmd: docker logs --tail 12 cine_immich_machine_learning)
- `cine_immich_redis` (service `redis`). Valkey 9. Holds Immich BullMQ queues and the B-roll lists. Health check `redis-cli ping`. No host port. **It has no volume mount at all.** [V] (src: docker-compose.yml:290-297; cmd: docker inspect --format Mounts cine_immich_redis → empty)
- `cine_immich_postgres` (service `database`). Immich Postgres 14 with vectorchord/pgvectors. No host port. Healthy. [V] (src: docker-compose.yml:308-321; cmd: docker ps)
- `cine_broll_watcher` (service `broll_watcher`). Built from `./broll_agent`, runs `watcher.py`. No GPU (`runc`). Watches `/mnt/photos/upload` and `/mnt/photos/library` for `.mp4 .mov .mxf .mkv .avi` and pushes paths to `broll_queue`. RAM 512m. Up (no health check). [V] (src: docker-compose.yml:323-340; broll_agent/watcher.py:10-14; cmd: docker logs cine_broll_watcher)
- `cine_broll_worker` (service `broll_worker`). Runs `worker.py` with Florence-2-large on the GPU. RAM 4g, 2 CPUs. Health check runs a tiny CUDA matrix multiply every 2 minutes. Healthy. It holds a CUDA context all the time (host PID 6358, about 1,836 MiB). [V] (src: docker-compose.yml:342-420; broll_agent/worker.py:101; cmd: nvidia-smi --query-compute-apps; ps -p 6358)
- `cine-immich-broll_face_worker-1` (service `broll_face_worker`). Runs `face_recognition_worker.py`. No fixed container name so it can be scaled. No GPU (`runc`). RAM 1536m. Takes jobs from `broll_face_queue` with BLPOP. Uploads extracted frames to Immich as archived image assets. Up (no health check). [V] (src: docker-compose.yml:422-460; broll_agent/face_recognition_worker.py:21,294-357)
- `cine_search_proxy` (service `search-proxy`). Query expansion with a small Ollama model (`qwen2.5:1.5b-instruct` by default) plus hybrid search. Port `8090`. **State: Exited (0) since 2026-09-01.** [V] (src: docker-compose.yml:472-497; cmd: docker inspect --format State cine_search_proxy)
- Networks: `cine-immich_cine-network` (all services) and external `fortress-network` (server and gateway only). [V] (cmd: docker inspect --format Networks)
- Related monitoring container `fortress-cine-immich-redis-exporter` (defined in the monitoring stack). Exited (0) since 2026-09-09. [V] (src: homelab/monitoring/docker-compose.yml:90-100; cmd: docker ps -a)
- Listening host ports now: only `127.0.0.1:2285`. Ports 2284 and 8090 are not listening. [V] (cmd: ss -ltnp)
- No cron job and no systemd unit start or touch this stack. [V] (cmd: crontab -l; systemctl --user list-unit-files)
- It is NOT in the default boot profile. It runs because Docker restarts it (`restart: always`). [V] (src: ~/.config/fortress-control/profiles/default.json; homelab/control/boot.log tail)

## Files and data
- `~/homelab/cine-immich/` project root. [V] (cmd: ls -la)
- `~/homelab/cine-immich/.env` — **SECRET**. Holds API keys, DB credentials and paths. Never open it. [V] (src: GUIDE.md:131)
  - Variable names used by compose (values not read): `UPLOAD_LOCATION`, `DB_DATA_LOCATION`, `DB_PASSWORD`, `DB_USERNAME`, `DB_DATABASE_NAME`, `IMMICH_VERSION`, `IMMICH_API_KEY`, `HOST_PORT`, `IMMICH_SERVER_HOST_PORT`, `USE_IMPROVED_SEARCH`, `IMMICH_GATEWAY_TIMEOUT_S`, `SEARCH_PROXY_PORT`, `SEARCH_PROXY_LLM_PROVIDER`, `SEARCH_PROXY_LLM_MODEL`, `OLLAMA_BASE_URL`, `SEARCH_PROXY_TIMEOUT_S`, `CONVERT_SLOG3`, `BROLL_*`, `FACE_FRAMES_*`. Docs add `NOTIFIER_URL`, `IMMICH_METADATA_EXTRACTION_TIMEOUT_MS`, `IMMICH_CONFIG_FILE`. [V] (src: docker-compose.yml; TELEGRAM_NOTIFICATIONS.md:27-31; METADATA_TIMEOUT_FIX.md:18-19)
- `scripts/.env.migrate.example` — template only, no real key. [V] (src: scripts/.env.migrate.example:1-13)
- Upload root `UPLOAD_LOCATION` = `/mnt/photos` (mounted at `/data` in server and microservices, at `/mnt/photos` in the B-roll workers). **PRIVATE** (personal photos and videos). Do not list it. [V] (cmd: docker inspect --format Mounts cine_immich_server)
  - The disk is `/dev/sdb1`, ext4, 1.8T, 58% used on 2026-10-29. fstab uses `nofail`. [V] (cmd: df -h; grep /etc/fstab)
  - Cine writes under `/mnt/photos/upload`, `/library`, `/encoded-video`, `/thumbs`. The standard Immich uses `/mnt/photos/primary-immich`. [V] (src: watcher.py:10; repair_zero_byte_encoded_videos.py ENC_ROOT; docker inspect fortress-immich-server)
- `/mnt/photos/ai_cache` — ML model cache (`/cache` in ML and B-roll worker), Hugging Face models, `broll_forensics.jsonl`, `broll_description_ledger.jsonl`. [V] (cmd: test -e on each path)
- XMP sidecars: the worker writes `<video>.xmp` next to each video, and `<video>.broll_search.json` when `BROLL_SEARCH_SIDECAR_ENABLE=1`. [V] (src: broll_agent/worker.py:899,58-59)
- `postgres_cine/` — live Postgres data dir (`DB_DATA_LOCATION`). Owned by another uid. **PRIVATE**. [V] (cmd: docker inspect --format Mounts cine_immich_postgres)
- `postgres/` — older Postgres data dir from Jan 2026. Not mounted by any container. Vault-backup bootstrap still lists both dirs. [V] (cmd: ls -la; src: homelab/vault-backup/lib/bootstrap.sh:288-291) [I] probably stale.
- `config/immich_config.json` — mounted read-only at `/config`. Sets all job concurrency to 1, face `minScore 0.55`, `minFaces 2`, model `buffalo_l`, ffmpeg `nvenc`, 720p h264, `maxBitrate 6000k`. Contains no secrets. [V] (cmd: python3 json read of config/immich_config.json)
- `immich_config.json` in the project root differs from `config/immich_config.json` and is NOT mounted. [V] (cmd: diff -q) [I] the root copy is stale.
- `immich-server-patched/` — Dockerfile, `metadata.patch` (makes the metadata timeout read `IMMICH_METADATA_EXTRACTION_TIMEOUT_MS`), deprecated `entrypoint-patch.sh`. [V] (src: METADATA_TIMEOUT_FIX.md:5-29)
- `broll_agent/` — Dockerfile (base `nvcr.io/nvidia/pytorch:26.01-py3`), `watcher.py`, `worker.py`, `face_recognition_worker.py`, `reindex_worker.py`, `trigger_full_scan.py`, `archive_frame_assets.py`, `slog3_detect.py`, `monitor_resources.sh`. [V] (cmd: ls; src: broll_agent/Dockerfile)
- `immich_gateway/main.py`, `search_proxy/app.py` — gateway and search proxy sources. [V] (cmd: ls)
- `model-cache/` — root-owned old model cache. [V] (cmd: ls -la)
- `docker-compose.yml.bak.20260419192808`, `config/immich_config.json.bak.20260419192808` — backups. The old compose used stock Immich and transcoding concurrency 4. [V] (cmd: diff)
- `hwaccel.ml.yml`, `hwaccel.transcoding.yml` — not referenced by the compose file. [V] (src: docker-compose.yml)
- `scripts/.immich-migrate-state.sqlite` — migration resume state (Mar 2026). [V] (cmd: ls -la scripts)
- `~/.local/state/cine-immich/disk-import.sqlite` — import resume state (Mar 2026). [V] (cmd: ls -la)
- `logs/` — migration, overnight and repair logs, VRAM peak log, `broll_desc_v1_inventory.jsonl`. All from March 2026. [V] (cmd: ls -la logs)
- `upload_log.json`, `resource_profile_*.csv` — old profiling outputs from Jan 2026. [V] (cmd: ls -la)
- Symlinked docs in the project root point to `~/homelab/library/01-cine-immich/`. [V] (cmd: ls -la)
- `~/.cursor` is mounted read-write into the gateway (`/cursor_log`), search proxy (`/cursor_log`) and face worker (`/cursor_debug`). [V] (src: docker-compose.yml:112-113,443-444,478-479)
- Mount points used by imports: `/mnt/cine-immich-source`, `/mnt/cine-import`. [V] (src: scripts/migrate_from_source.sh:10; scripts/cine_import_menu.sh:12)

## Commands
Exact text, what it does, class.

Read-only:
- `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}" | grep cine_` (alias `cinehealth`) — container health. READ. (src: ~/.bashrc:148)
- `docker logs -f cine_immich_microservices --tail 50` (`cinelogs`), `docker logs -f cine_immich_machine_learning --tail 50` (`cinelogsml`), `docker logs -f cine_broll_worker --tail 50` (`cinelogsworker`) — follow logs. READ. (src: ~/.bashrc:143-145)
- `docker stats --format ...` (`cinestats`) — live RAM and CPU. READ. (src: ~/.bashrc:146)
- `watch -n 1 nvidia-smi` (`cinegpu`) — GPU view. READ. (src: ~/.bashrc:147)
- `docker exec cine_immich_redis redis-cli LLEN broll_queue` (`checkBrollQueue`), `... LLEN broll_face_queue` (`checkFaceQueue`) — queue lengths. READ, but it uses `docker exec`, which DUM-E may not run. (src: ~/.bashrc:157-158)
- `checkReindexStatus` = `docker exec cine_broll_face_worker python trigger_full_scan.py --check-only` — job counts (needs an admin API key). READ in intent. **Broken:** container `cine_broll_face_worker` does not exist; the real one is `cine-immich-broll_face_worker-1`. Working form: `cd ~/homelab/cine-immich && docker compose exec broll_face_worker python trigger_full_scan.py --check-only`. [V] (src: ~/.bashrc:151; guides/broll-face-scale-and-resume.md:23-27; cmd: docker ps -a)
- `bash ~/homelab/cine-immich/scripts/migrate_from_source.sh --dry-run` (`migrateCineDry`) — preview copy. READ. (src: scripts/migrate_from_source.sh:23)
- `bash ~/homelab/cine-immich/scripts/run_immich_migrate.sh --dry-run -y` — list large videos that would move. READ (network reads only). (src: GUIDE.md:626)
- `python3 ~/homelab/cine-immich/scripts/immich_upload_from_disk.py --root <dir> --dry-run` — list files only. READ. (src: scripts/immich_upload_from_disk.py:362)
- `python3 scripts/find_anemic_transcodes.py [--json] [--limit N]` — flags low-bitrate proxies via ffprobe inside microservices. READ (uses docker exec). (src: scripts/find_anemic_transcodes.py:1-25)
- `python3 scripts/monitor_vram_peak.py` — samples nvidia-smi for up to 2 h. READ. (src: scripts/monitor_vram_peak.py)
- `./profile_workload.sh 1800 &` then `python3 analyze_profile.py resource_profile_*.csv` — RAM profile. READ, writes a CSV. (src: GUIDE.md:464-472)
- `./broll_agent/monitor_resources.sh 120` — docker stats loop. READ. (src: broll_agent/monitor_resources.sh)
- `./diagnose_mount.sh` — checks the microservices mount (uses docker exec). READ. (src: diagnose_mount.sh:1-3,86-88)

Mutating:
- `cd ~/homelab/cine-immich && docker compose up -d` (`startCine`) — start the stack. MUTATES. (src: ~/.bashrc:160)
- `docker compose restart` (`restartCine`) — restart all containers. MUTATES. (src: ~/.bashrc:162)
- `docker compose up -d --force-recreate` (`restartCineAll`) — recreate all containers. MUTATES. [I] Also DELETES Redis queue contents, because Redis has no volume. (src: ~/.bashrc:163)
- `docker compose up -d --force-recreate <service>` — recreate one service. MUTATES. (src: GUIDE.md:77)
- `docker compose build immich-server immich-microservices` then `docker compose up -d --force-recreate immich-server immich-microservices` — rebuild the patched Immich. MUTATES. (src: METADATA_TIMEOUT_FIX.md:35-38)
- `docker compose up -d --scale broll_face_worker=3` — more face workers. MUTATES. (src: guides/broll-face-scale-and-resume.md:11)
- `docker compose up -d --build broll_worker` — rebuild the B-roll worker. MUTATES. (src: guides/broll-face-scale-and-resume.md:53)
- `docker stop cine_broll_worker` — stop the B-roll worker. MUTATES. (src: guides/broll-face-scale-and-resume.md:51)
- `triggerReindex` = `docker exec cine_broll_face_worker python trigger_full_scan.py` — starts Immich jobs one at a time, queues every asset for metadata and faces, and pushes every video to `broll_queue`. MUTATES. Alias is broken (wrong container name, see above). (src: broll_agent/trigger_full_scan.py:1-14,652-665)
- `trigger_full_scan.py --aggressive` — starts all jobs at once. MUTATES. Docs call it dangerous (past OOM crashes). (src: trigger_full_scan.py:29-34)
- `trigger_full_scan.py --pause` — pauses Immich job queues. MUTATES. (src: trigger_full_scan.py:42-45)
- `trigger_full_scan.py --notify-progress` — reindex plus Telegram milestones. MUTATES. (src: trigger_full_scan.py:52-56)
- `docker exec cine_broll_worker python reindex_worker.py --once [--force]` or `--continuous --interval 3600` — requeue videos that already have XMP. MUTATES. (src: module-readmes/broll_agent-README.md:150-160)
- `bash ~/homelab/cine-immich/scripts/migrate_from_source.sh` (`migrateCine`) — copies media from `/mnt/cine-immich-source` into `UPLOAD_LOCATION/library`. Never deletes the source. Skips same-size files. MUTATES. (src: scripts/migrate_from_source.sh:4-8,171)
- `cineImport` = `bash scripts/cine_import_menu.sh` — interactive. Mounts a chosen partition (udisksctl, else `sudo mount` to `/mnt/cine-import`), uploads everything with `immich_upload_from_disk.py` to `http://127.0.0.1:${HOST_PORT:-2284}`, then unmounts. MUTATES. Uses sudo. (src: scripts/cine_import_menu.sh:46-47,219-250)
- `mount_immich_ssd` = `sudo mount -t exfat /dev/sda2 /mnt/cine-immich-source` — MUTATES, uses sudo. [V] On 2026-10-29 `/dev/sda` is the `/mnt/backup-volume` disk and has no `sda2`, so this alias points at the wrong device now. (cmd: lsblk) [I] device names change with plug order.
- `python3 scripts/immich_upload_from_disk.py --root <dir>` — uploads files with SHA1 checksum and SQLite resume. MUTATES. (src: scripts/immich_upload_from_disk.py:1-12)
- `docker exec cine_broll_face_worker python archive_frame_assets.py` — archives all frame assets uploaded by the face worker. MUTATES. (src: broll_agent/archive_frame_assets.py:1-9)
- `python3 scripts/export_broll_desc_v1_inventory.py` — writes `logs/broll_desc_v1_inventory.jsonl` (overwrites it). MUTATES. (src: scripts/export_broll_desc_v1_inventory.py:48)
- `bash scripts/run_overnight_reliability.sh` — migration, transcode and thumbnail requeue, full scan. MUTATES. (src: scripts/run_overnight_reliability.sh:1-6,88)
- `screen -dmS immich_migrate bash ~/homelab/cine-immich/scripts/run_immich_migrate_in_screen.sh` — runs the real migration in screen. MUTATES and DELETES (see below). (src: scripts/run_immich_migrate_in_screen.sh:1-6,25)

Deleting:
- `clearRedisQueues` = `docker exec -it cine_immich_redis redis-cli DEL broll_queue broll_face_queue` — deletes all pending B-roll and face jobs. DELETES. (src: ~/.bashrc:156)
- `docker exec -it cine_immich_redis redis-cli FLUSHALL` — wipes all Redis data, including Immich queues and sessions. DELETES. (src: GUIDE.md:66,382)
- `trigger_full_scan.py --empty` — empties all Immich job queues. DELETES (queued jobs). (src: trigger_full_scan.py:47-50)
- `cd ~/homelab/cine-immich && docker compose down` (`stopCine`) — removes all containers. DELETES containers. [I] It also deletes all Redis queues, because Redis has no volume. (src: ~/.bashrc:161)
- `docker compose down -v` — docs say "DELETES ALL DATA". DELETES. [I] All data here is in bind mounts, so `-v` removes only anonymous volumes; treat it as destructive anyway. (src: GUIDE.md:82-83; COMMANDS.md:136-137)
- `bash scripts/run_immich_migrate.sh -y` — moves large videos (>100 MiB and >90 s) from standard Immich (2283) into cine-immich, then puts each source asset in the standard Immich trash (`DELETE /api/assets`, `force: false`) after verifying it. DELETES (soft) on the standard Immich. (src: GUIDE.md:603-605; scripts/migrate_immich_large_videos.py:6,870-891,1108-1121)
- `python3 scripts/repair_zero_byte_encoded_videos.py` — with sudo, `rm -f` each zero-byte encoded video and copies the original in its place, then queues transcodes. DELETES and overwrites. Last run fixed 419 files (Mar 2026). (src: scripts/repair_zero_byte_encoded_videos.py:95-112; logs/repair_zero_byte_encoded.log)
- `docker rm -f cine_broll_face_worker` — removes the old single face-worker container. DELETES. (src: guides/broll-face-scale-and-resume.md:17)
- `docker compose build --no-cache ...` — rebuilds without cache. MUTATES. (src: technical-docs/IMMICH_METADATA_TIMEOUT_BUILD.md:153)
- Face worker code deletes its own temp frames in `/tmp/broll_face_frames` with `os.remove`. DELETES (temp only, automatic). (src: broll_agent/face_recognition_worker.py:369)

## Depends on
- GPU: yes. Server, microservices, ML and B-roll worker reserve the NVIDIA GPU. VRAM is not capped. Docs say idle models use about 1.7 GB and spikes reach 3-5 GB. [V] (src: docker-compose.yml:14-15,93-97; GUIDE.md:267-281)
- The GPU is an discrete GPU (example: 16 GB VRAM) with 16,303 MiB. On 2026-10-29 22:38: 10,389 MiB used, 0% load. llama-server used 8,530 MiB, the B-roll worker 1,836 MiB. [V] (cmd: nvidia-smi)
- Homelab GPU guard always allows `cine_immich` to start, even when the GPU is busy. [V] (src: homelab/control/lib/gpu.sh:45-49)
- The VRAM watchdog pauses the AI brain on :8081 when free VRAM drops below 2,048 MiB, and resumes at 6,144 MiB free plus a quiet GPU. The B-roll worker's permanent CUDA context is the reason the watchdog was changed to use "quiet" instead of "no process". [V] (src: homelab/control/vram-watchdog.sh:1-17)
- AI brain on :8081: no direct dependency. They only share the GPU. [V] (src: docker-compose.yml)
- Ollama :11434: the search proxy uses it (`OLLAMA_BASE_URL` default `http://host.docker.internal:11434`, model `qwen2.5:1.5b-instruct`). The proxy is stopped now. [V] (src: docker-compose.yml:484-488)
- Notifier: `trigger_full_scan.py --notify-progress` posts to `NOTIFIER_URL` (default `http://notifier:8000`). [V] (src: trigger_full_scan.py:85)
- Disk: `/mnt/photos` must be mounted. Postgres lives on `/home`. [V] (cmd: docker inspect --format Mounts; df -h)
- Standard Immich on 2283 is the source for the large-video migration. [V] (src: scripts/run_immich_migrate.sh:17)
- Docker network `fortress-network` must exist (external). [V] (src: docker-compose.yml:502-504)

## How to check it (read-only)
- DUM-E tools: `containers` (state of all `cine_*`), `services` (Homelab status of `cine_immich`), `gpu` (VRAM and who holds it), `ai_brain` (whether the watchdog paused the AI), `ports` (2284, 2285, 8090), `disk_memory` (`/mnt/photos`, `/`), `log_tail` (container logs), `incidents` (source `cine_immich`), `manual`, `graph`.
- Owner commands:
  - `docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep -i cine`
  - `docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' cine_broll_worker`
  - `docker logs --tail 50 cine_broll_worker`
  - `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv`
  - `ss -ltnp | grep -E ':(2284|2285|8090)\b'`
  - `df -h /mnt/photos`
- Healthy looks like: all `cine_*` Up; server, microservices, ML, redis, postgres, broll_worker "(healthy)"; port 2284 listening; B-roll worker log shows "Processing" lines for different files. [V] (src: COMMANDS.md:150; GUIDE.md:402-404)

## Known problems and fixes
1. **B-roll worker stuck in a hot retry loop.** [V]
   - Symptom: `cine_broll_worker` logs "moov atom not found" and "Could not generate description" about 1,276 times per minute, always for the same 4,096-byte `.mp4` under `/mnt/photos/upload/...`. (cmd: docker logs --since 1m cine_broll_worker | grep -c 'Claimed job')
   - Cause: with `BROLL_RELIABLE_QUEUE=1`, a failed job is pushed straight back to `broll_queue` with no delay and no retry limit. Only missing files are dropped. An unreadable but existing file loops forever. (src: broll_agent/worker.py:1042-1063; guides/broll-face-scale-and-resume.md:62-68)
   - Effect [I]: wasted CPU, very large container log on the root filesystem (`/var/lib/docker`), which is 91% full. Real B-roll jobs behind it may starve.
   - Fix (owner): find the asset in Immich and delete or re-upload it, then remove that one path from the queue. DUM-E has no action for this; the owner runs: `docker exec cine_immich_redis redis-cli LREM broll_queue 0 '<path>'` (DELETES one queue entry). Long-term fix: add a retry counter or backoff in `worker.py`.
2. **Gateway (port 2284) and search proxy (8090) are stopped.** [V]
   - Symptom: the cine web UI and mobile apps on `:2284` do not answer. Only `127.0.0.1:2285` works. (cmd: ss -ltnp; docker ps -a)
   - Cause: both exited with code 0 on 2026-09-01 07:33 UTC. Restart policy is `unless-stopped`, so a manual stop keeps them down after reboot. (cmd: docker inspect --format State)
   - Also: `cineImport` and `immich_upload_from_disk.py` default to `http://127.0.0.1:2284`, so imports fail while the gateway is down. [I] (src: scripts/cine_import_menu.sh:46-47)
   - Fix: DUM-E has no action for this; the owner runs: `cd ~/homelab/cine-immich && docker compose up -d immich-gateway search-proxy` (MUTATES). Check first that this is wanted.
3. **Redis has no persistent storage.** [V]
   - `cine_immich_redis` has no mounts. Queues survive `restart`, but not `down`, `--force-recreate` or an image update. [I]
   - The scale guide wrongly says queues persist unless you run `down -v`. (src: guides/broll-face-scale-and-resume.md:58,76)
   - Fix (owner): add a volume for `/data` in the `redis` service. DUM-E has no action for this.
4. **Reindex aliases point at a container that no longer exists.** [V]
   - `triggerReindex` and `checkReindexStatus` call `cine_broll_face_worker`. The real container is `cine-immich-broll_face_worker-1`. (src: ~/.bashrc:150-151; cmd: docker ps -a)
   - Fix (owner): use `docker compose exec broll_face_worker python trigger_full_scan.py ...` from the stack folder, or edit the aliases. (src: guides/broll-face-scale-and-resume.md:23-27)
5. **Telegram progress notifications cannot reach the notifier.** [I]
   - `NOTIFIER_URL` defaults to `http://notifier:8000`. The notifier container sits only on network `notifier_default`. The face worker sits only on `cine-immich_cine-network`. So the name `notifier` does not resolve. (cmd: docker inspect --format Networks notifier-notifier-1 cine-immich-broll_face_worker-1)
   - The doc also says the host port is 8000; the notifier host port is 8001 (8000 is Portainer). (src: TELEGRAM_NOTIFICATIONS.md:20,131; DUM-E.md section 10.4)
6. **Redis exporter cannot see cine Redis.** [I]
   - `fortress-cine-immich-redis-exporter` is only on `fortress-network`, but `cine_immich_redis` is only on the cine network. It is also stopped. Grafana queue panels will be empty. (src: monitoring/docker-compose.yml:90-100; monitoring/prometheus/prometheus.yml:27-30; cmd: docker ps -a)
7. **Duplicate frame uploads cause Postgres errors.** [V]
   - `cine_immich_server` logged 52 "error" lines in 90 minutes, such as `duplicate key value violates unique constraint "UQ_assets_owner_checksum"`, while the face worker uploaded identical frames. Harmless but noisy. (cmd: docker logs --since 90m cine_immich_server | grep -ci error)
8. **Compose project name mismatch.** [V] + [U]
   - File says `name: cine_immich`; running containers say project `cine-immich` and network `cine-immich_cine-network`. (src: docker-compose.yml:40; cmd: docker inspect labels)
   - [U] If `.env` does not set `COMPOSE_PROJECT_NAME=cine-immich`, then `docker compose up -d` (and `fortress start cine_immich`) would try a new project and fail with "container name already in use".
9. **Machine-learning container flaps healthy/unhealthy at startup.** [V]
   - Microservices logged ML "became unhealthy" then "healthy" several times after boot on 2026-10-29. It settled. (cmd: docker logs --tail 12 cine_immich_microservices)
   - Past cause: gunicorn 300 s timeout while loading face models. Fixed by `-t 900`, pids 150 and thread limits. (src: GUIDE.md:224-241)
10. **Out-of-memory crashes during full scans (historical).** [V]
    - Cause: many parallel ffmpeg jobs. Fix in place: memory limits, concurrency 1, safe trigger mode. Exit codes 137/143 mean OOM. (src: GUIDE.md:189-220,415-418)
11. **Metadata timeout on big videos on HDD (historical).** [V]
    - Error `timeout: waited 120000ms`. Fixed by the patched server image and `IMMICH_METADATA_EXTRACTION_TIMEOUT_MS=600000`. After an Immich upgrade the patch may fail to apply at build time. (src: METADATA_TIMEOUT_FIX.md; technical-docs/IMMICH_METADATA_TIMEOUT_BUILD.md:121-147)
12. **"0 assets queued" after a trigger (historical).** [V]
    - Library scan only covers external libraries. The script now queues assets itself. Status needs an admin API key. (src: GUIDE.md:245-263)
13. **"libgomp: Thread creation failed".** [V]
    - Fix in place: `OMP_NUM_THREADS=2` and related variables in the worker. (src: docker-compose.yml:379-383; WHY_HARDER_THAN_SIMPLE_IMMICH.md:124-135)
14. **Zero-byte encoded videos (historical).** [V]
    - 419 broken transcodes were repaired on 2026-03-28 with `repair_zero_byte_encoded_videos.py`. (src: logs/repair_zero_byte_encoded.log)
15. **Not in the default profile but marked default.** [V]
    - `services.yaml` sets `default: true`, but the boot profile omits `cine_immich`. When it was down (2026-10-19/20), hourly health checks raised duplicate "not running" incidents. (src: services.yaml:50; ~/.config/fortress-control/profiles/default.json; ~/.local/state/homelab/incidents.log:5771-5800)
16. **Both Immich stacks run at once.** [V]
    - The orchestration quick reference says "Don't run both Immich and Cine-Immich together". Both are running. (src: library/08-orchestration/guides/QUICK_REFERENCE.md:115; cmd: docker ps)
17. **Photo backup is not working.** [V]
    - The weekly photo backup of `/mnt/photos` failed on its only logged run (2026-10-04) with "Setup incomplete". (src: /mnt/backup-volume/vault-backup/logs/cron-photos.log) See manual 21-immich.

When the GPU is too full for the AI brain: the watchdog handles it. DUM-E may use `watchdog_clear_pause` or `llama_restart` with approval. DUM-E must not stop cine containers by itself.

## Logs
- Container logs: `docker logs --tail 50 <name>` for `cine_immich_server`, `cine_immich_microservices`, `cine_immich_machine_learning`, `cine_broll_worker`, `cine_broll_watcher`, `cine-immich-broll_face_worker-1`, `cine_immich_gateway`, `cine_search_proxy`. [V] (src: COMMANDS.md:28-50)
  - In `cine_broll_worker` look for: `Claimed job`, `Processing`, `broll_perf_failed`, `moov atom not found`, `Could not generate description`, `Killed`.
  - In `cine_immich_microservices` look for: `fetch failed`, `Machine learning request failed`, `waited 120000ms`, `Unable to run job handler`.
  - In `cine_immich_machine_learning` look for: `CRITICAL WORKER TIMEOUT`, `can't start new thread`, `Application startup complete`.
- `/mnt/photos/ai_cache/broll_forensics.jsonl` — per-video B-roll outcome lines. [V] (src: docker-compose.yml:369)
- `/mnt/photos/ai_cache/broll_description_ledger.jsonl` — description version history. [V] (src: docker-compose.yml:374)
- `~/homelab/cine-immich/logs/migrate-*.log`, `overnight-*.log`, `repair_zero_byte_encoded.log`, `vram_peak_*.log`. [V] (cmd: ls -la logs)
- `scripts/migrate-limit1.log` — a migration test that ended with `EXIT:143` (killed) during upload on 2026-03-25. [V] (src: scripts/migrate-limit1.log)
- Homelab incidents: `~/.local/state/homelab/incidents.log`, source `cine_immich`. [V]
- Grafana dashboard "Cine-Immich Operations": `homelab/monitoring/grafana/provisioning/dashboards/json/cine-immich-operations.json`. [V] (cmd: grep -rl)

## Rules for DUM-E here
- Never run `docker exec`, `redis-cli` writes, `docker compose up/down/restart/stop/build`, or `docker rm` in this stack.
- Never open `.env`. Never print an Immich API key.
- Never list or read `/mnt/photos` contents or `postgres_cine/`. They are private.
- `service_start cine_immich` and `service_stop cine_immich` exist as approvable actions. `service_stop` runs `docker compose stop` (containers kept). Before proposing either, check item 8 above, and warn that stopping breaks the B-roll pipeline. [V] (src: homelab/control/lib/actions.sh:38-50)
- Do not suggest `triggerReindex --aggressive`.
- DELETES operations that exist here (never run them; only name them):
  - `clearRedisQueues` (`redis-cli DEL broll_queue broll_face_queue`)
  - `redis-cli FLUSHALL`
  - `redis-cli LREM broll_queue ...`
  - `trigger_full_scan.py --empty`
  - `docker compose down` / `stopCine` (also loses Redis queues)
  - `docker compose down -v`
  - `docker compose up -d --force-recreate` / `restartCineAll` (loses Redis queues)
  - `run_immich_migrate.sh -y` and `migrate_immich_large_videos.py` without `--dry-run` (trashes source assets in standard Immich)
  - `run_immich_migrate_in_screen.sh`, `run_overnight_reliability.sh` (run the migration)
  - `repair_zero_byte_encoded_videos.py` (`sudo rm -f` encoded files)
  - `docker rm -f cine_broll_face_worker`
  - deleting partial downloads in `model-cache/` (suggested by GUIDE.md:457)

## Open questions
- [U] Does `.env` set `COMPOSE_PROJECT_NAME=cine-immich`? Settle: owner runs `grep -c '^COMPOSE_PROJECT_NAME=cine-immich' ~/homelab/cine-immich/.env` (prints a count only).
- [U] Why were the gateway and search proxy stopped on 2026-09-01? Settle: ask the owner; check shell history around that date.
- [U] How many jobs are in `broll_queue`, `broll_queue_processing` and `broll_face_queue`? DUM-E cannot read Redis. Settle: owner runs `checkBrollQueue` and `checkFaceQueue`, or start the exporter on the cine network.
- [U] How large is the `cine_broll_worker` log file? Settle: owner runs `sudo du -sh /var/lib/docker/containers/*/` and matches the container id.
- [U] Is `IMMICH_METADATA_EXTRACTION_TIMEOUT_MS=600000` still set? Settle: owner runs `grep -c '^IMMICH_METADATA_EXTRACTION_TIMEOUT_MS=600000' ~/homelab/cine-immich/.env`.
- [U] Face model: config says `buffalo_l`, docs say `antelopev2`. Which one is loaded? Settle: read ML log lines "Loading detection model".
- [U] Is the old `postgres/` folder safe to remove? Settle: owner confirms nothing uses it; only then, by hand.
- [U] Is `/dev/sda2` (alias `mount_immich_ssd`) still the right device for the source SSD? Settle: owner runs `lsblk -o NAME,FSTYPE,LABEL,SIZE` with the SSD plugged in.
