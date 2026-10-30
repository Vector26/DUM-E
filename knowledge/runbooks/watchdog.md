---
title: VRAM watchdog not running or acting strangely
symptom: The VRAM watchdog is not running, the AI stays paused, or the AI pauses and resumes over and over
last_verified: 2026-10-30
related: 03-gpu-vram-watchdog, 04-fortress-control
---

# VRAM watchdog not running or acting strangely

## Symptom
- `dume doctor` lists "VRAM watchdog is not running". [V]
- The AI brain is paused for a long time although the GPU looks free. [V]
- The log shows PAUSE and RESUME again and again. [V]

## Quick check
1. `ai_brain {}` - look for: "VRAM watchdog: running PID" or "NOT running", and the last log lines.
2. `log_tail {"log":"watchdog","lines":40}` - look for: "start:", "PAUSE", "RESUME", "still paused".

## Diagnosis
1. "NOT running" -> cause A. The watchdog is started only by Homelab Control (`services.yaml` id `vram_watchdog`, a `nohup` line). It is not a systemd unit, so it does not come back by itself before the next boot. [V]
2. Running, but the AI is paused for more than 10 minutes with free VRAM at least 6144 MiB and utilisation at most 10 % -> cause B. Look for "still paused" lines and the `quiet_polls` counter. If `quiet_polls` keeps resetting, GPU utilisation is spiking (cine tagging). [V]
3. Many PAUSE and RESUME pairs -> cause C: VRAM pressure from cine tagging plus the AI. A resume is followed by a 300 s cooldown (RESUME_COOLDOWN_S=300), so flapping is limited but real. [V]

## Fix
- A: `propose_action {"action":"watchdog_restart"}`. Tell the owner: dume approve <ID>.
- B: wait and watch `quiet_polls` count up to 4. If it never does, the GPU is never quiet; see C.
- C: this is the owner's decision. Options: run the smaller brain (`fortress ai hauhaucs_iq3`, owner runs it), or stop cine tagging (`propose_action {"action":"service_stop","args":{"service_id":"cine_immich"}}`, then "Tell the owner: dume approve <ID>").

## Verify
- `ai_brain {}` shows "VRAM watchdog: running PID".
- `log_tail {"log":"watchdog","lines":10}` shows a fresh "start:" line.

## Do not
- Do not run `fortress start vram_watchdog` through a pipe. The background child keeps the pipe open and the command hangs. [V]
- Do not edit `vram-watchdog.sh`. Changes to the thresholds are the owner's call.
- Do not make agent-heal restart the watchdog. It does not manage it. [V]

## Sources
- `~/homelab/control/vram-watchdog.sh` (thresholds, cooldown)
- `~/homelab/control/services.yaml` (id vram_watchdog)
- manual 03-gpu-vram-watchdog
