---
title: Productivity apps (LifePath, Plane, AFFiNE, Anytype)
scope: LifePath (~/homelab/LifePath), Plane project boards (~/homelab/plane + orchestration/stacks/plane), AFFiNE notes (~/homelab/affine), Anytype sync and Notion export hub (~/homelab/anytype)
last_verified: 2026-10-29
sources: LifePath/docker-compose.yml, LifePath/DOCKER.md, LifePath/.env.example, library/02-lifepath/*, ~/.bashrc:171-188, plane/docker-compose.yml, orchestration/stacks/plane/docker-compose.yml, plane/scripts/*, plane/setup.sh, library/11-plane/*, homelab/docker-compose.yml, affine/docker-compose.yml, affine/.env.example, affine/systemd/*, affine/scripts/notion_data_import/cli.py+pipeline.py, library/09-affine/scripts-README.md, anytype/docker-compose.yml, anytype/README.md, anytype/scripts/*, control/services.yaml, incidents.log, docker ps/inspect/logs/image inspect, curl
---

# Productivity apps (LifePath, Plane, AFFiNE, Anytype)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
### LifePath
LifePath is the owner's gamified productivity / life planner app ("LifePath City"): a Spring Boot API, a Vite web front end, and Android/iOS specs. [V] (src: ~/.bashrc:179; library/02-lifepath/docs/LIFEPATH_POC_PRIORITIES.md:1-15; LifePath/backend/pom.xml present) It is **not running**, and no LifePath containers exist. Its database volume remains. [V] (cmd: docker ps -a --filter name=lifepath; docker volume ls)
### Plane
Plane is a self-hosted project management board (Plane.so v1.2.2). It is used as the ticket system for LifePath and for AI agents. [V] (src: plane/docker-compose.yml:66; library/11-plane/SETUP_TICKETING.md:1) It runs now (12 containers). `plane-space-1` shows **unhealthy**, but this is a false alarm (see Known problems). [V] (cmd: docker ps)
### AFFiNE
AFFiNE is a self-hosted notes and knowledge base. Notion data was migrated into it with custom scripts. [V] (src: control/services.yaml:70-77; library/09-affine/scripts-README.md:1) It runs now on port 3010. [V] (cmd: docker ps; curl → 200)
### Anytype
The `anytype` folder has two parts: an optional self-hosted Anytype sync server, and a "Notion export hub" that exports all Notion data to cleaned JSON. [V] (src: anytype/README.md:1-5) The sync server is **stopped** since 2026-07-21. [V] (cmd: docker inspect --format State anytype_sync_bundle)

## How the owner refers to it
### LifePath
- "LifePath", "Life planner app". Service id `lifepath`. [V] (src: control/services.yaml:146-153)
- Aliases [V] (src: ~/.bashrc:182-188): `lifepath` (cd), `lifepath-up` (`docker compose up -d`), `lifepath-down` (`docker compose down`), `lifepath-logs` (`docker compose logs -f`), `lifepath-rebuild` (`down` + `build --no-cache` + `up -d`), `lifepath-be` (`mvn spring-boot:run`, dev API on :39081), `lifepath-fe` (`npm run dev`, dev web on :39173).
### Plane
- "Plane", "Plane projects", "Project management boards". Service id `plane`. [V] (src: control/services.yaml:61-68)
- Board for LifePath: workspace `life-path` on `http://localhost:8082`. [V] (src: library/02-lifepath/docs/LIFEPATH_POC_PRIORITIES.md:3)
- No `.bashrc` aliases. [V] (cmd: grep -i plane ~/.bashrc)
### AFFiNE
- "AFFiNE", "Affine notes", "Notes and knowledge base". Service id `affine`. [V] (src: control/services.yaml:70-77)
- Aliases `affine-on` / `affine-off` (see Known problems: they are broken). [V] (src: ~/.bashrc:175-176)
### Anytype
- "Anytype sync", "Self-hosted Anytype sync server", "Notion export hub". Service id `anytype`. [V] (src: control/services.yaml:79-86; anytype/README.md:1)

## Components
### LifePath
- Compose project `lifepath`, file `~/homelab/LifePath/docker-compose.yml`. [V]
- `backend` — built from `LifePath/backend` (Spring Boot, profile `postgres`). Port **0.0.0.0:39081**. Healthcheck `wget http://localhost:39081/api/v1/actuator/health`. [V] (src: LifePath/docker-compose.yml:4-26)
- `web` — built from `LifePath/web`. Port **0.0.0.0:39173**. Healthcheck `wget http://localhost:39173`. The image copies `public/lifepath.apk`. [V] (src: LifePath/docker-compose.yml:28-41; DOCKER.md:39-41)
- `postgres` — `postgres:16-alpine`, volume `lifepath_pgdata` (exists as `lifepath_lifepath_pgdata`, created 2026-02-28). No host port. [V] (src: LifePath/docker-compose.yml:43-60; cmd: docker volume inspect --format)
- No restart policy is set in compose (default `no`). [V] (src: LifePath/docker-compose.yml)
- Homelab Control: detect port 39081, `gpu: false`, `default: false`. [V] (src: control/services.yaml:146-153)
### Plane
- Compose project `plane`. Homelab uses `~/homelab/orchestration/stacks/plane/docker-compose.yml`, which only `include`s `~/homelab/plane/docker-compose.yml`. [V] (src: stacks/plane/docker-compose.yml:9-12)
- Images `artifacts.plane.so/makeplane/plane-*:v1.2.2` (APP_RELEASE default). [V] (src: plane/docker-compose.yml:66-221)
- Containers (all restart `always`, created 2026-02-27) [V] (cmd: docker ps; docker inspect --format RestartPolicy):
  - `plane-proxy-1` — Caddy proxy. Host ports **0.0.0.0:8082→80** and **0.0.0.0:8443→443** (from `LISTEN_HTTP_PORT`/`LISTEN_HTTPS_PORT` in env files). HTTP only (no TLS). [V] (cmd: docker ps; docker logs plane-proxy-1)
  - `plane-web-1` (healthy), `plane-admin-1` (healthy), `plane-space-1` (**unhealthy**), `plane-live-1`, `plane-api-1`, `plane-worker-1`, `plane-beat-worker-1`. [V]
  - `plane-plane-db-1` — `postgres:15.7-alpine`, `max_connections=1000`, volume `plane_pgdata`. [V] (src: plane/docker-compose.yml:174-184)
  - `plane-plane-redis-1` — `valkey/valkey:7.2.11-alpine`, volume `plane_redisdata`. [V]
  - `plane-plane-mq-1` — `rabbitmq:3.13.6-management-alpine`, volume `plane_rabbitmq_data`. [V]
  - `plane-plane-minio-1` — `minio/minio:latest`, file uploads in volume `plane_uploads`. [V]
- Defined but **never created**: `plane-postgres-exporter` (:9187) and `plane-redis-exporter` (:9121). The `migrator` container is also absent (one-shot). [V] (cmd: docker ps -a --filter label=com.docker.compose.project=plane)
- Other volumes: `plane_logs_api`, `plane_logs_worker`, `plane_logs_beat-worker`, `plane_logs_migrator`, `plane_proxy_config`, `plane_proxy_data`. [V] (cmd: docker volume ls)
- Homelab Control: detect container `plane-proxy-1`, `gpu: false`, `default: true`. In the boot profile. [V] (src: control/services.yaml:61-68; DUM-E.md §3 F5)
- **Duplicate Plane set (compose project `fortress`)**: `fortress-api-1`, `fortress-worker-1`, `fortress-beat-worker-1`, `fortress-plane-db-1`, `fortress-plane-mq-1`, `fortress-plane-redis-1`. Created 2026-02-27 12:18 UTC (4 minutes before the real set) from `~/homelab/docker-compose.yml` with working dir `~/homelab`. Restart `always`. Own volumes (`fortress_pgdata`, `fortress_rabbitmq_data`, `fortress_logs_*`). No web or proxy, so nothing uses them. [V] (cmd: docker inspect --format Labels/Mounts/RestartPolicy; docker volume inspect --format)
### AFFiNE
- Compose project `affine`, file `~/homelab/affine/docker-compose.yml`. [V]
- `affine_server` — `ghcr.io/toeverything/affine:${AFFINE_REVISION:-stable}`. Port **0.0.0.0:3010**. Indexer off. Restart `unless-stopped`. No healthcheck. Running; HTTP 200. [V] (src: affine/docker-compose.yml:4-31; cmd: curl)
- `affine_migration_job` — one-shot predeploy (`self-host-predeploy.js`). Exited 0. [V] (src: affine/docker-compose.yml:33-55; cmd: docker ps -a)
- `affine_redis` — `redis:7`, healthy. [V]
- `affine_postgres` — `pgvector/pgvector:pg16`, data in `${DB_DATA_LOCATION}` (`affine/postgres_data`), healthy, **`POSTGRES_HOST_AUTH_METHOD: trust`**. [V] (src: affine/docker-compose.yml:72-93)
- All on `fortress-network`. Labels `com.fortress.service=affine`. [V]
- Homelab Control: detect container `affine_server`, `default: true`. Not in the boot profile; it starts via `unless-stopped`. [V] (src: control/services.yaml:70-77; DUM-E.md §3 F5)
- Unit files for a Notion→AFFiNE import exist in `affine/systemd/` but are **not installed**. [V] (cmd: systemctl status / systemctl --user status → "could not be found")
### Anytype
- Compose project `anytype`, file `~/homelab/anytype/docker-compose.yml`. [V]
- `anytype_sync_bundle` — `ghcr.io/grishy/any-sync-bundle:1.4.3-2026-04-21`. Ports **33010/tcp** and **33020/udp**. Data `./data`. Restart `unless-stopped`. State: exited 137 at 2026-07-21 15:47 UTC. [V] (src: anytype/docker-compose.yml; cmd: docker inspect --format State)
- Notion export scripts in `anytype/scripts/` (`export_pipeline.py`, `notion_unified_export.py`, `notion_ai_clean.py`, `enrich_export.py`, `notion_to_anytype.py`, `import_to_anytype.py`, `ollama_keep_model.sh`, `pause_resume_clean.sh`, …). They run with the AFFiNE scripts venv. [V] (cmd: ls scripts; src: anytype/README.md:9-19)
- Homelab Control: detect container `anytype_sync_bundle`, `default: true`. [V] (src: control/services.yaml:79-86)

## Files and data
### LifePath
- `LifePath/.env` — does not exist; `.env.example` has only `POSTGRES_PASSWORD`. Other settable names: `APP_FRONTEND_URL`, `GOOGLE_REDIRECT_URI`. [V] (cmd: ls -la; src: docker-compose.yml:16-17)
- `LifePath/backend/data/lifepath.mv.db`, `lifepath.trace.db` — local H2 database for dev runs. **PRIVATE** (personal tasks). [V] (cmd: ls backend/data)
- Volume `lifepath_lifepath_pgdata` — Docker DB. **PRIVATE.** [V]
- `LifePath/tools/sync-plane-epics.mjs` — syncs epics with Plane. [V] (cmd: ls tools)
- `~/homelab/plane/lifepath.env.example` — template for LifePath-Plane settings; a real `lifepath.env` would be **SECRET**. [V]
- Docs: `~/homelab/library/02-lifepath/` (`DOCKER.md`, `web-README.md`, `docs/` specs). `LifePath/DOCKER.md` and `LifePath/docs` are symlinks. [V]
- `Gamified Productivity App Impact Analysis.pdf` — research PDF. [V]
### Plane
- `plane/.env`, `plane/plane.env`, `plane/variables.env` — **SECRET**. Never open. [V] (DUM-E.md §3 F4)
- `plane/docker-compose.yml` contains **hard-coded fallback secrets** for `SECRET_KEY` and `LIVE_SERVER_SECRET_KEY`, and default DB/MQ/MinIO passwords. Treat the file as **SECRET-bearing**; never quote those lines. [V] (src: plane/docker-compose.yml:7,19,24,43,49,57-62)
- `plane/scripts/create_lifepath_project.sh`, `add-unlock-metadata.mjs`, `delete_all_work_items.sh` — API scripts; need `PLANE_API_KEY` (**SECRET**). [V]
- `plane/setup.sh` — the upstream Plane installer/manager (install, start, stop, restart, upgrade, logs, backup). [V] (src: plane/setup.sh functions)
- Docs: `~/homelab/library/11-plane/` (`SETUP_TICKETING.md`, `LIFEPATH_AGENT_GUIDE.md`, `agent_lifepath_ticket_rules.md`); symlinked from `plane/`. [V]
- Volumes `plane_*` — boards, tickets, uploads. **PRIVATE.** [V]
### AFFiNE
- `affine/.env` — **SECRET** (`AFFINE_REVISION`, `PORT`, `DB_DATA_LOCATION`, `UPLOAD_LOCATION`, `CONFIG_LOCATION`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`). [V] (src: .env.example names)
- `affine/config/private.key` — **SECRET**. `affine/config/config.json`. [V]
- `affine/scripts/.env` — **SECRET** (Notion API key; also used by Anytype scripts). [V] (src: anytype/README.md:33-35; DUM-E.md §3 F4)
- `affine/storage/` (root-owned uploads) — **PRIVATE**. `affine/postgres_data/` — **PRIVATE**. [V]
- `affine/notion_export/` and `affine/ae8b39b1-…_ExportBlock-….zip` (80 MB) — Notion export. **PRIVATE.** [V] (DUM-E.md §9.3)
- `affine/backups/pre_import_*` — pre-import backups (2026-09-29). **PRIVATE.** [V]
- `affine/scripts/` — Notion→AFFiNE migration tools (`notion_data_import/` package, validators, logs). Docs: `~/homelab/library/09-affine/scripts-README.md`. [V]
- `affine/systemd/notion-affine-import.service` (`python -m notion_data_import.cli run --skip-reset`), `notion-affine-import-watchdog.service` + `.timer` (every 5 min). Not installed. [V]
### Anytype
- `anytype/.env` — **SECRET** (`ANYTYPE_BUNDLE_TAG`, `ANYTYPE_PORT_TCP`, `ANYTYPE_PORT_UDP`, `ANYTYPE_DATA_DIR`, `ANY_SYNC_BUNDLE_INIT_EXTERNAL_ADDRS` per compose). [V]
- `anytype/data/bundle-config.yml`, `data/client-config.yml` — sync node config, likely holding node keys. Treat as **SECRET**. [I]
- `anytype/data/mongo/`, `data/redis/`, `data/storage/` — sync server data. **PRIVATE.** [V] (cmd: ls data)
- `anytype/data/notion_raw.json`, `notion_enriched.json`, `notion_clean.json`, `notion_canonical.json`, `ai_complaints.json`, `clean_report.json`, `import_readiness*.{md,json}`, `sample_matrix.json` — full Notion export. **PRIVATE.** [V]
- Docs: `anytype/README.md`, `SCHEMA.md`, `IMPORT_MAC.md`, `VERIFICATION.md`; library shelf `~/homelab/library/13-anytype/README.md`. [V]

## Commands
### LifePath
- `lifepath-up` / `fortress start lifepath` — `docker compose up -d` (builds images if needed). MUTATES. [V]
- `lifepath-down` — `docker compose down`. MUTATES (removes containers; keeps the volume). [V]
- `lifepath-rebuild` — `down`, `build --no-cache`, `up -d`. MUTATES. [V]
- `lifepath-be`, `lifepath-fe` — dev servers on 39081/39173 (stop them before Docker). MUTATES. [V] (src: DOCKER.md:7-8)
- `lifepath-logs` — follow logs. READ. [V]
### Plane
- `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8082/` — UI reachable (200). READ. [V]
- `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8082/spaces/` — Space app (200). READ. [V]
- `curl -s http://127.0.0.1:8082/api/instances/` — API answers (200). READ. [V]
- `fortress start plane` / `fortress stop plane` — `docker compose up -d` / `stop` in `orchestration/stacks/plane`. MUTATES. [V]
- `plane/setup.sh` — interactive manager: start, stop, restart, upgrade (pulls new images), view logs, backup. MUTATES; its backup/upgrade code runs `rm -rf` on backup and temp folders (DELETES). [V] (src: plane/setup.sh:195,337-475,544-576)
- `plane/scripts/create_lifepath_project.sh` — creates a project and labels via API. MUTATES. [V]
- `node plane/scripts/add-unlock-metadata.mjs` — edits work item descriptions. MUTATES. [V]
- `plane/scripts/delete_all_work_items.sh` — **DELETES every work item** in the lifePath project (HTTP DELETE, 60/min). [V] (src: plane/scripts/delete_all_work_items.sh:2-3,36,44)
- `node LifePath/tools/sync-plane-epics.mjs` — syncs epics to Plane. MUTATES. [I]
### AFFiNE
- `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3010/` — UI up (200). READ. [V]
- `fortress start affine` / `fortress stop affine` — `docker compose up -d` / `stop` in `affine/`. MUTATES. [V]
- `affine-on` / `affine-off` — run in `~/homelab` (root); broken (see Known problems). [V]
- `affine/scripts/.venv/bin/python -m notion_data_import.cli run` — Notion import. **Without `--skip-reset` it resets the AFFiNE workspace first (DELETES).** Other subcommands: `preflight`, `backup`, `retry-failed`, `status`, `notify-flush`, `dedupe-sidebar` (DELETES duplicates [I]), `debug`. [V] (src: notion_data_import/cli.py:309-357; pipeline.py:220-223)
- `affine/scripts/run_migration.sh`, `VERIFY_SIDEBAR.sh`, `verify_notion_data_import.sh` — migration and checks. MUTATES / READ (not read in full) [U].
### Anytype
- `fortress start anytype` — `docker compose up -d`. MUTATES. [V]
- `python export_pipeline.py [--llm-mode none|audit] [--skip-pages]` — full Notion export (30–60 min) + optional Ollama cleaning. MUTATES (writes `data/*.json`, uses Notion API and GPU). [V] (src: anytype/README.md:9-19)
- `scripts/ollama_keep_model.sh [model]` — loads a model into Ollama with `keep_alive: -1` (pinned in VRAM forever; default `qwen3.6:35b-a3b`, 23 GB). MUTATES (GPU). [V] (src: anytype/scripts/ollama_keep_model.sh)
- `scripts/pause_resume_clean.sh` — pauses and resumes `notion_ai_clean`. MUTATES. [V]

## Depends on
### LifePath
- No GPU, no AI brain, no Ollama. [V] (src: compose; services.yaml:152)
- Google Calendar OAuth (redirect `…/api/v1/calendar/callback`). [V] (src: docker-compose.yml:17)
- Plane for tickets (dev process). [V] (src: library/11-plane/LIFEPATH_AGENT_GUIDE.md)
### Plane
- No GPU, no AI brain, no Ollama. [V] (src: services.yaml:67)
- Prometheus jobs `plane-postgres` and `plane-redis` expect the exporters. [V] (src: monitoring/prometheus/prometheus.yml:42-50)
- Network `fortress-network` (exporters). [V]
### AFFiNE
- No GPU, no AI brain. [V] (src: services.yaml:76)
- Notion API (import only). [V]
### Anytype
- Sync server: none. [V]
- Export scripts: **Ollama :11434** (GPU) for `--llm-mode audit`, Notion API, and the AFFiNE scripts venv and `.env`. [V] (src: anytype/README.md:33-46)

## How to check it (read-only)
- Running? DUM-E tool `services` (ids `lifepath`, `plane`, `affine`, `anytype`) and `containers`.
- Ports: DUM-E tool `ports` → 8082, 8443 (Plane), 3010 (AFFiNE), 39081/39173 (LifePath, absent now), 33010 (Anytype, absent now).
- Plane health: `curl` to `http://127.0.0.1:8082/` and `/spaces/` (both 200 today). Ignore the `plane-space-1` "unhealthy" flag (see below).
- Healthcheck details: `docker inspect --format '{{json .State.Health}}' plane-space-1`.
- Incidents: DUM-E tool `incidents` (sources `anytype`, `affine`).
- Logs: DUM-E tool `log_tail` on `plane-api-1`, `plane-space-1`, `affine_server`.
- Prometheus targets: DUM-E tool `health` (plane exporters show down).

## Known problems and fixes
### Plane
- **`plane-space-1` is "unhealthy" but works.** Its healthcheck (from the image, not from compose) is `curl -fsS http://127.0.0.1:3000/`. Every check fails with `/bin/sh: curl: not found` (186 failures in a row). The app itself logs `[react-router-serve] http://localhost:3000` and `http://127.0.0.1:8082/spaces/` returns 200. [V] (cmd: docker inspect --format Health plane-space-1; docker image inspect --format Healthcheck plane-space:v1.2.2; docker logs --tail 50; curl) The web and admin images use the same check and pass, so the space image lacks `curl`. [I]
  Fix: owner may override the healthcheck for `space` in `plane/docker-compose.yml` (e.g. `wget -q -O /dev/null` or `node -e` fetch) and recreate. Or ignore it. DUM-E has no action for this.
- **Duplicate "fortress" Plane containers.** Six `fortress-*` Plane containers run from a compose project named `fortress` whose file `~/homelab/docker-compose.yml` now contains only comments ("Do NOT deploy as a single stack"). They restart `always`, so they come back every boot and use RAM. [V] (cmd: docker inspect --format Labels; src: homelab/docker-compose.yml:1-28) Fix (owner): `docker stop` and `docker rm` those six containers, then decide on the `fortress_*` volumes. DUM-E has no action for this; the owner runs: `docker rm -f fortress-api-1 fortress-worker-1 fortress-beat-worker-1 fortress-plane-db-1 fortress-plane-mq-1 fortress-plane-redis-1` (DELETES containers; volumes stay).
- **Exporters never created.** `plane-postgres-exporter` and `plane-redis-exporter` were added to compose (file date 2026-03-18) after the stack was created (2026-02-27). Prometheus shows both targets down. [V] (cmd: docker ps -a; Prometheus targets API; ls -la plane) Fix (owner): `docker compose up -d` in `orchestration/stacks/plane` (or DUM-E `service_start plane` after approval, which runs the same command).
- **Netdata probes Plane's Postgres** and fails: `password authentication failed for user "netdata"`. Harmless noise. [V] (cmd: docker logs plane-plane-db-1; systemctl status netdata)
- One FK error at start-up: `update or delete on table "issues" violates foreign key constraint …` (2026-10-29 15:36). Single event. [V] (cmd: docker logs plane-plane-db-1) Cause [U].
- Worker warns "MongoDB connection parameters not configured". Optional feature; harmless. [V] (cmd: docker logs plane-worker-1)
- Ports 8082/8443 bind 0.0.0.0; firewall off. [V] (DUM-E.md §3 F9)
### AFFiNE
- **`affine-on` / `affine-off` are broken.** They run `docker compose up -d affine …` from `~/homelab`, but the root compose file has no services. [V] (src: ~/.bashrc:175-176; homelab/docker-compose.yml) Use `fortress start affine` instead.
- **Postgres trusts everyone on `fortress-network`.** `POSTGRES_HOST_AUTH_METHOD: trust` means any container on that shared network can log in without a password. [V] (src: affine/docker-compose.yml:82,92-93)
- **Old "not running" alerts.** 21 incidents on 2026-09-29 only. [V] (src: incidents.log)
- Port 3010 binds 0.0.0.0. [V] (cmd: docker ps)
### Anytype
- **Stopped since 2026-07-21** (exit 137, same minute as Jarvis). Restart policy `unless-stopped`, so it was stopped on purpose [I]. Last log lines show "check ownership error … unexpected fileproto error" and "redis: client is closed" while stopping. [V] (cmd: docker inspect; docker logs --tail 8)
- **Alert noise: 737 incidents** "Anytype sync: not running (default service)" (2026-09-29 → 2026-10-29), because it is `default: true` but not in the boot profile. [V] (src: incidents.log; DUM-E.md §3 F6) Fix (owner): start it, or set `default: false` in `services.yaml`.
- **`ollama_keep_model.sh` pins a 23 GB model in VRAM forever.** That blocks the AI brain on :8081 (16 GB GPU). [V] (src: anytype/scripts/ollama_keep_model.sh:2-13; DUM-E.md §4) If the brain will not start, DUM-E can propose `ollama_unload`.
### LifePath
- **Not running, containers removed.** Volume kept. [V]
- No restart policy: after a reboot it stays down even if it was up. [V] (src: LifePath/docker-compose.yml)
- `lifepath-down` / `lifepath-rebuild` use `docker compose down`. [V]

## Logs
- Plane: `docker logs --tail 50 plane-api-1` (gunicorn), `plane-worker-1` (celery JSON), `plane-proxy-1` (Caddy JSON), `plane-plane-db-1` (Postgres), `plane-live-1` (Redis manager). Volumes `plane_logs_*` hold app logs.
- AFFiNE: `docker logs --tail 50 affine_server`; migration logs in `affine/scripts/*.log`.
- Anytype: `docker logs --tail 50 anytype_sync_bundle`; export logs `/tmp/notion_ai_pause_resume.log`. [V] (src: pause_resume_clean.sh:4)
- LifePath: `lifepath-logs` when running.
- Homelab incidents: `~/.local/state/homelab/incidents.log` (sources `anytype`, `affine`, `plane`, `lifepath`).

## Rules for DUM-E here
- Never open `plane/.env`, `plane.env`, `variables.env`, `lifepath.env`, `affine/.env`, `affine/scripts/.env`, `affine/config/private.key`, `anytype/.env`, `anytype/data/*config.yml`. Never quote the secret fallback lines in `plane/docker-compose.yml`.
- Never read Notion exports, AFFiNE storage, Anytype data JSON, LifePath DB files or Plane volumes. Paths only.
- Never run `plane/setup.sh`, the Plane API scripts, the Notion import/export scripts, or `ollama_keep_model.sh`.
- Use only `service_start` / `service_stop` with ids `plane`, `affine`, `anytype`, `lifepath`, after approval.
- DELETES operations that exist here:
  - `plane/scripts/delete_all_work_items.sh` (all lifePath tickets).
  - `plane/setup.sh` backup/upgrade (`rm -rf` of backup and temp folders).
  - `notion_data_import.cli run` without `--skip-reset` (resets the AFFiNE workspace); `dedupe-sidebar` [I].
  - `lifepath-down`, `lifepath-rebuild` (`docker compose down`).
  - Removing the duplicate `fortress-*` containers or any `plane_*`, `fortress_*`, `lifepath_*` volume.
  - Anytype export re-runs overwrite `data/*.json`.

## Open questions
- Does the owner still use Anytype sync, or only the export hub? [U]
- Should the duplicate `fortress-*` Plane set be removed, and is `fortress_pgdata` empty? [U] Owner checks.
- Is LifePath still active? [U]
- What caused the Plane FK error at start-up? [U] Owner checks Plane beat-worker logs.
- Are the AFFiNE import systemd units meant to be installed? [U]
