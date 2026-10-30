---
title: The machine (homelab-host)
scope: Hardware, disks and partitions, swap, network identity, users and privileges, time zone
last_verified: 2026-10-29
sources: lscpu, nvidia-smi, free, df, swapon, lsblk-equivalent df output, mesh-vpn status, sudo -l, systemctl cat zram.service
---

# The machine (homelab-host)

## What it is
One Linux workstation/server that runs everything in the homelab: Docker stacks, the local AI model on the GPU, backups, monitoring and small scripts. The owner's account is `owner`. The host name is `homelab-host` (src: sudo -l output "User owner may run ... on homelab-host") [V]; on Mesh VPN (e.g. Tailscale) it appears as `homelab-host` (cmd: mesh-vpn status) [V].

## How the owner refers to it
"the server", "the box", "homelab-host", "the homelab" (the homelab is the set of projects in `~/homelab`; the machine is what runs them). `nextplan.md` calls it the "Batcomputer" [V].

## Components
- CPU: AMD host CPU, 8 cores (cmd: lscpu) [V].
- RAM: 30 GiB usable (30,963 MiB as reported by llama.cpp) (cmd: free -h; src: llama log) [V]. The owner's notes say 32 GB; 30 GiB is what the OS sees [V].
- GPU: NVIDIA GeForce discrete GPU (example: 16 GB VRAM), 16,303 MiB VRAM, driver 580.159.03 (cmd: nvidia-smi) [V]. llama.cpp reports 15,831 MiB usable [V].
- Integrated AMD GPU: used for the display when the NVIDIA driver is unloaded by `powersaver` (src: .bashrc power functions) [V].
- UPS: a UPS exporter container runs (`fortress-ups-exporter`) [V]; UPS model unknown [U].

## Files and data
Disks and mount points (cmd: df -h, 2026-10-29) [V]:
| Mount | Device | Size | Used | Notes |
|---|---|---|---|---|
| `/` | /dev/nvme1n1p2 | 234 GB | 91 % (21 GB free) | System, Docker data (`/var/lib/docker`, 146 GB), swap file |
| `/home` | /dev/nvme0n1p5 | 672 GB | 29 % | Owner files, `~/homelab`, models, AI logs |
| `/mnt/backup-volume` | /dev/sda1 | 1.9 TB | 16 % | "Expansion" USB HDD: backup cache/logs, model cold storage |
| `/mnt/photos` | /dev/sdb1 | 1.8 TB | 58 % | Photo library (PRIVATE) |
| `/mnt/win_nvme0`, `/mnt/win_nvme0_recovery` | nvme0n1p3/p4 | 248 GB / 695 MB | 25 % / 91 % | Windows partitions; the recovery partition is always nearly full and is not a problem [I] |
| `/boot/efi` | nvme1n1p1 | 1.1 GB | 1 % | |

Important: `/home` is a separate partition. Files in `~/` (including the 31 MB llama log) do NOT fill `/` [V].

What fills `/` (cmd: sudo du -xsh, docker system df, 2026-10-29) [V]:
- `/var/lib/docker` 146 GB: images 64.6 GB (59.5 GB not used by a running container), volumes 38 GB (19.8 GB not attached to a running container; these can hold data of stopped stacks such as mediastack), build cache 17 GB, containers 0.95 GB.
- `/usr` 24 GB, `/swap.img` 8.1 GB, `/var/lib/snapd` 6.3 GB, `/usr/share/ollama` 5.2 GB, `/var/log` 3.9 GB (journal 3.3 GB), `/var/cache` 3.4 GB.

Swap (cmd: swapon --show) [V]:
- `/dev/zram0`: 15.1 GB compressed RAM swap, priority 100, created at boot by `zram.service` (lz4, 50 % of RAM) (src: /etc/systemd/system/zram.service) [V].
- `/swap.img`: 8 GB swap file on `/`, priority -2 (used only after zram) [V].
- `~/scripts/add_swap_8g.sh` exists (src: ls ~/scripts) [V]; see manual 33.

## Commands
- `df -h`, `free -h`, `swapon --show`, `lscpu`, `nvidia-smi` - READ.
- `docker system df` - READ (sizes only).
- Disk cleanup: Docker images go through the weekly cron script (`docker_image_cleanup_run` if the owner approves; images only, never volumes). `journalctl --vacuum-size=...` is DELETES and owner only. See runbook:disk-full.

## Depends on
Nothing; this is the base.

## How to check it (read-only)
- DUM-E tools: `snapshot` (overview), `disk_memory` (filesystems, RAM, swap, big logs), `gpu`.

## Known problems and fixes
- Root filesystem 91 % full (2026-10-29) [V]. Cause: Docker images/volumes/build cache. Fix is the owner's decision; see runbook:disk-full. DUM-E cannot delete anything.
- High swap use (8.8 GB of zram used on 2026-10-29) [V] is expected: the AI server keeps MoE expert weights in RAM (`-ncmoe 32`), and many containers run [I].

## Logs
- System journal: `journalctl` (3.3 GB) [V].

## Rules for DUM-E here
- Privileges: the owner account has passwordless sudo for everything (`(ALL) NOPASSWD: ALL`) (cmd: sudo -n -l) [V]. That is why DUM-E runs as its own user `dume`, which cannot use sudo except for the one DUM-E gateway rule. DUM-E never runs sudo.
- Time zone: India Standard Time, +05:30 (timestamps in logs) [V].

## Open questions
- UPS model and runtime [U]: check the ups-exporter metrics in Prometheus.
- Why `/usr/share/ollama` is only 5.2 GB although `ollama list` shows a 23 GB model [U]: the models folder may be a symlink to another disk; check `ls -la /usr/share/ollama/.ollama`.
