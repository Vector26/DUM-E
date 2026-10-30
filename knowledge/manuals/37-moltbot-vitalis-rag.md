---
title: Vitalis and Meilisearch (Moltbot and RAG agent removed 2026-10-29)
scope: Optional stopped projects — Vitalis health platform (~/homelab/vitalis) and Meilisearch play (~/homelab/meilisearch-play). Moltbot and the Notion RAG agent were removed from the host on 2026-10-29.
last_verified: 2026-10-29
sources: vitalis/README.md, vitalis/docker-compose.yml, vitalis/.env.example, vitalis/docs/*.md, meilisearch-play/docker-compose.yml, meilisearch-play/CONTEXT.md, control/services.yaml
---

# Vitalis and Meilisearch

> **Removed 2026-10-29:** `homelab/moltbot` and `homelab/rag-agent` (plus orchestration stack `stacks/rag-agent`) were deleted. Historical notes below about Moltbot/RAG are kept for context only.

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.

## What it is
### Moltbot (OpenClaw)
Moltbot is a self-hosted copy of OpenClaw, an AI assistant with a web "Control UI". It talks to a local Ollama model and can read an input folder and write an output folder. [V] (src: moltbot/MOLTBOT_SETUP.md:7-13) It was set up in February 2026. It is **not running**, and its container and image no longer exist. [V] (cmd: docker ps -a --filter name=moltbot → none; docker image ls | grep -ic claw → 0)
### Vitalis
Vitalis ("Concierge Health") is a private health analytics stack for an Amazfit Helio Strap and a Samsung Galaxy Watch 7. It ingests wearable data, scores readiness/sleep/strain/recovery, and writes daily non-medical AI briefings. [V] (src: vitalis/README.md:1-13) It holds **PRIVATE health data** once deployed. It has **never been deployed** here: no containers, no `vitalis_pgdata` volume, no `.env`. [V] (cmd: docker ps -a --filter name=vitalis; docker volume ls; ls -la vitalis)
### RAG agent
The RAG agent was a "Notion RAG": ask questions about the owner's Notion notes, backed by a Qdrant vector database. [V] (src: control/services.yaml:173-180; orchestration/stacks/rag-agent/docker-compose.yml:1-8) **The application code is gone.** Only Qdrant data remains. The architecture plan calls it "Dead/broken". [V] (cmd: ls rag-agent; src: VIRTUAL_SELF_ARCHITECTURE_PLAN.md:91-100)
### Meilisearch play
A Meilisearch search server "for experiments" (testing only). [V] (src: meilisearch-play/CONTEXT.md:1-3; meilisearch-play/docker-compose.yml:1) It is stopped since 2026-10-19. [V] (cmd: docker inspect --format State fortress-meilisearch-play)

## How the owner refers to it
### Moltbot
- "Moltbot", "OpenClaw", "Moltbot / OpenClaw", "Agent gateway (uses Ollama)". Service id `moltbot`. [V] (src: control/services.yaml:202-209)
- No `.bashrc` alias. The owner's helper is `~/homelab/moltbot/moltbot.sh {start|stop|restart|logs|status|cli|info}`. [V] (cmd: grep moltbot ~/.bashrc → none; src: moltbot/moltbot.sh)
### Vitalis
- "Vitalis", "Health / concierge platform". Service id `vitalis`. [V] (src: control/services.yaml:155-162)
### RAG agent
- "RAG Agent", "Ask questions about your Notion notes (GPU)". Service id `rag_agent`. [V] (src: control/services.yaml:173-180)
- Aliases: `rag-agent` → `~/homelab/rag-agent/.venv/bin/rag-agent`; `getNotionRagCount` → `cd ~/homelab/rag-agent && .venv/bin/python -m cli.main count`. [V] (src: ~/.bashrc:484-485) Comment calls it "Onyx/Qdrant document search CLI". [V] (src: ~/.bashrc:482)
- `runQdrant` → `docker run -p 6333:6333 qdrant/qdrant` (throwaway Qdrant, no volume). [V] (src: ~/.bashrc:95-96)
### Meilisearch
- "meilisearch-play", "Meilisearch (play)". Not registered in `services.yaml`. [V] (src: control/services.yaml — absent)

## Components
### Moltbot
- Compose project `moltbot`, file `~/homelab/moltbot/docker-compose.yml`. [V]
- `moltbot-gateway` (service `openclaw-gateway`): image `openclaw:local` (built from `moltbot/repo`). Host networking. Command `node dist/index.js gateway --bind loopback --port 18789`. Caps dropped except `NET_BIND_SERVICE`, `no-new-privileges`. Restart `unless-stopped`. [V] (src: moltbot/docker-compose.yml:4-42)
- `moltbot-cli` (service `openclaw-cli`): same image, interactive (stdin/tty), entrypoint `node dist/index.js`. No profile, so a plain `docker compose up -d` also tries to start it. [V] (src: moltbot/docker-compose.yml:44-67)
- Port: **127.0.0.1:18789** (loopback). Remote access was via **Mesh VPN (e.g. Tailscale) Serve** HTTPS (`https://homelab-host.your-tailnet.ts.net`) proxying to 127.0.0.1:18789. [V] (src: MOLTBOT_SETUP.md:11-13,70-74) Something listens on `100.x.x.x:443` now; whether it is a Mesh VPN (e.g. Tailscale) Serve rule for Moltbot is [U]. (cmd: ss -ltnp)
- Homelab Control: id `moltbot`, detect container `moltbot-gateway`, `gpu: false`, `default: false`. [V] (src: control/services.yaml:202-209)
### Vitalis
- Compose project `vitalis`, file `~/homelab/vitalis/docker-compose.yml`. [V]
- `backend` — built from `vitalis/backend` (Python app `app.main`). Port **0.0.0.0:39082**. Healthcheck `wget http://localhost:39082/health`. Memory 768 MB. Networks `fortress-network` + `vitalis-internal`. [V] (src: vitalis/docker-compose.yml:4-35)
- `worker` — same image, `python -m app.workers.runner` (Zepp pull, scores, trends, AI briefings; "runs every 30 min"). Memory 512 MB. Network `vitalis-internal` only. [V] (src: vitalis/docker-compose.yml:36-60; docs/HUMAN_GUIDE.md:61)
- `web` — built from `vitalis/web` (Vite/React + nginx). Port **0.0.0.0:39174**. Memory 256 MB. [V] (src: vitalis/docker-compose.yml:62-80)
- `postgres` — `timescale/timescaledb:latest-pg16`. Volume `vitalis_pgdata`. Init SQL from `db/init` (`001_schema.sql`, `002_baselines_trends.sql`). Internal network only. [V] (src: vitalis/docker-compose.yml:82-100; cmd: ls db/init)
- Networks: `fortress-network` (external) and `vitalis-internal` (`internal: true`). [V] (src: vitalis/docker-compose.yml:105-110)
- Restart policy for all: `unless-stopped`. [V]
- Android companion (`vitalis/android/`) — scaffold only; reads Health Connect and pushes to the backend. [V] (src: docs/TECHNICAL_CONTEXT.md:338)
- Homelab Control: id `vitalis`, detect port 39082, `gpu: false`, `default: false`. [V] (src: control/services.yaml:155-162)
### RAG agent
- Compose project `rag-agent`, file `~/homelab/orchestration/stacks/rag-agent/docker-compose.yml`. [V]
- `rag-agent-qdrant` — `qdrant/qdrant:latest`, ports **6333** (HTTP) and **6334** (gRPC) on all interfaces, volume `rag-agent-qdrant-storage`. Healthcheck uses `curl`. [V] (src: stack compose:12-34)
- `rag-agent-ui` — **build context `~/homelab/rag-agent`, which has no Dockerfile**. Port **8000:8000**. GPU reservation (`nvidia`, count all). Ollama via `host.docker.internal:11434`, model `llama3.2`. [V] (src: stack compose:37-82; cmd: ls -la rag-agent)
- `rag-agent-notion-sync` — profile `sync`; runs `rag-agent notion ingest` every hour. [V] (src: stack compose:84-126)
- Homelab Control: id `rag_agent`, detect port 6333, **`gpu: true`**, `default: false`. [V] (src: control/services.yaml:173-180)
- No containers exist now. [V] (cmd: docker ps -a)
### Meilisearch
- Compose project `meilisearch-play`, file `~/homelab/meilisearch-play/docker-compose.yml`. [V]
- `fortress-meilisearch-play` — `getmeili/meilisearch:v1.16`. Ports `${TAILSCALE_IP}:${MEILI_HTTP_PORT}` and `127.0.0.1:${MEILI_HTTP_PORT}` → 7700. The container was created with **100.x.x.x:7700** and **127.0.0.1:7700**. Memory 6 GB (swap 8 GB). Healthcheck `wget /health`. Analytics off. Restart `unless-stopped`. [V] (src: meilisearch-play/docker-compose.yml:5-33; cmd: docker inspect)
- State: `Exited (143)` at 2026-10-19 18:55 UTC. Not restarted at the 2026-10-29 boot. [V] (cmd: docker inspect --format State)

## Files and data
### Moltbot
- `moltbot/.env` — **SECRET** (compose vars `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_CONFIG_DIR`, `OPENCLAW_WORKSPACE_DIR`, `MOLTBOT_INPUT_DIR`, `MOLTBOT_OUTPUT_DIR`). [V] (src: moltbot/docker-compose.yml:11-21; MOLTBOT_SETUP.md:36-41)
- `moltbot/ACCESS_INFO.txt` — **SECRET**. Never open. [V]
- `moltbot/get-tokenized-url.sh` — **SECRET-bearing script** (builds a URL with the token). Never run or print. [V]
- `moltbot/TOKENIZED_URL.txt` — **SECRET** (URL with token). Never open. [I] (name)
- `moltbot/FINAL_STATUS.txt` — setup summary; may contain the token. Treat as **SECRET**. [U]
- `moltbot/moltbot.sh`, `moltbot/start-moltbot.sh`, `moltbot/QUICK_ACCESS.sh` — contain the **gateway token hard-coded** in plain text. **SECRET-bearing.** Never print. [V] (cmd: read with long strings redacted)
- `moltbot/config/` (mode 700) — `openclaw.json`, `config.json`, `gateway.token`, `credentials/`, `identity/`, `devices/`, `agents/` (sessions), `cron/`, `canvas/`, `workspace/`. **SECRET.** [V] (cmd: ls config)
- `moltbot/workspace/` — agent home (identity, soul, memory). PRIVATE. [V] (src: MOLTBOT_SETUP.md:21-22,222)
- `moltbot/input/` (read-only to the agent; holds `reference_site.html`), `moltbot/output/` (empty). [V] (cmd: ls)
- `moltbot/repo/` — upstream OpenClaw source clone (has its own `docker-compose.yml`, `fly.toml`). [V] (cmd: ls repo)
- `moltbot/ollama-config.json` — model `ollama/qwen2.5:14b-instruct`, gateway bind `lan`. [V]
- `moltbot/ollama-override.conf` — a copy of the Ollama systemd override that sets `OLLAMA_HOST=0.0.0.0` "so Docker containers (e.g. MoltBot) can reach Ollama". [V]
- `moltbot/MOLTBOT_SETUP.md` → symlink to `~/homelab/library/99-third-party/moltbot/MOLTBOT_SETUP.md`. [V] (cmd: ls -la)
### Vitalis
- `vitalis/.env` — does not exist. `.env.example` names: `POSTGRES_PASSWORD`, `DATABASE_URL`, `APP_ENV`, `API_BASE_URL`, `WEB_BASE_URL`, `ANDROID_PUSH_TOKEN`, `ZEPP_HOST`, `ZEPP_APP_TOKEN`, `ZEPP_USER_ID`, `OLLAMA_URL`, `LLAMA_CPP_URL`, `LLM_MODEL`, `CURSOR_AGENT_MODEL`. When created, `.env` is **SECRET**. [V] (cmd: ls -la; grep names .env.example)
- Health data would live in Docker volume `vitalis_pgdata` (**PRIVATE**). It does not exist yet. [V] (cmd: docker volume ls)
- Docs: `vitalis/docs/HUMAN_GUIDE.md`, `vitalis/docs/TECHNICAL_CONTEXT.md`, `vitalis/android/AGENT_BUILD_SPEC.md`. [V]
- `vitalis/backend/.venv`, `backend/tests`, `web/dist` — dev artefacts. [V]
### RAG agent
- `~/homelab/rag-agent/qdrant_storage/` — root-owned Qdrant data from 2026-02-07, one collection `rag`. Notion content embeddings: **PRIVATE**. [V] (cmd: ls -la)
- Docker volumes `rag-agent_qdrant-storage` (created 2026-02-09) and `rag-agent_rag-agent-data` (2026-02-07). **PRIVATE.** [V] (cmd: docker volume inspect --format)
- The current stack compose names its volumes `rag-agent-qdrant-storage` and `rag-agent-data` — **different names**. Starting it would create new empty volumes and ignore the old ones. [I] (src: stack compose:128-140)
- Old Onyx volumes `onyx-rag-agent_*` (api_server_data, background_data, clara_model_cache, minio_data, postgres_data, redis_data, vespa_data) still exist; the Onyx folder `~/onyx-rag-agent` is gone. **PRIVATE.** [V] (cmd: docker volume ls; ls ~/onyx-rag-agent)
- Compose env names: `NOTION_API_KEY`, `NOTION_ROOT_PAGE_ID` (**SECRET** values), `NOTION_RATE_LIMIT_INTERVAL_SECONDS`, `NOTION_REQUEST_TIMEOUT_MS`, `NOTION_SYNC_INTERVAL_SECONDS`, `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL`. [V] (src: stack compose:50-58,108-112)
### Meilisearch
- `meilisearch-play/CREDENTIALS.md` — **SECRET**. Never open. [V]
- `meilisearch-play/.env` — **SECRET** (`MEILI_MASTER_KEY`, `MEILI_ENV`, `MEILI_HTTP_PORT`, `TAILSCALE_IP` per compose). [V] (src: docker-compose.yml:10-20)
- `meilisearch-play/meili_data/` — index data. [V]
- `meilisearch-play/datasets/movies.json` — sample data. [V]
- `meilisearch-play/scripts/` — **empty**; `CONTEXT.md` mentions `scripts/seed-movies.sh`, which is missing. [V] (cmd: ls scripts)

## Commands
### Moltbot
- `moltbot.sh status` / `moltbot.sh logs` — `docker ps | grep moltbot` and compose logs. READ (but the script prints the token in `info`; DUM-E must not run it). [V] (src: moltbot/moltbot.sh)
- `moltbot.sh start` — `docker compose up -d openclaw-gateway`. MUTATES. [V]
- `moltbot.sh stop` — **`docker compose down`** (removes containers). MUTATES. [V]
- `moltbot.sh restart` — `docker compose restart openclaw-gateway`. MUTATES. [V]
- `moltbot.sh cli …` — `docker compose run --rm openclaw-cli …`. MUTATES. [V]
- `moltbot.sh info`, `QUICK_ACCESS.sh`, `get-tokenized-url.sh` — print the token. Not for DUM-E. [V]
- `start-moltbot.sh` — **overwrites `config/config.json` and `config/gateway.token`**, then starts the gateway. DELETES (overwrites config). [V] (src: start-moltbot.sh)
- `setup-moltbot.sh` — first-time setup. MUTATES. [I] (name; not read in full)
- `docker build -t openclaw:local -f Dockerfile .` (in `repo/`) — rebuild the image. MUTATES. [V] (src: MOLTBOT_SETUP.md:27)
- `fortress start moltbot` — `docker compose up -d` in `moltbot/`. MUTATES. [V] (src: control/lib/actions.sh:38-44)
### Vitalis
- `docker compose config` — validate compose. READ. [V] (src: vitalis/README.md:20)
- `cp .env.example .env` then `docker compose up -d --build` — first deploy. MUTATES. [V] (src: README.md:18-21)
- `docker exec -i <postgres> psql … < db/init/002_baselines_trends.sql` — apply migration by hand. MUTATES. [V] (src: TECHNICAL_CONTEXT.md:310-313)
- `cd backend && python -m pytest`; `cd web && npm install && npm run build && npm run test` — tests. MUTATES (installs/builds). [V] (src: README.md:70-73)
- `fortress start vitalis` — `docker compose up -d` (builds images). MUTATES. [V]
### RAG agent
- `rag-agent …`, `getNotionRagCount` — **broken** (`.venv` does not exist). [V] (cmd: ls rag-agent/.venv → missing)
- `runQdrant` — starts a throwaway Qdrant on 6333 in the foreground. MUTATES. [V]
- `fortress start rag_agent` — `docker compose up -d` in the stack dir. Would fail on the missing Dockerfile. MUTATES. [I]
- `docker compose --profile sync up -d` — hourly Notion ingest. MUTATES. [V] (src: stack compose:122-123)
### Meilisearch
- `curl -s http://127.0.0.1:7700/health` — health (when running). READ. [I] (src: compose healthcheck)
- `docker compose up -d` (in `meilisearch-play/`) — start. MUTATES. [V] (src: CONTEXT.md:5)
- Meilisearch HTTP API can create, replace and **delete** indexes and documents (master key needed). DELETES possible. [I]

## Depends on
### Moltbot
- **Ollama :11434 — required.** Host network; config must use `http://127.0.0.1:11434/v1`. [V] (src: MOLTBOT_SETUP.md:115-123) This is why Ollama listens on 0.0.0.0. [V] (src: moltbot/ollama-override.conf)
- Configured model `qwen2.5:14b-instruct` is **not installed** (installed: `qwen2.5:7b`, `qwen3.6:35b-a3b`, `nomic-embed-text`). [V] (src: ollama-config.json; cmd: ollama list)
- GPU: through Ollama only. AI brain :8081: not used. Notifier: not used. [V] (src: compose, config)
- Mesh VPN (e.g. Tailscale) Serve for remote HTTPS access. [V] (src: MOLTBOT_SETUP.md:13)
### Vitalis
- **Ollama :11434** first (model `llama3.1` by default — **not installed**), then a llama.cpp server on **:8080** (nothing listens on 8080; the AI brain is on 8081), then a fixed fallback text. [V] (src: docker-compose.yml:93-95; TECHNICAL_CONTEXT.md:249-254; cmd: ollama list; ss -ltnp)
- Optional `cursor-agent --model composer-2.5` (a cloud coding agent) for "deep analysis". This would send health data to a cloud service. [V] (src: TECHNICAL_CONTEXT.md:256)
- Zepp/Huami cloud API (token-based, unofficial). [V] (src: README.md:30-39)
- Phone on Mesh VPN (e.g. Tailscale) (100.x.x.x) for Android push. [V] (src: README.md:60)
- The `worker` is only on the internal network, so it probably **cannot reach** Ollama or Zepp. [I] (src: docker-compose.yml:135-136,185-186)
### RAG agent
- **GPU** (compose reserves all GPUs; `services.yaml` says `gpu: true`). [V]
- **Ollama :11434** (`llama3.2`, not installed). [V] (src: stack compose:56-58; cmd: ollama list)
- Notion API (cloud). [V]
- **Port 8000 conflicts with Portainer** (`fortress-portainer` binds 0.0.0.0:8000). [V] (cmd: docker ps)
### Meilisearch
- Mesh VPN (e.g. Tailscale) IP 100.x.x.x must exist when the container starts (it binds to it). [V] (cmd: docker inspect port bindings)
- No GPU, no AI brain, no Ollama. [V] (src: compose)

## How to check it (read-only)
- Running at all? DUM-E tool `services` (ids `moltbot`, `vitalis`, `rag_agent`) and `containers`. Owner: `docker ps -a --filter name=moltbot` (and `vitalis`, `rag-agent`, `meilisearch`).
- Ports: DUM-E tool `ports` → 18789, 39082, 39174, 6333/6334, 7700 should all be absent today.
- Ollama models present: DUM-E tool `gpu` or `ai_brain`; owner `ollama list`.
- Volumes and disk: DUM-E tool `disk_memory`; owner `docker volume ls | grep -E 'rag-agent|onyx|vitalis'`.
- Incidents: DUM-E tool `incidents` — none for these four services. [V] (src: incidents.log grep)

## Known problems and fixes
### Moltbot
- **Image `openclaw:local` is gone.** `service_start moltbot` will fail (no image to pull). [V] (cmd: docker image ls) Fix (owner): rebuild from `moltbot/repo` (see Commands).
- **Model not installed.** `qwen2.5:14b-instruct` is missing from Ollama. [V] Fix (owner): change the model in `config/openclaw.json` or pull it.
- **Token in plain text in three scripts** and token-only auth with device pairing turned off (`allowInsecureAuth: true`, pairing disabled). [V] (src: MOLTBOT_SETUP.md:76-87) Fix (owner): rotate the token and remove it from scripts.
- **`moltbot.sh stop` uses `docker compose down`**, not `stop`. [V]
- Old setup issues (from the doc): "pairing required" (1008), "requires HTTPS or localhost" (1008), Ollama 404 because `baseUrl` lacked `/v1`, agent timeout (set `timeoutSeconds: 120`), stale sessions (clear `config/agents/main/sessions/*.jsonl`), config path (`OPENCLAW_CONFIG_PATH`), WebSocket frames through Mesh VPN (e.g. Tailscale) Serve. [V] (src: MOLTBOT_SETUP.md:98-154)
### Vitalis
- **Never deployed.** No `.env`, containers or volume. [V]
- **Unsafe defaults if started without `.env`:** `POSTGRES_PASSWORD` falls back to a fixed default and `ANDROID_PUSH_TOKEN` to `replace-me`. The web dashboard has **no auth** and binds 0.0.0.0. [V] (src: docker-compose.yml:91-92,166; TECHNICAL_CONTEXT.md:343)
- **LLM settings point at things that do not exist:** `:8080` llama.cpp, `llama3.1` in Ollama. [V]
- **Detector checks only the backend port 39082.** The web on 39174 could be down unseen. [V] (src: control/services.yaml:160)
- Zepp tokens expire; re-extract and restart `worker`. [V] (src: README.md:39; HUMAN_GUIDE.md:60)
- Android app is a scaffold (no permissions UI, no WorkManager, no gradlew). [V] (src: TECHNICAL_CONTEXT.md:338)
- Migrations in `db/init` only run on an empty volume; later ones must be applied by hand. [V] (src: TECHNICAL_CONTEXT.md:308-313)
### RAG agent
- **Dead.** No source, no Dockerfile, no `.venv`; aliases fail. [V] (cmd: ls -la rag-agent)
- **Would conflict on port 8000** with Portainer. [V]
- **Volume names changed**, so old data would not be used. [I]
- Health alerts: none, because `default: false`. [V]
- Fix: owner decides whether to retire it (remove from `services.yaml`, drop aliases) and whether to keep the old Qdrant data. The plan recommends: mark retired, keep the volume until the owner decides. [V] (src: VIRTUAL_SELF_ARCHITECTURE_PLAN.md:98-100) DUM-E has no action for this.
### Meilisearch
- **Did not come back after reboot** despite `unless-stopped`. It exited with 143 (SIGTERM) at 2026-10-19 18:55 UTC, the same moment other containers stopped for a shutdown. [V] (cmd: docker inspect; docker logs of plane/vself) Cause [U]: a manual `docker stop`, or the Mesh VPN (e.g. Tailscale) IP missing when Docker started (bind fails). Check `journalctl -u docker` around the 2026-10-29 boot (owner).
- **Not registered in `services.yaml`**, so `fortress health` never checks it. [V]
- **Seed script missing** (`scripts/seed-movies.sh`). [V]

## Logs
- Moltbot: `docker compose logs openclaw-gateway` (when it exists); `moltbot/watch-connections.sh` watches connections; `debug-ws-standalone.mjs` / `run-debug-ws.sh` for WebSocket debugging. [V] (cmd: ls; src: MOLTBOT_SETUP.md:142-154)
- Vitalis: `docker logs <vitalis-worker>` for Zepp auth errors (after deploy). [V] (src: README.md:39)
- RAG agent: none (no containers).
- Meilisearch: `docker logs --tail 50 fortress-meilisearch-play`.

## Rules for DUM-E here
- Never open `moltbot/.env`, `ACCESS_INFO.txt`, `TOKENIZED_URL.txt`, `FINAL_STATUS.txt`, `config/`, or print the token from `moltbot.sh`, `start-moltbot.sh`, `QUICK_ACCESS.sh`. Never run `get-tokenized-url.sh`, `moltbot.sh info` or `QUICK_ACCESS.sh`.
- Never open `meilisearch-play/CREDENTIALS.md` or `.env`.
- Never read Vitalis health data or Qdrant/Onyx volumes. Paths only.
- Never start Vitalis or the RAG agent. Do not propose `service_start rag_agent` (it is broken) or `service_start vitalis` (no `.env`; insecure defaults) without first telling the owner these problems.
- `service_start moltbot` will fail until the image is rebuilt; tell the owner instead.
- DELETES operations that exist here:
  - `moltbot.sh stop` (`docker compose down`).
  - `start-moltbot.sh` overwrites `config/config.json` and `config/gateway.token`.
  - Clearing Moltbot sessions (`config/agents/main/sessions/*.jsonl`, `sessions.json`) as a documented fix.
  - Meilisearch index/document delete via its API.
  - Removing the orphaned `rag-agent_*` or `onyx-rag-agent_*` volumes (`docker volume rm`) would destroy old Notion data; owner only.

## Open questions
- Is there a Mesh VPN (e.g. Tailscale) Serve rule still pointing 443 at Moltbot's 18789? [U] Owner runs `mesh-vpn serve status`.
- Does the owner want Vitalis deployed? If so, which LLM (`OLLAMA_URL` model, or the brain on :8081)? [U]
- Can the Vitalis worker reach Ollama from an internal-only network? [U] Test after deploy.
- Keep or drop the old `rag-agent_*` and `onyx-rag-agent_*` volumes? [U] Owner decides.
- Why did Meilisearch not restart on 2026-10-29? [U] Owner checks Docker logs.
- Is `FINAL_STATUS.txt` token-free? [U] Owner checks.
