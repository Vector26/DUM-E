---
title: GPU memory, the VRAM watchdog and the GPU guard
scope: Who uses VRAM, how the watchdog pauses and resumes the AI, how Homelab Control prevents GPU conflicts
last_verified: 2026-10-29
sources: control/vram-watchdog.sh (version of 2026-10-29), control/lib/gpu.sh, control/lib/actions.sh, control/services.yaml, control/ai_models.yaml, nvidia-smi, docker top
---

# GPU memory, the VRAM watchdog and the GPU guard

## What it is
The discrete GPU (example: 16 GB VRAM) has 16 GB of VRAM. Several things want it: the AI brain (about 8.5 GB plus KV cache), the Cine-Immich B-roll AI worker (about 1.8 GB, always resident), and Ollama models. Two mechanisms keep them from crashing each other:
1. The GPU guard in Homelab Control refuses to start a GPU service when the GPU is busy (with two exceptions).
2. The VRAM watchdog pauses the AI brain when free VRAM gets critically low, and resumes it later.

## How the owner refers to it
"VRAM", "the GPU", "free the GPU", "clear VRAM", "the watchdog", "the AI got paused". The bashrc comment for `ollama-offload` says "Unload all Ollama models from VRAM" [V].

## Components
GPU users (cmd: nvidia-smi --query-compute-apps; docker top) [V on 2026-10-29]:
- `llama-server` (host process) ~8.5 GB - the AI brain.
- `python worker.py` as root inside container `cine_broll_worker` - 1,836 MiB, resident permanently (restart policy `always`).
- Ollama: none loaded on 2026-10-29; when loaded, kept forever because `OLLAMA_KEEP_ALIVE=-1` (src: ollama override.conf) [V].
Services marked `gpu: true` in services.yaml: `cine_immich`, `ai_llama` [V].

The VRAM watchdog (src: ~/homelab/control/vram-watchdog.sh) [V]:
- Polls every 15 s (POLL_S).
- PAUSE: if no pause flag, llama-server is running, free VRAM < 2048 MiB (FREE_PAUSE_MIB), and at least 300 s since the last resume (RESUME_COOLDOWN_S): runs `llama-server-ctl stop`, writes the current epoch into `~/.local/state/fortress-vram-watchdog/ai-paused`, logs "PAUSE", sends a Telegram alert via `http://localhost:8001/notify`.
- RESUME (changed 2026-10-29): if paused for >= 60 s (MIN_PAUSE_S), free VRAM >= 6144 MiB (FREE_RESUME_MIB), and GPU utilisation <= 10 % (QUIET_UTIL_PCT) for 4 consecutive polls (QUIET_POLLS_NEEDED, about 60 s): runs `llama-server-ctl start`, removes the pause flag, logs "RESUME ... start rc=N", sends a Telegram alert.
- While paused, logs "still paused (...)" with the live gate values every 10 min (NOTE_EVERY_S).
- Before 2026-10-29 the resume rule required NO compute process on the GPU at all, so the always-resident cine_broll_worker blocked resume forever (the AI stayed paused 52 min until the fix) [V]. Backup of the old script: `control/vram-watchdog.sh.bak-20261029-2215` [V].
- It is started by Homelab Control as service `vram_watchdog` (a `nohup` line in services.yaml), not by systemd [V].

The GPU guard (src: control/lib/gpu.sh `fc_gpu_guard`) [V]:
- Used only by `fortress start <id>` for services with `gpu: true`.
- Allows the start if the GPU has no compute process; or for `ai_llama`/`hauhaucs*` if a llama-server is already there; or always for `cine_immich`.
- Otherwise refuses: "GPU is busy. Free it first (Choose AI -> None), then retry." and logs an incident.
- Consequence: `fortress start ai_llama` is refused while cine_broll_worker holds the GPU; `llama-server-ctl start` directly is not guarded [V].

## Files and data
- `~/.local/state/fortress-vram-watchdog/ai-paused` - pause flag (epoch seconds). Present = AI is paused on purpose [V].
- `~/.local/state/fortress-vram-watchdog/watchdog.pid` - watchdog PID [V].
- `~/.local/state/fortress-vram-watchdog/watchdog.log` - decisions (empty before 2026-10-29) [V].

## Commands
- `nvidia-smi` and `nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv` - READ.
- `checkgpu` alias -> `~/homelab/system-monitor/check_gpu_usage.sh` - READ, but it runs `sudo fuser` on /dev/nvidia* [V]; DUM-E uses its own `gpu` tool instead.
- `ollama-offload` alias - MUTATES (unloads Ollama models). DUM-E action `ollama_unload`.
- `fortress ai none` - MUTATES (stops AI, unloads Ollama). Owner only.
- Restart watchdog: `fortress stop vram_watchdog; fortress start vram_watchdog` - MUTATES. DUM-E action `watchdog_restart`. Note: `fortress start vram_watchdog` never returns when its output is piped (the background child keeps the pipe open); redirect to a file [V].
- Force resume: remove the flag and start the AI - DUM-E action `watchdog_clear_pause` (housekeeping deletion of the flag file; owner approves).

## Depends on
- The notifier on :8001 for alerts.
- `llama-server-ctl` for stop/start.

## How to check it (read-only)
- `ai_brain`: watchdog running?, paused since?, the rules read from the script, live free VRAM and util, last log lines.
- `gpu`: VRAM numbers and every GPU process named by container.
- `log_tail log=watchdog`.

## Known problems and fixes
- AI paused for a long time -> runbook:ai-down (check the gates; the GPU must be quiet, not empty).
- Pause right after boot: the AI (262k context) and the cine stack start together; at 21:10:50 on 2026-10-29, 5 minutes after boot, the watchdog paused the AI [V]. The free VRAM at that moment was not logged (logging added later) [U]. A boot grace period was proposed but not added.
- Watchdog not running -> runbook:watchdog. From 2026-09-29 to 2026-10-06 the health log reported "VRAM watchdog: not running" 306 times [V].
- Ollama hogging VRAM: `OLLAMA_KEEP_ALIVE=-1` keeps any loaded model in VRAM forever [V] -> propose `ollama_unload`.

## Logs
- `log_tail log=watchdog`: lines "start:", "PAUSE: free=...", "still paused (...)", "RESUME: ... start rc=0".
- Alert notifications from source `vram-watchdog`.

## Rules for DUM-E here
- Never run the power functions (`powersaver*`, `performance`); they unload the NVIDIA driver with sudo.
- Overriding a pause (`watchdog_clear_pause`) only on the owner's explicit wish; warn that VRAM may run out.

## Open questions
- Whether cine_broll_worker ever releases its CUDA context when idle [U]: watch `gpu` over an hour.
