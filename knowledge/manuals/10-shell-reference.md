---
title: The owner's shell (bashrc) reference
scope: Aliases and functions in ~/.bashrc grouped by purpose, with their class (READ / MUTATES / DELETES) and DUM-E's equivalent
last_verified: 2026-10-29
sources: ~/.bashrc (609 lines; 72 alias lines, 11 function definitions at top level), shell_index tool
---

# The owner's shell (bashrc) reference

## What it is
Most of the owner's day-to-day control of the homelab is through short aliases and functions in `~/.bashrc`. DUM-E cannot run them (they only exist in an interactive shell), but knowing them lets DUM-E understand the owner and tell them the right command. The `shell_index` tool lists them live (secrets and exports are never shown) [V].

## How the owner refers to it
By the alias names below.

## Components
AI and GPU [V]:
- `pi` (function): runs the pi agent; starts the AI brain first if pi's default provider is `llama-hauhaucs`. MUTATES (may start the AI).
- `pih` -> `~/bin/pi-hauhaucs`: pi with the HauhauCS provider; starts the AI brain. MUTATES.
- `llama-hauhaucs` -> `~/bin/llama-server-ctl` (start|stop|status|restart|foreground). MUTATES. DUM-E: llama_start/stop/restart, ai_brain.
- `ollama-offload`: unload all Ollama models from VRAM. MUTATES. DUM-E: ollama_unload.
- `checkgpu` -> `system-monitor/check_gpu_usage.sh` (uses `sudo fuser`). READ. DUM-E: gpu.
- `cinegpu`: `watch -n 1 nvidia-smi`. READ. DUM-E: gpu.
- `lclaude` (completion file sourced): local Claude-CLI wrapper on Ollama models (manual 39).
- `pi-cyber`, `pi-case` (functions): the separate pi-cyber security workspace. Out of DUM-E's scope.

Homelab Control and monitoring [V]:
- `fortress`, `f` -> `homelab/control/fortress`. Mixed. DUM-E: services, health, service_start/stop.
- `fortress-vitals` -> `~/bin/fortress-vitals` (live status in tmux). READ.
- `sysmon` (cd), `sys-check` (live health dashboard), `plaintop` (PlainTop TUI). READ. DUM-E: snapshot.

Power (all use sudo; DUM-E must never run them) [V]:
- `powersaver`, `powersaver-lite`, `powersaver-force`, `performance`: MUTATE CPU governor/boost, GPU power limit, can unload the NVIDIA driver. `powerstatus`: READ. See manual 28.

Cine-Immich (manual 20) [V]: `cine` (cd), `cineImport` (mount SSD -> import -> unmount menu), `mount_immich_ssd` (sudo mount /dev/sda2; that device no longer exists), `cinelogs`, `cinelogsml`, `cinelogsworker` (READ), `cinestats`, `cinehealth` (READ), `triggerReindex`, `checkReindexStatus` (call a container that no longer exists), `migrateCine`, `migrateCineDry`, `rediscli` (interactive Redis), `clearRedisQueues` (DELETES Redis queues broll_queue, broll_face_queue), `checkBrollQueue`, `checkFaceQueue` (READ), `startCine`, `stopCine` (`docker compose down`, removes containers), `restartCine`, `restartCineAll` (force-recreate).

Other services [V]:
- n8n: `n8n-on`, `n8n-off` (`n8n/n8n_scheduler.sh start|stop`). MUTATES.
- `nfa` -> `node core-orchestration/fortress_cli.cjs` (NFA queue CLI).
- AFFiNE: `affine-on`, `affine-off` (compose in `~/homelab`). MUTATES.
- LifePath: `lifepath`, `lifepath-up`, `lifepath-down`, `lifepath-logs`, `lifepath-rebuild` (no-cache rebuild), `lifepath-be` (Spring on :39081), `lifepath-fe` (Vite on :39173).
- Virtual Self: `vself`, `vself-up`, `vself-down`, `vself-logs`, `vself-chat`, `vself-talk`, `vself-bake`, `vself-status`, `vself-archive-sync`, `vself-archive-run`, `vself-archive-status`, `virtual-self`.
- Backups: `vault-backup`, `vault-backup-menu`, `vault-backup-status` (READ), `vault-backup-daily`, `vault-backup-photos`, `vault-backup-full` (MUTATE; daily/photos/full also apply retention = DELETES old snapshots).
- Research digest: `rdigest`.
- Sharing: `expose`, `share-media` (`~/.local/bin/proxy-share.sh`, Cloudflare quick tunnel to a local URL), `share-stop-all` (`pkill -f cloudflared; screen -wipe`). Make services public on the internet; owner only.
- Microphone: `micdelay`, `micrange`, `micptt` -> `~/vox/scripts/mic-delay` (a separate `/home/fortress` folder; the path exists).
- Generic: `ll`, `la`, `l`, `alert`.

Environment set in bashrc [V]: llama tuning (PI_CTX_SIZE, TQ_CACHE_K/V, LLAMA_FIT*, LLAMA_CPU_MOE, LLAMA_NCMOE), NVM and Bun paths, `HF_XET_HIGH_PERFORMANCE=1`, and two Hugging Face token exports (SECRET; never shown).

Boot hook [V]: on a local console login (tty1-6), once per session: `fortress boot --prompt-if-tty`.

## Files and data
- `~/.bashrc` (contains secrets; DUM-E reads only a parsed, redacted index).
- `~/.bash_aliases` is sourced if it exists.

## Commands
See Components; each item has its class.

## Depends on
An interactive bash shell.

## How to check it (read-only)
- `shell_index query=<word>`.

## Known problems and fixes
- Broken aliases (from the cine manual, 2026-10-29): `triggerReindex`, `checkReindexStatus` (container gone), `mount_immich_ssd` (/dev/sda2 gone; /dev/sda is now the Expansion disk) [V by build agent].

## Logs
None.

## Rules for DUM-E here
- Tell the owner the alias when it is the simplest way for them to do something; never pretend DUM-E can run it.

## Open questions
None.
