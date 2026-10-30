---
title: n8n, Dexter and research orchestration
scope: n8n workflow engine (~/homelab/n8n) with its Postgres and ChromaDB, the NFA research pipeline (~/homelab/core-orchestration, alias nfa), the Dexter financial research agent (~/homelab/dexter), and the Detective / hierarchical-agent lab (~/homelab/hierarchial-agent)
last_verified: 2026-10-29
sources: n8n/docker-compose.yml, n8n/Dockerfile, n8n/n8n_scheduler.sh, ~/.bashrc:164-170, control/services.yaml:16-23, core-orchestration/READ THIS FIRST!!!.md, core-orchestration/fortress_cli.cjs, core-orchestration/config/fortress_queue.json, library/03-core-orchestration/docs/FORTRESS_CLI.md, dexter/README.md (library/05-dexter/project-README.md), dexter/Dockerfile.worker, dexter/overnight_research.sh, dexter/src/n8n_worker.ts, dexter/env.example, hierarchial-agent/bin/*.sh, hierarchial-agent/detective/*.py, hierarchial-agent/eval/detective-hld.md, incidents.log, docker ps/inspect/logs, curl health
---

# n8n, Dexter and research orchestration

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
### n8n
n8n is the workflow automation engine of the homelab. It runs scheduled and triggered jobs. [V] (src: control/services.yaml:16-23) It runs now with its Postgres and a ChromaDB vector store. [V] (cmd: docker ps)
Active workflows at the last start: "Research News Digest", "Homelab Report Resume", "Homelab Error Notifier". [V] (cmd: docker logs --tail 50 n8n_server)
### Core orchestration (NFA)
`core-orchestration` holds the "Homelab research pipeline": n8n workflow templates, shell and Node scripts, and run data. A Gemini "manager" plans research, Ollama/Dexter "workers" gather evidence, a Gemini "reviewer" checks it, and the pipeline builds a PDF report and notifies the owner. [V] (src: core-orchestration/READ THIS FIRST!!!.md:7-45) The owner manages its queue with `nfa`. [V] (src: library/03-core-orchestration/docs/FORTRESS_CLI.md:1-5)
### Dexter
Dexter is an open-source autonomous financial research agent (TypeScript, Bun), customised here. It is used as a headless "worker" by n8n and by the Detective. [V] (src: dexter/README.md:1-5, dexter/src/n8n_worker.ts:1-12)
### Hierarchical agent / The Detective
`hierarchial-agent` (spelled this way on disk) is a lab for local-worker + cloud-supervisor agents. Its main product is "The Detective": a private research persona that reads the personal-feed intake and investigates politics in GPU-opportunistic waves. [V] (src: hierarchial-agent/context.md:1; eval/detective-hld.md:1-10) It is **not scheduled now** (no crontab entries). [V] (cmd: crontab -l | grep -c detective → 0)

## How the owner refers to it
- "n8n", "Workflows (n8n)", "workflows". Service id `n8n`. [V] (src: control/services.yaml:16-18)
- `n8n-on` → `~/homelab/n8n/n8n_scheduler.sh start`. `n8n-off` → `… stop`. [V] (src: ~/.bashrc:168-169)
- `nfa` → `node ~/homelab/core-orchestration/fortress_cli.cjs` ("NFA queue CLI (finance analyst workflows)"). [V] (src: ~/.bashrc:170)
- "Fortress" in the pipeline docs means this research pipeline, not the whole server. The CLI is called `nfa` to avoid the clash. [V] (src: FORTRESS_CLI.md:3-4)
- "Dexter", "Detective", "sleuth" (code name), "the-detective" (cron block name). [V] (src: eval/detective-hld.md:3-4; bin/install_cron.sh:15)

## Components
### n8n
- Compose project `n8n`, file `~/homelab/n8n/docker-compose.yml`. [V] (src: n8n/docker-compose.yml:1)
- `n8n_server` — image `homelab/n8n:with-libsecret` (built from `n8nio/n8n:latest` + libsecret for the Gemini CLI). Version 2.8.3. Port **0.0.0.0:5678**. Restart `unless-stopped`. No healthcheck. [V] (src: n8n/docker-compose.yml:4-14, n8n/Dockerfile; cmd: docker logs, docker ps)
  - Allows Code nodes to use Node built-ins `fs` and `path`. [V] (src: n8n/docker-compose.yml:30)
  - Webhook base `http://${SUBDOMAIN}.${DOMAIN_NAME}:5678/` (logs show `http://n8n.internal.local:5678`). [V] (src: n8n/docker-compose.yml:33; cmd: docker logs)
  - `host.docker.internal` → host-gateway. [V] (src: n8n/docker-compose.yml:34-35)
  - Mounts: `n8n/n8n_data`→`/home/node/.n8n`; `n8n/n8n_files`→`/files`; `core-orchestration`→`/orchestration` (read-write); host Node `~/.nvm/versions/node/v20.20.0`→`/host-node` (read-only); **`~/.gemini`→`/home/node/.gemini` (read-write)**; `dexter`→`/dexter` (read-write). [V] (src: n8n/docker-compose.yml:36-42)
  - Networks: default + `fortress-network`. [V] (src: n8n/docker-compose.yml:43-45)
- `n8n_postgres` — image `postgres:15-alpine`. Data bind `n8n/postgres_data`. No host port. Restart `unless-stopped`. [V] (src: n8n/docker-compose.yml:47-56)
- `fortress_chromadb` — image `chromadb/chroma:0.6.3`. Port **127.0.0.1:8100**→8000. No auth (`CHROMA_SERVER_AUTHN_PROVIDER: ""`), telemetry off. Memory 512 MB. Data bind `n8n/chromadb_data` (root-owned). Restart `unless-stopped`. [V] (src: n8n/docker-compose.yml:58-75)
- Homelab Control: id `n8n`, detect container `n8n_server`, `gpu: false`, `default: true`. It is in the boot profile. [V] (src: control/services.yaml:16-23; DUM-E.md §3 F5)
### Core orchestration
- No container of its own. Its files are mounted into n8n at `/orchestration`. [V] (src: n8n/docker-compose.yml:39)
- Main workflow template: `fortress_base_workflow_with_manual.import.json`. Others: `fortress_report_resume.import.json`, `fortress_error_notify_workflow.import.json`, `fortress_dev_workflow.import.json`. [V] (cmd: ls core-orchestration; READ THIS FIRST!!!.md:33-45)
- Shell steps (run by n8n Execute Command): `gemini_manager.sh`, `gemini_checkpoint.sh`, `gemini_review_verdict.sh`, `build_report_package.sh`, `notify_ceo.sh`, `notify_fortress_alert.sh`, `run_dexter_worker.sh`, `hive_init.sh`, `hive_tail.sh`, `hive_rm.sh`. [V] (cmd: ls; READ THIS FIRST!!!.md:37-45)
- Queue CLI: `fortress_cli.cjs` (`nfa`). Config: `config/fortress_queue.json` (queue + schedule; now 1 item, cron `0 23 * * *`, enabled), `config/fortress_runtime.json`, `config/fortress_run_prompts.json`. [V] (src: FORTRESS_CLI.md:47-51; cmd: python3 read of queue JSON → schedule and length only)
- `scripts/model_manager.sh` is **deprecated** and exits 1. [V] (src: core-orchestration/scripts/model_manager.sh:1-10)
### Dexter
- Code in `~/homelab/dexter` (package `dexter-ts` 2026.3.5, Bun, LangChain, Playwright). [V] (src: dexter/package.json)
- `src/n8n_worker.ts` — headless worker for n8n. All LLM calls go to local Ollama. Fallback model `ollama:qwen2.5:14b-instruct`. Writes JSON to `core-orchestration/raw_data/runs/<run_id>/worker_outputs/`. [V] (src: dexter/src/n8n_worker.ts:1-28)
- `Dockerfile.worker` — "Detective worker": hardened container, no GPU, read-only root, no caps, entrypoint `bun run src/n8n_worker.ts`. Image name expected by the Detective: `detective-worker:latest`. [V] (src: dexter/Dockerfile.worker; hierarchial-agent/bin/dexter_worker.sh:37)
- `overnight_research.sh "<query>"` — runs Dexter, then a Gemini CLI critique, writes `dexter/reports/<ts>_research_report.md`. [V] (src: dexter/overnight_research.sh)
- WhatsApp gateway support exists in package scripts (`gateway`, `gateway:login`, Baileys). Not set up as a service. [V] (src: dexter/package.json scripts) [U] whether ever used.
### Hierarchical agent / Detective
- Python package `hierarchial-agent/detective/` (`sleuth.py`, `loop.py`, `gpu_gate.py`, `llm_lease.py`, `run_lock.py`, `local_llm.py`, `or_llm.py`, `kg.py`, `db.py`, …) with its own `.venv`. [V] (cmd: ls detective)
- `bin/install_cron.sh` — would install 3 cron lines: 07:30 `sleuth run --auto`, 22:30 `sleuth nightly`, every 15 min `sleuth resume`. **Not installed now.** [V] (src: bin/install_cron.sh:15-19; cmd: crontab -l)
- `bin/dexter_worker.sh` — runs one Dexter task in a throwaway hardened `docker run --rm` (`detective-worker:latest`, 10 GB RAM, 4 CPUs). [V] (src: bin/dexter_worker.sh)
- `bakeoff/` — harness benchmarks (electrictown, bernstein, pi), OpenRouter client with a "SpendGuard". `lab-sandbox/` — a tiny calculator repo for agent tests. `eval/` — design and plan docs. `docs/` — static HTML docs (`docs/build.py`). [V] (cmd: ls; src: lab-sandbox/README.md:1-3)
- `runs/` — run outputs and `cron.log` (last written 2026-09-02). [V] (cmd: ls -la runs/cron.log)

## Files and data
- `n8n/.env` — **SECRET**. Never open. Holds `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `N8N_PUBLIC_API_DISABLED`, `GENERIC_TIMEZONE`, `TZ`, `SUBDOMAIN`, `DOMAIN_NAME` (names from compose), and `N8N_API_KEY` (per the nfa doc). [V] (src: n8n/docker-compose.yml:15-33; FORTRESS_CLI.md:31)
- `n8n/.env.bak` — **SECRET** (old copy). [V] (cmd: ls -la n8n)
- `n8n/n8n_data/config` — **SECRET** (n8n encryption key file, mode 600). `n8n/n8n_data/ssh/` — **SECRET**. [V] (cmd: ls -la n8n_data)
- `n8n/n8n_data/n8nEventLog*.log` — event logs; `n8nEventLog-1.log` and `-3.log` are ~11 MB each. `crash.journal` (0 bytes). `binaryData/`. [V] (cmd: ls -la n8n_data)
- `n8n/postgres_data/` — n8n database files (owned by uid 70, not readable by `(owner)`). Holds workflows and credentials (encrypted). **SECRET.** [V] (cmd: ls -la n8n)
- `n8n/chromadb_data/` — ChromaDB data (root-owned). Content [U].
- `n8n/n8n_files/research-digest/` — files for the "Research News Digest" workflow (`run_digest.sh`, `pipeline_lib.mjs`, `pi`, `pi-runtime`, `latest.json`, `latest.txt`). Last output 2026-10-06 08:01. [V] (cmd: ls -la)
- `n8n/docker-compose.yml.bak2` — older compose copy. [V]
- `n8n/docker-compose.yml` is **world-writable** (`-rw-rw-rw-`). [V] (cmd: ls -la n8n)
- `~/.gemini/` — Gemini CLI login (**SECRET**), mounted read-write into n8n. [V] (src: n8n/docker-compose.yml:41)
- `core-orchestration/.env.orchestration.example` — template; names include `GEMINI_*`, `OLLAMA_BASE_URL`, `OLLAMA_RESEARCH_MODEL`. [V] (cmd: grep names)
- `core-orchestration/raw_data/` — run state: `reports/`, `runs/`, `run_hive/`, `agent_logs/`, `reviewer_*`, `review_state_*` JSON, PDFs. 2.2 MB. **World-writable** directory. [V] (cmd: ls -la; du -sh)
- `core-orchestration/logs/` — `workflow_observable_*.log`, `workflow_run_*.out` (March 2026). [V]
- `core-orchestration/execution_*.json`, `wf_*.json` — saved n8n executions / workflow dumps (March 2026). [V]
- Docs: `~/homelab/library/03-core-orchestration/docs/` (FORTRESS_CLI, ORCHESTRATION_GUIDE, N8N_PIPELINE_ARCHITECTURE, FORTRESS_RESUME_AND_QUEUE, LOKI traces, …) and `steps/step1–5.md`. `core-orchestration/docs` and `step*.md` are symlinks to these. [V] (cmd: ls -la)
- `dexter/.env` — **SECRET**. Names (from `env.example`): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`, `MOONSHOT_API_KEY`, `DEEPSEEK_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_TIMEOUT_MS`, `PLANNER_MODEL`, `VALIDATOR_MODEL`, `ACTION_MODEL`, `ANSWER_MODEL`, `FINANCIAL_DATASETS_API_KEY`, `INDIANAPI_*`, `ANGELONE_*` (broker login incl. PIN/TOTP), `TOFLER_*`, `EXASEARCH_API_KEY`, `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_*`. [V] (src: dexter/env.example)
- `dexter/.env.research.example` — template. [V]
- `dexter/.dexter/scratchpad/` — agent scratch files; **world-writable**. [V] (cmd: ls -la)
- `dexter/combined.log` (205 KB), `dexter/error.log` — Dexter logs. [V]
- Dexter docs: `~/homelab/library/05-dexter/` (`project-README.md`, `repository-root/SOUL.md`, `AGENTS.md`, `docs/INDIAN_APIS.md`). `dexter/README.md`, `SOUL.md`, `AGENTS.md`, `docs` are symlinks there. `SOUL.docker.md` is a dereferenced copy for the image. [V] (cmd: ls -la dexter)
- `hierarchial-agent/.env` — **SECRET** (holds an OpenRouter key, read by `or_llm.py`). [V] (src: detective/or_llm.py:30-33)
- The Detective reads the database DSN `FF_PG_DSN` from **`~/homelab/personal-feed/.env`** (SECRET) unless `JD_PG_DSN` is set. [V] (src: detective/db.py:3,15-25) The HLD says its data lives "in the shared n8n Postgres". [V] (src: eval/detective-hld.md:5) Which database the DSN points to is [U].
- `hierarchial-agent/runs/` (3 MB), `.venv` (385 MB), `vendor` (260 MB). [V] (cmd: du -sh)

## Commands
### Read-only
- `curl -s http://127.0.0.1:5678/healthz` → `{"status":"ok"}`. READ. [V]
- `curl -s http://127.0.0.1:8100/api/v2/heartbeat` → nanosecond heartbeat. READ. [V]
- `docker logs --tail 50 n8n_server` (or `n8n_postgres`, `fortress_chromadb`). READ.
- `nfa status`, `nfa list` — print the queue and budget. READ. [V] (src: FORTRESS_CLI.md:37-45) (DUM-E still must not run `nfa`; see Rules.)
### Mutating
- `n8n-on` (`n8n_scheduler.sh start`) — first runs `docker compose stop` in `$ONYX_COMPOSE_DIR` (default `~/onyx-rag-agent`, which does not exist), then `docker compose up -d` for n8n if nothing is running. MUTATES. [V] (src: n8n/n8n_scheduler.sh:6-21; cmd: ls ~/onyx-rag-agent → missing)
- `n8n-off` (`n8n_scheduler.sh stop`) — `docker compose stop` for n8n, then tries to start Onyx; on Onyx failure it runs `docker compose down` there. MUTATES. [V] (src: n8n/n8n_scheduler.sh:22-32)
- `fortress start n8n` / `fortress stop n8n` — `docker compose up -d` / `stop` in `n8n/`. MUTATES. [V] (src: control/lib/actions.sh:38-49)
- `docker compose build n8n && docker compose up -d n8n` — rebuild the n8n image. MUTATES. [V] (src: n8n/Dockerfile:3)
- `nfa add|remove <n>|schedule|budget` — edit the queue and runtime files. MUTATES. [V] (src: fortress_cli.cjs:628-641)
- `nfa apply` — writes `fortress_run_prompts.json` and `fortress_runtime.json`, patches the workflow cron, and **pushes the full workflow to the live n8n** using `N8N_API_KEY` read from `n8n/.env`. MUTATES. [V] (src: FORTRESS_CLI.md:24-31; fortress_cli.cjs:231-256)
- `nfa clear-hashes` — clears `last_successful_hash` and `last_applied_hash`, so the scheduled gate runs again. MUTATES. [V] (src: fortress_cli.cjs:216-228)
- `push_fortress_workflow_to_n8n.sh`, `push_fortress_error_notifier_to_n8n.sh`, `scripts/update_n8n_workflow.sh` — HTTP `PUT` of workflows into n8n (127.0.0.1:5678 or 100.x.x.x:5678). MUTATES. [V] (src: push_fortress_workflow_to_n8n.sh:2,12,91; scripts/update_n8n_workflow.sh:19,68)
- `notify_ceo.sh`, `notify_fortress_alert.sh` — send messages and files to the notifier at `host.docker.internal:8001`. MUTATES (phone alert). [V] (src: notify_ceo.sh:2,15; notify_fortress_alert.sh:2,25)
- `fortress_queue_advance.cjs` — removes the queue head after a successful notify. MUTATES (DELETES a queue item). [V] (src: FORTRESS_CLI.md "Queue completion behavior")
- `prune_fortress_raw_data.cjs` — keeps only the newest N runs (default 2); **DELETES** old `reports/<id>`, `runs/<id>`, `run_hive/<id>.jsonl`, `agent_logs/<id>`, old Dexter outputs and stale payloads. [V] (src: prune_fortress_raw_data.cjs:2-8)
- `hive_rm.sh <run_id>` — **DELETES** `run_hive/<run_id>.jsonl` and `.digest.md`. [V] (src: hive_rm.sh:16)
- `dexter/overnight_research.sh "<query>"` — runs Dexter + Gemini (cloud). MUTATES (writes reports; calls paid/cloud APIs). [V]
- `bun run src/n8n_worker.ts --topic …` / `run_dexter_worker.sh` — one research worker run. MUTATES. [V]
- `hierarchial-agent/bin/install_cron.sh` — **edits the user crontab** (removes any old "the-detective" block and adds a new one). MUTATES. [V] (src: bin/install_cron.sh:7,21)
- `hierarchial-agent/bin/dexter_worker.sh "<task>"` — `docker run --rm` worker. MUTATES. [V]
- `.venv/bin/python -m detective.sleuth run|nightly|resume` — Detective runs; write to its database and feed. MUTATES. [V] (src: bin/install_cron.sh:16-18)
- `.venv/bin/python docs/build.py` — regenerates the static docs. MUTATES. [V] (src: docs/README.md)

## Depends on
- **n8n itself:** no GPU, no AI brain directly. [V] (src: control/services.yaml:22)
- **"Research News Digest" workflow uses the AI brain :8081** through `pi` with provider `llama-hauhaucs`. [V] (src: n8n/n8n_files/research-digest/pipeline_lib.mjs:107,151)
- **Research pipeline workers use Ollama :11434** at `http://host.docker.internal:11434`. [V] (src: run_dexter_worker.sh:12; detect_ollama_worker_models.sh:6) The pipeline expects "one Ollama model preloaded". [V] (src: scripts/model_manager.sh:3-9)
- **Dexter fallback model `qwen2.5:14b-instruct` is not installed** in Ollama (installed: `qwen2.5:7b`, `qwen3.6:35b-a3b`, `nomic-embed-text`). [V] (src: dexter/src/n8n_worker.ts:27; cmd: ollama list) Whether `.env` overrides it is [U].
- **Cloud:** the manager, checkpoint and reviewer use the Gemini CLI (Google). Dexter can use OpenAI, Anthropic, Exa, Tavily, Financial Datasets, etc. [V] (src: READ THIS FIRST!!!.md:11-13; dexter/env.example)
- **Notifier :8001** for reports and alerts. [V] (src: notify_ceo.sh:15)
- **Loki/Grafana** for pipeline traces (docs `FORTRESS_LOKI_TRACES.md`, scripts `fortress_loki_state_traces.sh`). [V] (cmd: ls)
- **The Detective:** AI brain :8081 first, then Ollama :11434 (`qwen3.6:27b`, which is **not installed** — it is in cold storage). [V] (src: detective/local_llm.py:3,13-14; DUM-E.md §5.2) OpenRouter (cloud) as another path. [V] (src: detective/or_llm.py) Worker containers point to `host.docker.internal:8081` with model `your-local-model-id`. [V] (src: bin/dexter_worker.sh:26-30) It has a GPU gate that defers when another process holds VRAM. [V] (src: detective/gpu_gate.py:1-8)
- Docker network `fortress-network` (external). [V] (src: n8n/docker-compose.yml:77-80)

## How to check it (read-only)
- n8n up? DUM-E tool `services` (id `n8n`), `containers` (`n8n_server`, `n8n_postgres`, `fortress_chromadb`), `health`. Owner: `curl -s http://127.0.0.1:5678/healthz`.
- Ports: DUM-E tool `ports` → 0.0.0.0:5678 and 127.0.0.1:8100.
- ChromaDB: `curl -s http://127.0.0.1:8100/api/v2/heartbeat`.
- Workflows active: DUM-E tool `log_tail` on `n8n_server` (look for "Currently active workflows").
- Queue state: read `core-orchestration/config/fortress_queue.json` with the `manual`/file tools (it holds research goals; summarise, do not quote).
- Ollama models: DUM-E tool `gpu` / `ai_brain`.
- Incidents: DUM-E tool `incidents` (source `n8n`).
- Detective schedule: DUM-E tool `schedules` (expect no "the-detective" block).

## Known problems and fixes
- **n8n "not running" alerts (402).** "Workflows (n8n): not running (default service)" from 2026-10-11 16:01 to 2026-10-20 00:05. [V] (src: incidents.log, aggregated) n8n has been running since the 2026-10-29 boot. [V] (cmd: docker inspect --format State n8n_server) Cause of the gap [U]; it overlaps the period when the host or cron was off (DUM-E.md §3 F6). If it happens again, DUM-E can propose `service_start n8n`.
- **`n8n-on` / `n8n-off` touch a missing Onyx stack.** `ONYX_COMPOSE_DIR` defaults to `~/onyx-rag-agent`, which is gone, so those steps are skipped. Old Onyx Docker volumes (`onyx-rag-agent_*`) still exist. [V] (src: n8n_scheduler.sh:6; cmd: docker volume ls) Fix (owner): remove the Onyx lines from the script; decide on the old volumes.
- **The alias comment says "scheduled cron may also start it".** No cron line starts n8n today. [V] (src: ~/.bashrc:168; cmd: crontab -l)
- **Gemini credentials are writable from n8n.** `~/.gemini` is mounted read-write, and Code nodes may use `fs`. A bad workflow could read or change those credentials. [V] (src: n8n/docker-compose.yml:30,41)
- **n8n port 5678 is open on all interfaces**, with the firewall off. [V] (cmd: ss -ltnp; DUM-E.md §3 F9)
- **World-writable files.** `n8n/docker-compose.yml` (rw-rw-rw-), `core-orchestration/raw_data/` and `dexter/.dexter/scratchpad/` (drwxrwxrwx). Any local user could change the compose file that runs as Docker. [V] (cmd: ls -la)
- **n8n telemetry tries to phone home.** Logs show `[Rudder] error: Response error code: EAI_AGAIN` (DNS failure for the telemetry endpoint). [V] (cmd: docker logs n8n_server) Fix (owner): set `N8N_DIAGNOSTICS_ENABLED=false` in `n8n/.env` and recreate.
- **n8n Python task runner missing.** "Failed to start Python task runner in internal mode because Python 3 is missing". Python Code nodes will not work. [V] (cmd: docker logs)
- **Storage path deprecation.** n8n warns that `binaryData` becomes `storage` in v3. [V] (cmd: docker logs)
- **Research digest output is stale.** `latest.txt`/`latest.json` last written 2026-10-06. [V] (cmd: ls -la n8n_files/research-digest) Possible cause: AI brain paused or down at run time [I] (DUM-E.md §3 F1). Check with `log_tail n8n_server` and the n8n execution list.
- **Execute Command drops item JSON.** Data before an Execute Command node can vanish; the pipeline saves `review_state_*.json` to recover. Do not add Execute Command steps without persisting state. [V] (src: READ THIS FIRST!!!.md:49-62)
- **Dexter worker fallback model not installed** (see Depends on). [V]
- **Dexter search fails without DNS** (`getaddrinfo EAI_AGAIN lite.duckduckgo.com`), last seen 2026-03-23. [V] (src: dexter/error.log tail)
- **Detective worker image missing.** `bin/dexter_worker.sh` needs `detective-worker:latest`; no such image exists. Every worker call would fail. [V] (cmd: docker image ls) Fix (owner): `docker build -f dexter/Dockerfile.worker -t detective-worker:latest dexter` (not run; MUTATES).
- **Detective last cron run failed on OpenRouter rate limits** ("OpenRouter HTTP 429"). [V] (src: hierarchial-agent/runs/cron.log tail, 2026-09-02)
- **Detective Ollama fallback model `qwen3.6:27b` is in cold storage.** [V] (src: detective/local_llm.py:14; DUM-E.md §5.2)
- **Unregistered container.** `fortress_chromadb` is not in `services.yaml`; it belongs to the n8n compose. [V] (src: DUM-E.md §3 F11)

## Logs
- `docker logs --tail 50 n8n_server` — start-up, active workflows, telemetry errors, license renewals.
- `~/homelab/n8n/n8n_data/n8nEventLog*.log` — n8n event log (large; ~11 MB files).
- `~/homelab/core-orchestration/logs/` — older pipeline run logs.
- `~/homelab/core-orchestration/raw_data/agent_logs/`, `status_snapshots/`, `watch_logs/` — per-run traces.
- Loki: pipeline traces (see `library/03-core-orchestration/docs/FORTRESS_LOKI_TRACES.md`).
- `~/homelab/dexter/combined.log`, `error.log` — Dexter JSON logs.
- `~/homelab/hierarchial-agent/runs/cron.log` — Detective scheduled runs (last 2026-09-02).
- `~/.local/state/homelab/incidents.log` — source `n8n`.

## Rules for DUM-E here
- Never open `n8n/.env`, `.env.bak`, `n8n_data/config`, `n8n_data/ssh`, `~/.gemini`, `dexter/.env`, `hierarchial-agent/.env`, `personal-feed/.env`.
- Never run `nfa`, not even `nfa status`. With no argument it opens an interactive menu, and `nfa apply` reads `n8n/.env` and pushes to live n8n. Read the config JSON files instead.
- Never run `n8n-on`, `n8n-off`, `n8n_scheduler.sh`, the push/update scripts, Dexter, or `sleuth`.
- Never run `install_cron.sh`. It rewrites the crontab.
- Use only `service_start n8n` / `service_stop n8n` after approval.
- Do not quote research goals from `fortress_queue.json`; summarise counts and schedule only.
- DELETES operations that exist here:
  - `prune_fortress_raw_data.cjs` (old runs, reports, logs, payloads).
  - `hive_rm.sh` (run hive files).
  - `fortress_queue_advance.cjs` and `nfa remove <n>` (queue items).
  - `nfa clear-hashes` (clears stored hashes).
  - `n8n_scheduler.sh stop` can run `docker compose down` on the Onyx stack (if it ever exists again).
  - `install_cron.sh` deletes the old "the-detective" crontab block before re-adding it.
  - `dexter/overnight_research.sh` deletes its temp critique file (harmless).
  - n8n workflows themselves may delete data; their content was not reviewed [U].

## Open questions
- Which n8n workflows run on a schedule, and when? [U] Owner checks the n8n UI (Workflows → Active).
- Is the NFA base workflow (`m6gBf69MuOgPnyQ7`, cron `0 23 * * *`) active? The start-up log lists only 3 active workflows, not this one. [I] Owner checks in n8n.
- Does `n8n/.env` set `N8N_DIAGNOSTICS_ENABLED`? [U] Owner checks.
- Which Postgres does the Detective use (`FF_PG_DSN`)? [U] Owner checks `personal-feed/.env`.
- What is in `fortress_chromadb`, and who uses it? [U] Owner lists collections (`GET /api/v2/...collections`).
- Is the Detective retired or paused? [U] Ask the owner.
