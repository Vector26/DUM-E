---
title: Container unhealthy, restarting or exited
symptom: A container is unhealthy, restarting or exited
last_verified: 2026-10-30
related: 05-services-catalog, 27-portainer-and-stacks
---

# Container unhealthy, restarting or exited

## Symptom
- `dume doctor` lists "Container <name> ... (unhealthy)" or "Restarting". [V]
- Example today: `plane-space-1` is "Up 17 hours (unhealthy)". [V]

## Quick check
1. `containers {}` - look for: the "Needs attention" list.
2. `containers {"name":"<container>","log_lines":30}` - look for: the health check output and the last errors.

## Diagnosis
1. Health output says "curl: not found" or "wget: not found" -> cause A: false alarm. The image lacks the check tool. Known case: `plane-space-1`. [V]
2. "Restarting" with errors in the logs -> cause B: a real crash. Read the error. Find the owning stack with `graph {"action":"search","query":"<container>"}`.
3. "Exited (0)" long ago -> cause C: stopped on purpose (for example the media stack). Not a problem unless the owner wants it -> runbook:service-not-running.
4. A container belonging to an agent (`virtual_self_*`, `n8n_*`) is not running -> runbook:agent-container-down. agent-heal restarts those by itself. [V]

## Fix
- A: nothing to fix in DUM-E. The owner may change the health check in the compose file.
- B: restart the owning service, not the single container: `propose_action {"action":"service_stop","args":{"service_id":"<id>"}}`, then `service_start` for the same id (find it with `services {}`). Tell the owner: dume approve <ID>. A single-container restart is the owner's: `docker restart <container>`.
- C: see runbook:service-not-running.

## Verify
- `containers {}` no longer lists it in "Needs attention".

## Do not
- Do not run or propose `docker rm`, `compose down` or `--force-recreate`. Some stacks keep queues only in memory. [I]
- Do not restart databases to "fix" an unhealthy app container.
- Do not propose changes to Immich, Plane or backup containers without the owner's say.

## Sources
- `docker ps -a` (this session)
- manual 05-services-catalog, 27-portainer-and-stacks
- `~/homelab/DUM-E/bin/dume` (doctor)
