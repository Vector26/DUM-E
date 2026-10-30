---
title: Other projects and folders
scope: Remaining folders in ~/homelab not covered by other manuals (vid-gen, voice-poc, PS5LM, whatisthewordfor, archived, extensions, library, pi-cyber, and the PRIVATE data trees), helper scripts in ~/bin (lclaude, hauhaucs-*.sh), and ~/vox (Vox voice project, mic-delay tools, voicebox container)
last_verified: 2026-10-29
sources: vid-gen/HANDOFF.md, vid-gen/package.json, voice-poc/README.md, voice-poc/run_poc.py, PS5LM/README.md, PS5LM/.git/config, whatisthewordfor/README.md, archived/icloudpd/docker-compose.yml (secrets redacted), extensions/*, library/README.md, ~/.bashrc:95-96,520-547,570-590, ~/bin/lclaude, ~/bin/hauhaucs-*.sh, ~/vox/README.md, ~/vox/vox, ~/vox/scripts/*, ~/vox/orchestrator/config.yaml, ~/vox/voicebox/docker-compose.yml, DUM-E.md §7, §9, du -sh, docker ps/inspect, ollama list
---

# Other projects and folders

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
This manual covers small, paused, third-party or private items. None of them is registered in `control/services.yaml`, except that `voicebox` runs unregistered. [V] (src: control/services.yaml; DUM-E.md §3 F11)
Folders covered by other manuals (control, monitoring, notifier, orchestration, cine-immich, immich, vault-backup, vault-storage, personal-feed, research-digest, system-monitor, netwatch, kindle-dash, music-service, spot-spot, backups, and manuals 34–38) are not repeated here.
### vid-gen
A paused plan for a local prompt-to-video web app: ComfyUI (headless, 127.0.0.1:8188) + an Express app on :5178, model LTX-Video 13B distilled fp8. Paused 2026-07-08. Only ComfyUI is cloned; the app files are still TODO. [V] (src: vid-gen/HANDOFF.md:1-16,95-120)
### voice-poc
A small speech-recognition accuracy test. It records sentences from the mic and scores faster-whisper transcripts. [V] (src: voice-poc/README.md; voice-poc/run_poc.py:2)
### PS5LM
A clone of the public GitHub project `cobanov/PS5LM`: llama.cpp running on a jailbroken PS5's GPU, serving OpenAI/Anthropic APIs to the network. It runs on the console, not on this server. [V] (src: PS5LM/README.md:1-27; PS5LM/.git/config)
### whatisthewordfor
A planning folder for the website whatisthewordfor.com: a no-LLM reverse dictionary. Design docs only, no app code. [V] (src: whatisthewordfor/README.md:1-7)
### archived
`archived/icloudpd/` — an old iCloud photo downloader + Immich uploader setup. No containers exist. [V] (cmd: ls archived; docker ps -a | grep icloud → none)
### extensions
`extensions/spotify2navidromeSyncer.py` and `extensions/syncer/` (Spotisub installer). Spotify → Navidrome playlist sync helpers. Not running. [V] (cmd: ls; head of files)
### library
`~/homelab/library` is the homelab documentation library: 409 markdown files on numbered "shelves". Project folders keep symlinks to it. [V] (src: library/README.md:1-4; cmd: find -name '*.md' | wc -l)
### pi-cyber
`~/homelab/pi-cyber` (6.6 GB) is a separate offensive-security / OSINT agent workspace built on `pi`. It holds SecLists, HackTricks, CTF write-ups, playbooks, skills, a RAG folder and investigations. It is launched by the `pi-cyber` and `pi-case` shell functions with its own system prompt, skill and session store; `bin/pi-cyber-kill` stops its sessions. **It is a separate scope and is excluded from DUM-E.** DUM-E must not read, run or change anything in it. [V] (cmd: ls pi-cyber; du -sh; src: ~/.bashrc:570-590; DUM-E.md §6.1)
### PRIVATE data trees (names only)
- `NOTION-DATA [DO NOT REMOVE OR TOUCH]/` (45 MB) — the owner's Notion data. **Rule from its own name: do not remove or touch.** PRIVATE. [V] (cmd: ls; du -sh)
- `notion_html_export/` (65 MB) and `notion_html_export.zip` (55 MB) — Notion HTML export. PRIVATE. [V]
- `HumanReadableData/` (11 MB) — personal documents. PRIVATE. [V] (DUM-E.md §9.3)
- `People-research/` (4 KB) — PRIVATE. [V]
- `life-archive-data/` (35 GB) — personal archive (Takeout etc.; used read-only by Virtual Self, manual 35). PRIVATE. [V]
- `nextplan.md` (4.8 KB) — owner's planning note. PRIVATE. [V]
### ~/bin helpers (this manual covers `lclaude` and `hauhaucs-*.sh`)
- `lclaude` — runs Claude Code against **local Ollama** (Anthropic-compatible API on :11434). [V] (src: ~/bin/lclaude:6-8)
- `hauhaucs-download-q4km.sh`, `hauhaucs-redownload-q4km.sh`, `hauhaucs-install-validate.sh`, `hauhaucs-rebuild-llama.sh` — install, verify and rebuild tools for the AI brain model and `llama-server`. [V] (src: file headers)
- Other files in `~/bin` (`llama-server-ctl`, `pi-hauhaucs`, `ollama-cold`, `fortress-vitals`, `wifi-*`) belong to other manuals.
### ~/vox
Vox is a separate voice project in `~/` (not `~/homelab/`). It is a live voice conversation + note-taker: mic → Voicebox (Whisper STT) → LLM → Voicebox TTS → speaker, with markdown notes. [V] (src: ~/vox/README.md; DUM-E.md §7.2) The `micdelay`, `micrange` and `micptt` shell functions call its `mic-delay` tool. [V] (src: ~/.bashrc:545-547) Its `voicebox` container is running. [V] (cmd: docker ps)

## How the owner refers to it
- "vid-gen", "video gen" (no aliases). [V] (cmd: grep ~/.bashrc)
- "voice POC", "mic test". [I]
- "PS5LM". [V]
- "library", "shelves", "docs". [V]
- `pi-cyber`, `pi-case <name>` (functions). [V] (src: ~/.bashrc:572-590)
- `lclaude`, `lclaude fast`, `lclaude models`. Tab completion from `~/bin/lclaude.completion.bash`. [V] (src: ~/.bashrc:536-537; ~/bin/lclaude)
- `micdelay` → `~/vox/scripts/mic-delay`; `micrange` → `mic-delay --monitor`; `micptt` → `mic-delay --ptt`. [V] (src: ~/.bashrc:545-547)
- `vox` (script `~/vox/vox`, "Live Jarvis"). Not an alias. [V] (src: ~/vox/vox:2)
- `runQdrant` — throwaway Qdrant (see manual 37). [V]

## Components
### vid-gen
- `engine/ComfyUI/` (78 MB, cloned, `.venv` partly set up, `models/checkpoints` has only `put_checkpoints_here`). `server/`, `public/`, `workflows/`, `scripts/`, `output/`, `cache/` are **empty**. [V] (cmd: ls; du -sh)
- `package.json` is stale (points to a deleted `src/index.js`). [V] (src: HANDOFF.md:104)
- Planned ports: ComfyUI 127.0.0.1:8188, web app 5178. Nothing listens on them. [V] (src: HANDOFF.md:12-13; cmd: ss -ltnp)
### voice-poc
- `run_poc.py` (record + transcribe + score), `diagnose_mic.py` (mic hardware test), `statements.txt`, `states.txt`, `.venv` (455 MB). [V] (cmd: ls; du -sh)
- Uses faster-whisper `small` from the **Jarvis** cache `~/homelab/jarvis/data/whisper`. [V] (src: run_poc.py:22-26)
### PS5LM
- `ps5/`, `probes/`, `patches/` (llama.cpp patches), `scripts/` (build, run, `console-setup.sh`, `send.sh`), `site/`, `docs/`, `third_party/` (submodules `llama.cpp`, `ps5-homebrew-ui`). 35 MB. [V] (cmd: ls; .gitmodules)
- On the console it serves on port **8081**. That is the console's port, not this host's AI brain. [V] (src: PS5LM/README.md:46-47)
### archived/icloudpd
- `docker-compose.yml` (services `icloudpd`, `immich_uploader`), `main.py`, `uploader.py`, `icloud_auth_test.py`, `venv/`, `icloud_downloads/`, `icloud_downloads_new/`. 5.6 GB in total. [V] (cmd: ls; du -sh)
### extensions
- `spotify2navidromeSyncer.py`, `syncer/install_spotisub_docker.sh`, `syncer/dependencies/` (cache, docker-compose.yml). 48 KB. [V]
### library
- Shelves: `00-meta`, `01-cine-immich`, `02-lifepath`, `03-core-orchestration`, `04-notifier`, `05-dexter`, `06-monitoring`, `07-netwatch`, `08-orchestration`, `09-affine`, `10-system-monitor`, `11-plane`, `12-vault-storage`, `13-anytype`, `99-third-party` (Moltbot). Index files `README.md`, `CATALOG.md` (424 lines), `SYMLINKS.md` (35 lines). [V] (cmd: ls library; wc -l)
- Rules in the README: add new docs here on the right shelf; vendor trees go in `99-third-party`. [V] (src: library/README.md "Rules")
### ~/bin
- `lclaude` — sets `ANTHROPIC_BASE_URL` (default `http://127.0.0.1:11434`), `ANTHROPIC_AUTH_TOKEN` (default `ollama`), empties `ANTHROPIC_API_KEY`, then runs `claude` (or `npx -y @anthropic-ai/claude-code`). Default model `qwen3.6:27b` ("smart"); `lclaude fast` uses `qwen3.6:35b-a3b`. [V] (src: ~/bin/lclaude:56-75)
- `hauhaucs-download-q4km.sh` — downloads the default quant GGUF (~21 GB) with `aria2c` into `~/models/hauhaucs/`, checks size, then **restarts the AI brain** and runs a smoke chat. Log `~/.local/state/hauhaucs-q4km-download.log`. [V]
- `hauhaucs-redownload-q4km.sh` — re-downloads with SHA-256 check; renames a corrupt file to `*.corrupt.<epoch>`. Log `~/.local/state/hauhaucs-q4km-redownload.log`. [V]
- `hauhaucs-install-validate.sh` — checks model size and SHA, llama-server build, pi config; then **stops and starts the AI brain** and runs test prompts (including `pi -p`). Log `~/.local/state/hauhaucs-validate.log`. [V]
- `hauhaucs-rebuild-llama.sh` — rebuilds `~/llm/llama-cpp-turboquant` for sm_120a with CUDA 12.8+. It first runs **`rm -rf build`**. Log `~/.local/state/hauhaucs-rebuild.log`. [V]
### ~/vox
- `voicebox` container — built from `~/vox/voicebox` (compose project `voicebox`). Port **127.0.0.1:17600**→17493. Restart `unless-stopped`. Healthy. Volumes `voicebox_voicebox-data`, `voicebox_huggingface-cache`, bind `voicebox/output`. CPU limit 4. Not in `services.yaml`. [V] (src: voicebox/docker-compose.yml; cmd: docker ps; docker inspect --format Mounts/RestartPolicy/Health; curl 127.0.0.1:17600/health → 200)
- `orchestrator/` — Python voice loop (`cli.py`, `pipeline.py`, `stt_stream.py`, `tts_engine.py`, `llm_client.py`, `usb_mic_linux.py`, …) with its own `.venv`. Config `orchestrator/config.yaml`: Voicebox at `http://127.0.0.1:17600`, LLM at `http://127.0.0.1:8081/v1` with model `hauhaucs-iq3`. [V] (cmd: ls; grep config.yaml)
- `vox` — launcher for `orchestrator/cli.py`. [V]
- `scripts/mic-delay` (bash wrapper) + `scripts/mic-delay.py` (13 KB) — "Mic tools: live level range, delayed echo, or push-to-play". Options include `--monitor`, `--ptt`, `--delay` (default 1.0 s), `--rate`, `--blocksize`, `--threshold`. [V] (src: scripts/mic-delay; mic-delay.py:1-3,395-415)
- `scripts/micdiag` (mic stack diagnostic), `usb-mic-linux-setup` (applies USB mixer fixes), `99-jieli-usb-mic.rules` (udev rule to keep the Jieli/DWM-123 USB mic awake), `bluetooth-setup.sh`, `start.sh`, `start-llm.sh`, `status.sh`, `dl.sh`, `downloads.sh`, `download-model.sh`. [V] (cmd: ls; headers)
- `models/` — `faster-whisper-large-v3-turbo-ct2`, `chatterbox-turbo`, `jarvis_ref` (reference voice for cloning), `whisper-hf-src`. [V]
- `notes/2026-09-09/`, `memory/` (empty), `voices/`, `logs/` (`bluetooth.log`, `llm-server.log`, `talk.log`, download logs). [V]

## Files and data
- vid-gen: `HANDOFF.md` (full plan; read first). Original plan path `~/.cursor/plans/vid-gen_ltx_video_app_fa9d8f2e.plan.md` may not exist. [V] (src: HANDOFF.md:3)
- voice-poc: `results/` (two dated recording folders, `run_*.json`, `*_summary.csv`; 5.6 MB). These are recordings of the owner's voice: **PRIVATE**. [V] (cmd: ls results) [I] (recordings)
- PS5LM: `site/payloads.json`, `docs/*.md`. Third-party. [V]
- archived/icloudpd: `docker-compose.yml` holds an Apple ID password field and an Immich API key field: **SECRET-bearing**, never print. `icloud_downloads*/` — photos, **PRIVATE**. [V] (cmd: read with values redacted)
- extensions: `spotify2navidromeSyncer.py` has a "Spotify API credentials" constants block: **SECRET-bearing**, never print. [V] (cmd: head with comments only)
- library: `00-meta/fortress-repository-root/AGENT_INTEGRATION.md` is the notifier API guide and is **stale** (says port 8000; real port is 8001). [V] (DUM-E.md §3 F10)
- PRIVATE trees: `NOTION-DATA [DO NOT REMOVE OR TOUCH]/`, `notion_html_export/`, `notion_html_export.zip`, `HumanReadableData/`, `People-research/`, `life-archive-data/`, `nextplan.md`. Names only.
- pi-cyber: excluded. Do not list or read.
- `~/models/hauhaucs/*.gguf` — AI brain model files (default quant 21 GB, IQ3_M 15 GB). [V] (DUM-E.md §5.1)
- `~/.local/state/hauhaucs-*.log` — helper script logs. [V]
- `~/vox/voicebox/` has no `.env`; compose passes `HF_TOKEN` from the shell environment. `~/.bashrc` exports `HF_TOKEN` in plain text, so a `docker compose up` from an interactive shell injects it. [V] (src: voicebox/docker-compose.yml; DUM-E.md §3 F4) [I] (injection)
- `~/vox/logs/llm-server.pid` — **stale** (pid 207763 is not running). [V] (cmd: ps -p)

## Commands
### Read-only
- `curl -s http://127.0.0.1:17600/health` — Voicebox health (200). READ. [V]
- `~/vox/scripts/status.sh` — prints LLM (:8081) and Voicebox (:17600) status using `curl` and `docker ps/logs`. READ. [V] (src: status.sh:40-57)
- `lclaude models` / `lclaude --model-names` — `ollama list`. READ. [V]
- `python diagnose_mic.py` (voice-poc), `micdiag` (vox) — mic tests; they record audio. READ for the system, but they capture sound. [V]
### Mutating
- `micdelay`, `micrange`, `micptt` — run `mic-delay`, which first applies USB mic fixes and **changes ALSA mixer settings on card 2** (Master 87 %, unmute Front/Headphone, Auto-Mute off), then plays the mic back (echo/monitor/push-to-play). MUTATES (audio settings). [V] (src: scripts/mic-delay:8-18)
- `usb-mic-linux-setup` — applies mixer/USB fixes. MUTATES. [V]
- `sudo cp 99-jieli-usb-mic.rules /etc/udev/rules.d/ && sudo udevadm control --reload` — install udev rule. MUTATES (root). [V] (src: 99-jieli-usb-mic.rules:2)
- `~/vox/scripts/start.sh` — status, Bluetooth, waits for model download, runs `start-llm.sh`, then `docker compose up -d --build` for Voicebox. MUTATES. [V] (src: start.sh:37-44)
- `~/vox/scripts/start-llm.sh` — **kills whatever listens on :8081** (the AI brain) and starts a small Qwen3 model there. Today it exits early because both model folders are empty. MUTATES. [V] (src: start-llm.sh:5-34; cmd: ls ~/models/qwen3-0.6b ~/models/qwen3-4b → empty)
- `bluetooth-setup.sh` — pairs and connects Bluetooth, sets PipeWire defaults. MUTATES. [V]
- `dl.sh`, `download-model.sh` — downloads. MUTATES. [V]
- `vox` — starts the voice loop (uses :8081 and Voicebox; writes notes). MUTATES. [V]
- `lclaude [args]` — starts Claude Code on local Ollama. Loads an Ollama model into the GPU. MUTATES. [V]
- `hauhaucs-download-q4km.sh` — download + **AI brain restart**. MUTATES. [V]
- `hauhaucs-redownload-q4km.sh` — re-download; renames a corrupt model. MUTATES. [V]
- `hauhaucs-install-validate.sh` — **stops/starts the AI brain**. MUTATES. [V]
- `hauhaucs-rebuild-llama.sh` — **DELETES** the llama.cpp `build/` folder and rebuilds it. Until it finishes, the AI brain binary does not exist. [V] (src: hauhaucs-rebuild-llama.sh:19-20)
- vid-gen (planned): ComfyUI start; HANDOFF says to **stop the AI brain** before generating (`llama-server-ctl stop`). MUTATES. [V] (src: HANDOFF.md:70-80)
- voice-poc `python run_poc.py` — records and writes `results/`. MUTATES. [V]
- PS5LM `scripts/*.sh` — build and send payloads to a console on the network. MUTATES (remote device). [V]
- `pi-cyber`, `pi-case` — out of scope.

## Depends on
- `lclaude`: **Ollama :11434**. Default model `qwen3.6:27b` is **not installed** (it is in cold storage); only `qwen3.6:35b-a3b`, `qwen2.5:7b`, `nomic-embed-text` are. `lclaude` without `-m` will fail. `lclaude fast` should work. [V] (src: ~/bin/lclaude:66-71; cmd: ollama list; DUM-E.md §5.2)
- `hauhaucs-*.sh`: **GPU** and the AI brain on **:8081**; network for downloads (Hugging Face). [V]
- Vox orchestrator: **AI brain :8081** (model name `hauhaucs-iq3`) and Voicebox :17600. [V] (src: orchestrator/config.yaml:29-36)
- Voicebox: CPU (limit 4 cores); GPU use [U] (a ROCm compose variant exists; main compose sets no GPU). [V] (cmd: ls voicebox; compose)
- voice-poc: the Jarvis Whisper cache; a USB mic. [V]
- vid-gen (planned): the whole **GPU** (~12 GB VRAM); needs PyTorch nightly cu128 for Blackwell sm_120; never install xformers. [V] (src: HANDOFF.md:26-61)
- PS5LM, whatisthewordfor, archived, extensions, library: no Homelab runtime dependency. [V]

## How to check it (read-only)
- Voicebox: DUM-E tool `containers` (look for `voicebox`), `ports` (127.0.0.1:17600), `health`.
- AI brain conflicts from Vox or helper scripts: DUM-E tool `ai_brain` (check the model path in the process command line) and `gpu`.
- Ollama models for `lclaude`: DUM-E tool `gpu`/`ai_brain`, or owner `ollama list`.
- Disk use of big folders (`life-archive-data` 35 GB, `pi-cyber` 6.6 GB, `archived` 5.6 GB): DUM-E tool `disk_memory`.
- Shell functions and aliases: DUM-E tool `shell_index`.
- Docs: DUM-E tool `manual` / `graph` for library shelves.

## Known problems and fixes
- **`lclaude` default model missing.** `qwen3.6:27b` is not in Ollama. [V] Fix (owner): use `lclaude fast`, pass `-m qwen3.6:35b-a3b`, or set `LCLAUDE_DEFAULT_MODEL`. DUM-E has no action for this.
- **`hauhaucs-install-validate.sh` would fail its pi check.** It greps `~/.pi/agent/models.json` for `hauhaucs-qwen3.6-35b-iq3m`, but that file defines only `your-local-model-id`. [V] (src: hauhaucs-install-validate.sh:34; DUM-E.md §5.3) [I] (result) Its test prompts also ask for the `iq3m` alias. Fix (owner): update the script.
- **Helper scripts bypass the GPU guard and the watchdog.** `hauhaucs-download-q4km.sh` and `hauhaucs-install-validate.sh` restart the AI brain directly. [V] (DUM-E.md §3 F7) Use DUM-E `llama_restart` instead when only a restart is needed.
- **`hauhaucs-download-q4km.sh` sets `LLAMA_NCMOE=13`** for the restart; the normal setting is 32. A different MoE offload changes VRAM use. [V] (src: hauhaucs-download-q4km.sh; DUM-E.md §7.2) [I] (effect)
- **Vox `start-llm.sh` can kill the AI brain.** If a Qwen3 model is ever put back in `~/models/qwen3-4b` or `qwen3-0.6b`, running Vox `start.sh` will kill the process on :8081 and replace it. [V] (src: start-llm.sh:5-27) Never run it while the brain is needed.
- **Vox config asks for model `hauhaucs-iq3`.** The brain reports `your-local-model-id`. Whether llama-server ignores the name is [U]. [V] (src: orchestrator/config.yaml:36; DUM-E.md §3 F8)
- **`voicebox` is unregistered.** It runs on every boot (`unless-stopped`) without appearing in `fortress status` or health checks. [V] (DUM-E.md §3 F11)
- **Stale Vox PID file.** `logs/llm-server.pid` points to a dead process. Harmless. [V]
- **`micdelay` path.** It is not broken: `~/vox/scripts/mic-delay` exists. Note `/home/fortress` is different from `~/homelab`. [V] (DUM-E.md §7.2)
- **Mic dropouts (DWM-123 / Jieli dongle).** Fix: install the udev rule; if peak level stays below ~2000, check the transmitter and run `diagnose_mic.py`. [V] (src: 99-jieli-usb-mic.rules; voice-poc/README.md "Mic issues")
- **vid-gen is half set up.** Only the ComfyUI clone exists; no models, no app. [V]
- **Secrets inside non-secret-looking files:** `archived/icloudpd/docker-compose.yml`, `extensions/spotify2navidromeSyncer.py`. [V] Fix (owner): move values to an `.env` or delete the files.
- **Library README table omits shelf `13-anytype`.** [V] (src: library/README.md; cmd: ls library)
- **`AGENT_INTEGRATION.md` is stale** (port 8000 vs real 8001). [V] (DUM-E.md §3 F10)

## Logs
- `~/.local/state/hauhaucs-q4km-download.log`, `hauhaucs-q4km-redownload.log`, `hauhaucs-validate.log`, `hauhaucs-rebuild.log`. [V]
- `~/vox/logs/` — `llm-server.log` (last 2026-09-10), `talk.log`, `bluetooth.log`, download logs. [V]
- `docker logs --tail 50 voicebox`. [V]
- `/tmp/notion_ai_pause_resume.log` — not this manual (Anytype, manual 38).
- vid-gen, PS5LM, whatisthewordfor, archived, extensions: no live logs.

## Rules for DUM-E here
- `pi-cyber` is out of scope. Do not read, list, run or change it.
- PRIVATE trees (`NOTION-DATA [DO NOT REMOVE OR TOUCH]`, `notion_html_export*`, `HumanReadableData`, `People-research`, `life-archive-data`, `nextplan.md`, voice-poc `results/`, iCloud downloads): name only. Never read, move or delete. `NOTION-DATA` must never be removed or touched by anyone's automation.
- Never print values from `archived/icloudpd/docker-compose.yml` or `extensions/spotify2navidromeSyncer.py`.
- Never run `lclaude`, any `hauhaucs-*.sh`, Vox `start.sh`/`start-llm.sh`/`vox`, `micdelay`/`micrange`/`micptt`, or `mic-delay`. For an AI brain restart use the approvable `llama_restart`.
- DUM-E has no action for Voicebox; the owner runs: `cd ~/vox/voicebox && docker compose stop` (or `up -d`).
- DELETES operations that exist here:
  - `hauhaucs-rebuild-llama.sh`: `rm -rf build` (llama-server binary).
  - `hauhaucs-redownload-q4km.sh`: replaces the model file (old one renamed to `*.corrupt.*`; the temp download is moved over the target).
  - Vox `start-llm.sh`: kills the process on :8081.
  - Any cleanup of `life-archive-data`, `notion_html_export*`, `archived/` (5.6 GB) to free disk would destroy PRIVATE data; owner only.

## Open questions
- Is Voicebox still used, and should it be registered in `services.yaml` or stopped? [U] Ask the owner.
- Does Voicebox use the GPU? [U] Owner checks `nvidia-smi` while it synthesises.
- Is vid-gen still planned? [U]
- Are `archived/` (5.6 GB) and `voice-poc/.venv` (455 MB) still needed, given root is ~91 % full? [U] Owner decides.
- Is the Spotify→Navidrome syncer used anywhere? [U]
