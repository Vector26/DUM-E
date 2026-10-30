---
title: Portainer, orchestration stacks, and compose-project map
scope: homelab/orchestration (Portainer, Watchtower, the orchestration "fortress" CLI, stacks/, guides), the root docker-compose.yml reference file, and which compose project owns every container on the host.
last_verified: 2026-10-29
sources: homelab/orchestration/{docker-compose.yml,fortress,setup.sh,portainer/templates/templates.json,stacks/*/docker-compose.yml}, homelab/library/08-orchestration/{README.md,guides/*}, homelab/docker-compose.yml, ~/vox/voicebox/docker-compose.yml, homelab/control/{services.yaml,lib/actions.sh}, ~/.bashrc, docker compose ls -a, docker ps -a, docker inspect --format (Labels/State/RestartPolicy/Mounts/Networks), docker logs --tail, docker stats --no-stream, docker system df -v, curl, type -a fortress
---

# Portainer, orchestration stacks, and compose-project map

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Portainer is a web page for managing Docker containers and stacks. It runs from `homelab/orchestration`. [V] (src: homelab/orchestration/docker-compose.yml:1-21,44-81)
`homelab/orchestration/stacks/` holds compose files for Immich, Plane, the music service, the RAG agent, and an old copy of Cine-Immich. Homelab Control starts Immich, Plane, music and the RAG agent from there. [V] (src: homelab/control/services.yaml:52-68,164-180)
The root file `homelab/docker-compose.yml` is a reference list only. It says: do not deploy it as one stack. [V] (src: homelab/docker-compose.yml:1-6)
In practice a compose project named `fortress` was created from the root folder earlier in 2026. It still owns Grafana, cAdvisor, node-exporter and a broken second Plane backend. See the map below. [V] (cmd: docker inspect --format Labels)
Warning: the command `fortress` means two different programs. In an interactive shell it is Homelab Control. In scripts and cron it is this folder's orchestration CLI. [V] (src: ~/.bashrc:550; cmd: type -a fortress)

## How the owner refers to it
- "Portainer", "orchestration", "stacks". Homelab Control id `orchestration` (name "Portainer"). [V] (src: homelab/control/services.yaml:7-14)
- "deploy <stack>", "undeploy <stack>" — orchestration CLI words. [V] (src: homelab/orchestration/fortress:8-24)
- "Watchtower", "autoupdate". [V] (src: homelab/orchestration/docker-compose.yml:84-119)
- "the root compose", "Homelab compose index". [V] (src: homelab/vault-storage/CONTEXT.md:411; homelab/vault-backup/config/paths.tsv:14)

## Components
### Portainer (compose project `orchestration`)
- Compose file `homelab/orchestration/docker-compose.yml`, `name: orchestration`, network `fortress-network` (external). [V] (src: docker-compose.yml:21,151-154)
- Container `fortress-portainer`, image `portainer/portainer-ce:2.38.0-alpine`, restart `always`, `no-new-privileges`. Healthy. Started 2026-10-29 15:36 UTC. [V] (src: docker-compose.yml:44-49; cmd: docker inspect --format)
- Ports, all on `0.0.0.0`: [V] (src: docker-compose.yml:62-70; cmd: docker ps; ss -ltnp)
  - `9443` → HTTPS web UI (GET returns 200).
  - `9010` → container 9000, HTTP web UI (GET returns 200).
  - `8000` → container 8000, Edge agent tunnel (GET / returns 404; `/health` returns plain `OK`). This is NOT the notifier. [V] (cmd: curl)
- Mounts: `/var/run/docker.sock` (marked `:ro`, but the Docker API still gives full control), `homelab/orchestration/portainer/templates` → `/templates`, `/etc/localtime`, volume `fortress-portainer-data` → `/data` (2.1 MB). [V] (src: docker-compose.yml:50-61; cmd: docker inspect --format Mounts; docker system df -v) [I] for the socket note
- Health check: `wget --spider http://localhost:9000` every 30 s. [V] (src: docker-compose.yml:76-81)
- Templates: `PORTAINER_TEMPLATES=/templates/templates.json` with 4 app templates: RAG Agent, Music Service, Immich, Cine-Immich. [V] (src: docker-compose.yml:72-73; portainer/templates/templates.json)
- Homelab Control: `kind: compose`, `compose: homelab/orchestration`, `detect_container: fortress-portainer`, `default: true`. [V] (src: homelab/control/services.yaml:7-14)

### Watchtower
- Defined as `fortress-watchtower` (`containrrr/watchtower:1.7.1`) behind compose profile `autoupdate`. Schedule `0 0 3 * * 0` (Sundays 03:00), only containers labelled `com.centurylinklabs.watchtower.enable=true`, `WATCHTOWER_CLEANUP=true` (removes old images), Portainer excluded. [V] (src: docker-compose.yml:91-119)
- Not running. No container with that name exists. [V] (cmd: docker ps -a --filter name=watchtower)
- An nginx reverse proxy is in the file but commented out. [V] (src: docker-compose.yml:129-143)

### The orchestration CLI (`homelab/orchestration/fortress`)
- `/usr/local/bin/fortress` is a root-owned symlink to `homelab/orchestration/fortress`, made on 2026-02-07 by `setup.sh`. [V] (cmd: ls -la /usr/local/bin/fortress; src: homelab/orchestration/setup.sh:59-67)
- `.bashrc` line 550 has `alias fortress="~/homelab/control/fortress"`. Aliases work only in interactive shells. [V] (src: ~/.bashrc:550)
- So: interactive `fortress` = Homelab Control; cron, scripts, `bash -c`, and DUM-E subprocesses = this orchestration CLI. [V] (cmd: type -a fortress in a non-interactive shell → /usr/local/bin/fortress)
- The crontab calls Homelab Control by full path, so cron is not affected. [V] (cmd: crontab -l)
- Commands (any extra argument after start/stop/restart is ignored): [V] (src: homelab/orchestration/fortress:465-510)
  - `start` → creates `fortress-network` (172.20.0.0/16) if missing, then `docker compose up -d` in `orchestration/`. (fortress:78-104)
  - `stop` → `docker compose down` in `orchestration/` (removes the Portainer container). (fortress:106-114)
  - `restart` → stop, then start. (fortress:118-123)
  - `status`, `logs [service]`, `monitor` (`docker stats`), `health` (health of containers named `fortress-*`). Read-only.
  - `backup` → tars every volume labelled `com.fortress.backup=critical` plus `fortress-portainer-data` into `homelab/backups/fortress_backup_<timestamp>/` using `alpine` containers. (fortress:199-242)
  - `deploy <stack>` (`rag-agent`, `music-service`, `immich`, `cine-immich`, `plane`) → `docker compose up -d` in `stacks/<stack>`, with `--env-file` for immich, cine-immich and plane. For immich it may `mv` (or `sudo mv`) NVMe stub folders, force-recreate `immich-server`, and run `docker exec … findmnt`. (fortress:244-347)
  - `undeploy <stack>` → `docker compose down` in `stacks/<stack>`. (fortress:349-382)
  - `prune` → after a y/N prompt: `docker container prune -f`, `docker network prune -f`, `docker image prune -f`, `docker builder prune -f`. (fortress:433-462)
  - The header also lists `restore` and `update`, but they are not implemented. [V] (src: fortress:18-19,465-505)

### stacks/ (compose files used by Homelab Control and the orchestration CLI)
- `stacks/immich/docker-compose.yml` — project `immich`; `fortress-immich-server` (port 2283), `fortress-immich-ml`, `fortress-immich-redis`, `fortress-immich-postgres`. Header: "Deploy ONLY with `--env-file ~/homelab/immich/.env`". Homelab Control id `immich`. [V] (src: stacks/immich/docker-compose.yml:7-9,12-27; homelab/control/services.yaml:52-59)
- `stacks/plane/docker-compose.yml` — project `plane`; only `include: ~/homelab/plane/docker-compose.yml`. Homelab Control id `plane` (detects `plane-proxy-1`). [V] (src: stacks/plane/docker-compose.yml:9-12; homelab/control/services.yaml:61-68)
- `stacks/music-service/docker-compose.yml` — project `music-service`; `fortress-spotspot` (6544), `fortress-navidrome`. Homelab Control id `music`. Not running. [V] (src: stacks/music-service/docker-compose.yml:8-38; homelab/control/services.yaml:164-171)
- `stacks/rag-agent/docker-compose.yml` — project `rag-agent`; `rag-agent-qdrant` (6333), `rag-agent-ui` (port 8000), `rag-agent-notion-sync`. Homelab Control id `rag_agent`. Not running. [V] (src: stacks/rag-agent/docker-compose.yml:8-89; homelab/control/services.yaml:173-180)
- `stacks/cine-immich/docker-compose.yml` — project `cine_immich`, containers `fortress-cine-*`. This is an old copy. The running Cine-Immich comes from `homelab/cine-immich/docker-compose.yml` (project `cine-immich`, containers `cine_immich_*`). [V] (src: stacks/cine-immich/docker-compose.yml:10-274; homelab/control/services.yaml:43-50; cmd: docker compose ls)

### Root reference file `homelab/docker-compose.yml`
- 28 lines, comments only, no services. Modified 2026-10-15. It lists where each stack's real compose file is. [V] (src: homelab/docker-compose.yml:1-28; cmd: ls -la)
- It says: "Do NOT deploy as a single stack" and "Do not use include: or run docker compose up from here". [V] (src: homelab/docker-compose.yml:2-6)
- It is backed up by vault-backup as `fortress_root_compose`. [V] (src: homelab/vault-backup/config/paths.tsv:14)

### Compose project → container map (2026-10-29 22:4x)
From `docker compose ls -a` and each container's `com.docker.compose.project` and `…project.working_dir` labels. [V]

| Project | Compose file(s) | Containers (state) |
|---|---|---|
| `orchestration` | homelab/orchestration/docker-compose.yml | fortress-portainer (up, healthy) |
| `fortress` | homelab/docker-compose.yml (working dir ~/homelab) | 4bf74c64847c_fortress-grafana, fortress-cadvisor, fortress-node-exporter, fortress-api-1, fortress-worker-1, fortress-beat-worker-1, fortress-plane-db-1, fortress-plane-mq-1, fortress-plane-redis-1 (all up) |
| `fortress` | homelab/monitoring/docker-compose.yml (working dir homelab/monitoring) | fortress-prometheus, fortress-ups-exporter (up); fortress-cine-immich-redis-exporter (exited) |
| `monitoring` | homelab/monitoring/docker-compose.yml | fortress-loki, fortress-promtail, fortress-vault-backup-exporter (up) |
| `immich` | homelab/orchestration/stacks/immich/docker-compose.yml | fortress-immich-server, -ml, -postgres, -redis (up, healthy) |
| `plane` | homelab/orchestration/stacks/plane/docker-compose.yml | plane-admin-1, plane-api-1, plane-beat-worker-1, plane-live-1, plane-plane-db-1, plane-plane-minio-1, plane-plane-mq-1, plane-plane-redis-1, plane-proxy-1, plane-space-1 (unhealthy), plane-web-1, plane-worker-1 |
| `cine-immich` | homelab/cine-immich/docker-compose.yml | cine_immich_server, _microservices, _machine_learning, _postgres, _redis, cine_broll_worker, cine_broll_watcher, cine-immich-broll_face_worker-1 (up); cine_immich_gateway, cine_search_proxy (exited) |
| `affine` | homelab/affine/docker-compose.yml | affine_server, affine_postgres, affine_redis (up); affine_migration_job (exited) |
| `n8n` | homelab/n8n/docker-compose.yml | n8n_server, n8n_postgres, fortress_chromadb (up) |
| `notifier` | homelab/notifier/docker-compose.yml | notifier-notifier-1 (up) |
| `vault-storage` | homelab/vault-storage/docker-compose.yml | vault-minio, vault-browser (up) |
| `virtual-self` | homelab/virtual-self-memory/compose.yaml | virtual_self_api, _worker, _postgres, _searxng, _knowledge_gateway (up) |
| `voicebox` | ~/vox/voicebox/docker-compose.yml | voicebox (up, healthy) |
| `anytype` | homelab/anytype/docker-compose.yml | anytype_sync_bundle (exited 137) |
| `jarvis` | homelab/jarvis/docker-compose.yml | jarvis-gateway, jarvis-tts, jarvis-whisper (exited 137) |
| `mediastack` | ~/mediastack/docker-compose.yml | mediastack-jellyfin, -prowlarr, -qbittorrent, -radarr, -sonarr (exited 0) |
| `meilisearch-play` | homelab/meilisearch-play/docker-compose.yml | fortress-meilisearch-play (exited 143; failed at boot on port 100.x.x.x:7700) |

### Answer: who owns the second Plane set
- `fortress-api-1`, `fortress-worker-1`, `fortress-beat-worker-1`, `fortress-plane-mq-1`, `fortress-plane-db-1`, `fortress-plane-redis-1` belong to compose project `fortress`, working dir `~/homelab`, config file `~/homelab/docker-compose.yml`. [V] (cmd: docker inspect --format Labels)
- They were created on 2026-02-27 12:18 UTC (the same day `stacks/plane` was created). Restart policy `always`, so they come back on every boot. [V] (cmd: docker inspect --format Created,RestartPolicy; ls -la stacks)
- Images: `plane-backend:v1.2.2` (api, worker, beat-worker), `postgres:15.7-alpine`, `rabbitmq:3.13.6-management-alpine`, `valkey:7.2.11-alpine`. [V] (cmd: docker ps)
- Network `fortress_default` only. No published ports. Volumes `fortress_pgdata` (47.6 MB), `fortress_rabbitmq_data`, `fortress_redisdata`, `fortress_logs_api`, `fortress_logs_worker`, `fortress_logs_beat-worker`. [V] (cmd: docker inspect --format Networks,Mounts; docker system df -v)
- They do nothing useful: `fortress-api-1` and `fortress-worker-1` print "Waiting for database migrations to complete..." in a loop (there is no migrator). They use about 130 MB RAM in total and almost no CPU. [V] (cmd: docker logs --tail 15; docker stats --no-stream)
- [I] They were made when the root file still included the Plane compose (an earlier version of the root file was deployed as one stack, against its own rule). The 2026-02-21 state backup holds a 19 KB resolved config of the root folder. [V] (cmd: ls -la homelab/backups/*/compose-configs) [I] for the history

### Answer: who owns `voicebox`
- Compose project `voicebox`, file `~/vox/voicebox/docker-compose.yml`. `/home/fortress` is a folder owned by `(owner)`, outside `~/homelab`. [V] (cmd: docker compose ls; ls -la /home)
- Image built locally (`voicebox-voicebox`), restart `unless-stopped`, healthy, port `127.0.0.1:17600` → 17493, CPU limit 4, memory limit 8 GB. [V] (src: ~/vox/voicebox/docker-compose.yml:5-41; cmd: docker ps; docker inspect --format)
- Volumes `voicebox_voicebox-data` (1.6 MB), `voicebox_huggingface-cache` (6.5 GB), bind `~/vox/voicebox/output`. Env names `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN` (SECRET values). [V] (cmd: docker inspect --format Mounts; docker system df -v; src: docker-compose.yml:16-32)
- Not registered in `services.yaml`. [V] (src: homelab/control/services.yaml)

## Files and data
- `~/homelab/orchestration/docker-compose.yml` — Portainer + Watchtower (profile) + commented nginx. [V]
- `~/homelab/orchestration/fortress` — orchestration CLI (17.9 KB). [V]
- `~/homelab/orchestration/setup.sh` — one-time setup (see Commands). [V]
- `~/homelab/orchestration/portainer/templates/templates.json` — app templates. [V]
- `~/homelab/orchestration/stacks/{immich,plane,music-service,rag-agent,cine-immich}/docker-compose.yml`. [V]
- Symlinks in `orchestration/`: `README.md`, `QUICK_REFERENCE.md`, `SETUP_COMPLETE.md`, `USAGE_GUIDE.md` → `homelab/library/08-orchestration/…`. [V] (cmd: ls -la)
- Guides: `homelab/library/08-orchestration/README.md` (8 lines), `guides/QUICK_REFERENCE.md` (284), `guides/SETUP_COMPLETE.md` (334), `guides/USAGE_GUIDE.md` (802). [V] (cmd: wc -l)
- Portainer data: Docker volume `fortress-portainer-data` (labels `com.fortress.backup=true`). It holds Portainer's database (admin account). Treat as SECRET. [V] (src: docker-compose.yml:159-166) [I] for content
- Secret files used by stacks, named only: `homelab/immich/.env`, `homelab/cine-immich/.env`, `homelab/plane/.env`, `homelab/plane/plane.env`, `homelab/plane/variables.env`, `homelab/rag-agent/.env` — all SECRET. [V] (src: homelab/orchestration/fortress:264-281; DUM-E.md F4)
- `~/homelab/docker-compose.yml` — reference only. [V]
- `~/homelab/backups/` — target of `fortress backup` (no `fortress_backup_*` folders exist now). See manual 23. [V] (cmd: ls homelab/backups)

## Commands
Always call Homelab Control as `~/homelab/control/fortress`, never as bare `fortress`.

READ:
- `docker compose ls -a` — all projects and their compose files. [V]
- `docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'` — all containers. [V]
- `docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "com.docker.compose.project.working_dir"}}' <container>` — owner project of a container. [V]
- `curl -s -o /dev/null -w '%{http_code}' http://localhost:9010/` — Portainer UI up (200). [V]
- `curl -s localhost:8000/health` — Portainer edge port (`OK`). [V]
- `type -a fortress` — which `fortress` a shell will run. [V]
- Orchestration CLI read-only commands: `~/homelab/orchestration/fortress status|health|logs|monitor`. [V] (src: fortress:126-197,385-431)

MUTATES (owner only unless noted):
- `~/homelab/control/fortress start orchestration` → `docker compose up -d` in `orchestration/`. DUM-E action `service_start orchestration`. MUTATES. [V] (src: homelab/control/lib/actions.sh:38-45)
- `~/homelab/control/fortress stop orchestration` → `docker compose stop`. Excluded for DUM-E. MUTATES (not deletion). [V] (src: homelab/control/lib/actions.sh:47-50; DUM-E.md 15.2)
- `~/homelab/control/fortress start immich|plane|music|rag_agent` → `docker compose up -d` in the matching `stacks/` folder, without `--env-file`. DUM-E action `service_start <id>`. MUTATES. [V] (src: homelab/control/lib/actions.sh:38-45,77-80)
- `homelab/orchestration/fortress start` → may create `fortress-network`, then starts Portainer. MUTATES. [V]
- `homelab/orchestration/fortress deploy <stack>` → `docker compose up -d` (and for immich: `mv`/`sudo mv` of stub folders, `--force-recreate`, `docker exec`). MUTATES. [V]
- `homelab/orchestration/fortress backup` → writes tarballs into `homelab/backups/`. MUTATES. [V]
- `cd homelab/orchestration && docker compose --profile autoupdate up -d` → starts Watchtower, which later replaces labelled containers and deletes old images. MUTATES + DELETES. [V] (src: docker-compose.yml:99-119; library/08-orchestration/guides/USAGE_GUIDE.md:596-600)
- `homelab/orchestration/setup.sh` → `sudo ln -sf` for `/usr/local/bin/fortress`, creates `homelab/backups`, creates `fortress-network`. MUTATES. [V] (src: setup.sh:59-84)
- Anything done in the Portainer web UI (start, stop, redeploy, delete stacks, volumes, images). MUTATES or DELETES. [I]

DELETES (owner only):
- `homelab/orchestration/fortress stop` and `restart` → `docker compose down` removes the Portainer container. Note: in a non-interactive shell, plain `fortress stop <anything>` runs this. DELETES (container; volume kept). [V] (src: fortress:106-123,474-479)
- `homelab/orchestration/fortress undeploy <stack>` → `docker compose down` for that stack. DELETES (containers). [V] (src: fortress:349-382)
- `homelab/orchestration/fortress prune` → removes ALL stopped containers (today: jarvis-*, mediastack-*, anytype_sync_bundle, affine_migration_job, cine_immich_gateway, cine_search_proxy, fortress-meilisearch-play, fortress-cine-immich-redis-exporter), unused networks, dangling images, build cache. DELETES. [V] (src: fortress:433-462; cmd: docker ps -a)
- `docker compose -p fortress down` → would remove Grafana, cAdvisor, node-exporter, Prometheus, UPS exporter AND the orphan Plane set. DELETES. [I]
- Removing the orphan Plane set (`docker rm` of the six containers, `docker volume rm fortress_pgdata …`). DELETES. Owner decision. [I]
- `docker volume rm fortress-portainer-data` → Portainer settings and accounts lost. DELETES. [I]
- `docker compose down` / `docker rm` / `docker volume rm` of any stack. DELETES. [I]

## Depends on
- Docker daemon and the Docker socket. [V]
- External network `fortress-network` (created by `setup.sh` or `fortress start`, subnet 172.20.0.0/16). Many stacks need it: orchestration, monitoring, vault-storage, immich, others. [V] (src: setup.sh:74-84; docker-compose.yml files)
- `.env` files under each project folder for `deploy` (immich, cine-immich, plane, rag-agent). [V] (src: fortress:263-281)
- Not the GPU, not the AI brain, not the notifier (none referenced). [V]

## How to check it (read-only)
- DUM-E tool `containers` → `docker ps -a` with project labels; use it to answer "which project owns X".
- DUM-E tool `services` → Homelab Control ids `orchestration`, `immich`, `plane`, `music`, `rag_agent`.
- DUM-E tool `ports` → 8000, 9010, 9443 (Portainer); remember 8000 is not the notifier.
- DUM-E tool `graph` → container ↔ project ↔ compose-file edges, if the graph has them.
- Owner, read-only: `docker compose ls -a`; the `docker inspect --format` label command above; `curl -s -o /dev/null -w '%{http_code}' http://localhost:9010/`.

## Known problems and fixes
1. Two programs named `fortress`.
   - Evidence: `/usr/local/bin/fortress` → orchestration CLI; interactive alias → Homelab Control. [V] (cmd: ls -la /usr/local/bin/fortress; type -a fortress; src: ~/.bashrc:550)
   - Risk: a script or agent that runs `fortress stop immich` gets the orchestration `stop`, which ignores "immich" and runs `docker compose down` on Portainer. `fortress health` in a script runs a different health check. [V] (src: homelab/orchestration/fortress:106-114,465-505)
   - Fix: DUM-E always uses full paths. The owner may remove or rename the symlink (`sudo rm /usr/local/bin/fortress`, DELETES). DUM-E has no action for this.
2. The root reference file was deployed as a stack anyway.
   - Evidence: project `fortress` with working dir `~/homelab` owns 9 running containers. [V] (cmd: docker inspect --format Labels; docker compose ls)
   - Effect: the root file now has no services, so `docker compose` from the root folder cannot manage them; Grafana, cAdvisor and node-exporter are outside the `monitoring` project (manual 25). [I]
   - Fix: owner moves them into the right projects. DUM-E has no action for this.
3. A dead second Plane backend runs on every boot.
   - Evidence: see "who owns the second Plane set". [V]
   - Fix: owner removes the six containers and, if not needed, their volumes (DELETES). DUM-E has no action for this; the owner runs: `docker stop fortress-api-1 fortress-worker-1 fortress-beat-worker-1 fortress-plane-mq-1 fortress-plane-db-1 fortress-plane-redis-1`, then decides on `docker rm` and `docker volume rm`.
4. Homelab Control starts `stacks/immich` without `--env-file`.
   - Evidence: `fc_compose_up` runs plain `docker compose up -d`; the stack header says to deploy only with `--env-file ~/homelab/immich/.env`; `stacks/immich/` has no `.env` of its own. [V] (src: homelab/control/lib/actions.sh:44; stacks/immich/docker-compose.yml:7-9; cmd: ls -la stacks/immich)
   - Risk: variables like `UPLOAD_LOCATION` and `ORIGINALS_LOCATION` become empty, and compose may recreate `fortress-immich-server` with wrong mounts. It does nothing while the containers already match. [I]
   - Fix: owner uses `homelab/orchestration/fortress deploy immich` for Immich, or adds `--env-file` support to Homelab Control.
5. Port 8000 is used by Portainer's edge tunnel, but `stacks/rag-agent` also publishes 8000 (`rag-agent-ui`). Starting the RAG agent would fail with "port is already allocated". [V] (src: stacks/rag-agent/docker-compose.yml:43; cmd: ss -ltnp) [I] for the failure
6. Stale guides.
   - `QUICK_REFERENCE.md` says Portainer is at `:9000` and the RAG agent at `:8000`. Real Portainer HTTP is `:9010`. [V] (src: library/08-orchestration/guides/QUICK_REFERENCE.md:15-16; docker-compose.yml:67)
   - `setup.sh` and `cmd_start` print `http://<ip>:9000`. [V] (src: setup.sh:96; fortress:97)
   - The root file lists `orchestration … (Portainer, Watchtower)`, but Watchtower is off. [V] (src: homelab/docker-compose.yml:9; cmd: docker ps -a)
7. `stacks/cine-immich` is an old duplicate. Deploying it with the orchestration CLI would start a second Cine-Immich (`fortress-cine-*`) next to the real one. [V] (src: stacks/cine-immich/docker-compose.yml:10-15; homelab/orchestration/fortress:44,314-315) [I] for the effect
8. `plane-space-1` is unhealthy. [V] (cmd: docker ps) See the Plane manual for the cause. [U]
9. `voicebox` lives outside `~/homelab` and outside `services.yaml`, so Homelab Control and its health check do not see it. Restart policy `unless-stopped` brings it back at boot. [V]
10. Portainer has full control of Docker through the socket and its UI listens on all interfaces with the firewall off. [V] (cmd: ss -ltnp; DUM-E.md F9) [I] for the risk

## Logs
- `docker logs --tail 50 fortress-portainer` — start-up lines ("starting HTTPS server :9443", "starting HTTP server :9000", edge "Listening on http://0.0.0.0:8000"). [V]
- `docker logs --tail 15 fortress-api-1` — the "Waiting for database migrations" loop of the orphan set. [V]
- `journalctl -u docker -b | grep -iE "allocate port|failed to start container"` — containers that failed at boot (today: `fortress-meilisearch-play`). [V]
- Loki/Grafana dashboard "Homelab Live Control Tower" (uid `fortress-orchestration`) and per-stack log dashboards (manual 25). [V]
- No incidents in `incidents.log` come from source `orchestration`. [V] (src: incidents.log, aggregated)

## Rules for DUM-E here
- Never run bare `fortress`. Use `~/homelab/control/fortress` for Homelab Control. Never run `~/homelab/orchestration/fortress` except `status`, `health`, `logs` (read-only), and only with a timeout (`logs` follows with `-f`).
- Never deploy `homelab/docker-compose.yml` or run `docker compose` in `~/homelab`.
- Never run `prune`, `undeploy`, `stop`, `restart`, `deploy`, `backup` of the orchestration CLI, or any `docker compose up/down/restart/stop`, `docker rm`, `docker volume rm`.
- Never log in to Portainer or call its API.
- `service_start orchestration` is allowed with confirmation; `service_stop orchestration` is not.
- Before `service_start immich`, warn about problem 4. Before `service_start rag_agent`, warn about problem 5.
- Never open stack `.env` files or the Portainer volume.
- DELETES operations that exist here: orchestration `stop`/`restart` (compose down), `undeploy` (compose down), `prune` (containers, networks, images, build cache); Watchtower cleanup (old images); `docker compose -p fortress down`; removal of the orphan Plane set and its volumes; `docker volume rm fortress-portainer-data`; Portainer UI delete actions; `sudo rm /usr/local/bin/fortress`.

## Open questions
- Is the orphan Plane set needed for anything (for example old data in `fortress_pgdata`)? Settle: ask the owner. [U]
- Which exact earlier version of the root compose file created project `fortress`? Settle: the owner checks `homelab/backups/fortress_state_20260221_120030/compose-configs/__home__vector__fortress.resolved.yml` personally (it may contain secrets). [U]
- Are any stacks deployed through Portainer's own stack feature (not compose CLI)? Settle: the owner opens Portainer → Stacks. [U]
- Does `include:` in `stacks/plane` load `homelab/plane/.env` for variable substitution when started without `--env-file`? Settle: owner runs `docker compose config --quiet` in `stacks/plane` and reads warnings (do not print the full config; it shows secrets). [U]
