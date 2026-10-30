---
title: DUM-E itself is not working
symptom: dume does not start, the chat dies, or it answers with an error
last_verified: 2026-10-30
related: 11-dume, 12-pi-harness
---

# DUM-E itself is not working

## Symptom
- `dume` exits at once, prints "terminated", or the chat hangs. [V]
- DUM-E may be unable to answer, so these checks are for the owner.

## Quick check
Owner runs, in this order:
1. `dume doctor` - look for: findings that name :8181, :8190 or agent-heal.
2. `dume ask "reply with one word: pong"` - expected: a short answer in seconds.
3. `dume audit 20` - look for: `chat_start` followed by a `tool` entry after a real question.
4. `~/homelab/agents/scripts/agent-heal --check` - look for: FAIL lines.

## Diagnosis
1. "DUM-E is not installed yet" -> cause A: run `bash ~/homelab/DUM-E/install.sh`. [V]
2. "The AI brain (:8081) is not answering" -> runbook:ai-down. [V]
3. "terminated" right after launch -> cause B. This was the real failure on 2026-10-30. [V]
   - `dume` goes through the model queue (:8181). The queue's streaming path closed its HTTP client before the reply was sent: "RuntimeError: Cannot send a request, as the client has been closed." in `journalctl --user -u fortress-modelq`.
   - Fixed in `modelq/modelq/app.py` (the client is now opened inside the stream). If it returns, restart the unit and read the journal.
4. Queue not running (:8181 refused) -> cause C. `dume` now starts `fortress-modelq.service` for you; if that fails, runbook:model-queue-down. [V]
5. "sudo: a password is required" -> cause D: `/etc/sudoers.d/dume` is missing or wrong -> rerun the installer. [I]
6. "Unknown tool" -> cause E: `/opt/dume/ext/dume.ts` differs from `DUM-E/ext/dume.ts` -> rerun the installer. agent-heal reports this as `dume_install`. [V]
7. "Tool error (...)" -> read the message; the audit log has details. [I]
8. "dume-tool must run as the owner account" -> someone ran it as another user. [I]
9. pi settings are in `/var/lib/dume/.pi/agent/models.json`; `baseUrl` must be `http://127.0.0.1:8181/v1`. Owner reads it with `sudo cat`. agent-heal checks it as `endpoint:dume`. [V]

## Fix
- A, D, E: owner runs `bash ~/homelab/DUM-E/install.sh`. Read it first; it uses sudo.
- B: `systemctl --user restart fortress-modelq`, then `dume ask "pong"`.
- C: runbook:model-queue-down.

## Verify
- `dume ask "Use your snapshot tool, then answer in one line."` answers, and `dume audit 5` shows a `tool` entry for `snapshot`.

## Do not
- Do not run `dume` with sudo. It refuses. [V]
- Do not edit files under `/opt/dume` by hand.
- Do not add a DUM-E daemon or timer. DUM-E never runs by itself. [V]

## Sources
- `~/homelab/DUM-E/bin/dume`, `install.sh`
- `journalctl --user -u fortress-modelq`
- `/opt/dume/`, `/var/lib/dume/`, `/etc/sudoers.d/dume`, `~/homelab/DUM-E/state/audit.log`
