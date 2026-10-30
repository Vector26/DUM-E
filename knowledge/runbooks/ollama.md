---
title: Ollama model stuck in memory or Ollama not responding
symptom: An Ollama model sits in VRAM, or Ollama does not answer
last_verified: 2026-10-30
related: 07-ollama-and-models, 02-ai-brain
---

# Ollama model stuck in memory or Ollama not responding

## Symptom
- `gpu {}` shows an `ollama` process using VRAM. [V]
- Ollama on :11434 does not answer. [I]

## Quick check
1. `ai_brain {}` - look for: Ollama models in memory and on disk.
2. `gpu {}` - look for: the `ollama` process and its MiB.

## Diagnosis
1. `ollama.service` is a system unit with `Restart=always` and `RestartSec=3`. [V]
2. It runs with `OLLAMA_HOST=0.0.0.0`, `OLLAMA_KEEP_ALIVE=-1` (never unloads), `OLLAMA_CONTEXT_LENGTH=80000`, flash attention on. [V]
3. Installed models on 2026-10-30: `qwen2.5:7b`, `qwen3.6:35b-a3b`, `nomic-embed-text:latest`. [V]
4. A small `nomic-embed-text` entry (about 766 MiB VRAM) is normal: Virtual Self uses it for embeddings. [V]
5. A large model resident -> cause A: it will stay until unloaded.
6. The service is down -> cause B.
7. A model is cold-stored on `/mnt/backup-volume` -> cause C. The owner thaws it with `ollama-cold` (see `ollama-cold help`). [I]
8. Starting the AI brain unloads Ollama models first. agent-heal does not treat an Ollama process as a blocker. [V]

## Fix
- A: `propose_action {"action":"ollama_unload"}`. Models stay on disk. Tell the owner: dume approve <ID>.
- B: owner runs `sudo systemctl restart ollama`.
- C: owner runs `ollama-cold thaw <name:tag>`.

## Verify
- `gpu {}` no longer lists a large `ollama` allocation; `ai_brain {}` shows no model in memory.

## Do not
- Do not run `ollama rm`.
- Do not freeze or thaw models for the owner.
- Do not load a second large model while the brain runs.

## Sources
- `systemctl cat ollama`, `ollama list` (this session)
- manual 07-ollama-and-models
- `~/bin/llama-server-ctl` (unload_ollama_gpu)
