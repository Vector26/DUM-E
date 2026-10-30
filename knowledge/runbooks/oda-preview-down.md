---
title: ODA preview server down
symptom: ODA design previews on :7460 do not load
last_verified: 2026-10-30
related: 40-agent-platform
---

# ODA preview server down

## Symptom
- A preview link such as `http://100.x.x.x:7460/p/<slug>/` does not open. [V]
- `oda status` shows `oda-preview.service: inactive`. [V]

## Quick check
1. `ports {}` - look for: 7460 LISTEN on 0.0.0.0.
2. Owner runs `oda previews` - look for: the published slugs and URLs.
3. Owner runs `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7460/p/<slug>/` - expected: 200.

## Diagnosis
1. The server is the system unit `oda-preview.service`, run as the owner, `Restart=on-failure`, `RestartSec=3`. [V]
2. The server was killed (`kill -9`) -> it restarts by itself within seconds. [V]
3. The unit was stopped or failed repeatedly -> cause A: nobody restarts a stopped unit. agent-heal does, within 2 minutes (`sudo -n systemctl restart oda-preview.service`). [V]
4. `GET /` returns 404. That is normal. Only `/p/<slug>/` is served. [V]
5. Port 7460 answers but a slug returns 404 -> cause B: it was never published or its folder was removed. Check `oda previews`.
6. Remote link fails but localhost works -> cause C: Mesh VPN (e.g. Tailscale) or LAN path, not ODA. The preview binds 0.0.0.0. [V]

## Fix
- A: owner runs `oda preview-start` (uses sudo), or `sudo systemctl restart oda-preview`. agent-heal does the same on its own.
- B: ask ODA to publish again (`oda`, then "publish_preview").
- C: check Mesh VPN (e.g. Tailscale); not an ODA fault.

## Verify
- `~/homelab/agents/scripts/agent-heal --check` shows `OK oda_preview`.
- The page returns 200.

## Do not
- Do not delete published previews to "fix" a 404.
- Do not give ODA access to Homelab ops. It is design-only. [V]

## Sources
- `systemctl cat oda-preview.service`
- `~/homelab/ODA/bin/oda` (status, preview-start)
- `~/homelab/agents/scripts/agent-heal` (fix_oda_preview)
