---
title: AI is slow
symptom: DUM-E, pi or the agents answer very slowly
last_verified: 2026-10-30
related: 02-ai-brain, 33-memory-swap-oom
---

# AI is slow

## Symptom
- Answers take minutes, or a request seems stuck. [V]
- agent-heal logs "slow (timeout, brain probably busy)". [V]

## Quick check
1. `ai_brain {}` - look for: busy slots.
2. `gpu {}` - look for: utilisation and other processes.
3. `disk_memory {}` - look for: heavy swap use.

## Diagnosis
1. One brain is shared by pi, DUM-E, Jarvis, Virtual Self, the feed, ODA, Dexter, Detective and flowsmith. [V]
2. The model queue lets 2 requests run at once (`MODELQ_MAX_IN_FLIGHT=2`) and orders them: interactive first, then api, batch, nightly. [V]
3. Owner can see the queue: `curl -s http://127.0.0.1:8181/queue` - look at `active_count` and `waiting_count`. [V]
4. Many waiting requests -> cause A: too many clients at once. Batch jobs wait for interactive ones by design.
5. Prompt cache is often not reused for this model, so long conversations re-read everything -> cause B: a long chat is slow. [I]
6. MoE expert layers live in RAM (`-ncmoe 32`), so heavy swap slows it -> cause C. [V]
7. A reasoning model spends tokens thinking before it answers; a tiny `max_tokens` can return an empty reply. [V]

## Fix
- A: wait, or ask the owner to stop a client.
- B: start a fresh chat (`dume` without `-c`). For ODA use `oda continue`.
- C: report the swap use to the owner.
- Only if the brain is really broken: `propose_action {"action":"llama_restart"}`. **DELETES:** the server pid file. It interrupts every client for 1 to 2 minutes. Tell the owner: dume approve <ID>.

## Verify
- `ai_brain {}` shows no stuck slot, and a short `dume ask` answers in seconds.

## Do not
- Do not restart the brain just because it is slow.
- Do not bypass the queue (`MODELQ_BYPASS=1`) as a "speed fix".

## Sources
- `~/homelab/modelq/modelq/config.py`, `queue_manager.py`
- manual 02-ai-brain, 33-memory-swap-oom
