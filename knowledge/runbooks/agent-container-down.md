---
title: Agent container stopped or unhealthy
symptom: Virtual Self or n8n (flowsmith) stops answering because a container is stopped or unhealthy
last_verified: 2026-10-30
related: 35-virtual-self, 36-n8n-dexter-orchestration
---

# Agent container stopped or unhealthy

## Symptom
- Virtual Self chat through the gateway fails. [V]
- `flowsmith list` fails, or n8n on :5678 does not answer. [V]
- `docker ps -a` shows `Exited` for `virtual_self_api`, `virtual_self_worker` or `n8n_server`. [V]

## Quick check
1. `containers {}` - look for: the "Needs attention" list.
2. `containers {"name":"virtual_self_api","log_lines":30}` - look for: the last error.

## Diagnosis
1. The compose policy is `restart: unless-stopped`. A container stopped by hand (`docker stop`) stays stopped. [V]
2. agent-heal watches these: `virtual_self_api`, `virtual_self_worker`, `virtual_self_searxng`, `virtual_self_knowledge_gateway`, `virtual_self_postgres`, `n8n_server`, `n8n_postgres`. [V]
3. Stopped (exited) -> agent-heal runs `docker start <name>`. [V]
4. Unhealthy or restarting -> agent-heal runs `docker restart <name>`, except for the two databases, which it only starts when stopped. [V]
5. After 3 fix attempts in 30 minutes agent-heal stops trying and sends one Alert message. [V]
6. Virtual Self calls the model queue at `host.docker.internal:8181` (172.28.0.1 on its network). The queue must listen on 0.0.0.0 -> runbook:model-queue-down. [V]
7. A container that does not exist at all (never created) is reported as a warning. agent-heal does not create containers. [V]
8. Dexter and Detective have no resident container. The gateway runs them as host commands. [V]

## Fix
- Wait for agent-heal (2 minutes), or the owner runs `~/homelab/agents/scripts/agent-heal --fix`.
- Owner can do it by hand: `docker start <name>`. For Virtual Self after a compose change: `cd ~/homelab/virtual-self-memory && docker compose up -d --no-deps --no-build api worker`.
- A crash loop -> read the logs, report the exact error. Do not restart the database.

## Verify
- `~/homelab/agents/scripts/agent-heal --check` shows `OK container:<name>` and `OK vself_api` or `OK n8n`.
- `~/homelab/agents/scripts/agent-heal --e2e` shows `gateway:virtual-self` OK.

## Do not
- Do not run `docker rm`, `compose down`, `docker volume prune` or any prune. Postgres data lives in volumes. [V]
- Do not restart `virtual_self_postgres` or `n8n_postgres`.
- Do not touch Immich, Plane or backup containers with this runbook.

## Sources
- `~/homelab/virtual-self-memory/compose.yaml`
- `~/homelab/agents/scripts/agent-heal` (CONTAINERS, make_container_fix)
- manual 35-virtual-self, 36-n8n-dexter-orchestration
