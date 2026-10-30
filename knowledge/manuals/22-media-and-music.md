---
title: Media and music (Jellyfin + *arr, Navidrome, Spotspot, Spotify sync)
scope: The mediastack (Jellyfin, Sonarr, Radarr, Prowlarr, qBittorrent, optional Gluetun VPN) in ~/mediastack; the music service (Spotspot + Navidrome) in homelab/music-service, homelab/orchestration/stacks/music-service and homelab/spot-spot; the Spotify-to-Navidrome syncer in homelab/extensions and the helper scripts ~/spotifySync.sh and ~/enableSpotifySync.sh.
last_verified: 2026-10-29
sources: ~/mediastack/docker-compose.yml, homelab/orchestration/stacks/music-service/docker-compose.yml, homelab/music-service/docker-compose.yml, homelab/spot-spot/docker-compose.yml, homelab/extensions/spotify2navidromeSyncer.py (non-secret lines), homelab/extensions/syncer/*, ~/spotifySync.sh, ~/enableSpotifySync.sh, homelab/control/services.yaml:107-114,164-171, ~/.config/fortress-control/profiles/default.json, ~/.local/state/homelab/incidents.log, library/08-orchestration/guides/*, docker ps/inspect/logs, findmnt, lsblk, ss
---

# Media and music (Jellyfin + *arr, Navidrome, Spotspot, Spotify sync)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
This manual covers two separate home-entertainment stacks. Neither is running on 2026-10-29. [V] (cmd: docker ps -a)
The **mediastack** is a movie and TV server. Jellyfin plays media. Sonarr (TV), Radarr (movies) and Prowlarr (indexers) find releases. qBittorrent downloads them. An optional Gluetun VPN profile exists but is not configured. [V] (src: ~/mediastack/docker-compose.yml:14-134)
The **music service** is a Spotify downloader (Spotspot, based on spotDL) plus a music streaming server (Navidrome, Subsonic API). [V] (src: homelab/orchestration/stacks/music-service/docker-compose.yml:1-6)
A small Python tool copies a Spotify playlist into a Navidrome playlist by searching for songs already in the library. [V] (src: homelab/extensions/spotify2navidromeSyncer.py:84-300)

## How the owner refers to it
- Mediastack: "Media (Jellyfin)", "Media server", "movies, TV, downloads", "*arr stack". Homelab id `mediastack`. [V] (src: services.yaml:107-114; homelab/control/lib/fc_incident.sh:47)
- Music: "Music service", "Spotify downloader + music streaming", "Spotspot", "spot-spot", "Navidrome". Homelab id `music`. [V] (src: services.yaml:164-171; library/08-orchestration/guides/USAGE_GUIDE.md:34)
- Sync tool: "Spotify to Navidrome sync", `spotify-sync` (planned command name). [V] (src: ~/enableSpotifySync.sh:3,39)
- No bash aliases exist for these stacks. [V] (cmd: grep -n -i 'jellyfin|navidrome|spot|music|mediastack' ~/.bashrc → only cine/immich lines and `share-media`)
- Old docs say `fortress deploy music-service`. That command does not exist. [V] (src: library/08-orchestration/guides/QUICK_REFERENCE.md:38; DUM-E.md section 8.2)

## Components

### Mediastack
Compose file `~/mediastack/docker-compose.yml`, project `mediastack`, network `mediastack`. Log driver json-file, 10m x 3. All `restart: unless-stopped`. PUID/PGID 1000, TZ Asia/Kolkata. [V] (src: ~/mediastack/docker-compose.yml:1-12,136-138)
All five containers exited with code 0 on 2026-07-30 10:54 UTC (a clean stop). Images are from about six months ago. [V] (cmd: docker inspect --format State; docker images)
- `mediastack-jellyfin` — media player. Port `0.0.0.0:8096`. Config `./config/jellyfin`, media `./data`. [V] (src: compose:121-134)
- `mediastack-sonarr` — TV. Port `0.0.0.0:8989`. [V] (src: compose:106-119)
- `mediastack-radarr` — movies. Port `0.0.0.0:7878`. [V] (src: compose:91-104)
- `mediastack-prowlarr` — indexers. Port `0.0.0.0:9696`. [V] (src: compose:77-89)
- `mediastack-qbittorrent` — torrent client. Web UI `0.0.0.0:8080`, torrent port `6881` TCP and UDP. [V] (src: compose:41-58)
- `mediastack-gluetun` and `mediastack-qbittorrent-vpn` — only with compose profile `vpn`. Gluetun has `VPN_SERVICE_PROVIDER`, `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_ADDRESSES` set to the placeholder `REPLACE_ME`. Never created. [V] (src: compose:15-39,60-75; cmd: docker ps -a)
- Homelab marks it `default: true`, but it is NOT in the boot profile. [V] (src: services.yaml:107-114; ~/.config/fortress-control/profiles/default.json)
- Detected by container name `mediastack-jellyfin`. [V] (src: services.yaml:112)
- No ports of this stack are listening now. [V] (cmd: ss -ltnp)

### Music service
Three compose files define Spotspot. Only the first is registered in homelab. [V]
1. `~/homelab/orchestration/stacks/music-service/docker-compose.yml` — registered (`compose:` in services.yaml:168). Project `music-service`. [V]
   - `fortress-spotspot` — image `ghcr.io/mattblackonly/spotspot:latest`, port `6544`, music → `/data`, config → `/config`, `SPOTDL_THREADS=1`, outputs under `/data/singles`, `/data/albums`, `/data/playlists`. Networks `music-service-internal` and `fortress-network`. [V] (src: lines 11-34)
   - `fortress-navidrome` — image `deluan/navidrome:latest`, `network_mode: host`, port `4533` (`ND_PORT`), scan every 15 min, TLS off, Mesh VPN (e.g. Tailscale) certs mounted read-only from `/var/lib/mesh-vpn/certs`. [V] (src: lines 36-53)
   - Homelab detects it by port `6544`. `default: false`. [V] (src: services.yaml:164-171)
2. `~/homelab/music-service/docker-compose.yml` — the original. Same project name `music-service`. Container names `spotspot` and an unnamed navidrome. [V] (src: lines 1-43)
3. `~/homelab/spot-spot/docker-compose.yml` — Spotspot only. Project `spot-spot`, container name `spotspot`, `GENERATE_M3U_PLAYLIST=True`, uses `~` paths. [V] (src: lines 1-20)
- No Spotspot, Navidrome or Spotisub containers exist, and no images for them are pulled. [V] (cmd: docker ps -a; docker images)
- Ports 6544 and 4533 are not listening. [V] (cmd: ss -ltnp)

### Spotify-to-Navidrome syncer
- `~/homelab/extensions/spotify2navidromeSyncer.py` — interactive. Asks for a Spotify playlist link, reads tracks with spotipy (client-credentials), searches Navidrome (`/rest/search3`), creates a playlist (`/rest/createPlaylist`) and adds songs (`/rest/updatePlaylist`). It talks to `http://100.x.x.x:4533` (a Mesh VPN (e.g. Tailscale) address). [V] (src: lines 15, 84-375)
- `~/spotifySync.sh` — runs the syncer inside venv `~/music-sync-env`. [V] (src: ~/spotifySync.sh:4-24)
- `~/enableSpotifySync.sh` — one-time setup: makes the venv, `pip install spotipy requests`, then `sudo tee /usr/local/bin/spotify-sync` and `sudo chmod +x`. [V] (src: ~/enableSpotifySync.sh:8-36)
  - The venv exists. `/usr/local/bin/spotify-sync` does NOT exist. [V] (cmd: ls)
- `~/homelab/extensions/syncer/` — an installer `install_spotisub_docker.sh` and a generated `dependencies/docker-compose.yml` for Spotisub (`blastbeng/spotisub:latest`, port 5183, `restart: always`). Not deployed. [V] (src: syncer/dependencies/docker-compose.yml:1-23; cmd: docker ps -a)

### Schedules
- No cron job and no systemd unit for any of these. [V] (cmd: crontab -l; systemctl --user list-unit-files; systemctl list-unit-files)

## Files and data
- `~/mediastack/config/{gluetun,jellyfin,prowlarr,qbittorrent,qbittorrent-vpn,radarr,sonarr}` — app configs. [I] They hold app API keys and passwords in their own files; treat as SECRET. [V] (cmd: ls)
- `~/mediastack/secrets/` — **SECRET** (mode 700). Not referenced by the compose file. Never open. [V] (cmd: ls -la; src: compose)
- `~/mediastack/data` → symlink to `/mnt/movie-storage/mediastack-data`. **The link is dangling.** [V] (cmd: test -e → false)
  - `/mnt/movie-storage` is in fstab (UUID `e294d1fe-...`, ext4, `nofail`), but that disk is not attached and not mounted. [V] (src: /etc/fstab:19; cmd: findmnt; lsblk)
  - The empty mount point on the root disk contains a root-owned folder `vault-storage` (created 2026-09-10). [V] (cmd: ls -la /mnt/movie-storage) [I] Something wrote there while the disk was absent, so it sits on the 91%-full root disk.
- `~/homelab/music-service/music/` — downloaded music, 3.1G, with `albums`, `media`, `playlists`, `singles`. [V] (cmd: ls; du -sh)
- `~/homelab/music-service/navidrome-data/` — live Navidrome DB used by the registered stack (`navidrome.db`, 7.5 MB, 2026-03-25, root-owned). [V] (cmd: ls -la)
- `~/homelab/music-service/config/navidrome/` — older Navidrome DB (2025-09-18). [I] Stale copy. [V] (cmd: ls -la)
- `~/homelab/music-service/config/spotspot/config.toml` — spotDL settings (section `[spotdl]`). [V] (cmd: key names only)
- `~/homelab/music-service/homelab-host.your-tailnet.ts.net.key` — **SECRET** (TLS private key, root-only). `.crt` next to it is the certificate. [V] (cmd: ls -la)
- `~/homelab/music-service/ssl/key.pem` — **SECRET**. `ssl/cert.pem` certificate. [V] (cmd: ls)
- `~/homelab/extensions/spotify2navidromeSyncer.py` — **contains plaintext secrets** on lines 12, 13 (Spotify client id and secret) and 18 (Navidrome password). Never print those lines. [V] (cmd: grep with values redacted)
- `~/homelab/extensions/.cache` — **SECRET** (spotipy token cache, mode 600). [V] (cmd: ls -la)
- `~/homelab/extensions/syncer/dependencies/docker-compose.yml` — **SECRET**: plaintext Spotify and Subsonic credentials (lines 6-12). [V]
- `~/music-sync-env/` — Python venv for the syncer. [V] (cmd: ls)
- Grafana dashboard `homelab/monitoring/grafana/provisioning/dashboards/json/music-service-logs.json`. [V] (cmd: grep -rl)

## Commands
Read-only:
- `docker ps -a --filter name=mediastack` — mediastack state. READ.
- `docker ps -a | grep -E 'spotspot|navidrome'` — music state. READ.
- `findmnt /mnt/movie-storage` — is the media disk mounted. READ.
- `ss -ltnp | grep -E ':(8096|8989|7878|9696|8080|6544|4533)\b'` — ports. READ.

Mutating:
- `cd ~/mediastack && docker compose up -d` — start mediastack (also `fortress start mediastack`). MUTATES. [I] Unsafe while the data link is dangling (see Known problems 1). (src: homelab/control/lib/actions.sh:38-45)
- `cd ~/mediastack && docker compose --profile vpn up -d` — would start Gluetun with `REPLACE_ME` values and clash with qBittorrent on 8080/6881. MUTATES. [I] Will fail. (src: compose:29-35,51-54)
- `cd ~/mediastack && docker compose stop` (= `fortress stop mediastack`). MUTATES. (src: homelab/control/lib/actions.sh:47-50)
- `cd ~/homelab/orchestration/stacks/music-service && docker compose up -d` (= `fortress start music`) — pulls images and starts Spotspot and Navidrome. MUTATES. (src: services.yaml:164-171)
- `docker compose stop` in the same folder (= `fortress stop music`). MUTATES.
- `cd ~/homelab/music-service && docker compose up -d` or `cd ~/homelab/spot-spot && docker compose up -d` — old duplicate stacks. MUTATES. [I] They use the same port 6544 and, for the old music file, the same project name, so they conflict with the registered stack.
- Downloads in the Spotspot web UI (port 6544) — write MP3 files into `music/`. MUTATES. [I]
- `bash ~/spotifySync.sh` — interactive; creates a Navidrome playlist and adds songs. MUTATES (Navidrome playlists). (src: spotify2navidromeSyncer.py:182-300)
- `bash ~/enableSpotifySync.sh` — creates venv, installs packages, writes `/usr/local/bin/spotify-sync` with sudo. MUTATES. Uses sudo. (src: ~/enableSpotifySync.sh:8-36)
- `bash homelab/extensions/syncer/install_spotisub_docker.sh` — asks for credentials and appends them in plain text to a new `docker-compose.yml`. MUTATES (writes secrets to disk). (src: install_spotisub_docker.sh:1-100)

Deleting:
- `docker compose down` in `~/mediastack` or a music folder — removes containers. DELETES containers.
- `docker compose down -v` — also removes volumes. DELETES. [I] All data here are bind mounts, so `-v` removes little, but treat it as destructive.
- Removing items in Sonarr/Radarr with "delete files", or deleting torrents with data in qBittorrent — deletes media files in `./data`. DELETES. [I]
- Navidrome playlist deletion in its UI or API — DELETES playlists. [I]
- `install_spotisub_docker.sh` refuses a non-empty install dir, so it does not overwrite files. [V] (src: lines 3-14)

## Depends on
- GPU: no. AI brain :8081: no. Ollama :11434: no. Notifier: no. [V] (src: compose files)
- Mediastack needs the disk mounted at `/mnt/movie-storage` (currently missing). [V]
- Mediastack uses network `mediastack` (created by the stack). [V] (src: compose:136-138)
- Music service needs external network `fortress-network`, Mesh VPN (e.g. Tailscale) certs at `/var/lib/mesh-vpn/certs`, and internet access to pull `:latest` images and to download from Spotify/YouTube. [V] (src: stacks/music-service/docker-compose.yml:43,59-61) [I] internet need.
- The syncer needs Navidrome on `100.x.x.x:4533` (Mesh VPN (e.g. Tailscale)), the Spotify Web API, and the venv. [V] (src: spotify2navidromeSyncer.py:15; ~/spotifySync.sh:5)

## How to check it (read-only)
- DUM-E tools: `services` (`mediastack`, `music`), `containers`, `ports`, `disk_memory` (is `/mnt/movie-storage` mounted; root disk usage), `incidents` (source `mediastack`), `health`, `log_tail`, `manual`, `graph`.
- Owner commands:
  - `docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep -E 'mediastack|spotspot|navidrome'`
  - `findmnt /mnt/movie-storage; ls -la ~/mediastack/data`
  - `ss -ltnp | grep -E ':(8096|6544|4533)\b'`
  - `tail -5 ~/.local/state/homelab/incidents.log`
- Healthy mediastack looks like: `/mnt/movie-storage` mounted from its own disk, five `mediastack-*` containers Up, Jellyfin on 8096.
- Healthy music looks like: `fortress-spotspot` Up on 6544, `fortress-navidrome` on 4533.

## Known problems and fixes
1. **Media disk missing; data link dangling.** [V] + [I]
   - `/mnt/movie-storage` is not mounted and its disk is not attached. `~/mediastack/data` points into it. (cmd: findmnt; lsblk; test -e)
   - [I] If mediastack starts now, Docker resolves the link and creates `/mnt/movie-storage/mediastack-data` on the root disk (91% full). qBittorrent downloads would then fill the root disk.
   - Fix: DUM-E must not start mediastack. The owner attaches and mounts the disk first (`sudo mount /mnt/movie-storage`), checks `findmnt`, then starts the stack. DUM-E has no action for mounting.
2. **Hourly "Media (Jellyfin): not running" alerts.** [V]
   - 737 incidents with source `mediastack` since 2026-09-29, often two per hour (duplicates). Cause: `services.yaml` says `default: true`, but the boot profile does not include it and the stack is stopped on purpose. (src: ~/.local/state/homelab/incidents.log; services.yaml:114; DUM-E.md finding F6)
   - Fix (owner): set `default: false` for `mediastack` in `services.yaml`, or add it to the profile once the disk is back. DUM-E has no action for this.
3. **Plaintext secrets in the syncer files.** [V]
   - `spotify2navidromeSyncer.py` lines 12, 13, 18 and `syncer/dependencies/docker-compose.yml` lines 6-12 hold real credentials. (cmd: grep with redaction)
   - Fix (owner): move them to environment variables or a mode-600 file, and rotate the Spotify client secret and the Navidrome password.
4. **Three Spotspot definitions.** [V] + [I]
   - Two use container name `spotspot`; all use port 6544; two share project name `music-service`. Starting the wrong one blocks the registered one. Use only `orchestration/stacks/music-service`. (src: the three compose files)
5. **All music and media images use `:latest`.** [V] + [I]
   - A fresh start pulls whatever is newest. Behaviour can change without warning. (src: compose files)
6. **Mediastack ports are open on all interfaces.** [V]
   - 8096, 8989, 7878, 9696, 8080, 6881 bind `0.0.0.0`. With the firewall off (DUM-E.md F9), the *arr admin UIs would be reachable on the LAN. (src: ~/mediastack/docker-compose.yml)
7. **Port 8080 clash inside the VPN profile.** [V] + [I]
   - Gluetun and plain qBittorrent both publish 8080 and 6881. Only one can run. (src: compose:32-35,51-54)
8. **`spotify-sync` command was never installed.** [V]
   - `/usr/local/bin/spotify-sync` is missing. Use `bash ~/spotifySync.sh`. (cmd: ls)
9. **Syncer cannot work while Navidrome is down.** [I]
   - It pings `/rest/ping` first and Navidrome is not running. (src: spotify2navidromeSyncer.py:328-344)
10. **Navidrome TLS is off although certs are mounted.** [V]
    - `ND_TLSENABLED=false`. Access is plain HTTP on 4533. (src: stacks/music-service/docker-compose.yml:43-48)

## Logs
- `docker logs --tail 50 mediastack-jellyfin` (and `-sonarr`, `-radarr`, `-prowlarr`, `-qbittorrent`). Last lines are a clean shutdown on 2026-07-30. [V] (cmd: docker logs --tail 4 mediastack-jellyfin)
- App logs also live under `~/mediastack/config/<app>/` [I] (linuxserver images keep logs in `/config`).
- Music containers have no logs because they do not exist. Grafana "music-service-logs" dashboard exists for when they run. [V]
- The syncer prints requests and responses to the terminal (`log_request`, `log_response`). [V] (src: spotify2navidromeSyncer.py:62-83) [I] Those prints may include the auth token and salt; do not paste them anywhere.
- Homelab incidents: `~/.local/state/homelab/incidents.log`, source `mediastack`. [V]

## Rules for DUM-E here
- Never open `~/mediastack/secrets/`, `~/mediastack/config/*` app files, `*.key`, `ssl/key.pem`, `extensions/.cache`, or the secret lines of the syncer files. Never print any token, client secret or password.
- Do not approve `service_start mediastack` while `/mnt/movie-storage` is not mounted (Known problem 1).
- `service_start music` and `service_stop music` are allowed with approval. Warn that the first start pulls images from the internet.
- Never run `enableSpotifySync.sh`, `spotifySync.sh`, `install_spotisub_docker.sh`, or the duplicate compose files.
- DELETES operations that exist here (never run them; only name them):
  - `docker compose down` / `down -v` in `~/mediastack`, `homelab/orchestration/stacks/music-service`, `homelab/music-service`, `homelab/spot-spot`
  - deleting media through Sonarr, Radarr or qBittorrent ("delete files")
  - deleting Navidrome playlists

## Open questions
- [U] Where is the movie disk (UUID `e294d1fe-d023-4bcb-8f53-ae25e5ba9a85`)? Is it unplugged or failed? Settle: owner plugs it in and runs `lsblk -o NAME,UUID,SIZE,MOUNTPOINT`.
- [U] What wrote `/mnt/movie-storage/vault-storage` on 2026-09-10, and how big is it? Settle: owner runs `sudo du -sh /mnt/movie-storage/vault-storage` and checks the vault-storage compose file.
- [U] Is the mediastack meant to come back, or should it be retired? Settle: ask the owner; then fix `default:` in `services.yaml`.
- [U] What is in `~/mediastack/secrets/`? DUM-E must not look. Settle: owner checks by hand.
- [U] Is the music service still wanted? It has no images pulled. Settle: ask the owner.
- [U] Does the Mesh VPN (e.g. Tailscale) address `100.x.x.x` still belong to this host? Settle: owner runs `mesh-vpn ip -4`.
