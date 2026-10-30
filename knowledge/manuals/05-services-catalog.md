---
title: Services catalog (all Homelab Control services)
scope: Every entry in control/services.yaml - what it is, how it starts, how it is detected, GPU, default, dependencies, state on 2026-10-29
last_verified: 2026-10-29
sources: control/services.yaml, control/status.py status (2026-10-29 22:45), docker ps, ~/.config/fortress-control/profiles/default.json
---

# Services catalog (all Homelab Control services)

## What it is
A "service" in the homelab is a whole stack or host program that Homelab Control starts and stops as one unit. They are defined in `~/homelab/control/services.yaml` [V]. "default(yaml)" means `default: true` in that file (health alerts expect it to run). "profile" means it is in the boot profile (boot starts it).

## How the owner refers to it
By name or id: "the AI", "cine", "immich", "plane", "n8n", "monitoring/Grafana", "notifier/Telegram", "vault", "jellyfin/media", "feed", "jarvis", "virtual self/vself", "lifepath", "vitalis", "music".

## Components
State columns are from 2026-10-29 22:45 [V]; always re-check with the `services` tool.

| id | name | kind | GPU | default(yaml) | profile | state | detected by |
|---|---|---|---|---|---|---|---|
| orchestration | Portainer | compose `homelab/orchestration` | no | yes | yes | ON | container fortress-portainer |
| n8n | Workflows (n8n) | compose `homelab/n8n` | no | yes | yes | ON | container n8n_server |
| monitoring | Monitoring (Grafana, Prometheus, logs) | compose `homelab/monitoring` | no | yes | yes | ON | container fortress-prometheus |
| notifier | Alert notifier | compose `homelab/notifier` | no | yes | yes | ON | container notifier-notifier-1 |
| cine_immich | Cine photos + AI tags | compose `homelab/cine-immich` | YES | yes | no | ON | container cine_immich_server |
| immich | Immich photos | compose `homelab/orchestration/stacks/immich` | no | yes | yes | ON | container fortress-immich-server |
| plane | Plane projects | compose `homelab/orchestration/stacks/plane` | no | yes | yes | ON | container plane-proxy-1 |
| affine | Affine notes | compose `homelab/affine` | no | yes | no | ON | container affine_server |
| anytype | Anytype sync | compose `homelab/anytype` | no | yes | no | off | container anytype_sync_bundle |
| jarvis | Jarvis voice | compose `homelab/jarvis` | no | yes | no | off | container jarvis-gateway; depends on ai_llama |
| vault | Vault storage (MinIO) | compose `homelab/vault-storage` | no | yes | yes | ON | container vault-minio |
| mediastack | Media (Jellyfin, *arr) | compose `~/mediastack` | no | yes | no | off | container mediastack-jellyfin (Exited 3 months ago) |
| personal_feed | Personal Feed | host: `homelab/personal-feed/start_backend.sh`; stop `pkill -f 'uvicorn api:app'` | no | yes | yes | ON | port 8077 |
| ai_llama | Local AI (HauhauCS) | host: `~/bin/llama-server-ctl start|stop` | YES | yes | yes | ON | port 8081 |
| vram_watchdog | VRAM watchdog | host: nohup `control/vram-watchdog.sh`; stop: kill pid file | no | yes | yes | ON | process vram-watchdog.sh |
| lifepath | LifePath | compose `homelab/LifePath` | no | no | no | off | port 39081 |
| vitalis | Vitalis | compose `homelab/vitalis` | no | no | no | off | port 39082 |
| music | Music service | compose `homelab/orchestration/stacks/music-service` | no | no | no | off | port 6544 |
| virtual_self | Virtual Self | compose `homelab/virtual-self-memory` | no | no | no | ON | container virtual_self_api; depends on ai_llama |
| virtual_self_archive | Virtual Self Archive | compose `homelab/virtual-self-memory` (profile archive) | no | no | no | off | container virtual_self_archive_sync; depends on virtual_self, ai_llama |

Services that are ON without being in the profile (cine_immich, affine, virtual_self) are brought up by something else, most likely Docker restart policies [I]; cine_broll_worker has restart policy `always` [V].

Containers running that belong to no service entry [V]: `voicebox`, `fortress_chromadb` (n8n compose, :8100), `virtual_self_searxng` (:8098), `virtual_self_knowledge_gateway` (:8099), a second Plane-like set `fortress-api-1`, `fortress-worker-1`, `fortress-beat-worker-1`, `fortress-plane-mq-1`, `fortress-plane-db-1`, `fortress-plane-redis-1` (owner project: see manual 27), monitoring exporters.

## Files and data
- `control/services.yaml` (definitions), `profiles/default.json` (boot set). Per-service data: see each service's manual (20-39).

## Commands
- `fortress start|stop <id>` - MUTATES. DUM-E actions `service_start`/`service_stop` (not for ai_llama, vram_watchdog; no stop for orchestration, notifier, monitoring).
- `fortress status` - READ.

## Depends on
- jarvis -> ai_llama; virtual_self -> ai_llama; virtual_self_archive -> virtual_self, ai_llama (src: services.yaml depends_on) [V].
- Homelab Control does not start dependencies automatically [I] (fc_start_service has no dependency handling, src: lib/actions.sh).

## How to check it (read-only)
- `services` (table) and `services id=<id>` (details and dependents).
- `containers name=<container>` for a stack's main container.

## Known problems and fixes
- anytype, jarvis, mediastack: default(yaml)=yes but not in profile and off -> hourly "not running (default service)" incidents (716 each in 30 days to 2026-10-29) [V]. Owner decides: start, add to profile, or mark default: false. runbook:health-alerts.
- mediastack containers exited 3 months ago (code 0) [V].
- plane-space-1 "unhealthy" is a false alarm: its health check runs `curl`, which is not installed in the image; the app answers 200 [V]. runbook:container-unhealthy.

## Logs
See each service's manual; homelab-level: `log_tail log=incidents`.

## Rules for DUM-E here
- Proposals only; warn about dependents when proposing a stop (use `services id=<id>`).

## Open questions
- Owner's intent for anytype, jarvis, mediastack (should they run?) [U].
