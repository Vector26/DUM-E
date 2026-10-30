---
title: GPU full or out of VRAM
symptom: The GPU is full, the AI cannot start, or the owner asks to free the GPU
last_verified: 2026-10-30
related: 02-ai-brain, 03-gpu-vram-watchdog, 07-ollama-and-models
---

# GPU full or out of VRAM

## Symptom
- `dume doctor` says "Free VRAM is low" or "GPU not readable". [V]
- The brain is paused by the watchdog, or `llama_start` is refused by the GPU guard. [V]
- Only one GPU-heavy job may run at a time on this machine. [V]

## Quick check
1. `gpu {}` - look for: every process with its MiB, and the free MiB.
2. `ai_brain {}` - look for: whether Ollama has a model in memory.

## Diagnosis
1. An Ollama process is listed -> cause A: an Ollama model is kept in VRAM. The service uses `OLLAMA_KEEP_ALIVE=-1`, so it never unloads by itself. [V]
2. `llama-server` uses about 8.5 GB -> this is the AI brain. Normal. [V]
3. A process about 1.8 GB named after cine tagging -> normal, it stays resident. [I]
4. A host process you do not know -> read the owner column and ask the owner. Do not guess.
5. "nvidia-smi failed" or no GPU -> the driver is unloaded. The owner fixes it (power function `performance`, sudo). DUM-E never runs power functions. [I]

## Fix
- A: `propose_action {"action":"ollama_unload"}`. Models stay on disk. Tell the owner: dume approve <ID>.
- Owner wants the GPU fully free: `propose_action {"action":"llama_stop"}` and `ollama_unload`, or the owner runs `fortress ai none`. **DELETES:** the brain's pid file (llama_stop). Tell the owner: dume approve <ID>.
- Another job needs the GPU: tell the owner which job holds it and ask which one to stop. Do not choose.

## Verify
- `gpu {}` shows more free MiB than before.
- Owner runs `nvidia-smi --query-compute-apps=pid,name,used_gpu_memory --format=csv,noheader` - expected: only the jobs the owner wants.

## Do not
- Do not suggest killing container processes.
- Do not start a second model server "to test". It can cause an out-of-memory kill and corrupt model state. [V]
- Do not run power functions.
- agent-heal never starts the brain while another non-Ollama GPU job runs. Do not work around that gate. [V]

## Sources
- manual 02-ai-brain, 03-gpu-vram-watchdog, 07-ollama-and-models
- `systemctl cat ollama` (OLLAMA_KEEP_ALIVE=-1)
- `~/homelab/agents/scripts/agent-heal` (brain start gates)
