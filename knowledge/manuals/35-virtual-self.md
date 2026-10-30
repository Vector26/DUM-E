---
title: Virtual Self memory service
scope: The Virtual Self stack in ~/homelab/virtual-self-memory (api, worker, postgres, searxng, knowledge gateway, archive profile, scripts, vself aliases) and the architecture of VIRTUAL_SELF_ARCHITECTURE_PLAN.md
last_verified: 2026-10-29
sources: virtual-self-memory/README.md, virtual-self-memory/compose.yaml, virtual-self-memory/Dockerfile, virtual-self-memory/.env.example, virtual-self-memory/scripts/*.sh, virtual-self-memory/docs/WEB_EGRESS.md, docs/WEB_GATEWAY.md, docs/ARCHIVE_AGENT_OWNERSHIP.md, ~/.bashrc:463-479, control/services.yaml, control/lib/actions.sh, VIRTUAL_SELF_ARCHITECTURE_PLAN.md (architecture sections only), incidents.log, docker ps/inspect/logs, ss, curl /health
---

# Virtual Self memory service

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Virtual Self is a local "memory + personality" service for a virtual copy of the owner. [V] (src: virtual-self-memory/README.md:1-3)
It reads the owner's life notes (read-only), stores evidence and memories in Postgres with pgvector, and gives agents a "context bundle" before they answer. [V] (src: README.md:65-74; VIRTUAL_SELF_ARCHITECTURE_PLAN.md:8-27)
It also has a chat CLI, an optional web search path (SearXNG + a hardened gateway), and an optional "archive" pipeline for Google Takeout data. [V] (src: compose.yaml:91-260)
All its content is the owner's personal data. **It is PRIVATE.** DUM-E may name paths, never read them.
It is running now: `virtual_self_api`, `virtual_self_worker`, `virtual_self_postgres`, `virtual_self_searxng`, `virtual_self_knowledge_gateway`. [V] (cmd: docker ps)

### Architecture plan (summary, no personal content)
Source: `~/homelab/VIRTUAL_SELF_ARCHITECTURE_PLAN.md` (status "Proposed", dated 2026-09-29). [V] (src: VIRTUAL_SELF_ARCHITECTURE_PLAN.md:1-6)
- Goal: an agent-independent personality and autobiographical memory service. Out of scope: chat UI, voice UI, public actions, fine-tuning. [V] (src: :4-6)
- Interfaces: a REST/OpenAPI API, a thin MCP server, optional adapters, a versioned "context compiler", and CRUD for memories. [V] (src: :17-23)
- Rule: user-owned evidence is the source of truth. Embeddings, facts, graph edges and prompt bundles are rebuildable. [V] (src: :25-26)
- Flow: sources → ingestion worker → evidence store → extraction/policy → memory store, full-text + vector index, temporal relations, personality proposals → owner approval → context bundle → REST/MCP → agents. [V] (src: :160-190)
- Parts: API service, MCP adapter, ingestion worker, memory worker, PostgreSQL with pgvector and full-text (no separate graph DB), model provider adapter, admin CLI. [V] (src: :192-239)
- Data model areas: identity/auth, evidence, memories with versions, temporal relations, personality, operations (sessions, audit, deletion jobs, suppressions, jobs/outbox, resource leases). [V] (src: :241-651)
- GPU rule: the worker must not start its own GPU runtime. One host broker should own GPU inference, with a shared lock that other Homelab GPU launchers also honour. [V] (src: :635-651)
- Privacy: bind to loopback/private network; scoped bearer tokens per agent; store token hashes; sensitivity levels; encryption; remote LLMs off for high-sensitivity data unless approved. [V] (src: :906-966,1116-1123)
- Forgetting: "forget", "correct" and "hard delete" are separate. Hard delete removes evidence, versions, embeddings, derived summaries, cached bundles and queued jobs, and leaves a content-free tombstone. [V] (src: :967-1020)
- No fine-tuning at first. [V] (src: :1125-1133)
- Deployment plan: api, worker, postgres, optional migrate; CPU-only; suggested limits Postgres 2–4 GiB, API 0.5–1 GiB, worker 1–2 GiB. [V] (src: :1135-1172)
- The plan marked `rag-agent` as dead/broken (no source, compose builds a missing Dockerfile). [V] (src: :91-100)

## How the owner refers to it
- "Virtual Self", "vself", "virtual-self", "VSM". Service ids `virtual_self` and `virtual_self_archive`. [V] (src: control/services.yaml:182-200)
- Aliases in `~/.bashrc` lines 467–479 [V] (src: ~/.bashrc:467-479):
  - `vself` — `cd ~/homelab/virtual-self-memory`.
  - `vself-up` — `docker compose up -d postgres api worker`.
  - `vself-down` — `docker compose down`.
  - `vself-logs` — `docker compose logs -f api worker`.
  - `vself-chat` — `scripts/fortress-cli.sh start`.
  - `vself-talk` — `docker exec -it virtual_self_api virtual-self start`.
  - `vself-bake` — `scripts/fortress-cli.sh bake`.
  - `vself-status` — `scripts/fortress-cli.sh status`.
  - `vself-archive-sync`, `vself-archive-run`, `vself-archive-status` — `scripts/fortress-cli.sh archive sync|run|status`.
  - `virtual-self` — `scripts/fortress-cli.sh` with any arguments.
- The comment at `~/.bashrc:465` says "API :8090 localhost only". In practice :8090 is not published at all (see Known problems). [V]

## Components
Compose project `virtual-self`, file `~/homelab/virtual-self-memory/compose.yaml`. All app containers share image `virtual-self-memory:latest`, built from the local `Dockerfile` (Python 3.12, runs as user `vsm`, includes `rclone`). [V] (src: compose.yaml:3-7, Dockerfile:1-23)

Always-on services (no profile):
- `virtual_self_postgres` — image `pgvector/pgvector:pg16`. Healthcheck `pg_isready`. Memory 2 GB. Restart `unless-stopped`. Declares host port `127.0.0.1:54329→5432`. Status: running, healthy. [V] (src: compose.yaml:50-70; cmd: docker inspect --format State/Health)
- `virtual_self_api` — command `virtual-self serve`. Listens on 8090 inside the container. Declares `127.0.0.1:8090:8090`. Memory 512 MB. Restart `unless-stopped`. No healthcheck. Running. [V] (src: compose.yaml:72-82; cmd: docker ps)
- `virtual_self_worker` — command `virtual-self worker` (job runner, chat memory extraction). Memory 512 MB. Restart `unless-stopped`. Running. [V] (src: compose.yaml:84-89)
- Common hardening for app containers: read-only root FS, `no-new-privileges`, `/tmp` tmpfs, `/corpus` mounted read-only, archive data read-only, `.state/` writable. [V] (src: compose.yaml:24-47)

Profile `web` (running now):
- `virtual_self_searxng` — image `searxng/searxng:latest`. Host port **127.0.0.1:8098**→8080. Network `virtual_self_web_egress` only (has internet). Memory 512 MB. Restart `unless-stopped`. [V] (src: compose.yaml:201-223; cmd: docker ps)
- `virtual_self_knowledge_gateway` — image `ghcr.io/littleoffice/mcp-searxng-relay` pinned by sha256. Host port **127.0.0.1:8099**→8080. On both `virtual_self_internal` and `virtual_self_web_egress`. Needs `WEB_GATEWAY_MCP_TOKEN`. Caps: no images, no Office docs, PDF and body ≤ 2 MiB, ≤ 20,000 extracted chars. Healthy. [V] (src: compose.yaml:168-199; docs/WEB_GATEWAY.md:1-22; cmd: curl -s 127.0.0.1:8099/health → {"status":"ok","searxng":"reachable"})

Profile `cli`:
- `virtual_self_chat` — interactive chat (`virtual-self start`). Started by `fortress-cli.sh start` only if the api container is not running. Not running. [V] (src: compose.yaml:91-98, scripts/fortress-cli.sh:42-49)

Profile `bake`:
- `virtual_self_bake` — full corpus build (`virtual-self bake`). One-shot. [V] (src: compose.yaml:100-105)

Profile `tools`:
- `virtual_self_migrate` — DB migrations (`virtual-self migrate`). One-shot. [V] (src: compose.yaml:107-111)

Profile `archive` (none exist now) [V] (cmd: docker inspect → "no such object"):
- `virtual_self_archive_sync` — `virtual-self archive sync-loop` (rclone pull of Takeout zips). Writes to the archive data root. Mounts rclone config read-only. Memory 256 MB. [V] (src: compose.yaml:113-138)
- `virtual_self_archive_worker` — `virtual-self worker` with `VSM_ARCHIVE_LLM_ENABLED=true`. Memory 1 GB. [V] (src: compose.yaml:140-166)
- `virtual_self_archive_flow_loop` — runs `scripts/archive-flow-watchdog.sh` in a loop. Restart `unless-stopped`. Bind-mounts host file `/tmp/archive-flow.log`. [V] (src: compose.yaml:225-260)

Networks:
- `virtual_self_internal` — `internal: true`, subnet 172.28.0.0/16, gateway **172.28.0.1** (host bridge `br-ab1f19c69ed0`). No internet. [V] (src: compose.yaml:262-269; cmd: ip -4 addr)
- `virtual_self_web_egress` — normal bridge with internet, for SearXNG and the gateway only. [V] (src: compose.yaml:270-271; docs/WEB_EGRESS.md)

Volume: `virtual_self_pgdata` (the database). [V] (src: compose.yaml:273-275)

Homelab Control registration [V] (src: control/services.yaml:182-200):
- `virtual_self`: compose dir `virtual-self-memory`, detect container `virtual_self_api`, `gpu: false`, `default: false`, `depends_on: [ai_llama]`.
- `virtual_self_archive`: same compose dir, detect container `virtual_self_archive_sync`, `default: false`, `depends_on: [virtual_self, ai_llama]`.

## Files and data
- `~/homelab/virtual-self-memory/.env` — **SECRET**. Never open. Variable names (from `.env.example`): `VSM_DATABASE_URL`, `VSM_FIELD_ENCRYPTION_KEY`, `VSM_BOOTSTRAP_TOKEN`, `VSM_API_HOST`, `VSM_API_PORT`, `VSM_LOG_LEVEL`, `VSM_METRICS_ENABLED`, `VSM_WORKER_ENABLED`, `VSM_WORKER_POLL_SECONDS`, `VSM_MY_LIFE_ROOT`, `VSM_OLLAMA_URL`, `VSM_EMBED_MODEL`, `VSM_EMBED_DIMS`, `VSM_LLM_BACKEND`, `VSM_OPENAI_BASE_URL`, `VSM_OPENAI_MODEL`, `VSM_CHAT_MODEL`, `VSM_CHAT_TIMEOUT_SECONDS`, `VSM_REQUIRE_AGENT_ENRICHMENT`, `VSM_ENRICH_ON_IMPORT`, `VSM_ENRICH_THAW_COLD_MODEL`, `VSM_CHAT_MEMORY_*`, `VSM_NOTIFY_*`, `VSM_ENRICH_NOTIFY_MILESTONES`, `SEARXNG_SECRET_KEY`, `SEARXNG_PORT`, `WEB_GATEWAY_MCP_TOKEN`, `WEB_GATEWAY_PORT`, `VSM_ARCHIVE_*`. [V] (src: .env.example)
- `.env.example` — safe template. Defaults: embed model `nomic-embed-text` (768 dims), chat model `qwen3.6:35b-a3b`, archive remote `vault-gdrive`, archive min free 15 GB, `VSM_ARCHIVE_DELETE_ZIP_AFTER=false`. [V] (src: .env.example:12-76)
- Corpus: the host path in `VSM_MY_LIFE_ROOT`, mounted read-only at `/corpus`. **PRIVATE.** The exact path is in `.env` and was not read. [V] (src: compose.yaml:27-30)
- Archive data root: default `~/homelab/life-archive-data` (35 GB), mounted read-only for api/worker and **read-write** for `archive-sync`. **PRIVATE.** [V] (src: compose.yaml:34-37,128-130; cmd: du -sh)
- `.state/` — writable state, logs, bake markers, eval outputs, approvals. 50 entries. **PRIVATE** (may hold memory text). Named items include `ORCHESTRATOR_PAUSED.json`, `pending_approvals.json`, `pytest.lock`, `bake.log`, `refresh.log`, `archive-flow.log`, `notify_audit.jsonl`, `web_audit.jsonl` path. [V] (cmd: ls .state)
- `.state/backups/` — DB dumps `vsm-<timestamp>.dump` + `.sha256` (8 files). **PRIVATE.** [V] (cmd: ls .state/backups)
- `/mnt/photos/vsm-backups/` — second copy of DB dumps and `vsm-config-<ts>.tgz`. That tarball **includes `.env`** (SECRET) and `.state`. [V] (src: scripts/backup-db.sh:7,19-29)
- rclone config: `~/.config/vault-backup/rclone.conf` — **SECRET** (Google Drive credentials), mounted read-only into archive containers. [V] (src: compose.yaml:131-134)
- `web/searxng/settings.yml` — SearXNG config, mounted read-only. [V] (src: compose.yaml:212-216)
- `migrations/001…014_*.sql` — schema history. [V] (cmd: ls migrations)
- `docs/` — design notes (web gateway, egress, archive ownership, persona/voice/trait docs). The persona/voice/trait docs may describe the owner: treat as PRIVATE. [V] (cmd: ls docs)
- `eval/heldout/` — held-out evaluation set. **PRIVATE** (likely personal questions). [I]
- `/tmp/archive-flow.log` — archive watchdog log. Does not exist now. [V] (cmd: ls /tmp/archive-flow.log)
- Images kept for rollback: `virtual-self-memory:pre-chat-ready`, `virtual-self-memory:pre-overnight`. [V] (cmd: docker image ls)
- `~/homelab/VIRTUAL_SELF_ARCHITECTURE_PLAN.md` — design plan (41 KB). Architecture only is summarised below. [V]

## Commands
Read-only:
- `docker ps --filter name=virtual_self` — list containers. READ.
- `curl -s http://127.0.0.1:8099/health` — knowledge gateway health. READ. [V]
- `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8098/healthz` — SearXNG (returned 200). READ. [V]
- `docker logs --tail 50 virtual_self_api` (or `_worker`, `_searxng`, `_knowledge_gateway`). READ.

Mutating (owner only, unless noted):
- `vself-up` — `docker compose up -d postgres api worker`. MUTATES. [V] (src: ~/.bashrc:468)
- `vself-down` — `docker compose down`. MUTATES (removes containers and networks; keeps the volume). [V] (src: ~/.bashrc:469)
- `vself-chat` / `virtual-self start` — opens chat via `docker exec` into the api, or starts the stack and runs the `chat` container. MUTATES (chat turns can be saved as memories). [V] (src: scripts/fortress-cli.sh:42-49; README.md:65-69)
- `vself-talk` — `docker exec -it virtual_self_api virtual-self start`. MUTATES. [V] (src: ~/.bashrc:473)
- `vself-status`, `vself-archive-status`, `virtual-self <anything>` — **not read-only.** The script first runs `docker compose up -d postgres api worker` if postgres is down, then `docker compose exec`. It may also `cp .env.example .env` if `.env` is missing. MUTATES. [V] (src: scripts/fortress-cli.sh:7-9,30-38,61-63)
- `vself-bake` — full corpus build in a one-shot container; Telegram when done. MUTATES. [V] (src: scripts/fortress-cli.sh:50-52; README.md:22)
- `vself-archive-sync` — rclone pull + ledger. MUTATES (writes to the archive data root). [V] (src: README.md:90)
- `vself-archive-run` — unpack → OLAP → LLM → memories. MUTATES. [V] (src: README.md:91)
- `virtual-self archive flow` — one zip at a time. Sets `VSM_ARCHIVE_DELETE_ZIP_AFTER=true` unless overridden: **DELETES** the Takeout zip after processing. [V] (src: README.md:89,112)
- `virtual-self archive reconcile --delete` — **DELETES** ledger/archive entries (exact scope [U]). [V] (src: docs/ARCHIVE_AGENT_OWNERSHIP.md:9)
- `docker compose --profile archive up -d archive-sync archive-worker` and `… up -d archive-flow-loop` — start archive containers. MUTATES. [V] (src: README.md:95,106)
- `scripts/backfill-people-journal.sh [--no-rebuild|--full]` — rebuild image, re-enrich People and Journal, `import-my-life --apply`. MUTATES. [V] (src: README.md:28-34)
- `scripts/backup-db.sh` — `pg_dump` via `docker exec`, two copies, config tarball. MUTATES (writes; copies `.env` to the HDD). [V] (src: scripts/backup-db.sh)
- `scripts/make-chat-ready.sh` — backup, tests, rebuild, deploy, reindex. It **restarts the AI brain** with `llama-server-ctl restart` and **deletes the watchdog pause flag** `~/.local/state/fortress-vram-watchdog/ai-paused`. MUTATES + DELETES. [V] (src: scripts/make-chat-ready.sh:11,78-86)
- `scripts/overnight-run.sh` — same pipeline, then **`sudo shutdown now`** unless `OVERNIGHT_DRY_RUN=1`. Also restarts llama and deletes the pause flag. MUTATES + DELETES. [V] (src: scripts/overnight-run.sh:2-4,15-16,86-97,154-159)
- `scripts/overnight-watch.sh` — watches the run; on failure or deadline it kills the runner and runs **`sudo shutdown now`**. MUTATES. [V] (src: scripts/overnight-watch.sh:27-53)
- `scripts/make-chat-ready-watch.sh` — kills `make-chat-ready.sh` past deadline. MUTATES. [V] (src: scripts/make-chat-ready-watch.sh:29-38)
- `scripts/kill-vsm-pytest.sh` — `kill -9` on pytest processes of this repo. MUTATES. [V] (src: scripts/kill-vsm-pytest.sh)
- `scripts/archive-flow-watchdog.sh` — restarts `archive flow` when work remains. MUTATES. [V] (src: scripts/archive-flow-watchdog.sh:2,115)
- `scripts/run-bake-openrouter.sh`, `run-enrich-openrouter.sh`, `run-refresh.sh` — host-side jobs; the names say OpenRouter (a cloud LLM). Sending personal data to the cloud is possible. MUTATES. [I] (src: file names; compose.yaml:14 comment)
- `scripts/pytest-once.sh` — the only allowed way to run tests (lock `.state/pytest.lock`). MUTATES. [V] (src: docs/ARCHIVE_AGENT_OWNERSHIP.md:26)
- API writes: `POST /v1/memories` (memory CRUD, including delete), `POST /v1/context:compile`. MUTATES / DELETES. [V] (src: README.md:71-74)
- `fortress start virtual_self` / `fortress stop virtual_self` — runs `docker compose up -d` / `docker compose stop` in the folder. MUTATES. [V] (src: control/lib/actions.sh:38-49)

## Depends on
- **AI brain :8081 — required for chat and memory extraction.** Containers call `http://host.docker.internal:8081/v1`, model `your-local-model-id`. Chat memory extraction also uses :8081 (backend `openai`), so Ollama does not load a second model. [V] (src: compose.yaml:13-18)
- **Ollama :11434 — embeddings.** `VSM_OLLAMA_URL=http://host.docker.internal:11434`; embed model `nomic-embed-text`. [V] (src: compose.yaml:12; .env.example:26)
- `host.docker.internal` is pinned to **172.28.0.1**, the internal bridge gateway, because `host-gateway` (docker0) is often down. [V] (src: compose.yaml:23-25) So :8081 and :11434 must listen on 0.0.0.0 (or on 172.28.0.1). Binding them to 127.0.0.1 would break Virtual Self. [V] (src: DUM-E.md §3 F9)
- **Notifier :8001.** `VSM_NOTIFIER_URL=http://host.docker.internal:8001/notify`. Scripts also POST to `http://127.0.0.1:8001/notify`. [V] (src: compose.yaml:19; scripts/make-chat-ready.sh:28)
- **GPU:** none directly (`gpu: false`). It uses the GPU only through :8081 and Ollama. [V] (src: control/services.yaml:188)
- The architecture plan requires a host-wide GPU broker/lock before background extraction. No such broker exists today. [V] (src: VIRTUAL_SELF_ARCHITECTURE_PLAN.md:635-651) [I] (no broker found in control/)
- Internet: only SearXNG and the knowledge gateway (via `virtual_self_web_egress`). App containers have none. [V] (src: docs/WEB_EGRESS.md)
- Archive profile: rclone remote `vault-gdrive` (Google Drive), shared with vault-backup. [V] (src: .env.example:70; README.md:86)
- Disk: archive refuses to download below 15 GB free or below 2.5× the zip size. Root is ~91 % full. [V] (src: README.md:112; DUM-E.md §3 F2)

## How to check it (read-only)
- Running? DUM-E tool `services` (ids `virtual_self`, `virtual_self_archive`) and `containers` (`virtual_self_*`).
- Ports: DUM-E tool `ports` → expect 127.0.0.1:8098 and 127.0.0.1:8099. Not 8090, not 54329.
- Health: `curl -s http://127.0.0.1:8099/health` should print `{"status":"ok","searxng":"reachable"}`. DUM-E tool `health`.
- Postgres health: DUM-E tool `containers` shows `virtual_self_postgres (healthy)`.
- Brain and embeddings: DUM-E tool `ai_brain` (:8081) and `gpu` (Ollama models loaded).
- Incidents: DUM-E tool `incidents` (sources `virtual_self`, `virtual_self_archive`).
- Logs: DUM-E tool `log_tail` on `virtual_self_api`, `virtual_self_worker`.
- Disk for archive: DUM-E tool `disk_memory`.

## Known problems and fixes
- **API port 8090 is not reachable from the host.** Compose asks for `127.0.0.1:8090` and `127.0.0.1:54329`, but `docker ps` shows only `8090/tcp` and `5432/tcp`, `ss` has no 8090/54329, and `curl 127.0.0.1:8090` fails. [V] (cmd: docker ps; ss -ltnp; curl)
  Cause: the api and postgres are only on `virtual_self_internal`, which is `internal: true`. Docker does not publish ports for containers on internal-only networks. [I]
  Effect: host tools cannot call the REST API or MCP over HTTP. Chat works through `docker exec`. [I]
  Fix: owner decision (e.g. a small proxy). DUM-E has no action for this.
- **Homelab start/stop ignores compose profiles.** `fc_compose_up` runs plain `docker compose up -d`; `fc_compose_down` runs plain `docker compose stop`. [V] (src: control/lib/actions.sh:38-49)
  Effect 1: `service_start virtual_self_archive` cannot start the archive containers (profile `archive`), so its detector `virtual_self_archive_sync` never appears. [I]
  Effect 2: `service_stop virtual_self_archive` would stop the **main** Virtual Self (same compose dir). [I]
  Effect 3: SearXNG and the gateway (profile `web`) are not started by `service_start virtual_self`. [I] Who started them now is unknown [U].
  Fix: owner changes `services.yaml`/`actions.sh` to pass `--profile`. DUM-E has no action for this.
- **Archive start failed once.** Incident "Failed to start Virtual Self Archive", exit 1, 2026-10-11 15:14. [V] (src: incidents.log:3022) Cause [U]. Check with the owner; possibly the missing `/tmp/archive-flow.log` bind source (it does not exist now) [I] (src: compose.yaml:252-254; README.md:105).
- **Scripts can restart the AI brain and clear the watchdog pause.** `make-chat-ready.sh` and `overnight-run.sh` call `llama-server-ctl restart` and `rm -f …/ai-paused`. This bypasses the GPU guard and the VRAM watchdog. [V] (src: scripts/make-chat-ready.sh:78-86; scripts/overnight-run.sh:86-97; DUM-E.md §3 F7)
- **Two scripts shut the machine down.** `overnight-run.sh` and `overnight-watch.sh` end with `sudo shutdown now` unless `OVERNIGHT_DRY_RUN=1`. [V] (src: scripts/overnight-run.sh:154-159; scripts/overnight-watch.sh:27-32) The last fleet-wide SIGTERM was 2026-10-19 18:55 UTC (worker, plane, meilisearch logs) [V]; whether that was an overnight run is [U].
- **Backups copy the secret `.env` to the HDD.** `backup-db.sh` tars `.env` into `/mnt/photos/vsm-backups/vsm-config-*.tgz`. [V] (src: scripts/backup-db.sh:27-29)
- **Compose has a plain DB password.** `VSM_DATABASE_URL` and `POSTGRES_PASSWORD` are written in `compose.yaml`. Postgres is internal-only, so risk is low. [V] (src: compose.yaml:10,55-57) Do not copy the value.
- **Worker DB errors at shutdown.** The worker logged "failed to resolve host 'postgres'" and "connection refused" on 2026-10-19 18:55 while the stack stopped. It started cleanly on 2026-10-29. Harmless. [V] (cmd: docker logs --tail 50 -t virtual_self_worker)
- **SearXNG warnings.** "The limiter requires Valkey", "X-Forwarded-For nor X-Real-IP header is set", some engines fail to load (`torch`, `ahmia`). Search still works (health 200). [V] (cmd: docker logs --tail 50 virtual_self_searxng)
- **Not in the boot profile but still runs.** `virtual_self` is `default: false` and not in `default.json`, yet it runs after boot because of `restart: unless-stopped`. [V] (src: control/services.yaml:189; DUM-E.md §3 F5)
- **Possible cloud use of personal data.** `.env` "may hold OpenRouter settings for host-side bakes". [V] (src: compose.yaml:14) Whether it does is [U] (`.env` is not read).

## Logs
- `docker logs --tail 50 virtual_self_api` — JSON lines, e.g. `vsm_started`, uvicorn on 0.0.0.0:8090. [V]
- `docker logs --tail 50 virtual_self_worker` — `worker_started`, job errors, DB connection errors. [V]
- `docker logs --tail 50 virtual_self_searxng` — engine and limiter errors. [V]
- `docker logs --tail 50 virtual_self_knowledge_gateway` — JSON, `fetch failed` lines. [V]
- `~/homelab/virtual-self-memory/.state/*.log` — bake, refresh, archive, pytest logs. **PRIVATE** content possible; DUM-E may report names and sizes only.
- `/tmp/archive-flow.log` — archive watchdog (when used). [V] (src: README.md:98)
- `~/.local/state/homelab/incidents.log` — sources `virtual_self`, `virtual_self_archive`. [V]

## Rules for DUM-E here
- Never read the corpus, `life-archive-data`, `.state/`, `eval/heldout/`, backups, persona/voice/trait docs, or database rows. Paths only.
- Never open `.env` or `rclone.conf`.
- Never run any `vself*` alias or `virtual-self` command, even "status". They can start containers and use `docker exec`.
- Never run `make-chat-ready.sh`, `overnight-run.sh` or `overnight-watch.sh`. They restart the AI brain, clear the watchdog flag, and can shut the host down.
- Use only `service_start virtual_self` / `service_stop virtual_self` after approval. Never use `service_stop virtual_self_archive` (it stops the main stack too). [I]
- DELETES operations that exist here:
  - `vself-down` (`docker compose down`) removes containers and networks.
  - `virtual-self archive flow` deletes Takeout zips after processing (`VSM_ARCHIVE_DELETE_ZIP_AFTER=true` in flow mode).
  - `virtual-self archive reconcile --delete`.
  - Memory delete through the API (`/v1/memories`), and the plan's "hard delete" of evidence.
  - `make-chat-ready.sh` / `overnight-run.sh`: `rm -f` of the watchdog pause flag and `rm -f .state/bake.pid`; `overnight-run.sh` also `rm -rf` of its own lock/done markers.
  - `fortress-cli.sh` runs `cp -n .env.example .env` when `.env` is missing. `-n` means it never overwrites an existing `.env`. This creates a file but deletes nothing.
  - Rolling back re-tags images (`docker tag … :latest`), replacing the current image tag.

## Open questions
- Is the corpus path in `.env` still valid? [U] Owner checks `.env` (DUM-E must not).
- Who started the `web` profile containers, and is that intended? [U] Ask the owner.
- Why did "Failed to start Virtual Self Archive" happen on 2026-10-11? [U] Owner reruns with output, or checks `.state/archive-*.log`.
- Does `.env` enable OpenRouter (cloud) for bakes? [U] Owner checks.
- Is the 8090 API meant to be reachable from the host? [U] Owner decides.
- Does the internal network let containers reach 172.28.0.1:8081 and :11434? It works today (api started, no LLM errors in the last 50 lines) [I], but a chat call was not tested [U].
