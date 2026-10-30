---
title: The AI brain (local LLM server on :8081)
scope: llama-server with the HauhauCS Qwen3.6-35B-A3B model - files, settings, start/stop, clients, speed, quirks
last_verified: 2026-10-29
sources: ~/bin/llama-server-ctl, ~/bin/pi-hauhaucs, ~/.pi/agent/models.json, control/ai_models.yaml, control/services.yaml, ~/.local/state/llama-server-ctl.log, llama-server --help
---

# The AI brain (local LLM server on :8081)

## What it is
The homelab's own language model. A llama.cpp server (`llama-server`, from the `llama-cpp-turboquant` fork) loads one GGUF model file and answers OpenAI-style requests on port 8081. It is the brain behind DUM-E, the `pi` coding agent, Jarvis voice, Virtual Self and the Personal Feed. It runs on the GPU (dense layers and KV cache) and in RAM (MoE expert weights).

## How the owner refers to it
"the brain", "the AI", "local AI", "the model", "HauhauCS", "Q4", "the uncensored model", "the abliterated/obliterated model" (the files say "Uncensored-HauhauCS-Aggressive") [V]. Homelab Control calls the service `ai_llama`, label "Local AI (HauhauCS)" (src: control/services.yaml) [V].

## Components
- Binary: `~/llm/llama-cpp-turboquant/build/bin/llama-server`, build `version: 1 (a62320c)`, commit dated 2026-06-04 (cmd: llama-server --version) [V].
- Wrapper: `~/bin/llama-server-ctl {start|stop|status|restart|foreground}` (src: the script) [V].
- Model files (src: ls ~/models/hauhaucs) [V]:
  - `Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-default quant.gguf`, 21.2 GB - default, "best for coding and long chats".
  - `Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ3_M.gguf`, 15.4 GB - smaller and faster, slightly less sharp.
- Default settings in the wrapper (src: ~/bin/llama-server-ctl; also exported in .bashrc ~line 513) [V]:
  - bind `0.0.0.0:8081`, OpenAI API at `/v1`, no API key.
  - context `-c 262144` (PI_CTX_SIZE); `--fit on` shrinks it only if VRAM cannot hold it, never below 131072 (LLAMA_FIT_CTX_MIN); keeps 2560 MiB VRAM free (LLAMA_FIT_TARGET).
  - KV cache TurboQuant: K `q8_0`, V `turbo3`; flash attention on; `--jinja`.
  - MoE: `-ncmoe 32` (32 MoE layers' experts in RAM). `LLAMA_CPU_MOE=1` would put all experts in RAM (`-cmoe`).
  - alias `your-local-model-id` - hard-coded, reported even when the IQ3_M file is loaded.
  - Unloads Ollama models from the GPU before starting (LLAMA_OFFLOAD_OLLAMA=1).
  - Verifies the default quant file's SHA256 before each start and refuses a corrupt file (fix: `~/bin/hauhaucs-redownload-q4km.sh`).
- Observed at runtime (2026-10-29) [V]: about 8.5 GB of VRAM used by llama-server (cmd: nvidia-smi); 4 parallel slots, each n_ctx 262144 (src: llama log); generation speed 55-61 tokens/s in a logged request (src: llama log print_timing).

## Files and data
- Log: `~/.local/state/llama-server-ctl.log` (31 MB on 2026-10-29, grows without rotation) [V].
- PID file: `~/.local/state/llama-server-ctl.pid` [V].
- pi provider config: `~/.pi/agent/models.json` provider `llama-hauhaucs` -> `http://127.0.0.1:8081/v1`, model id `your-local-model-id`, contextWindow 262144, maxTokens 16384 [V]. The file has an apiKey field (SECRET, value not read).
- Brain menu: `control/ai_models.yaml` ids `hauhaucs_q4`, `hauhaucs_iq3`, `ollama_smart`, `ollama_fast`, `none` [V].
- Boot default: `~/.config/fortress-control/profiles/default.json` field `ai` (hauhaucs_q4 since 2026-10-29 22:13) [V].

## Commands
- `~/bin/llama-server-ctl status` - READ.
- `~/bin/llama-server-ctl start` - MUTATES (loads the model; uses most of the GPU). DUM-E action `llama_start`.
- `~/bin/llama-server-ctl stop` - MUTATES + removes its pid file (housekeeping). DUM-E action `llama_stop`.
- `~/bin/llama-server-ctl restart` - MUTATES. DUM-E action `llama_restart`.
- `fortress ai hauhaucs_q4` / `fortress ai hauhaucs_iq3` - MUTATES: unloads Ollama, sets HAUHAUCS_MODEL, restarts the server, and writes the choice into the boot profile. Owner only (no DUM-E action).
- `fortress ai none` - MUTATES: stops the server and unloads Ollama. Owner only.
- `pi` (bashrc function) and `pih` (`~/bin/pi-hauhaucs`) start the server automatically if needed [V].
- Health: `curl -s http://127.0.0.1:8081/health` -> `{"status":"ok"}` - READ.

## Depends on
- GPU with enough free VRAM (see manual 03). The VRAM watchdog can stop it.
- RAM for MoE experts and swap.
Clients that depend on it (src: services.yaml depends_on; compose files) [V]:
- Jarvis (`127.0.0.1:8081`, host network), Virtual Self and its archive (`host.docker.internal:8081` = 172.28.0.1), Personal Feed (start_backend.sh launches the server if :8081 is down; daily jobs at 05:00/06:00 use pi), pi, DUM-E.

## How to check it (read-only)
- DUM-E tool `ai_brain`: process, real model file (from the process command line), context, KV, MoE, /health, slots busy, watchdog state, Ollama, boot default.
- `snapshot` for a one-line view.
- Never trust the alias to tell Q4 from IQ3; the model file path is the truth [V].

## Known problems and fixes
- Not running after boot because the watchdog paused it and the old resume rule waited for "no GPU process at all" (cine_broll_worker always holds 1.8 GB). Fixed 2026-10-29 (resume when GPU util <= 10 % for 4 polls) [V]. See runbook:ai-down.
- Several programs can start it (Homelab Control, `fortress ai`, `pi`, `pih`, personal-feed `start_backend.sh`, the watchdog) [V]. Only `fortress start` checks the GPU guard [V].
- `pih` defaults to model id `hauhaucs-qwen3.6-35b-iq3m`, which is not in `models.json` [V]; it may fail with "unknown model" [U - untested].
- Prompt re-processing: the log warns "forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory)" [V]. Long prompts are re-read often; keep prompts short.
- Bound to 0.0.0.0 without a key: reachable from the LAN (firewall off) [V]. Owner decided (2026-10-29) not to change this now, because containers reach it through the Docker bridge.
- The log grows without rotation [V].

## Logs
- `log_tail log=llama` (look for: "server is listening", "cleaning up before exit", "out of memory", "print_timing" for speed).
- `log_tail log=feed_llama` when the Personal Feed started it.

## Rules for DUM-E here
- Starting, stopping or restarting it only through proposals (`llama_start`, `llama_stop`, `llama_restart`) that the owner approves.
- Stopping it ends DUM-E's own conversation; say so in the proposal.
- Never change model files, the wrapper, or `fortress ai` choices.

## Open questions
- Exact VRAM the fit step chose at the last start [U]: the log lines with "fitted" were not found.
