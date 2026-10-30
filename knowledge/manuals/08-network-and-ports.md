---
title: Network and ports
scope: Every listening port, what it is, who can reach it, Mesh VPN (e.g. Tailscale), firewall, how containers reach host services
last_verified: 2026-10-29
sources: ss -ltnp, docker ps ports, compose files (grep 8081/11434/host.docker.internal), mesh-vpn status, ufw status, notifier/docker-compose.yml
---

# Network and ports

## What it is
The homelab exposes many web UIs and APIs. Most bind to all interfaces (0.0.0.0), and the firewall (ufw) is inactive, so they are reachable from the home LAN [V]. Remote access is through Mesh VPN (e.g. Tailscale) (this node: `homelab-host`, 100.x.x.x) [V].

## How the owner refers to it
"ports", "what's open", "Mesh VPN (e.g. Tailscale)", "expose/share a service" (Cloudflare quick tunnels, manual 29).

## Components
Listening ports (cmd: ss -ltnH; docker ps; 2026-10-29) [V]:
| Port | Bound to | What |
|---|---|---|
| 22 | 0.0.0.0 | SSH |
| 443, 64063 | 100.x.x.x (Mesh VPN (e.g. Tailscale) IP) | Mesh VPN (e.g. Tailscale)-only listeners [U: which program] |
| 2283 | 0.0.0.0 | Immich (fortress-immich-server) |
| 3010 | 0.0.0.0 | AFFiNE |
| 3030 | 0.0.0.0 | Grafana (container port 3000) |
| 3100 | 0.0.0.0 | Loki |
| 5678 | 0.0.0.0 | n8n |
| 8000 | 0.0.0.0 | Portainer edge agent port (NOT the notifier) |
| 8001 | 0.0.0.0 | Alert notifier (container port 8000) |
| 8077 | 0.0.0.0 | Personal Feed API (uvicorn) |
| 7460 | 0.0.0.0 | ODA static design previews (oda-preview.service) [V] |
| 8081 | 0.0.0.0 | AI brain (llama-server), no API key |
| 8181 | 0.0.0.0 | Model queue (fortress-modelq.service); 0.0.0.0 so containers reach it via host.docker.internal [V] |
| 8190 | 127.0.0.1 | Agent gateway (fortress-agent-gateway.service) [V] |
| 8082 / 8443 | 0.0.0.0 | Plane proxy http / https |
| 8098 / 8099 | 127.0.0.1 | Virtual Self searxng / knowledge gateway |
| 8100 | 127.0.0.1 | ChromaDB (n8n stack) |
| 9010 / 9443 | 0.0.0.0 | Portainer |
| 9090 | 0.0.0.0 | Prometheus |
| 9100 | 0.0.0.0 | node-exporter |
| 9122 | 0.0.0.0 | vault-backup exporter |
| 11434 | * | Ollama |
| 18765 | 0.0.0.0 | Kindle dashboard PNG server (`kindle-dash.service`, token-protected; manual 30) |
| 19999 | 0.0.0.0 | unknown [U] |
| 53, 631, 2285, 4317, 8125, 17600, others | 127.0.0.1 | local system/editor services [U] |
When on: 8800 Jarvis (Mesh VPN (e.g. Tailscale) IP only), 9808 Jarvis metrics, 6333 Qdrant, 39081 LifePath, 39082 Vitalis, 6544 music, 9400 dcgm-exporter.

How containers reach host services (src: compose files) [V]:
- Through `host.docker.internal`: Virtual Self -> :8081 and :11434 (mapped to the bridge gateway 172.28.0.1); Moltbot, Vitalis, Cine-Immich -> :11434; Vitalis -> :8080; Personal Feed compose -> :8081; notifier -> Virtual Self API :8090.
- Jarvis uses host networking and reaches 127.0.0.1:8081.
- Therefore binding 8081 or 11434 to 127.0.0.1 would break these containers [I].

Firewall: `ufw status` = inactive (cmd: sudo ufw status) [V].

Mesh VPN (e.g. Tailscale) (cmd: mesh-vpn status) [V]: this node `homelab-host` 100.x.x.x. The owner's other devices include MacBooks and an Android phone; an older node `homelab-host` is offline for 347 days.

## Files and data
- Compose files define port mappings; the notifier mapping is `8001:8000` in `homelab/notifier/docker-compose.yml` [V].

## Commands
- READ: `ss -ltnp`, `docker ps --format '{{.Names}} {{.Ports}}'`, `mesh-vpn status`.
- MUTATES (owner only): firewall rules, Mesh VPN (e.g. Tailscale) settings, compose port changes.

## Depends on
Docker networking; Mesh VPN (e.g. Tailscale) daemon (`mesh-vpnd`, active).

## How to check it (read-only)
- DUM-E tool `ports` (live list with names), `containers name=<c>` (its ports).

## Known problems and fixes
- Doc mismatch: `library/00-meta/fortress-repository-root/AGENT_INTEGRATION.md` says the notifier is at `http://localhost:8000` from the host; in reality it is 8001 (8000 is Portainer) [V].
- LAN exposure with the firewall off. Owner decision 2026-10-29: leave it for now; if changed later, use a firewall that allows Docker bridges and Mesh VPN (e.g. Tailscale), not loopback binds [V].

## Logs
None specific.

## Rules for DUM-E here
- Never change ports, binds or firewall. Do not suggest rebinding 8081/11434 to 127.0.0.1 (it breaks containers).

## Open questions
- Owners of ports 19999, 18765, 443/64063 on the Mesh VPN (e.g. Tailscale) IP [U]: `sudo ss -ltnp` (owner) shows process names.
