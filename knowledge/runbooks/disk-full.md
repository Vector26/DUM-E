---
title: Disk full
symptom: A disk is almost full (root at 88 % or more, or a mount above 90 %)
last_verified: 2026-10-30
related: 01-machine, 33-memory-swap-oom
---

# Disk full

## Symptom
- `dume doctor` lists "Filesystem <mount> is NN% full" (the limit is 90 %). [V]
- Builds, pulls or the AI log start failing with "No space left on device". [I]

## Quick check
1. `disk_memory {}` - look for: which mount is high, the swap use, and the large known log files.

## Diagnosis
1. Which mount is high? [V]
   - `/` is 234 GB and a separate disk from `/home`. Files in `~/` do not fill `/`. On 2026-10-30 it was 88 % used (27 GB free). [V]
   - `/home` is 672 GB and 29 % used. [V]
   - `/mnt/backup-volume` is 1.9 TB and 16 % used. [V]
   - `/mnt/win_nvme0_recovery` is a 695 MB Windows recovery partition at 91 %. Ignore it. [V]
2. `/` is high -> Docker is the usual cause (`/var/lib/docker`: images, volumes, build cache). The owner checks with `docker system df`. [I]
3. `/mnt/backup-volume` is high -> backup logs and cache. Read `backup {}`. [I]
4. `/home` is high -> read the large log list in `disk_memory {}`.

## Fix
Docker images are the one thing DUM-E may propose to free space, and only through one approved action. Everything else is owner-run and DELETES.
1. Run `image_cleanup_preview {}` (read-only dry run) and show the owner what it would remove and what it keeps. [V]
2. If the owner wants it, propose `docker_image_cleanup_run`. It DELETES unused images and long-stopped containers of registered stacks, and the owner must type `PRUNE IMAGES`. It is the same script cron runs every Sunday 07:30 (`homelab/control/docker-image-cleanup.py`; log: `log_tail log=image_cleanup`). [V]
3. The script skips cine-immich, anything in `docker-image-cleanup.keep`, and anything used by a running container. Images are pulled or rebuilt when a stack starts again. [V]
- Owner-run, not proposed by DUM-E: `sudo journalctl --vacuum-size=1G` (**DELETES:** old journal entries), `docker builder prune` (**DELETES:** build cache).
- **Volumes are never deleted.** Never propose or suggest `docker volume prune|rm`, `docker system prune --volumes`, or `docker compose down -v`. A guard at `/usr/local/bin/docker` refuses them, and the cleanup script cannot issue a volume command. [V]

## Verify
- `disk_memory {}` shows lower use on the mount.

## Do not
- Do not propose any deletion except `docker_image_cleanup_run`, and only after showing `image_cleanup_preview`. Describe the rest and let the owner decide.
- Do not touch volumes, and do not touch cine-immich images or containers.
- Do not touch `~/homelab/NOTION-DATA [DO NOT REMOVE OR TOUCH]`.
- Do not add swap on `/`. It uses more of the full disk.

## Sources
- `df -h` (this session)
- manual 01-machine, 33-memory-swap-oom
- `~/homelab/DUM-E/lib/dume/tools.py` (disk_memory)
