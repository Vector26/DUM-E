---
title: Jarvis voice assistant
scope: The Jarvis voice stack in ~/homelab/jarvis (gateway, Whisper STT, TTS, sandbox, metrics, Android client)
last_verified: 2026-10-29
sources: jarvis/README.md, jarvis/docker-compose.yml, jarvis/.env.example, jarvis/gateway/app/config.py, jarvis/gateway/app/main.py, jarvis/gateway/Dockerfile, jarvis/android/JARVIS_README.md, control/services.yaml, monitoring/prometheus/prometheus.yml, ~/.local/state/homelab/incidents.log, docker ps/inspect/logs
---

# Jarvis voice assistant

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Jarvis is a private voice assistant. It turns speech into text, sends the text to the local AI brain on :8081, and turns the reply back into speech. [V] (src: jarvis/README.md:1-12)
It exists because phone apps that do "live voice" send audio to Google. Jarvis keeps audio and the model on this box. [V] (src: jarvis/README.md:8-12)
It is reachable only over Mesh VPN (e.g. Tailscale), on 100.x.x.x:8800, and needs an API key. [V] (src: jarvis/README.md:17, jarvis/docker-compose.yml:59-60)
It also has a file "sandbox": drop a text file in `io/in`, get an answer in `io/out`. [V] (src: jarvis/README.md:79-81)
**Right now Jarvis is NOT running.** All three containers exited on 2026-07-21 and have stayed down. [V] (cmd: docker ps -a --filter name=jarvis)

## How the owner refers to it
- "Jarvis", "Jarvis voice", "voice assistant". Service id `jarvis`, name "Jarvis voice", blurb "Voice assistant (needs Local AI)". [V] (src: control/services.yaml:88-96)
- The Grafana dashboard is called "Jarvis Voice Assistant" (`/d/jarvis-voice`). [V] (src: jarvis/README.md:85-87)
- The phone app is also called "Jarvis" (built from FluxVoice). [V] (src: jarvis/android/JARVIS_README.md:1-6)
- There are no `.bashrc` aliases for Jarvis. [V] (cmd: grep -n jarvis ~/.bashrc → no match)
- Do not confuse with `~/vox/vox`, whose comment says "Live Jarvis". That is the separate Vox project (manual 39). [V] (src: ~/vox/vox:2)

## Components
- Compose project `jarvis`, file `~/homelab/jarvis/docker-compose.yml`. [V] (src: jarvis/docker-compose.yml:1)
- `jarvis-gateway` container. Image `homelab/jarvis-gateway:local`, built from `jarvis/gateway`. Python 3.12, FastAPI + uvicorn. [V] (src: jarvis/docker-compose.yml:42-45, jarvis/gateway/Dockerfile:1-18)
  - Uses **host networking** (`network_mode: host`). [V] (src: jarvis/docker-compose.yml:52)
  - Main API listens on `JARVIS_BIND_HOST:JARVIS_BIND_PORT`, default 100.x.x.x:8800 (the Mesh VPN (e.g. Tailscale) IP only). [V] (src: jarvis/docker-compose.yml:59-60, gateway/app/config.py:22-23)
  - A second Prometheus metrics listener on **0.0.0.0:9808** (all interfaces, no auth). [V] (src: jarvis/docker-compose.yml:61-62, gateway/app/config.py:27-28, gateway/app/main.py:60)
  - Runs as user `1000:1000` so sandbox files are owned by `(owner)`. [V] (src: jarvis/docker-compose.yml:48)
  - Memory limit 512 MB (swap 768 MB). Restart policy `unless-stopped`. [V] (src: jarvis/docker-compose.yml:46-50; cmd: docker inspect --format RestartPolicy jarvis-gateway)
- `jarvis-whisper` container. Speech-to-text. Image `fedirz/faster-whisper-server:latest-cpu`. CPU only, int8. Model `Systran/faster-whisper-small`. Published on **127.0.0.1:8771** → 8000. Memory limit 2 GB. [V] (src: jarvis/docker-compose.yml:11-27)
- `jarvis-tts` container. Text-to-speech (Piper voices via openedai-speech). Image `ghcr.io/matatonic/openedai-speech-min:latest`. Published on **127.0.0.1:8772** → 8000. Memory limit 1 GB. [V] (src: jarvis/docker-compose.yml:29-40)
- Whisper and TTS join the external Docker network `fortress-network` (172.20.0.0/16, gateway 172.20.0.1). [V] (src: jarvis/docker-compose.yml:26-27,39-40,75-78; cmd: docker network inspect --format … fortress-network)
- Gateway HTTP routes: `/healthz`, `/metrics`, `/v1/models`, `/v1/chat/completions`, `/v1/audio/transcriptions`, `/v1/audio/speech`, WebSocket `/ws/voice`, web UI `/` and `/app`. [V] (src: gateway/app/main.py:104,120,128,143,177,187,302,462)
- Sandbox worker: an async loop inside the gateway that polls `io/in` every 5 s. [V] (src: gateway/app/main.py:426-455, gateway/app/config.py:40-41)
- Android client source in `jarvis/android/` (FluxVoice fork, Kotlin, minSdk 35). It is built on a PC, not on this server. [V] (src: jarvis/android/JARVIS_README.md:23-35)
- Homelab Control registration: id `jarvis`, kind compose, detected by container name `jarvis-gateway`, `gpu: false`, `default: true`, `depends_on: [ai_llama]`. [V] (src: control/services.yaml:88-96)
- No systemd unit and no cron job for Jarvis. [V] (cmd: crontab -l; DUM-E.md §10.2)

## Files and data
- `~/homelab/jarvis/.env` — **SECRET**. Holds `JARVIS_API_KEY` and other settings. Never open. [V] (src: jarvis/README.md:39-40)
- `~/homelab/jarvis/.env.example` — safe template. Variable names: `JARVIS_API_KEY`, `JARVIS_BIND_HOST`, `JARVIS_BIND_PORT`, `JARVIS_LLM_BASE`, `JARVIS_LLM_MODEL`, `JARVIS_WHISPER_BASE`, `JARVIS_TTS_BASE`, `WHISPER_MODEL`, `WHISPER_IMAGE`, `TTS_IMAGE`, `JARVIS_SYSTEM_PROMPT`, `JARVIS_TTS_VOICE`. [V] (src: jarvis/.env.example:1-21)
- Other env names read by the gateway: `JARVIS_TTS_MODEL`, `JARVIS_METRICS_HOST`, `JARVIS_METRICS_PORT`, `JARVIS_IO_IN`, `JARVIS_IO_OUT`, `JARVIS_SANDBOX_ENABLED`, `JARVIS_SANDBOX_POLL_SECONDS`, `JARVIS_MAX_TOKENS` (1024), `JARVIS_REQUEST_TIMEOUT` (300 s), `JARVIS_DISABLE_THINKING` (1). [V] (src: gateway/app/config.py:15-51)
- `jarvis/io/in/` — drop `.txt` or `.md` prompts here. Mounted into the gateway as `/io/in`. [V] (src: jarvis/docker-compose.yml:72)
- `jarvis/io/in/_processed/` — prompts move here after an answer. Currently empty. [V] (src: gateway/app/main.py:421-423; cmd: ls io/in/_processed)
- `jarvis/io/in/_processing/` and `jarvis/io/in/_failed/` — created by the worker when needed. Neither exists now. [V] (src: gateway/app/main.py:398-399,445; cmd: ls io/in)
- `jarvis/io/out/` — answers land here as `<name>.<YYYYmmdd-HHMMSS>.md`. Mounted as `/io/out`. [V] (src: gateway/app/main.py:417-419, jarvis/docker-compose.yml:73)
- `jarvis/data/whisper/` — Hugging Face cache for Whisper (`hub/models--Systran--faster-whisper-small`). Also reused by `voice-poc`. [V] (cmd: ls data/whisper/hub; src: homelab/voice-poc/run_poc.py:22-26)
- `jarvis/data/piper/` — Piper voice files (`en_US-libritts_r-medium`, `en_GB-northern_english_male-medium`, `voices.json`). [V] (cmd: ls data/piper)
- `jarvis/gateway/web/` — the bundled push-to-talk web app (PWA). [V] (cmd: ls gateway/web)
- `jarvis/android/app/src/main/java/com/techrifter/fluxvoice/domain/model/AppSettings.kt:22` — **SECRET**: holds a long hard-coded default `openAiApiKey` value. The README says the API key is "pre-filled". Treat it as the Jarvis key. Never print it. [V] (src: jarvis/android/JARVIS_README.md:10-13; cmd: grep with value redacted)
- `jarvis/android/app/src/main/res/xml/network_security_config.xml` — allows plain http only to 100.x.x.x. [V] (src: jarvis/android/JARVIS_README.md:20)
- Grafana dashboard file: `~/homelab/monitoring/grafana/provisioning/dashboards/json/jarvis-voice.json`. [V] (cmd: grep -rln jarvis monitoring)

## Commands
- `cd ~/homelab/jarvis && docker compose ps` — show the stack. READ. [V] (src: jarvis/README.md:43)
- `curl -s http://100.x.x.x:8800/healthz` — health of llm, whisper, tts. READ (no auth needed). [V] (src: jarvis/README.md:44, gateway/app/main.py:104-117)
- `curl -s http://127.0.0.1:9808/metrics` — Prometheus metrics. READ. [I] (src: gateway/app/config.py:27-28)
- `docker logs --tail 50 jarvis-gateway` — recent gateway log. READ. [V]
- `docker compose up -d` (in jarvis/) — start whisper, tts and gateway. Builds the gateway image if missing. MUTATES. [V] (src: jarvis/README.md:42)
- `docker compose up -d jarvis-gateway` — restart gateway after editing `.env` (e.g. persona). MUTATES. [V] (src: jarvis/README.md:106-107)
- `docker compose stop` (in jarvis/) — what `fortress stop jarvis` runs. MUTATES. [V] (src: control/lib/actions.sh:47-49)
- `fortress start jarvis` / `fortress stop jarvis` — Homelab Control wrapper. MUTATES. [V] (src: control/lib/actions.sh:38-49)
- `cp .env.example .env` — creates config. MUTATES; if `.env` already exists this **DELETES** (overwrites) the real key file. [V] (src: jarvis/README.md:39)
- Dropping a file into `io/in/` — starts a sandbox job. MUTATES (moves the file, writes to `io/out`). An **empty** prompt file is **deleted** by the worker (DELETES). [V] (src: gateway/app/main.py:405-407)
- Android build (`./gradlew`, Android Studio) — runs on a PC, not here. [V] (src: android/JARVIS_README.md:23-31)

## Depends on
- **AI brain on :8081 — required.** The gateway calls `http://127.0.0.1:8081` for all text. [V] (src: jarvis/docker-compose.yml:63, gateway/app/config.py:10) Homelab Control lists `depends_on: [ai_llama]`. [V] (src: control/services.yaml:96)
- Model name sent: `hauhaucs-qwen3.6-35b-iq3m` by default. The server ignores or mismatches this alias (it always reports `your-local-model-id`). [V] (src: jarvis/docker-compose.yml:64; DUM-E.md §3 F8) Requests still work if llama-server ignores the model field. [U] — settle with one chat call while Jarvis runs.
- Reasoning is turned off by appending `/no_think` to the system message. [V] (src: gateway/app/main.py:224-235)
- **GPU:** Jarvis itself uses no GPU. STT and TTS are CPU-only. The GPU is used only through the AI brain. [V] (src: jarvis/README.md:32, jarvis/docker-compose.yml:19)
- **Ollama :11434:** not used. [V] (src: gateway/app/config.py — no Ollama URL)
- **Notifier :8001:** not used. [V] (src: gateway/app/main.py — no notify call)
- **Mesh VPN (e.g. Tailscale):** the gateway binds to 100.x.x.x. If Mesh VPN (e.g. Tailscale) is not up, uvicorn cannot bind. [I] (src: jarvis/docker-compose.yml:59)
- Docker network `fortress-network` must exist (external). [V] (src: jarvis/docker-compose.yml:75-78)
- Prometheus (monitoring stack) scrapes job `jarvis-gateway` at `172.20.0.1:9808`. [V] (src: monitoring/prometheus/prometheus.yml:54-59)
- Internet: Whisper image downloads its model on first use; TTS downloads voices on first synth. [V] (src: jarvis/README.md:47-48) The Whisper container also contacted `api.gradio.app` at start-up (a gradio telemetry call). [V] (cmd: docker logs --tail 5 jarvis-whisper)

## How to check it (read-only)
- Is it running? DUM-E tool `containers` (look for `jarvis-gateway`, `jarvis-whisper`, `jarvis-tts`) or `services` (id `jarvis`). Owner: `docker ps -a --filter name=jarvis`.
- Is the brain up? DUM-E tool `ai_brain`. Owner: `curl -s http://127.0.0.1:8081/health`.
- Ports: DUM-E tool `ports` (8800 on 100.x.x.x, 9808, 127.0.0.1:8771, 127.0.0.1:8772). Owner: `ss -ltnp | grep -E '8800|9808|877[12]'`.
- Health: when running, `curl -s http://100.x.x.x:8800/healthz` should print `{"llm":"ok","whisper":"ok","tts":"ok"}`. [V] (src: jarvis/README.md:44)
- Incidents: DUM-E tool `incidents` (source `jarvis`).
- Logs: DUM-E tool `log_tail` on the three containers.
- Prometheus target state: DUM-E tool `health`, or `curl -s 'http://127.0.0.1:9090/api/v1/targets?state=active'` (job `jarvis-gateway`).

## Known problems and fixes
- **Jarvis is down since 2026-07-21.**
  Symptom: no `jarvis-*` containers running. Port 8800 not listening.
  Evidence: all three exited with code 137 at 2026-07-21 15:47 UTC. Restart policy is `unless-stopped`, so they did not come back after reboots. [V] (cmd: docker inspect --format State/RestartPolicy jarvis-gateway jarvis-whisper jarvis-tts)
  Cause: exit 137 means SIGKILL. `docker stop` sends SIGKILL after its timeout. The Anytype container stopped at the same minute. [I] Someone stopped them on purpose (a manual stop). [U] — settle by asking the owner.
  Fix: if the owner wants Jarvis, DUM-E can propose `service_start jarvis` (approvable). Check the AI brain is up first (`ai_brain`).
- **Health alert noise.** `fortress health` logged "Jarvis voice: not running (default service)" 737 times from 2026-09-29 to 2026-10-29. [V] (src: incidents.log, aggregated)
  Cause: Jarvis is `default: true` in `services.yaml` but not in the saved boot profile. [V] (src: control/services.yaml:95; DUM-E.md §3 F6)
  Fix: owner decides. Either start Jarvis, or set `default: false` in `services.yaml`. DUM-E has no action for this; the owner edits `~/homelab/control/services.yaml`.
- **Model alias mismatch.** Jarvis asks for `hauhaucs-qwen3.6-35b-iq3m`. The server alias is `your-local-model-id`. [V] (src: jarvis/docker-compose.yml:64; DUM-E.md §3 F8) Effect unknown [U]. Fix (owner): set `JARVIS_LLM_MODEL` in `.env` to the served alias, then `docker compose up -d jarvis-gateway`.
- **Metrics port open to the LAN.** 9808 binds 0.0.0.0 on the host network. The firewall is off. Metrics have no secrets but reveal usage. [V] (src: gateway/app/config.py:25-28; DUM-E.md §3 F9) DUM-E has no action for this; the owner can set `JARVIS_METRICS_HOST=172.20.0.1` in `.env` and recreate the gateway.
- **Auth turns off if the key is empty.** `_check_key` returns true when `JARVIS_API_KEY` is empty. [V] (src: gateway/app/main.py:80-83) A missing `.env` would open the API on the tailnet. [I]
- **`/healthz` and `/metrics` on :8800 need no key.** [V] (src: gateway/app/main.py:104-124)
- **Sandbox: a failed job can get stuck.** The worker first moves the file to `io/in/_processing/`. On error it tries to move the *original* path to `_failed/`, which no longer exists, and silently gives up. The file stays in `_processing/`. [I] (src: gateway/app/main.py:398-402,436-448) Fix (owner): move the file back to `io/in/` by hand after fixing the cause.
- **Sandbox needs the brain.** With :8081 down, every sandbox job fails. [I] (src: gateway/app/main.py:239-245)
- **Prometheus target is down** while Jarvis is stopped (`connect: connection refused` on 172.20.0.1:9808). Expected. [V] (cmd: Prometheus targets API)
- **RAM is tight.** Memory limits are kept small on purpose. Keep Whisper at `small`. [V] (src: jarvis/README.md:102-104)

## Logs
- `docker logs --tail 50 jarvis-gateway` — uvicorn start lines ("Uvicorn running on http://100.x.x.x:8800"), and `[sandbox] <file> failed:` tracebacks. [V] (cmd: docker logs; src: gateway/app/main.py:441-442)
- `docker logs --tail 50 jarvis-whisper` — model download and request lines. [V]
- `docker logs --tail 50 jarvis-tts` — voice download and synth lines. [I]
- Loki/Grafana: live logs panel on the "Jarvis Voice Assistant" dashboard. [V] (src: jarvis/README.md:85-87)
- Homelab incidents: `~/.local/state/homelab/incidents.log`, source `jarvis`. [V]

## Rules for DUM-E here
- Never open `jarvis/.env` or print the hard-coded key in `android/.../AppSettings.kt`. Name them only.
- Never run `docker compose up/down/stop/restart` in this folder. Use only `service_start jarvis` / `service_stop jarvis`, and only after owner approval.
- Never start Jarvis while the AI brain is paused by the watchdog. Check `ai_brain` first.
- Never write into `io/in/`. A file there becomes an LLM job.
- Never edit `.env` or the persona. That is the owner's job.
- DELETES operations that exist here:
  - The sandbox worker deletes empty prompt files (`work.unlink`). (src: gateway/app/main.py:405-407)
  - `cp .env.example .env` overwrites the real `.env` if run again.
  - `docker compose down` (not used by homelab, but possible) removes the containers.

## Open questions
- Why was Jarvis stopped on 2026-07-21? [U] Ask the owner.
- Does llama-server accept the `iq3m` model name? [U] Test one `/v1/chat/completions` call when Jarvis and the brain are both up.
- Is the Android app installed and in use? [U] Ask the owner.
- Is gradio telemetry in the Whisper image switchable off? [U] Check the image docs.
- Does the gateway still bind if Mesh VPN (e.g. Tailscale) starts after Docker at boot? [U] Check `docker logs jarvis-gateway` after the next start at boot.
