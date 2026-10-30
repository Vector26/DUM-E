---
title: No Alert notifications arrive
symptom: Alert notifications from Homelab do not arrive
last_verified: 2026-10-30
related: 26-notifier, 13-logs-and-incidents
---

# No Alert notifications arrive

## Symptom
- The owner expects an alert and gets none. [V]
- agent-heal logs "notify FAILED" lines. [V]

## Quick check
1. `containers {"name":"notifier-notifier-1","log_lines":30}` - look for: errors and "Up".
2. `ports {}` - look for: 8001 listening.
3. Owner can run `curl -s http://localhost:8001/health` - expected: `{"status":"ok"}`. [V]

## Diagnosis
1. Host port 8001 maps to container port 8000. Host :8000 is Portainer edge, not the notifier. [V]
2. Container not running -> cause A.
3. Health is ok, but the notifier answers 503 on /notify -> cause B: the Notifier token or chat id is not configured. [I]
4. It answers 502 -> cause C: the Telegram API returned an error. [I]
5. Alerts are deduplicated for 6 hours (`~/.local/state/homelab/notify_dedupe.tsv`), so a repeated problem alerts only every 6 hours. This is by design, not a failure. [V]
6. agent-heal sends a message only after a check fails 3 runs in a row (about 6 minutes), or after it gave up fixing. Its fix actions alone send nothing. [V]
7. Containers on the Virtual Self internal network cannot reach the notifier on 172.28.0.1:8001 (timed out when tested on 2026-10-30). Host-side callers work. [V]

## Fix
- A: `propose_action {"action":"service_start","args":{"service_id":"notifier"}}`. Tell the owner: dume approve <ID>.
- B, C: the owner fixes the token or chat id. DUM-E must never read the notifier's `.env`.

## Verify
- `curl -s http://localhost:8001/health` returns `{"status":"ok"}`.

## Do not
- Do not send a test message unless the owner asks. It pings the owner's phone.
- Do not read the notifier's `.env`.
- Do not stop the notifier. DUM-E may not stop `notifier`. [V]

## Sources
- `curl http://localhost:8001/health` (this session)
- `~/homelab/control/lib/fc_incident.sh`
- `~/homelab/agents/scripts/agent-heal` (notify)
- manual 26-notifier
