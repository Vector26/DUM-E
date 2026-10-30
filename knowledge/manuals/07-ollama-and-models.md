---
title: Ollama and model files
scope: The Ollama service, its settings, which models exist, cold storage on the Expansion drive, other model folders
last_verified: 2026-10-29
sources: /etc/systemd/system/ollama.service(.d/override.conf), ollama list/ps, ~/bin/ollama-cold, /mnt/backup-volume/models-cold/INDEX.md, ls ~/models, control/ai_models.yaml, ~/.pi/agent/models.json
---

# Ollama and model files

## What it is
Ollama is a second, separate model server (port 11434). It is used by Moltbot, Vitalis, Cine-Immich (OLLAMA_BASE_URL), Virtual Self (embeddings/fallback), and as alternative "brains" in the homelab menu. Only one GPU-heavy brain should be loaded at a time; starting the AI brain on :8081 unloads Ollama first [V].

## How the owner refers to it
"Ollama", "the Ollama models", "cold storage", "freeze/thaw a model", `ollama-offload` [V].

## Components
- Service: system unit `ollama.service`, `ExecStart=/usr/local/bin/ollama serve`, user `ollama`, `Restart=always` (src: /etc/systemd/system/ollama.service) [V].
- Override (src: /etc/systemd/system/ollama.service.d/override.conf) [V]:
  - `OLLAMA_HOST=0.0.0.0` ("so Docker containers (e.g. MoltBot) can reach Ollama")
  - `OLLAMA_KEEP_ALIVE=-1` (loaded models never unload by themselves)
  - `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_CONTEXT_LENGTH=80000`, `OLLAMA_FLASH_ATTENTION=1`, `CUDA_VISIBLE_DEVICES=0`
- Models on disk (cmd: ollama list) [V]: `qwen2.5:7b` (4.7 GB), `qwen3.6:35b-a3b` (23 GB), `nomic-embed-text:latest` (274 MB).
- Loaded in memory on 2026-10-29: none (cmd: ollama ps) [V].
- Cold storage (src: /mnt/backup-volume/models-cold/INDEX.md) [V]: `qwen3.6:35b-a3b` and `qwen3.6:27b` frozen 2026-09-29; GGUF files `Qwen3-4B-Instruct-2507-Q5_K_M.gguf` and `Qwen3-0.6B-Q8_0.gguf`. Note: `qwen3.6:35b-a3b` is listed as frozen AND still shows in `ollama list`, so the INDEX is partly stale [I].
- Brain menu entries using Ollama (src: ai_models.yaml) [V]: `ollama_smart` = qwen3.6:27b (cold, thaw first), `ollama_fast` = qwen3.6:35b-a3b.
- Other model folders in `~/models` [V]: `hauhaucs/` (the AI brain, manual 02), `chatterbox-turbo/` (TTS weights), `whisper-large-v3-turbo/` (STT), `qwen3-0.6b/` and `qwen3-4b/` (empty; moved to cold storage).

## Files and data
- Ollama model store: `/usr/share/ollama/.ollama/models` (manifests + blobs) (src: ~/bin/ollama-cold LIVE_ROOT) [V]. `du -xsh /usr/share/ollama` = 5.2 GB [V] although `ollama list` shows 28 GB of models [U - the store may be partly elsewhere].
- Cold store: `/mnt/backup-volume/models-cold/` with `INDEX.md`, `ollama/`, `gguf/` [V].

## Commands
- READ: `ollama list`, `ollama ps`, `ollama-cold list`.
- MUTATES: `ollama-offload` alias / POST keep_alive 0 (DUM-E action `ollama_unload`).
- DELETES (owner only, never DUM-E): `ollama rm <model>`; `ollama-cold freeze <name:tag>` (copies to the Expansion drive, then `sudo ollama rm`) [V].
- MUTATES (owner only): `ollama-cold thaw <name:tag>` (copies back with sudo; no download) [V].

## Depends on
- GPU; the Expansion drive (`/mnt/backup-volume` must be mounted) for cold storage.

## How to check it (read-only)
- `ai_brain` (Ollama in memory + on disk, brain menu), `gpu` (VRAM users), `ports` (11434 bound to `*`).

## Known problems and fixes
- A loaded Ollama model stays in VRAM forever (KEEP_ALIVE=-1) and can block the AI brain -> propose `ollama_unload`.
- Ollama listens on all interfaces with the firewall off; anyone on the LAN can use or (through its API) remove models [V/I]. The owner chose not to change this now (containers need it).
- `fortress ai ollama_*` runs `sudo systemctl start ollama` [V] - owner only.

## Logs
- `journalctl -u ollama` (owner; DUM-E has no tool for the system journal).

## Rules for DUM-E here
- Never remove, freeze or thaw models. Only `ollama_unload` (no data is lost).

## Open questions
- Where the 23 GB `qwen3.6:35b-a3b` blobs physically are [U].
