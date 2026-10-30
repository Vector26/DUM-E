---
title: AI brain not answering
symptom: DUM-E, pi, Jarvis or Virtual Self says the AI is not answering (nothing on :8081)
last_verified: 2026-10-30
related: 02-ai-brain, 03-gpu-vram-watchdog
---

# AI brain not answering

## Symptom
- `dume` prints "The AI brain (:8081) is not answering, so DUM-E cannot talk yet." [V]
- `dume doctor` lists "AI brain not running or not answering on :8081" or "AI brain paused by the VRAM watchdog". [V]

## Quick check
1. `ai_brain {}` - look for: "llama-server: NOT running", "PAUSED since", the "/health" code.
2. `gpu {}` - look for: free MiB and any other process holding VRAM.

## Diagnosis
1. "PAUSED since" is shown -> cause A: the VRAM watchdog paused the brain on purpose. [V]
   - Read the live gates in the `ai_brain` output: free VRAM must be at least 6144 MiB, GPU utilisation at most 10 %, for 4 quiet polls (about 60 s). [V]
   - Free VRAM below 6144 MiB -> something else holds VRAM -> runbook:gpu-vram.
   - Utilisation above 10 % -> the GPU is busy (often cine tagging) -> wait. It resumes about 60 s after the GPU goes quiet.
   - Gates fine and the watchdog is running -> it resumes within about 75 s. Check `log_tail {"log":"watchdog","lines":10}` for "RESUME".
2. No pause flag, llama-server not running -> cause B: never started or stopped. Check `services {"id":"ai_llama"}` for "in boot profile". [V]
3. llama-server running but /health is not 200 -> cause C: still loading, or crashed. [V]
   - Loading checks a 21 GB file first and can take 1 to 3 minutes. [V]
   - `log_tail {"log":"llama","lines":40}` - look for "server is listening" (fine) or "error" / "out of memory" (crashed).
4. Pause flag present and the watchdog is NOT running -> cause D: nothing will resume it -> runbook:watchdog.

## Fix
- A: wait. If the owner insists now: `propose_action {"action":"watchdog_clear_pause"}`. **DELETES:** the pause flag. Warn that VRAM may run out. Tell the owner: dume approve <ID>.
- B: `propose_action {"action":"llama_start"}`. Tell the owner: dume approve <ID>.
- C: wait 3 minutes. If still failing: `propose_action {"action":"llama_restart"}`. **DELETES:** the server pid file. Tell the owner: dume approve <ID>.
- D: `propose_action {"action":"watchdog_restart"}`. Tell the owner: dume approve <ID>.
- agent-heal can also start the brain by itself, but only through `~/bin/llama-server-ctl start`, and only when no pause flag exists, no other GPU job runs and at least 10240 MiB VRAM is free. [V]

## Verify
- `ai_brain {}` shows "/health: 200" and the default quant model file.
- Owner runs `~/homelab/agents/scripts/agent-heal --check --quiet` - expected: no `FAIL brain` line.

## Do not
- Do not propose `service_start ai_llama`. It is excluded, and the GPU guard refuses it while another GPU job runs. [V]
- Do not start a second GPU or model process to "help". One GPU job at a time. [V]
- Do not trust the model alias for the quantisation. Read the file name in `ai_brain`.

## Sources
- manual 02-ai-brain, 03-gpu-vram-watchdog
- `~/homelab/control/vram-watchdog.sh` (FREE_RESUME_MIB=6144, QUIET_UTIL_PCT=10, QUIET_POLLS_NEEDED=4)
- `~/homelab/agents/scripts/agent-heal` (fix_brain gates)
- `~/homelab/DUM-E/bin/dume` (ensure_ai, doctor)
