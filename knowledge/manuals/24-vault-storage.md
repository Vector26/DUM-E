---
title: Vault storage (MinIO inbound backup target)
scope: The vault-storage compose stack (vault-minio, vault-browser), its data path, ports, scripts, secrets and known problems.
last_verified: 2026-10-29
sources: homelab/vault-storage/{docker-compose.yml,.env.example,.gitignore,CONTEXT.md,scripts/*}, homelab/library/12-vault-storage/{README.md,WEB_UI.md,AGENT_INTEGRATION.md}, homelab/control/services.yaml, docker ps, docker inspect --format, docker port, docker logs --tail, ss -ltnp, df, lsblk, findmnt, /etc/fstab, journalctl -u docker
---

# Vault storage (MinIO inbound backup target)

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Vault storage is a self-hosted S3 store (MinIO) on the homelab. Other machines, mainly the owner's MacBook, push encrypted backups into it over Mesh VPN (e.g. Tailscale). [V] (src: homelab/vault-storage/CONTEXT.md:13-20)
The Mac encrypts files with rclone crypt before upload, so the server only sees scrambled names and content. [V] (src: homelab/vault-storage/CONTEXT.md:19,97)
An optional web page (`vault-browser`) decrypts on the fly so the owner can browse and stream the Mac "Journals" backup. [V] (src: homelab/vault-storage/CONTEXT.md:20,266-298)
It is the opposite direction of vault-backup: vault-backup sends server data OUT to Google Drive (manual 23). [V] (src: homelab/vault-storage/CONTEXT.md:9; homelab/control/services.yaml:100)
Right now it is not usable from the network: no ports are published, and the data disk is not mounted. See Known problems. [V]

## How the owner refers to it
- "Vault", "vault storage", "Vault storage (MinIO)". Homelab Control id `vault`. [V] (src: homelab/control/services.yaml:98-105)
- Telegram label "Vault storage". [V] (src: homelab/control/lib/fc_incident.sh:35)
- "Journals backup", "Mac sync", "web UI", "browse backups". [V] (src: homelab/vault-storage/CONTEXT.md:192,266)
- Do not confuse with "vault-backup" (Google Drive, manual 23) or Plane's MinIO `plane-plane-minio-1`. [V] (src: homelab/vault-storage/CONTEXT.md:22)

## Components
- Compose file: `~/homelab/vault-storage/docker-compose.yml`, project name `vault-storage`. [V] (src: docker-compose.yml:15; cmd: docker compose ls)
- Network: external `fortress-network`. [V] (src: docker-compose.yml:85-88)
- Container `vault-minio`: [V] (src: docker-compose.yml:18-44)
  - Image `minio/minio:RELEASE.2025-04-22T22-12-26Z` (pinned).
  - Command `server /data --console-address ":9001"`.
  - Restart policy `unless-stopped`. Memory limit 1 GB. `no-new-privileges`.
  - Planned ports: S3 API `${TAILSCALE_IP}:${VAULT_API_PORT}` → 9000 (example 100.x.x.x:9092); console `127.0.0.1:${VAULT_CONSOLE_PORT}` → 9001 (example 9093). [V] (src: docker-compose.yml:28-32; .env.example:13,17-18)
  - Health check: `curl -sf http://127.0.0.1:9000/minio/health/live` every 30 s, 3 retries. [V] (src: docker-compose.yml:39-44)
  - State now: running, healthy, started 2026-10-29 15:36 UTC (21:06 IST), restart count 0, created 2026-05-30. [V] (cmd: docker inspect --format State/RestartCount/Created)
  - Mount now: `/mnt/movie-storage/vault-storage/data` → `/data`. [V] (cmd: docker inspect --format Mounts)
  - Inside Docker the service name is `minio` (port 9000), not `vault-minio`. [V] (src: CONTEXT.md:142)
- Container `vault-browser`: [V] (src: docker-compose.yml:48-83)
  - Image `rclone/rclone:1.69.0`. Compose profile `browser` (only starts with `--profile browser`).
  - Runs `rclone serve http vault-crypt-macbook: --read-only --vfs-cache-mode minimal` with basic auth from `VAULT_BROWSER_USER` / `VAULT_BROWSER_PASS`.
  - Planned port `${TAILSCALE_IP}:${VAULT_BROWSER_PORT}` → 8080 (example 9094).
  - Mount now: `~/.config/rclone` → `/config/rclone` (read-only). [V] (cmd: docker inspect --format Mounts)
  - Waits for `minio` to be healthy. Memory limit 512 MB. No health check.
  - State now: running since 2026-10-29 15:36 UTC, restart count 0, created 2026-05-30. [V] (cmd: docker inspect --format)
- Published ports now: none. `docker ps` shows an empty PORTS column for both containers, `docker port` prints nothing, `ss -ltnp` shows nothing on 9092, 9093 or 9094, and `curl http://100.x.x.x:9092/minio/health/live` fails. [V] (cmd: docker ps; docker port vault-minio; ss -ltnp; curl)
- Mesh VPN (e.g. Tailscale) address of this host: `100.x.x.x` on `mesh-vpn0`. [V] (cmd: ip -4 addr show mesh-vpn0)
- No systemd unit, no cron job, no host script runs for vault-storage. [V] (cmd: crontab -l; systemctl list-units --all)
- Homelab Control entry: `kind: compose`, `detect_container: vault-minio`, `default: true`. [V] (src: homelab/control/services.yaml:98-105)

## Files and data
- `~/homelab/vault-storage/` — stack folder. [V]
- `docker-compose.yml` — the stack. [V]
- `.env` — SECRET (mode 600). Holds `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `VAULT_BROWSER_USER`, `VAULT_BROWSER_PASS`, paths and ports. Never open. [V] (cmd: ls -la; src: .env.example:4-17)
- `.env.example` — template, no real secrets. Variables: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `VAULT_BUCKET` (vault-backups), `VAULT_AGENT_USER` (vault-agent), `VAULT_DATA_DIR` (/mnt/movie-storage/vault-storage/data), `TAILSCALE_IP` (100.x.x.x), `VAULT_API_PORT` (9092), `VAULT_CONSOLE_PORT` (9093), `VAULT_BROWSER_PORT` (9094), `VAULT_BROWSER_USER`, `VAULT_BROWSER_PASS`, `RCLONE_CONFIG_DIR` (${HOME}/.config/rclone), `VAULT_MAC_PREFIX` (macbook-hritik), `VAULT_JOURNALS_SUBPATH` (journals). [V] (src: .env.example:1-29)
- The real `.env` values were not read. The mounts confirm `VAULT_DATA_DIR=/mnt/movie-storage/vault-storage/data` and `RCLONE_CONFIG_DIR=~/.config/rclone`. [V] (cmd: docker inspect --format Mounts) Ports and IP in the real file are [U].
- `CONTEXT.md` — the main, long guide for humans and AI. [V]
- `.gitignore` — ignores `.env`, `data/`, `*.log`, `scripts/vault-agent-policy.json`. [V]
- `scripts/init-bucket.sh`, `scripts/setup-server-rclone.sh`, `scripts/install-crypt-password.sh` — see Commands. [V]
- `scripts/vault-agent-policy.json` — generated IAM policy: list the bucket, get/put/delete objects in `vault-backups/*`. Not secret. [V]
- Data path: `/mnt/movie-storage/vault-storage/data` (bucket folder would be `vault-backups/macbook-hritik/journals/`). [V] (src: CONTEXT.md:85-95)
  - Now it holds only `.minio.sys` and uses 120 KB. There is no `vault-backups` bucket folder. [V] (cmd: ls -A; du -sh)
  - It sits on the root filesystem `/dev/nvme1n1p2` (234 GB, 91 % full), because `/mnt/movie-storage` is not mounted. [V] (cmd: findmnt -T /mnt/movie-storage; df -h)
  - Content, when present, is PRIVATE (owner's journals), encrypted with rclone crypt. [V] (src: CONTEXT.md:192-197)
- Secret files outside the repo, named only (from the docs; existence not checked): [V] (src: CONTEXT.md:101-108)
  - `~/.config/vault-storage/agent-credentials.env` — SECRET (S3 keys for the `vault-agent` user).
  - `~/.config/vault-storage/crypt-password` — SECRET (Mac crypt passphrase; needed to decrypt).
  - `~/.config/rclone/rclone.conf` — SECRET (protected folder). It is mounted into `vault-browser`. [V] (cmd: docker inspect --format Mounts)
- On the Mac (not on this server): `~/.local/bin/vault-sync-journals.sh`, `~/.local/bin/vault-sync-journals-setup.sh`, launchd job `com.fortress.vault-journals-sync` every 6 h. [V] (src: CONTEXT.md:110-118,243-252) Not verifiable from here [U].
- The MinIO data folder is not in the vault-backup path list, so it has no off-site copy. [V] (src: homelab/vault-backup/config/paths.tsv)

## Commands
READ:
- `docker ps --filter name=vault-` — state and ports. [V]
- `docker port vault-minio` and `docker port vault-browser` — published ports (empty now). [V]
- `docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' vault-minio` — health. [V]
- `docker logs --tail 50 vault-minio` and `docker logs --tail 50 vault-browser`. Do not copy secrets. [V]
- `curl -sf http://100.x.x.x:9092/minio/health/live && echo OK` — S3 API health over Mesh VPN (e.g. Tailscale) (fails now). [V] (src: CONTEXT.md:139)
- `ss -ltnp | grep -E ':909[234] '` — listening ports. [V]
- `findmnt /mnt/movie-storage` and `df -h /mnt/movie-storage` — is the data disk mounted. [V]
- `du -sh /mnt/movie-storage/vault-storage/data` — data size. [V] (src: CONTEXT.md:356)

MUTATES (owner only unless noted):
- `fortress start vault` → `docker compose up -d` in the stack folder. Starts `vault-minio` only, because `vault-browser` is behind a profile. DUM-E action `service_start vault`. MUTATES. [V] (src: homelab/control/lib/actions.sh:38-45) [I] for the profile effect
- `fortress stop vault` → `docker compose stop`. Stops `vault-minio`; `vault-browser` is likely left running because of its profile. DUM-E action `service_stop vault`. MUTATES (not deletion). [V] (src: homelab/control/lib/actions.sh:47-50) [I] for the profile effect
- `cd ~/homelab/vault-storage && docker compose --profile browser up -d vault-browser` — start the web UI. MUTATES. [V] (src: CONTEXT.md:290)
- `docker compose --profile browser stop vault-browser` — stop the web UI. MUTATES. [V] (src: CONTEXT.md:304)
- `docker compose restart minio` — restart storage only. MUTATES. [V] (src: CONTEXT.md:353)
- `./scripts/install-crypt-password.sh` — writes `~/.config/vault-storage/crypt-password`; asks before overwriting. MUTATES, DELETES (overwrite) if you answer y. [V] (src: scripts/install-crypt-password.sh:4-20)

DELETES (owner only):
- `./scripts/init-bucket.sh` — creates the bucket, writes `vault-agent-policy.json`, creates the IAM policy, and if user `vault-agent` exists it runs `mc admin user remove` and re-adds it with a new secret. It then overwrites `~/.config/vault-storage/agent-credentials.env`. Every Mac using the old key stops working until updated. DELETES (user, credentials file). Uses `minio/mc:latest`. [V] (src: scripts/init-bucket.sh:60-115)
- `./scripts/setup-server-rclone.sh` — rewrites `~/.config/rclone/rclone.conf` from scratch with two remotes (`vault-s3`, `vault-crypt-macbook`). Any other remote in that file is lost. DELETES (overwrite). Uses `rclone/rclone:latest`. [V] (src: scripts/setup-server-rclone.sh:9,33-52)
- `docker compose down` in the stack folder — removes the containers (data folder stays). DELETES (containers). [I]
- On the Mac: `rclone sync … --delete-after` mirrors deletions to the server. A file deleted on the Mac is deleted in the vault. DELETES. [V] (src: CONTEXT.md:53,374; library/12-vault-storage/AGENT_INTEGRATION.md:49-69)
- `rclone sync vault-crypt:/path /local/dest` (restore) deletes local files that are not in the backup. DELETES. [V] (src: library/12-vault-storage/AGENT_INTEGRATION.md:112-116) [I] for the effect

## Depends on
- Mesh VPN (e.g. Tailscale) must be up and hold 100.x.x.x before Docker publishes the ports. [V] (src: docker-compose.yml:30,74) [I] for the boot order
- The data disk at `/mnt/movie-storage` (fstab UUID `e294d1fe-…`, `nofail`). It is not present now. [V] (src: /etc/fstab:19; cmd: lsblk; blkid)
- Docker network `fortress-network` (external, must exist). [V] (src: docker-compose.yml:85-88; cmd: docker network ls)
- `vault-browser` needs `~/.config/rclone/rclone.conf` with a `vault-crypt-macbook` remote and MinIO healthy. [V] (src: docker-compose.yml:57,72,75-77)
- No GPU, no AI brain (:8081), no Ollama, no notifier. [V] (no references in compose or scripts)

## How to check it (read-only)
- DUM-E tool `containers` → are `vault-minio` and `vault-browser` running, and is `vault-minio` healthy.
- DUM-E tool `ports` → are 9092/9093/9094 listening (they should be; they are not now).
- DUM-E tool `disk_memory` → is `/mnt/movie-storage` a separate mount, or the root disk.
- DUM-E tool `services` → Homelab Control id `vault`. Note: it checks only the container name, so it says "running" even with no ports. [I] (src: homelab/control/services.yaml:103)
- DUM-E tool `log_tail` is not wired for this stack; use `docker logs --tail 50 vault-minio`.
- Owner, read-only: `docker port vault-minio`; `curl -sf http://100.x.x.x:9092/minio/health/live && echo OK`; `findmnt /mnt/movie-storage`.

## Known problems and fixes
1. No ports are published. The Mac cannot sync and the web UI is unreachable.
   - Evidence: empty `docker port` output; nothing listening on 9092/9093/9094; health curl fails. [V] (cmd: docker port; ss -ltnp; curl)
   - Likely cause: at boot (21:06:09) Docker started containers before the Mesh VPN (e.g. Tailscale) address existed. Docker logged "failed to bind host port 100.x.x.x:7700/tcp: cannot assign requested address" for another container at the same second. [V] (cmd: journalctl -u docker -b) [I] that the same happened to vault-minio; no line names vault-minio, and the 127.0.0.1:9093 console is missing too, so the cause is not fully proven [U].
   - Fix: the owner recreates the containers after Mesh VPN (e.g. Tailscale) is up: `cd ~/homelab/vault-storage && docker compose --profile browser up -d --force-recreate`, then checks `docker port vault-minio`. DUM-E has no action for this; `service_start vault` does nothing because the container already runs. [I]
2. The data disk is missing. MinIO writes to the root disk.
   - Evidence: `/etc/fstab` line 19 mounts UUID `e294d1fe-d023-4bcb-8f53-ae25e5ba9a85` on `/mnt/movie-storage` with `nofail`. No device with that UUID exists. `/mnt/movie-storage` resolves to `/` (`/dev/nvme1n1p2`, 91 % full). The folder `/mnt/movie-storage/vault-storage` is root-owned, created 2026-09-10. [V] (cmd: findmnt -T; lsblk; blkid; ls -la)
   - Effect: the bucket is empty (only `.minio.sys`, 120 KB). Any earlier Journals backup is not visible here. If syncing resumes, it fills the nearly full root disk. [V] for empty, [I] for the rest
   - Fix: the owner finds and mounts the right disk (a 931.5 GB disk `sdc` with no recognised filesystem exists; whether it is that disk is [U]), then recreates the stack. DUM-E has no action for this.
3. The web UI password is visible in the process list.
   - Evidence: `ps` shows the root process `rclone serve http vault-crypt-macbook: … --user … --pass <value>`. Any local user can read it. [V] (cmd: ps -eo args; src: docker-compose.yml:62-65) The value is not copied here.
   - Fix: owner moves the password to an environment variable or `--htpasswd` file and changes it. [I]
4. Docs list ports and IP as facts, but the real `.env` was not read. If the ports differ, the docs are wrong. [U] Settle: `docker compose config --services` is safe, but `docker compose config` prints secrets; the owner should check `.env` personally.
5. `scripts/setup-server-rclone.sh` overwrites the whole `~/.config/rclone/rclone.conf`. Other rclone remotes in that file (if any) would be lost. [V] (src: scripts/setup-server-rclone.sh:33-52) Whether other remotes exist is [U] (protected folder).
6. Images `minio/mc:latest` and `rclone/rclone:latest` are pulled unpinned by the scripts. [V] (src: scripts/init-bucket.sh:10; scripts/setup-server-rclone.sh:31)

## Logs
- No log files on disk. MinIO and rclone log to Docker. [V] (src: docker-compose.yml)
- `docker logs --tail 50 vault-minio` — shows start banners ("API: http://127.0.0.1:9000", "WebUI: http://127.0.0.1:9001") and "Exiting on signal: TERMINATED" at each stop. [V]
- `docker logs --tail 50 vault-browser` — was empty of errors at check time. [V]
- Promtail ships all container logs to Loki (manual 25), so these appear in Grafana too. [V] (src: homelab/monitoring/promtail/promtail.yml:12-29)
- `journalctl -u docker -b | grep -i "allocate port"` — port binding failures at boot. [V]
- No incidents in `incidents.log` come from source `vault`. [V] (src: incidents.log, aggregated)

## Rules for DUM-E here
- Never open `vault-storage/.env`, `~/.config/vault-storage/*`, or `~/.config/rclone/rclone.conf`. Never print the browser password, even though it shows in `ps`.
- Never run `init-bucket.sh`, `setup-server-rclone.sh`, `install-crypt-password.sh`, `mc`, or `rclone` here.
- Never touch files under `/mnt/movie-storage/vault-storage/data`. They are MinIO's internal store.
- Never run `docker compose down`, `restart`, `--force-recreate` or `rm` here. Recommend them to the owner instead.
- `service_start vault` and `service_stop vault` are allowed with confirmation. Say that `vault-browser` is not covered by them.
- DELETES operations that exist here: `init-bucket.sh` (removes and re-creates `vault-agent`, overwrites the credentials file); `setup-server-rclone.sh` (overwrites `rclone.conf`); `install-crypt-password.sh` (overwrites the passphrase file on "y"); `docker compose down`; the Mac's `rclone sync --delete-after`; `rclone sync` restore into a non-empty folder.

## Open questions
- Which disk should be at `/mnt/movie-storage`, and where are the earlier Journals backups? Settle: the owner checks `lsblk -f` and the disk labels. [U]
- Exact cause of the missing port bindings. Settle: the owner runs `journalctl -u docker -b | grep -iE "vault|allocate"` right after the next boot. [U]
- Real values of `TAILSCALE_IP` and the ports in `.env`. Settle: owner reads `.env` personally. [U]
- Does the Mac sync job still run, and what does it log? Settle: on the Mac, `~/.local/state/vault-journals-sync.log`. [U] (src: CONTEXT.md:250)
- Do `~/.config/vault-storage/agent-credentials.env` and `crypt-password` exist on the server? Settle: owner runs `ls ~/.config/vault-storage`. [U]
