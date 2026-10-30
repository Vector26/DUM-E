---
title: Service not running
symptom: A Homelab service is down or "not running (default service)"
last_verified: 2026-10-30
related: 04-fortress-control, 05-services-catalog
---

# Service not running

## Symptom
- `dume doctor` lists "Health: <id>: not running (default service)". [V]
- On 2026-10-30 this applied to cine_immich, anytype, jarvis and mediastack. [V]

## Quick check
1. `services {"id":"<id>"}` - look for: state, "default", "in boot profile", dependents.
2. `containers {"name":"<container>"}` - look for: the container the service detects.

## Diagnosis
1. default is yes, boot profile is no, and it is off -> cause A: boot never starts it. Homelab health still reports it. [V]
2. It depends on `ai_llama` and the AI is down -> cause B -> runbook:ai-down first. [V]
3. The service is `immich` -> cause C: it must start with `docker compose --env-file ~/homelab/immich/.env up -d` from its stack folder, so `fortress start immich` is unsafe. DUM-E's action refuses it. [I]
4. The service is `mediastack` -> cause D: its data disk `/mnt/movie-storage` may not be mounted. Starting it could write downloads to the root disk. DUM-E's action refuses it. [I]
5. The service is `personal_feed` -> a host process on :8077 started by `start_backend.sh`; that script also starts the AI brain if :8081 is down. [I]
6. The service is `modelq`, `agent_gateway` or `oda_preview` -> runbook:model-queue-down, runbook:agent-gateway-down or runbook:oda-preview-down. agent-heal restarts them by itself. [V]

## Fix
- A, B: `propose_action {"action":"service_start","args":{"service_id":"<id>"}}`. Tell the owner: dume approve <ID>.
- C, D: owner only. Explain the warning above and let the owner run it.
- If the owner does not want it on: they set `default: false` in `~/homelab/control/services.yaml` (owner edit).

## Verify
- `services {"id":"<id>"}` shows RUNNING.

## Do not
- Do not propose `service_start` for `ai_llama`, `vram_watchdog`, `immich` or `mediastack`. They are excluded. [V]
- Do not use `fortress start` through a pipe for host services; it can hang.

## Sources
- `~/homelab/control/services.yaml`
- manual 04-fortress-control, 05-services-catalog
- `~/homelab/DUM-E/config/actions.json`
