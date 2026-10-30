---
title: Personal feed did not update
symptom: The feed app shows old content
last_verified: 2026-10-30
related: 31-personal-feed, 02-ai-brain
---

# Personal feed did not update

## Symptom
- The feed app shows an old deck. [V]
- On 2026-10-30 the boot log noted "deck is 2026-10-05, today is 2026-10-29". [V]

## Quick check
1. `log_tail {"log":"feed_cron","lines":40}` - look for: errors and the date of the last success.
2. `log_tail {"log":"feed_learn","lines":40}` - look for: the same.
3. `services {"id":"personal_feed"}` - look for: RUNNING on :8077.
4. `ai_brain {}` - look for: "/health: 200". The feed needs the brain.

## Diagnosis
1. The crons: learn at 05:00 and daily at 06:00. [V]
2. The AI brain is down -> cause A -> runbook:ai-down. [V]
3. The log says "No route to host 172.21.0.2" -> cause B: the database address in the feed's `.env` is a Docker IP that only `start_backend.sh` refreshes. [I]
4. The service is off -> cause C -> runbook:service-not-running.
5. The feed's own brain calls go straight to :8081, not to the model queue, so a model queue outage does not stop it. [V]
6. Note: `start_backend.sh` also starts the brain if :8081 is down. That bypasses the GPU guard. [I]

## Fix
- A: runbook:ai-down.
- B: the owner restarts the backend through `start_backend.sh`. DUM-E can propose `service_stop` then `service_start` for `personal_feed`. Tell the owner: dume approve <ID>. Then wait for the next cron, or the owner runs `run_daily.sh` from the feed folder.
- C: runbook:service-not-running.

## Verify
- `log_tail {"log":"feed_cron","lines":10}` shows a success with today's date.

## Do not
- Do not run `start_backend.sh` while another GPU job runs; it may start the brain.
- Do not edit the feed's `.env`.

## Sources
- `crontab -l` (feed entries)
- `~/homelab/personal-feed/start_backend.sh` (FF_LLM_BASE_URL default http://127.0.0.1:8081)
- manual 31-personal-feed
