---
title: Monitoring (Prometheus, Grafana, Loki, exporters)
scope: The homelab/monitoring stack - containers, compose-project split, scrape targets, log shipping, dashboards, exporters, the fortress-vitals TUI, and known problems.
last_verified: 2026-10-29
sources: homelab/monitoring/{docker-compose.yml,prometheus/prometheus.yml,loki/loki.yml,promtail/promtail.yml,grafana/provisioning/**,vault-backup-exporter/*,ups-exporter/*,scripts/*,cmd/fortress-vitals/README.txt}, homelab/library/06-monitoring/*, homelab/control/{services.yaml,host_jobs.yaml}, docker ps -a, docker compose ls, docker inspect --format, docker logs --tail, docker system df -v, curl localhost:9090/api/v1/targets, curl :9122/metrics, ss -ltnp
---

# Monitoring (Prometheus, Grafana, Loki, exporters)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
The monitoring stack collects numbers (metrics) and logs from the homelab and shows them in Grafana dashboards. [V] (src: homelab/monitoring/docker-compose.yml)
Prometheus scrapes metrics. Loki stores logs. Promtail ships Docker and backup logs into Loki. Grafana draws both. [V] (src: prometheus/prometheus.yml; promtail/promtail.yml; grafana/provisioning/datasources/datasources.yml)
It does not send alerts. There are no alert rules and no Alertmanager. Phone alerts come from `fortress health` and the notifier (manual 26). [V] (cmd: curl -s localhost:9090/api/v1/rules → empty groups)
The running containers belong to two different compose projects, which makes start and stop unreliable. See Known problems. [V] (cmd: docker compose ls; docker inspect --format Labels)

## How the owner refers to it
- "Monitoring", "Grafana, Prometheus, logs". Homelab Control id `monitoring`. [V] (src: homelab/control/services.yaml:25-32)
- "Grafana" (port 3030), "Prometheus" (9090), "Loki" (3100). [V] (cmd: docker ps)
- Dashboard names, e.g. "Homelab Live Control Tower", "Vault Backup — Google Drive & Restic", "Homelab Task Manager". [V] (src: grafana/provisioning/dashboards/json/*.json, title field)
- `fortress-vitals` — terminal dashboard (alias in `.bashrc:490`, binary `~/bin/fortress-vitals`). [V] (src: ~/.bashrc:490; cmd: ls -la ~/bin/fortress-vitals)
- Health job `vault_backup_exporter`, label "Backup monitoring". [V] (src: homelab/control/host_jobs.yaml:23-28; homelab/control/lib/fc_incident.sh:34)

## Components
Compose file: `~/homelab/monitoring/docker-compose.yml` with `name: monitoring`. Network `fortress-network` (external); the redis exporter also joins `cine-immich_cine-network`. [V] (src: docker-compose.yml:1,179-186)

Owning compose project, from container labels: [V] (cmd: docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "com.docker.compose.project.working_dir"}}')
- Project `fortress`, working dir `homelab/monitoring`: `fortress-prometheus`, `fortress-ups-exporter`, `fortress-cine-immich-redis-exporter`.
- Project `fortress`, working dir `~/homelab` (the root reference file): `4bf74c64847c_fortress-grafana`, `fortress-cadvisor`, `fortress-node-exporter` (created 2026-02-21).
- Project `monitoring`, working dir `homelab/monitoring`: `fortress-loki`, `fortress-promtail`, `fortress-vault-backup-exporter`.

Containers: [V] (src: docker-compose.yml; cmd: docker ps -a; docker inspect --format)
- `fortress-prometheus` — `prom/prometheus:latest`. Port `0.0.0.0:9090`. Keeps data 35 days (`--storage.tsdb.retention.time=35d`). `--web.enable-lifecycle` is on. Volume `fortress_prometheus-data` (5.67 GB). Memory limit 512 MB. Running. (src: docker-compose.yml:4-21; cmd: docker system df -v)
- `4bf74c64847c_fortress-grafana` — `grafana/grafana:latest`, version 12.3.3. Port `0.0.0.0:3030` → 3000. Volume `fortress_grafana-data` (52.7 MB). Provisioning folder mounted read-only. Admin user and password are set as plain text in the compose file (SECRET values, not copied). Sign-up disabled. Running. (src: docker-compose.yml:118-136; cmd: curl -s localhost:3030/api/health)
  - The name has a `4bf74c64847c_` prefix, a leftover of a Docker rename during recreate. Anything that looks for `fortress-grafana` will miss it. [V] (cmd: docker ps) [I] for the cause
- `fortress-loki` — `grafana/loki:latest`. Port `0.0.0.0:3100`. Volume `fortress_loki-data` (4.60 GB). Auth disabled. Restarted 3 times this boot; `/ready` answered "ready" at 22:4x. (src: docker-compose.yml:138-151; loki/loki.yml:1; cmd: docker inspect --format RestartCount; curl localhost:3100/ready)
- `fortress-promtail` — `grafana/promtail:latest`. No port. Reads `/var/lib/docker/containers`, the Docker socket, and the two vault-backup log folders. (src: docker-compose.yml:153-169)
- `fortress-cadvisor` — `gcr.io/cadvisor/cadvisor:latest`. Container metrics on internal port 8080 only. Mounts `/`, `/var/run`, `/sys`, `/var/lib/docker`, `/dev/disk` read-only. Healthy. (src: docker-compose.yml:23-36)
- `fortress-node-exporter` — `prom/node-exporter:latest`. Host metrics on `0.0.0.0:9100`. Mounts `/` read-only. (src: docker-compose.yml:38-51)
- `fortress-vault-backup-exporter` — built from `monitoring/vault-backup-exporter/` (image `homelab/vault-backup-exporter:local`). Port `0.0.0.0:9122`. Uses `pid: host`. Mounts `~/.config/vault-backup` read-only (SECRET folder: restic password and Drive token), `/mnt/backup-volume` read-only, the restic cache read-write, and the legacy logs folder. (src: docker-compose.yml:53-73)
- `fortress-ups-exporter` — built from `monitoring/ups-exporter/` (image `homelab/ups-exporter:local`). Internal port 9121. Runs `/usr/sbin/pwrstat -status` through the host socket `/var/pwrstatd.ipc`; runs as root. Host service `pwrstatd.service` is active. (src: docker-compose.yml:75-88; ups-exporter/exporter.py:17-49; ups-exporter/Dockerfile; cmd: systemctl is-active pwrstatd)
- `fortress-cine-immich-redis-exporter` — `oliver006/redis_exporter:v1.66.0`, would read `broll_queue` and `broll_face_queue` from `cine_immich_redis`. NOT running: exited (code 0) on 2026-09-09 12:19 UTC. (src: docker-compose.yml:90-101; cmd: docker inspect --format State)
- `fortress-dcgm-exporter` — `nvidia/dcgm-exporter:latest`, GPU metrics on 9400. NOT running, and no container with that name exists at all. GPU metrics are not in Prometheus. (src: docker-compose.yml:103-116; cmd: docker ps -a)
- Watchtower is not part of this stack (see manual 27).

Prometheus scrape targets (scrape every 15 s; vault-backup every 30 s with 25 s timeout). State at 22:4x on 2026-10-29: [V] (src: prometheus/prometheus.yml:5-66; cmd: curl -s 'localhost:9090/api/v1/targets?state=active')
- up: `prometheus:9090`, `node-exporter:9100`, `cadvisor:8080` (scraped twice: jobs `cadvisor` and `affine-cadvisor`), `grafana:3000`, `ups-exporter:9121`, `vault-backup-exporter:9122`.
- down: `dcgm-exporter:9400` (no container), `cine-immich-redis-exporter:9121` (stopped), `plane-postgres-exporter:9187` and `plane-redis-exporter:9121` (no such containers exist), `172.20.0.1:9808` job `jarvis-gateway` (Jarvis is not running).

Alerting: none. `prometheus.yml` has no `rule_files` and no `alerting` block; the rules API returns no groups; Loki's ruler points at `http://localhost:9093` where nothing runs; Grafana provisioning has no alerting folder. [V] (src: prometheus/prometheus.yml; loki/loki.yml:48-49; cmd: ls grafana/provisioning; curl localhost:9090/api/v1/rules)

Other parts:
- `cmd/fortress-vitals/` — Go source of the terminal dashboard. Built binary `~/bin/fortress-vitals` (10.6 MB, 2026-03-23). Build line: `go build -o ~/bin/fortress-vitals .`. [V] (src: cmd/fortress-vitals/README.txt:1; cmd: ls -la ~/bin/fortress-vitals)
- `scripts/fortress-vitals-tmux.sh` — older tmux 2×2 dashboard (btop/htop, nvtop, lazydocker, summary). `scripts/fortress-vitals-summary.sh` prints Ollama models, an optional Prometheus GPU line, and containers by stack. `scripts/fortress-vitals-stacks.sh` groups running containers by compose project. All read-only. [V] (src: scripts/fortress-vitals-tmux.sh:1-28; scripts/fortress-vitals-summary.sh:1-12; scripts/fortress-vitals-stacks.sh:1-20)
- `PLAN_LOGS_DASHBOARDS.md` — symlink to `library/06-monitoring/PLAN_LOGS_DASHBOARDS.md` (a plan, not live config). [V] (cmd: ls -la homelab/monitoring)
- Homelab Control: `kind: compose`, `compose: homelab/monitoring`, `detect_container: fortress-prometheus`, `default: true`. [V] (src: homelab/control/services.yaml:25-32)
- Host job `vault_backup_exporter`: checks that `fortress-vault-backup-exporter` runs. [V] (src: homelab/control/host_jobs.yaml:23-28)

## Files and data
- `homelab/monitoring/docker-compose.yml` — the stack (contains Grafana admin credentials in plain text: SECRET values). [V]
- `homelab/monitoring/prometheus/prometheus.yml` — scrape config (mounted read-only). [V]
- `homelab/monitoring/loki/loki.yml` — Loki config: filesystem store under `/loki`, schema v13 tsdb, `compactor.retention_enabled: false` (logs are never deleted), `auth_enabled: false`. [V] (src: loki/loki.yml:1,17-44)
- `homelab/monitoring/promtail/promtail.yml` — log shipping config. Positions file `/tmp/positions.yaml` inside the container (lost on recreate). [V] (src: promtail/promtail.yml:6)
  - Job `docker`: every container's JSON log, labels `container`, `stream`, `job=docker`; parses migration JSON fields into labels. [V] (src: promtail/promtail.yml:12-48)
  - Job `vault-backup`: `/mnt/backup-volume/vault-backup/logs/*.log` and `~/homelab/vault-backup/logs/*.log`. [V] (src: promtail/promtail.yml:50-61)
  - Job `fortress-incidents`: `~/.local/state/homelab/incidents.log`. This path is not mounted into the container, so it ships nothing. [V] (src: promtail/promtail.yml:64-78; docker-compose.yml:160-165) [I] for the effect
  - Job `migration-logs`: `~/homelab/affine/scripts/migration_*.log`. Also not mounted, so it ships nothing. [V] (src: promtail/promtail.yml:81-99) [I]
- `homelab/monitoring/grafana/provisioning/datasources/datasources.yml` — Prometheus (default, `http://prometheus:9090`) and Loki (uid `loki`, `http://loki:3100`). [V]
- `homelab/monitoring/grafana/provisioning/dashboards/dashboards.yml` — provider "Fortress", folder "Fortress", files from `json/`, `disableDeletion: false`, `allowUiUpdates: true`, reload every 30 s. [V]
- Dashboards in `grafana/provisioning/dashboards/json/` (title / uid / panels): [V]
  - `affine-migration-control-tower.json` — Affine Migration Control Tower / affine-migration-control-tower / 33
  - `all-containers-logs.json` — All Containers Logs / all-containers-logs / 1
  - `cine-immich-operations.json` — Cine-Immich Operations / cine-immich-ops / 21
  - `fortress-monitoring-logs.json` — Homelab Monitoring Logs / fortress-monitoring-logs / 1
  - `fortress-orchestration.json` — Homelab Live Control Tower / fortress-orchestration / 11
  - `immich-logs.json` — Immich Logs / immich-logs / 1
  - `jarvis-voice.json` — Jarvis Voice Assistant / jarvis-voice / 12
  - `lifepath-logs.json` — LifePath Logs / lifepath-logs / 1
  - `music-service-logs.json` — Music Service Logs / music-service-logs / 1
  - `n8n-logs.json` — n8n Logs / n8n-logs / 1
  - `onyx-rag-agent-logs.json` — Onyx RAG Agent Logs / onyx-rag-agent-logs / 1
  - `plane-logs.json` — Plane Logs / plane-logs / 1
  - `task-manager.json` — Homelab Task Manager / fortress-task-manager / 14
  - `vault-backup.json` — Vault Backup — Google Drive & Restic / vault-backup / 18 (uses `vault_backup_*` metrics)
- `homelab/monitoring/vault-backup-exporter/exporter.py` — vault-backup metrics (details below). [V]
- `homelab/monitoring/ups-exporter/exporter.py` — UPS metrics `fortress_ups_exporter_up`, `fortress_ups_load_watts`, `fortress_ups_rating_watts`. [V] (src: ups-exporter/exporter.py:61-80)
- Docker volumes (all under `/var/lib/docker` on the root disk, 91 % full): `fortress_prometheus-data` 5.67 GB, `fortress_loki-data` 4.60 GB, `fortress_grafana-data` 52.7 MB. [V] (cmd: docker system df -v; docker info --format DockerRootDir; df -h /)
- Docs: `homelab/library/06-monitoring/README.md` (index) and `PLAN_LOGS_DASHBOARDS.md` (dashboard plan; lists dcgm-exporter as part of the monitoring set). [V]

### vault-backup exporter metrics
- Listens on `0.0.0.0:9122`; caches a scrape for 60 s and refreshes in the background. [V] (src: vault-backup-exporter/exporter.py:17-19,293-312)
- Runs `rclone about vault-gdrive:` (120 s), `restic stats --json` (90 s) and `restic snapshots --json` (60 s). It skips both restic calls while any `restic backup` process runs. [V] (src: exporter.py:77-116)
- Metrics: `vault_backup_exporter_up`, `vault_backup_process_running`, `vault_backup_expansion_{used,free,total}_bytes`, `vault_backup_gdrive_{used,free,total}_bytes`, `vault_backup_gdrive_used_percent`, `vault_backup_restic_repo_size_bytes`, `vault_backup_restic_file_count`, `vault_backup_restic_snapshots_total{tag}`, `vault_backup_restic_last_snapshot_age_seconds{tag}`, `vault_backup_log_files_processed`, `vault_backup_log_last_update_timestamp`, `vault_backup_gdrive_ok`, `vault_backup_restic_ok`, `vault_backup_healthy`. [V] (src: exporter.py:147-290)
- `vault_backup_healthy` = 1 when Drive answers AND (restic answers OR a backup is running). [V] (src: exporter.py:285-287)
- Values at 22:4x: process_running 1, gdrive_ok 1, restic_ok 0, healthy 1, Drive used 259 GB of 5.50 TB (4.71 %), expansion disk 314 GB used of 2.0 TB, log_last_update 1790899730 (= 2026-10-02 05:38 IST). [V] (cmd: curl -s localhost:9122/metrics)

## Commands
READ:
- `docker ps --filter name=fortress- --format '{{.Names}} {{.Status}} {{.Ports}}'` — container states. [V]
- `docker compose ls` — project list (shows the `fortress` and `monitoring` split). [V]
- `curl -s localhost:9090/-/healthy` — "Prometheus Server is Healthy." [V]
- `curl -s 'localhost:9090/api/v1/targets?state=active'` — target health. [V]
- `curl -s localhost:9090/api/v1/rules` — alert rules (none). [V]
- `curl -s localhost:3100/ready` — Loki readiness. [V]
- `curl -s localhost:3030/api/health` — Grafana health and version. [V]
- `curl -s localhost:9122/metrics | grep -v '^#'` — backup exporter values. [V]
- `curl -s localhost:9100/metrics | head` — node exporter. [I]
- `docker logs --tail 50 fortress-promtail` — shipping errors (for example HTTP 429). [V]
- `~/bin/fortress-vitals` or alias `fortress-vitals` — terminal dashboard (interactive). READ. [V]
- `homelab/monitoring/scripts/fortress-vitals-stacks.sh` — containers grouped by project. READ. [V]

MUTATES (owner only unless noted):
- `fortress start monitoring` (control CLI, full path `~/homelab/control/fortress`) → `docker compose up -d` in `homelab/monitoring` as project `monitoring`. With the current split it will likely fail on container-name conflicts for Prometheus, cAdvisor, node-exporter, UPS exporter and the redis exporter, and may create a second Grafana that fails on port 3030. DUM-E action `service_start monitoring`. MUTATES. [V] (src: homelab/control/lib/actions.sh:38-45) [I] for the conflict
- `fortress stop monitoring` → `docker compose stop` in project `monitoring`. It would stop only Loki, Promtail and the vault exporter; Prometheus and Grafana keep running. DUM-E must not do this (it carries alerting data). MUTATES. [V] (src: homelab/control/lib/actions.sh:47-50; DUM-E.md section 15.2) [I] for the effect
- `curl -X POST localhost:9090/-/reload` or `/-/quit` — Prometheus lifecycle API (enabled). MUTATES. Owner only. [V] (src: docker-compose.yml:14) [I] for the endpoints
- `cd homelab/monitoring && docker compose build vault-backup-exporter ups-exporter` — rebuild local images. MUTATES. [I]
- `go build -o ~/bin/fortress-vitals .` in `cmd/fortress-vitals` — overwrites the binary. DELETES (overwrite). [V] (src: cmd/fortress-vitals/README.txt:1)

DELETES (owner only):
- `docker compose down` in `homelab/monitoring` (removes project `monitoring` containers) or `docker compose -p fortress down` (would remove Grafana, Prometheus, cAdvisor, node-exporter, UPS exporter, AND the orphan Plane set from manual 27). DELETES. [I]
- `docker volume rm fortress_prometheus-data | fortress_loki-data | fortress_grafana-data` — all history and dashboards edited in the UI. DELETES. [I]
- Removing a JSON file from `grafana/provisioning/dashboards/json/` deletes that dashboard in Grafana within 30 s, because `disableDeletion: false`. DELETES. [V] (src: dashboards.yml) [I] for the effect
- Prometheus drops data older than 35 days by itself. Automatic deletion. [V] (src: docker-compose.yml:13)

## Depends on
- Docker and the external network `fortress-network`. [V]
- `cine-immich_cine-network` for the redis exporter. [V] (src: docker-compose.yml:184-186)
- `pwrstatd.service` on the host for UPS metrics. [V]
- `/mnt/backup-volume` and `~/.config/vault-backup` for the vault exporter; Google Drive for its `rclone about`. [V]
- NVIDIA runtime for dcgm-exporter (not running). [V] (src: docker-compose.yml:109)
- Not the AI brain on :8081, not Ollama :11434 (only the vitals TUI reads Ollama at `127.0.0.1:11434`). [V] (src: cmd/fortress-vitals/README.txt:1; scripts/fortress-vitals-summary.sh:9)
- The notifier is not used by this stack. [V] (no references)

## How to check it (read-only)
- DUM-E tool `containers` → the 9 running monitoring containers and the 2 missing exporters.
- DUM-E tool `ports` → 9090, 3030, 3100, 9100, 9122 listen on 0.0.0.0. [V] (cmd: ss -ltnp)
- DUM-E tool `services` → id `monitoring` (detects `fortress-prometheus` only).
- DUM-E tool `health` → `vault_backup_exporter` host job.
- DUM-E tool `disk_memory` → root disk use; Loki and Prometheus volumes live there.
- DUM-E tool `gpu` → use this for GPU numbers; Prometheus has none (no dcgm-exporter).
- Owner, read-only: the curl commands in Commands; open Grafana at `http://<server>:3030`.

## Known problems and fixes
1. The stack is split across two compose projects.
   - Evidence: `docker compose ls` lists project `fortress` with config files `homelab/monitoring/docker-compose.yml,homelab/docker-compose.yml`, and project `monitoring` with 3 containers. Labels show which container belongs where (see Components). [V] (cmd: docker compose ls; docker inspect --format Labels)
   - Cause: older deployments ran the monitoring file under project name `fortress` and also from the root reference file. [I] (see manual 27)
   - Effect: `fortress start|stop monitoring` does not manage the whole stack. [I]
   - Fix: owner only. Recreate the stack under one project, for example remove the `fortress`-project monitoring containers by hand and run `docker compose up -d` in `homelab/monitoring`. DUM-E has no action for this.
2. GPU metrics are missing. dcgm-exporter was never created. [V] (cmd: docker ps -a) Fix: owner runs `cd ~/homelab/monitoring && docker compose up -d dcgm-exporter` after fixing problem 1. [I]
3. Five scrape targets are always down: dcgm, cine redis exporter, two Plane exporters that do not exist, and Jarvis. [V] (cmd: Prometheus targets API) Fix: owner starts the exporters or removes the jobs from `prometheus.yml`.
4. The cine redis exporter has been stopped since 2026-09-09 (exit 0). It has restart `unless-stopped`, so it was stopped on purpose or by `compose stop`. [V] (cmd: docker inspect --format State,RestartPolicy) [I]
5. No alerting exists in this stack. [V] Phone alerts come only from `fortress health --notify` (manual 26).
6. Logs grow without limit on the full root disk.
   - Loki retention is off; Loki volume 4.6 GB; root disk 91 % full. [V] (src: loki/loki.yml:44; cmd: docker system df -v; df -h /)
   - Promtail ships the huge, still growing vault-backup logs (927 MB and 339 MB files). [V] (src: promtail/promtail.yml:50-61; manual 23)
   - At boot Promtail hit "429 Too Many Requests: ingestion rate limit exceeded (limit: 4194304 bytes/sec)" because its positions file in `/tmp` is lost on recreate and it re-reads logs. [V] (cmd: docker logs --tail 3 fortress-promtail) [I] for the cause
   - Fix: owner enables Loki retention or excludes `bootstrap-*.log`. DUM-E has no action for this.
7. Loki holds a secret. The notifier container log contains the Telegram bot token inside request URLs, and Promtail ships all container logs to Loki. [V] for the log content (manual 26) [I] that Loki stored it. Anyone who can query Loki (port 3100, no auth) or Grafana can read it. Fix: owner silences the httpx request log, rotates the bot token, and deletes the affected Loki data (owner decision).
8. Open services with no auth on all interfaces while the firewall is off: Prometheus 9090 (with lifecycle API), Loki 3100, node-exporter 9100, vault exporter 9122, Grafana 3030. [V] (cmd: ss -ltnp; DUM-E.md F9)
9. The backup exporter says "healthy" while no daily backup has run for weeks: `healthy` is 1 whenever a backup process runs, and snapshot metrics are skipped during that time. `vault_backup_log_last_update_timestamp` only reads `restic-*.log`, so it is stuck at 2026-10-02. [V] (src: vault-backup-exporter/exporter.py:78-80,127-138,285-287; cmd: curl :9122/metrics)
10. Grafana's container name has a hash prefix (`4bf74c64847c_fortress-grafana`). [V] Detectors must match on the compose service label `grafana` or the suffix, not the exact name.
11. cAdvisor is scraped twice (jobs `cadvisor` and `affine-cadvisor`), doubling its series. [V] (src: prometheus/prometheus.yml:14-16,61-66)
12. All images except the redis exporter use `:latest`, so a recreate can change versions without notice. [V] (src: docker-compose.yml)

## Logs
- `docker logs --tail 50 fortress-prometheus` — scrape and storage errors. [V]
- `docker logs --tail 50 fortress-loki` — look for `level=error`, "Ingester not ready". [V]
- `docker logs --tail 50 fortress-promtail` — look for `status=429`, "error sending batch". [V]
- `docker logs --tail 50 4bf74c64847c_fortress-grafana` — Grafana errors. [I]
- `docker logs --tail 50 fortress-vault-backup-exporter` — "background scrape error". [V] (src: exporter.py:311)
- In Grafana: Explore → Loki → `{job="docker", container="<name>"}` or `{job="vault-backup"}`. [V] (src: promtail/promtail.yml)
- No incidents in `incidents.log` come from source `monitoring` or `vault_backup_exporter`. [V] (src: incidents.log, aggregated)

## Rules for DUM-E here
- Never stop the monitoring stack (`service_stop monitoring` is excluded). [V] (DUM-E.md 15.2)
- Before `service_start monitoring`, warn the owner that it will likely fail with name conflicts (problem 1).
- Never POST to Prometheus (`/-/reload`, `/-/quit`) or to Loki or Grafana APIs. GET only.
- Never query Loki for the notifier container's raw lines; they may contain the bot token. Never print a token found anywhere.
- Never open `~/.config/vault-backup/` even though the exporter mounts it.
- Never edit `prometheus.yml`, `loki.yml`, `promtail.yml` or dashboard JSON.
- DELETES operations that exist here: `docker compose down` / `docker compose -p fortress down`; `docker volume rm` of the three data volumes; removing a provisioned dashboard file (auto-deletes it in Grafana); Prometheus 35-day retention (automatic); rebuilding `~/bin/fortress-vitals` (overwrite).

## Open questions
- Was the Grafana admin password changed after first login, or is the compose default still valid? Settle: the owner logs in. [U]
- Did the redis exporter stop on purpose on 2026-09-09? Settle: ask the owner. [U]
- Does the `fortress-orchestration` dashboard ("Homelab Live Control Tower") rely on the missing exporters? Settle: open it in Grafana and look for empty panels. [U]
- Exact size Loki will reach before the root disk fills. Settle: watch `docker system df -v` over a few days. [U]
