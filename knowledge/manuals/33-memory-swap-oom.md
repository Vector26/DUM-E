---
title: Memory, Swap, OOM and Disks
scope: RAM, zram and swap file, zswap, the OOM protection stack (earlyoom, systemd-oomd, oom-check timer, sysctl), hd-idle, disks and mounts, and why the root filesystem is 91 % full
last_verified: 2026-10-29
sources: free -h, swapon --show, systemctl cat/status zram.service earlyoom systemd-oomd oom-check-memory.timer hd-idle, /etc/default/earlyoom, /etc/default/hd-idle, /etc/sysctl.d/99-oom-protection.conf, /etc/systemd/system.conf.d/50-oom-protection.conf, /etc/oom-protection/graceful-unmount.list, ~/oom-protection/, ~/scripts/add_swap_8g.sh, df -h, lsblk, /etc/fstab, /etc/docker/daemon.json, du -xh --max-depth=1 on / and ~/
---

# Memory, Swap, OOM and Disks

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
The homelab has 30 GiB of RAM and 23 GiB of swap. Swap is a 15.1 GiB compressed RAM disk (zram) plus an 8 GiB swap file. [V] (cmd: free -h; swapon --show)
Three things can kill processes when memory runs out: earlyoom, systemd-oomd, and the kernel OOM killer. A timer also checks memory every 30 s. [V] (cmd: systemctl status earlyoom systemd-oomd oom-check-memory.timer)
Data lives on two NVMe drives and three USB drives. [V] (cmd: lsblk)
The root filesystem `/` is 91 % full (21 GB free of 234 GB). `/home` is a separate partition and is only 29 % full. [V] (cmd: df -h)

## How the owner refers to it
- "zram", "ZRAM compressed swap (ComfyUI / large-model host)" — the unit description. [V] (cmd: systemctl cat zram.service)
- "OOM protection", "Global OOM Protection" — `~/oom-protection/`. [V] (src: ~/oom-protection/README.md:1)
- "add swap", `add_swap_8g.sh`. [V] (src: ~/scripts/add_swap_8g.sh:2)
- Mount names: `/mnt/backup-volume` ("Expansion" USB HDD, backups), `/mnt/photos` ("ImmichData"), `/mnt/win_nvme0` (Windows). [V] (cmd: lsblk -o …LABEL,MODEL)
- No `.bashrc` aliases for these. [I] (src: DUM-E.md section 7.2 alias list)

## Components
- **RAM** — 30 GiB total (30,963 MiB). At 22:3x: 9.4 GiB used, 1.3 GiB free, 20 GiB buff/cache, 20 GiB available. [V] (cmd: free -h)
- **zram.service** (system unit `/etc/systemd/system/zram.service`) — oneshot, `RemainAfterExit=yes`, `Before=swap.target`. Start: `modprobe zram`, compression `lz4`, disksize = MemTotal(kB) × 512 bytes (= 50 % of RAM), `mkswap -f /dev/zram0`, `swapon -p 100 /dev/zram0`. Stop: `swapoff /dev/zram0`, `echo 1 > /sys/block/zram0/reset`. Enabled; active (exited) since 21:05:58. [V] (cmd: systemctl cat zram.service; systemctl status zram.service)
- **/dev/zram0** — 15.1 GiB, priority 100, 9 GiB used now. [V] (cmd: swapon --show)
- **/swap.img** — 8 GiB swap file on `/` (root fs), priority -2, 0 B used. Listed in `/etc/fstab`. [V] (cmd: swapon --show; ls -la /swap.img; cat /etc/fstab)
- **zswap** is also enabled: `enabled=Y`, compressor `lzo`, pool `zsmalloc`, `max_pool_percent=25`. [V] (cmd: cat /sys/module/zswap/parameters/*)
- **VM settings**: `vm.swappiness=60`, `vm.vfs_cache_pressure=100`, `vm.overcommit_memory=0`, `vm.max_map_count=1048576`, `vm.oom_kill_allocating_task=1`. [V] (cmd: cat /proc/sys/vm/*; grep /etc/sysctl.d)
- **earlyoom.service** — active since 21:05:58, PID 1401, running `/usr/bin/earlyoom -r 3600`. Policy in effect (from its log): SIGTERM when mem ≤ 10 % **and** swap ≤ 10 %; SIGKILL when mem ≤ 5 % **and** swap ≤ 5 %. [V] (cmd: systemctl status earlyoom)
- earlyoom drop-in `/etc/systemd/system/earlyoom.service.d/override.conf`: `OOMScoreAdjust=-100`, `Nice=-20`. [V]
- `/etc/default/earlyoom` contains only `EARLYOOM_ARGS="-r 3600"`. [V] (cmd: cat, comments stripped)
- **systemd-oomd.service** — active since 21:05:58. [V] (cmd: systemctl status systemd-oomd)
- **oom-check-memory.timer** — enabled, every 30 s (`OnBootSec=1min`, `OnUnitActiveSec=30`). Runs `oom-check-memory.service` → `/usr/local/bin/oom-check-memory.sh` (Nice 19, `OOMScoreAdjust=1000`). [V] (cmd: systemctl status oom-check-memory.timer; src: ~/oom-protection/etc/systemd/system/oom-check-memory.{timer,service})
- `oom-check-memory.sh`: if MemAvailable < 15 % of MemTotal, runs `/usr/local/bin/oom-graceful-unmount.sh`. [V] (src: ~/oom-protection/scripts/oom-check-memory.sh:7,15-25)
- `oom-graceful-unmount.sh`: `sync` twice, then `umount -l` each mount listed in `/etc/oom-protection/graceful-unmount.list`. If that file is missing, it lazily unmounts every mount under `/mnt/*` and `/media/*`. [V] (src: ~/oom-protection/scripts/oom-graceful-unmount.sh:13-47)
- `/etc/oom-protection/graceful-unmount.list` exists and has only comment lines, so nothing is unmounted today. [V] (cmd: grep -v '^#')
- Installed scripts in `/usr/local/bin/` are identical to `~/oom-protection/scripts/`. [V] (cmd: cmp)
- `/etc/systemd/system.conf.d/50-oom-protection.conf`: `DefaultOOMPolicy=stop`. [V] (cmd: ls; src: ~/oom-protection/etc/systemd/system.conf.d/50-oom-protection.conf)
- **hd-idle.service** — active since 21:05:58, PID 1416, `/usr/sbin/hd-idle -i 0 -a sdc -i 1200`. Meaning: no spin-down by default; disk `sdc` after 1200 s idle. [V] (cmd: systemctl status hd-idle; cat /etc/default/hd-idle)
- **Disks** [V] (cmd: lsblk -o NAME,SIZE,MOUNTPOINT,FSTYPE; lsblk -o …UUID,LABEL,MODEL,TRAN; df -h):
  - `nvme1n1` 238.5 G: `p1` 1 G vfat `/boot/efi`; `p2` 237.4 G ext4 `/` (234 G, 203 G used, 21 G free, 91 %).
  - `nvme0n1` 931.5 G: `p1` 200 M vfat; `p2` 16 M; `p3` 247 G ntfs `/mnt/win_nvme0` (25 %); `p4` 695 M ntfs `/mnt/win_nvme0_recovery` (91 %, Windows recovery); `p5` 683.6 G ext4 `/home` (672 G, 184 G used, 454 G free, 29 %).
  - `sda` 1.8 T "Expansion HDD" (USB): `sda1` exfat, label Expansion, `/mnt/backup-volume` (16 %).
  - `sdb` 1.8 T WD (USB): `sdb1` ext4, label ImmichData, `/mnt/photos` (58 %).
  - `sdc` 931.5 G "Portable SSD" (USB): `sdc1` 200 M vfat EFI; `sdc2` 931.3 G, no filesystem shown, not mounted.
  - `zram0` 15.1 G swap.
- **Docker** data root is the default `/var/lib/docker` on `/`. `daemon.json` only adds the `nvidia` runtime. [V] (cmd: cat /etc/docker/daemon.json)

## Files and data
- `/etc/fstab` — read-only reference. Entries: `/` (by UUID), `/boot/efi`, `/swap.img none swap sw`, `/home` (ext4), `/mnt/photos` (ext4, `nofail`), `/mnt/ollama_hdd` (ext4, `nofail`), `/mnt/backup-volume` (exfat, `uid=1000,gid=1000,…,nofail`), `/mnt/movie-storage` (ext4, `nofail`), `/mnt/win_nvme0` and `/mnt/win_nvme0_recovery` (ntfs3, `nofail`). [V] (cmd: cat /etc/fstab)
- The UUIDs for `/mnt/ollama_hdd` and `/mnt/movie-storage` are not present on this machine, so those two never mount. [V] (cmd: ls /dev/disk/by-uuid | grep → none)
- Empty mount-point folders on `/`: `/mnt/{cine-immich-source, cine-import, dest_drive, movie-storage, newhome, oldhome, ollama_hdd, sandisk_write_test, source_drive, ssd_source, tmp_sda}`. All of `/mnt` uses only 188 K on `/`; `/mnt/movie-storage` holds 160 K. [V] (cmd: ls /mnt; du)
- `/swap.img` — 8 GiB, root-owned, mode 600, on `/`. [V]
- `~/scripts/add_swap_8g.sh` — swap-file creator. [V]
- `~/oom-protection/` — source of the OOM stack: `README.md`, `install.sh`, `scripts/`, `etc/`. [V]
- `~/oom-protection/etc/default/earlyoom` — the intended earlyoom config (`-m 12,10 -s 15,12 -r 0 --avoid '^(systemd|sshd|earlyoom|containerd)' --prefer '^(python|node|java|ollama|comfy|python3)'`). It was **not** installed. [V] (src: that file:3; cmd: cat /etc/default/earlyoom)
- `/etc/default/hd-idle` — `HD_IDLE_OPTS="-i 0 -a sdc -i 1200"`. [V]
- `/var/log/journal` — 3.6 G on `/`. [V] (cmd: du -xh --max-depth=2 /var)
- PRIVATE: `~/homelab/life-archive-data` (35 G). Named only for size. [V] (cmd: du)

## Commands
- `free -h` — READ. [V]
- `swapon --show` — READ. [V]
- `df -h` — READ. [V]
- `lsblk -o NAME,SIZE,MOUNTPOINT,FSTYPE` — READ. [V]
- `cat /etc/fstab` — READ. [V]
- `du -xh --max-depth=1 ~/` — READ (slow, minutes). [V]
- `du -xh --max-depth=1 / 2>/dev/null` — READ; root-only folders are skipped silently. [V]
- `systemctl cat zram.service` / `systemctl status zram.service earlyoom systemd-oomd hd-idle oom-check-memory.timer` — READ. [V]
- `cat /sys/module/zswap/parameters/enabled` — READ. [V]
- `sudo bash ~/scripts/add_swap_8g.sh [path] [GB]` — creates `/swap2.img` (default) with `dd if=/dev/zero` (8 GiB), `chmod 600`, `mkswap`, `swapon`, then asks whether to append a line to `/etc/fstab`. Refuses without root. If the file exists, it only prints status. MUTATES (uses 8 GB of disk; may edit fstab). [V] (src: add_swap_8g.sh:6-38) `/swap2.img` does not exist today. [V] (cmd: ls)
- `sudo ./install.sh` in `~/oom-protection` — installs scripts, config, earlyoom package, systemd units, sysctl; enables earlyoom and the timer. Keeps an existing `EARLYOOM_ARGS` line. MUTATES. [V] (src: ~/oom-protection/install.sh:12-64)
- Uninstall block in the README: many `sudo rm -f …` and `sudo rm -rf /etc/systemd/system/earlyoom.service.d`. DELETES. [V] (src: ~/oom-protection/README.md:44-58)
- `sudo systemctl restart earlyoom` — MUTATES (applies `/etc/default/earlyoom`). [V] (src: README.md:35)
- `/usr/local/bin/oom-graceful-unmount.sh` (run by hand as root) — syncs and lazily unmounts listed mounts. MUTATES. [V]
- `sudo systemctl stop zram.service` — runs `swapoff /dev/zram0` and resets it: with 9 GiB in zram this pushes pages back to RAM or the swap file. MUTATES, risky. [V] unit; [I] effect.
- Owner-only space tools (none run here): `docker system df` (READ, needs docker access), `docker image prune` / `docker system prune` (DELETES), `sudo journalctl --vacuum-size=<size>` (DELETES old journal), `sudo apt clean` (DELETES package cache, 604 M), removing old snap revisions (DELETES). [I] (general Linux knowledge; sizes from du)

## Depends on
- GPU: no direct link. But large models spill RAM: llama-server keeps MoE experts in CPU RAM; Ollama and ComfyUI are the stated reason for zram and extra swap. [V] (src: llama-server-ctl usage text "MoE experts on CPU RAM"; zram unit description; add_swap_8g.sh:3)
- The AI brain on :8081 and Ollama :11434 are the biggest RAM users when loaded. [I] (src: DUM-E.md section 4: 4 slots, 262k context, `LLAMA_NCMOE=32`)
- Docker: most of `/` is Docker data. [I] (see Known problems)
- Backups write to `/mnt/backup-volume` (vault-backup logs live there). [V] (src: DUM-E.md section 10.1)
- Immich data lives on `/mnt/photos`. [I] (label ImmichData)
- System monitor verdicts: disk ≥ 90 % = "Problem", ≥ 70 % = "Watch"; RAM available < 2 GB = "Problem", < 4 GB = "Watch". So `/` shows red in `sys-check`/`plaintop`. [V] (src: homelab/system-monitor/verdicts.py:49-54,229-235)

## How to check it (read-only)
- DUM-E tool `disk_memory` — `df -h` on `/`, `/mnt/backup-volume`, `/mnt/photos`, plus RAM and swap. [V] (src: DUM-E.md:619)
- DUM-E tool `snapshot` — includes disk `/` and RAM/swap. [V] (src: DUM-E.md section 2)
- DUM-E tool `services` — state of `zram.service`, `earlyoom`, `systemd-oomd`, `hd-idle`, `oom-check-memory.timer` if they are in the unit allowlist. [U] (allowlist not defined yet)
- DUM-E tool `health` — `fortress health` includes disk checks. [I]
- DUM-E tool `containers` — big containers explain Docker disk use. [I]
- DUM-E tool `manual` — this file. [I]
- Owner, read-only: `free -h`, `swapon --show`, `df -h /`, `lsblk -o NAME,SIZE,MOUNTPOINT,FSTYPE`. [V]
- Owner, read-only: `systemctl status earlyoom --no-pager` — the last lines show the thresholds and periodic memory reports. [V]
- Owner, needs sudo (read-only): `sudo du -xh --max-depth=1 /var/lib/docker` and `sudo docker system df`. [U] not run here.

## Known problems and fixes
- **Root filesystem 91 % full.** 21 G free of 234 G. [V] (cmd: df -h) Readable folders on `/` add up to about 55 G: `/usr` 29 G, `/var` 11 G (`/var/lib/snapd` 6.0 G, `/var/log/journal` 3.6 G, `/var/cache/apt` 604 M), `/data` 5.8 G (`/data/ai_cache`), `/swap.img` 8 G, `/boot` 518 M, `/opt` 409 M, `/home_backup` 301 M. [V] (cmd: du -xh --max-depth=1 /; du -xh --max-depth=2 /var) The other ~148 G sits in folders `(owner)` cannot read; the largest is almost certainly `/var/lib/docker` (mode 710 root) with `/var/lib/containerd`. [I] (203 G used − 55 G readable; Docker data root is the default) Exact Docker size [U]. Fix (owner): measure with `sudo du -xh --max-depth=1 /var/lib/docker` and `sudo docker system df`; then prune unused images/build cache, vacuum the journal, `apt clean`, remove old snap revisions, or move Docker's data root to `/home` (454 G free). DUM-E has no action for this.
- **Cleaning `~/` does not help `/`.** `/home` is its own partition. `~/` is 146 G there (`fortress` 69 G, `models` 40 G, `immich` 12 G, `.cache` 6.6 G, `.cursor-server` 5.0 G). [V] (cmd: df -h; du -xh --max-depth=1 ~/)
- **Running `add_swap_8g.sh` now would take 8 G of the 21 G free on `/`.** [V] (src: add_swap_8g.sh:6,21; cmd: df) Do not run it unless the path is moved to `/home` (pass a path argument). Owner only.
- **The intended earlyoom policy is not active.** `install.sh` skips the config when `EARLYOOM_ARGS` already exists, and it did: the live file has only `-r 3600`. So no `--avoid`/`--prefer` lists and default thresholds. [V] (src: ~/oom-protection/install.sh:35-40; cmd: cat /etc/default/earlyoom; systemctl status earlyoom) Fix (owner): edit `/etc/default/earlyoom` and `sudo systemctl restart earlyoom`. DUM-E has no action for this.
- **earlyoom acts only when memory and swap are both low.** With 23 G swap, RAM can be exhausted long before swap is ≤ 10 % free, so the machine may thrash in swap first. [V] rule (earlyoom log line); [I] effect.
- **`vm.oom_kill_allocating_task=1`** makes the kernel kill whichever task asked for memory, which can be a small innocent process (for example sshd or a shell) instead of the big model. [V] setting; [I] effect.
- **Three OOM killers overlap** (earlyoom, systemd-oomd, kernel). Which one fires first is not defined by config here. [V] all active; [I] overlap. Check after any crash: `journalctl -u earlyoom`, `journalctl -u systemd-oomd`, `journalctl -k | grep -i oom` (owner).
- **zswap and zram are both on.** zswap compresses pages before they reach swap, and the main swap is itself compressed (zram). This double work wastes CPU and RAM. [V] both enabled; [I] effect. Fix (owner): disable zswap (`zswap.enabled=0` kernel parameter) or remove zram. DUM-E has no action for this.
- **9 G in zram while 20 G RAM is free.** Pages swapped out during a model load stay in zram until touched. Not harmful by itself. [V] numbers; [I] cause.
- **Graceful-unmount fallback is dangerous.** If `/etc/oom-protection/graceful-unmount.list` is ever deleted, low memory would lazily unmount every `/mnt/*` mount, including `/mnt/backup-volume` (backups) and `/mnt/photos`. Writers would then fill `/` instead. [V] (src: oom-graceful-unmount.sh:34-47); [I] consequence. Fix (owner): change the script to do nothing when the list is missing. DUM-E must never delete that list.
- **Missing mounts write to `/`.** `nofail` lets boot continue without a disk; anything then written under `/mnt/<name>` lands on `/`. Today all are tiny. [V] (cmd: du /mnt) [I] risk.
- **Two fstab entries point to absent disks** (`/mnt/ollama_hdd`, `/mnt/movie-storage`). [V] Harmless with `nofail`; clean up later (owner).
- **hd-idle targets an SSD.** `sdc` is a "Portable SSD", not mounted; spinning it down does nothing useful. The two real HDDs (`sda`, `sdb`) are never spun down. [V] (cmd: lsblk MODEL; hd-idle args) [I] intent unknown.
- **Windows recovery partition shows 91 %.** It is `nvme0n1p4`, 695 M. Ignore it; the system monitor also ignores it. [V] (cmd: df; src: collectors.py:274-291)

## Logs
- earlyoom: system journal (`systemctl status earlyoom` shows the tail). With `-r 3600` it prints a memory report every hour. Kill lines start with "sending SIGTERM" / "sending SIGKILL". [V] (cmd: systemctl status earlyoom)
- systemd-oomd: system journal. [V]
- oom-graceful-unmount: journal tag `oom-graceful-unmount` ("Syncing filesystems…", "Unmounted (lazy): …", "Done. Unmounted N mount(s)."). [V] (src: oom-graceful-unmount.sh:9-11,50)
- Kernel OOM: `journalctl -k`, lines with "Out of memory" / "oom-kill". [I]
- hd-idle and zram: system journal; zram prints "Setting up swapspace version 1, size = 15.1 GiB" at boot. [V] (cmd: systemctl status zram.service)

## Rules for DUM-E here
- DUM-E must never delete anything here. That includes Docker images, volumes, journal files, swap files, package caches, snap revisions, files under `/home`, and `/etc/oom-protection/graceful-unmount.list`. [V] (DUM-E.md section 12.0; task rules)
- DUM-E must never run `add_swap_8g.sh`, `swapon`, `swapoff`, `mkswap`, `umount`, `oom-graceful-unmount.sh`, `~/oom-protection/install.sh`, or edit `/etc/fstab`, `/etc/default/earlyoom`, sysctl files, or zram settings. [V] (task rules)
- DUM-E must never stop or restart `zram.service`, `earlyoom`, `systemd-oomd`, `hd-idle`, or the OOM timer.
- For Docker images DUM-E can show `image_cleanup_preview` and propose `docker_image_cleanup_run` (DELETES; owner types `PRUNE IMAGES`; images only, never volumes). Anything else (journal, apt, snap) the owner runs after measuring with `sudo docker system df`. See runbook:disk-full.
- If RAM is the problem and a model is loaded, DUM-E may propose `ollama_unload` or `llama_stop` (approved actions), after naming who depends on them. [V] (src: DUM-E.md:633-635)
- DELETES operations that exist here:
  - `oom-graceful-unmount.sh` lazily unmounts filesystems (not a file delete, but it cuts writers off from their disk). [V]
  - `add_swap_8g.sh` writes 8 GiB with `dd` to a new file and may append to `/etc/fstab`. It refuses to overwrite an existing file. [V] (src: add_swap_8g.sh:14-18,21,36)
  - The oom-protection README uninstall block (`sudo rm -f …`, `sudo rm -rf …`). [V]
  - `zram.service` stop resets `/dev/zram0` (`echo 1 > reset`), discarding its contents after swapoff. [V]
  - `mkswap -f` in `zram.service` formats `/dev/zram0` at every start. [V]
  - Owner-side cleanup commands (`docker … prune`, `journalctl --vacuum-*`, `apt clean`, snap removal) all delete data. [I]

## Open questions
- How big is `/var/lib/docker`, and which images, volumes or build cache dominate? [U] Settle: owner runs `sudo du -xh --max-depth=1 /var/lib/docker` and `sudo docker system df -v`.
- What else is in the ~148 G that `(owner)` cannot read (`/root`, `/var/lib/containerd`, other root-only dirs)? [U] Settle: owner runs `sudo du -xh --max-depth=1 /` .
- Has earlyoom, systemd-oomd or the kernel killed anything recently? Only this boot's status tail was seen (no kills). [V] partial; history [U]. Settle: owner runs `journalctl -u earlyoom -u systemd-oomd --since -30d | grep -i -E 'sending|kill'` and `journalctl -k --since -30d | grep -i oom`.
- What is on `sdc2` (931 G, no filesystem shown)? [U] Settle: owner runs `sudo blkid /dev/sdc2`.
- Is the systemd-oomd policy applied to any slice (user or system)? [U] Settle: `oomctl` (owner, read-only).
- Why is `/data/ai_cache` (5.8 G) on `/`? Which tool writes it? [U] Settle: owner lists `/data/ai_cache`.
