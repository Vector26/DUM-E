---
title: Wi-Fi and Network Guard
scope: the Wi-Fi guard cron (wifi-safe-switch.sh), the emergency-home script, the disabled LAN scan, wifi-scan-reports, netwatch, Mesh VPN (e.g. Tailscale), the traffic analysis scripts, and the Cloudflare quick-tunnel aliases
last_verified: 2026-10-29
sources: ~/bin/wifi-safe-switch.sh, ~/bin/wifi-emergency-home.sh, ~/bin/wifi-safe-lan-scan.sh.DISABLED, ~/wifi-scan-reports/, homelab/netwatch/{wifi_manager.py,cron_setup.py,readme.md}, ~/analyze_internet.py, ~/analyze_network.py, ~/.local/bin/proxy-share.sh, ~/.bashrc:455-461, crontab -l, mesh-vpn status, ip -br link, nmcli connection show --active
---

# Wi-Fi and Network Guard

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
The homelab has no wired link up. It reaches the network over Wi-Fi on `wlp13s0`. The Ethernet port `enp12s0` is DOWN (NO-CARRIER). [V] (cmd: ip -br link)
A cron job runs `wifi-safe-switch.sh guard` every 10 minutes. It checks that a Mesh VPN (e.g. Tailscale) peer answers. If not, it tries other saved Wi-Fi profiles and then falls back to "Wayne Manor 5G". [V] (src: crontab -l; wifi-safe-switch.sh:265-286)
The guard exists so the owner keeps remote access over Mesh VPN (e.g. Tailscale). [I] (src: wifi-safe-switch.sh:2)
Other parts: an older Python Wi-Fi manager (netwatch, not scheduled), a disabled LAN scan script, two traffic-analysis helpers, and Cloudflare quick tunnels to share a local URL publicly. [V] (src: files listed in sources)

## How the owner refers to it
- "wifi guard", "wifi-mesh-vpn-guard" — the cron tag. [V] (src: crontab -l)
- `wifi-safe-switch.sh` with modes `guard`, `home`, `switch "<conn>"`, `scan-all`, `scan-remaining`, `detach …`. [V] (src: wifi-safe-switch.sh:341-353)
- `wifi-emergency-home.sh` — "go back home to 5G". [V] (src: wifi-emergency-home.sh:2)
- `expose`, `share-media` — start a Cloudflare quick tunnel (`~/.local/bin/proxy-share.sh`). [V] (src: ~/.bashrc:459-460)
- `share-stop-all` — `pkill -f cloudflared; screen -wipe`. [V] (src: ~/.bashrc:461)
- "netwatch" — `homelab/netwatch`, library shelf `07-netwatch`. [V] (src: homelab/netwatch/readme.md)
- Wi-Fi profile names in the scripts: "Wayne Manor 5G" (fallback), "Wayne Manor 4G", "Airtel_Batcave". [V] (src: wifi-safe-switch.sh:9,15)

## Components
- Cron `*/10 * * * * ~/bin/wifi-safe-switch.sh guard >> ~/wifi-scan-reports/wifi-guard-cron.log 2>&1 # wifi-mesh-vpn-guard`. [V] (cmd: crontab -l)
- `wifi-safe-switch.sh` — bash, `set -euo pipefail`, 359 lines. Uses `sudo -n nmcli connection up` and `sudo -n nmcli connection modify`. [V] (src: wifi-safe-switch.sh:3,24-26,47-56)
- Defaults (overridable from the config file): `WIFI_DEV=wlp13s0`, `FALLBACK_CONN="Wayne Manor 5G"`, `TAILSCALE_CHECK_IP=100.126.168.42` (the owner's MacBook node `hritiks-macbook-pro-1`), `TAILSCALE_CHECK_TIMEOUT_SEC=8`, `CONNECT_WAIT_SEC=25`, `LOG_DIR=~/wifi-scan-reports`, `LOCK_FILE=/tmp/wifi-safe-switch.lock`, `WIFI_CANDIDATES="Wayne Manor 5G|Wayne Manor 4G|Airtel_Batcave"`. [V] (src: wifi-safe-switch.sh:5-16; mesh-vpn status)
- Health check inside the script: `mesh-vpn ping -c 1 --timeout 8s <ip>`; plain `ping` if mesh-vpn is missing. [V] (src: wifi-safe-switch.sh:34-41)
- Lock: `flock -n` on `/tmp/wifi-safe-switch.lock`. A second run exits 0 with "Another wifi-safe-switch run is active". [V] (src: wifi-safe-switch.sh:256-263)
- `wifi-emergency-home.sh` — one line: `exec ~/bin/wifi-safe-switch.sh home`. [V] (src: wifi-emergency-home.sh:1-2)
- `wifi-safe-lan-scan.sh.DISABLED` — not executable (mode 664). Older switch+scan script. Not in cron. [V] (cmd: ls -la ~/bin)
- `homelab/netwatch/wifi_manager.py` — Python Wi-Fi chooser. Checks internet (`curl -I https://www.google.com`), Mesh VPN (e.g. Tailscale) peer RTT, Cloudflare download speed, then may run `nmcli device wifi connect <ssid>`. [V] (src: wifi_manager.py:13-29,40-125; lines 274-280 connect_to)
- `homelab/netwatch/cron_setup.py` — installs or removes its own cron line tagged `# NETWATCH_WIFI_MANAGER` (default `*/15`). That tag is not in the current crontab, so netwatch is not scheduled. [V] (src: cron_setup.py:8-9; cmd: crontab -l)
- Mesh VPN (e.g. Tailscale) — version 1.102.2. This host is node `homelab-host` (100.x.x.x). [V] (cmd: mesh-vpn status; mesh-vpn version)
- The owner's other Mesh VPN (e.g. Tailscale) nodes (names only): `homelab-host` (offline, older node of this host [I]), `hritiks-macbook-pro-1` (active, guard target), `hritiks-macbook-pro`, `hritiks-s25`, `iphone-13`, `macbook-pro`, `samsung-sm-s931b`, `tcl-smart-tv-pro`. [V] (cmd: mesh-vpn status)
- Tailnet DNS suffix `your-tailnet.ts.net`. [V] (src: personal-feed/.env.example:31 `homelab-host.your-tailnet.ts.net`)
- Mesh VPN (e.g. Tailscale) also binds a port on the Mesh VPN (e.g. Tailscale) IP (`64063` per DUM-E.md). [V] (src: DUM-E.md:428)
- Cloudflare quick tunnel — `cloudflared` at `/usr/local/bin/cloudflared`, run inside a detached `screen` session named `expose-<16 hex>`. No cloudflared process was running and no `cloudflared.service` exists. [V] (cmd: grep /proc/*/comm; systemctl cat cloudflared.service → not found)
- Active network connections now: Wi-Fi "Wayne Manor 5G" on `wlp13s0`, `mesh-vpn0`, many Docker bridges. LAN address `192.168.1.41/24`. [V] (cmd: nmcli -t connection show --active; ip -4 -br addr show wlp13s0)
- Ports: none of these scripts listen on a port. A running tunnel makes the target service public through Cloudflare. [V] (src: proxy-share.sh:56)

## Files and data
- `~/bin/wifi-safe-switch.sh` — main guard. [V]
- `~/.config/wifi-switch.conf` — SECRET. Sourced by the guard (`source "$CONF"`). May hold Wi-Fi passwords (the script reads `AIRTEL_PSK` from the environment). Not opened. Mode 664. [V] name and mode (cmd: ls -la; stat); contents [U]
- `~/bin/wifi-safe-lan-scan.sh.DISABLED` — SECRET. Line 75 holds a plaintext default Wi-Fi password (value not copied here). [V] (src: wifi-safe-lan-scan.sh.DISABLED:75)
- `~/wifi-scan-reports/` — 9.3 MB, 6 files. [V] (cmd: ls -la; du -sh)
  - `wifi-switch.log` — 6.2 MB, 98,585 lines. Main log, written by `log()` and by `mesh-vpn ping` output. [V]
  - `wifi-guard-cron.log` — 3.4 MB, 47,976 lines. Cron stdout/stderr. Duplicates many lines of `wifi-switch.log` because `log()` uses `tee -a`. [V] (src: wifi-safe-switch.sh:20-22)
  - `wifi-switch-detached.log` — output of `detach` runs (last 2026-09-26). [V]
  - `20260926-000805-Wayne_Manor_5G_current.txt`, `deep-wayne-5g-20260926-002232.txt`, `deep-wayne-2.4g-20260926-135705.txt` — PRIVATE. nmap reports of LAN devices (IPs, MACs, vendors, open ports). Do not quote. [V] names (cmd: ls)
- Neither log is rotated. Both grow every 10 minutes. [V] (src: wifi-safe-switch.sh; crontab)
- `/tmp/wifi-safe-switch.lock` — lock file, touched every run (last 22:40). [V] (cmd: ls -la)
- `~/homelab/netwatch/wifi_manager.log` — 417 KB, last entry 2026-02-21 11:39. [V] (cmd: ls -la; tail)
- `~/homelab/netwatch/readme.md` → `library/07-netwatch/README.md`, a 64-byte stub. [V]
- `~/analyze_internet.py` — parses `/tmp/internet_traffic.txt` (tcpdump text). That input file does not exist now. [V] (src: analyze_internet.py:48; cmd: ls)
- `~/analyze_network.py` — parses `/tmp/nethogs_output.txt`. Input does not exist now. Has a hard-coded Docker IP → name map (Onyx, Immich, spotspot, Portainer). [V] (src: analyze_network.py:6-24,51; cmd: ls)
- `~/.local/bin/proxy-share.sh` — quick-tunnel script, 74 lines. [V]
- `/tmp/expose-<id>.log` — tunnel log with the public `trycloudflare.com` URL. None exist now. [V] (cmd: ls /tmp/expose-*.log)

## Commands
- `wifi-safe-switch.sh guard` — if Mesh VPN (e.g. Tailscale) ping to the target works, exit 0. Else try each candidate profile (`sudo -n nmcli connection up`), wait for connect, ping again; after each failed try roll back to the fallback. Ends on the fallback; exit 1 if nothing worked. MUTATES (changes the active Wi-Fi network). [V] (src: wifi-safe-switch.sh:265-286)
- `wifi-safe-switch.sh home` — brings up the fallback profile, then checks Mesh VPN (e.g. Tailscale). MUTATES. [V] (src: wifi-safe-switch.sh:293-295,58-69)
- `wifi-emergency-home.sh` — same as `home`. MUTATES. [V]
- `wifi-safe-switch.sh switch "<conn>"` — first runs `sync_wifi_secrets`: copies the 5G password into the "Wayne Manor 4G" profile and, if `AIRTEL_PSK` is set, writes it into "Airtel_Batcave" (`sudo -n nmcli connection modify … wifi-sec.psk`). Then tries `<conn>`, rolls back on failure. MUTATES (changes saved NetworkManager profiles and the active network). [V] (src: wifi-safe-switch.sh:47-56,107-118,288-291)
- `wifi-safe-switch.sh scan-all` / `scan-remaining` — joins each listed network, runs `nmap -sn -PR` discovery and `sudo -n nmap -sS -p- -A --open -T4` against every live host, writes a report, ends on the fallback. MUTATES. Active network scanning of other devices. [V] (src: wifi-safe-switch.sh:131-254)
- `wifi-safe-switch.sh detach <mode> …` — runs the same in the background with `nohup setsid`, logging to `wifi-switch-detached.log`. MUTATES. [V] (src: wifi-safe-switch.sh:297-301)
- `wifi-safe-switch.sh` with no argument — prints usage and exits 1. Still runs `mkdir -p "$LOG_DIR"` and sources the config first. [V] (src: wifi-safe-switch.sh:5-6,18,340-355)
- `wifi-safe-lan-scan.sh.DISABLED` — would run `nmcli connection modify` (passwords), `nmcli connection up`, and `nmap -sV`. Not runnable as is. MUTATES if renamed and run. [V] (src: wifi-safe-lan-scan.sh.DISABLED:57,66-77,146)
- `python3 ~/homelab/netwatch/wifi_manager.py` — may switch Wi-Fi with `nmcli device wifi connect`. MUTATES. [V] (src: wifi_manager.py, connect_to)
- `python3 ~/homelab/netwatch/cron_setup.py [install|remove]` — rewrites the user crontab (`crontab -`). MUTATES; `remove` DELETES its cron line. `show` is READ. [V] (src: cron_setup.py:17-35)
- `python3 ~/analyze_internet.py` — READ (reads a /tmp file, does reverse DNS lookups). [V]
- `python3 ~/analyze_network.py` — READ. [V]
- `expose <url>` / `share-media <url>` (`proxy-share.sh <url>`) — needs exactly one argument; it does not prompt (the alias comment saying "prompts" is wrong). Accepts only hosts matching `localhost`, `127.`, `10.`, `172.16-31.`, `192.168.`, `100.64.`. Deletes `/tmp/expose-<id>.log`, starts `screen -dmS expose-<id> … cloudflared tunnel --url <scheme://host:port>`, waits up to 12 s and prints the public URL plus the original path. MUTATES (opens a public tunnel). [V] (src: proxy-share.sh:10-74; ~/.bashrc:459)
- `share-stop-all` — `pkill -f cloudflared; screen -wipe`. Kills every process whose command line contains "cloudflared". MUTATES. [V] (src: ~/.bashrc:461)
- `mesh-vpn status` — READ. [V]
- `mesh-vpn ping -c 1 <ip>` — READ (sends a probe). [V] (src: wifi-safe-switch.sh:37)
- `nmcli -t -f NAME,DEVICE connection show --active` — READ. [V]
- `crontab -l` — READ. [V]

## Depends on
- GPU: no. AI brain :8081: no. Ollama :11434: no. Notifier :8001: no. [V] (src: all scripts read)
- NetworkManager (`nmcli`), passwordless `sudo` for `nmcli` and `nmap`. [V] (src: wifi-safe-switch.sh:25,51,192)
- Mesh VPN (e.g. Tailscale) running on this host, and the target node `hritiks-macbook-pro-1` being online with a valid key. [V] (src: wifi-safe-switch.sh:10,34-41)
- `nmap` (`/usr/bin/nmap`), `iwgetid` (`/usr/sbin/iwgetid`) for scans. [V] (cmd: command -v)
- `cloudflared` and `screen` for tunnels. [V] (cmd: command -v)
- Services that depend on this network path: everything reached over Mesh VPN (e.g. Tailscale) (SSH, Kindle dash is LAN-only, personal-feed OAuth callback via Mesh VPN (e.g. Tailscale) serve). [I] (src: personal-feed/.env.example:30-31; kindle-dash/README.md:61-75)

## How to check it (read-only)
- DUM-E tool `schedules` — confirms the `*/10` guard line exists. [I]
- DUM-E tool `log_tail` on `wifi-scan-reports/wifi-switch.log` (registered log). Look for `[guard] Mesh VPN (e.g. Tailscale) check failed` and `Recovered on:`. [V] (src: DUM-E.md:626)
- DUM-E tool `ports` — a running tunnel shows no local listener; check processes instead. [I]
- DUM-E tool `manual` — this file. [I]
- Owner, read-only: `mesh-vpn status` — the guard target must show "active". [V]
- Owner, read-only: `grep -c '\[guard\] Mesh VPN (e.g. Tailscale) check failed' ~/wifi-scan-reports/wifi-switch.log` — count of failed guard runs. [V]
- Owner, read-only: `tail -n 20 ~/wifi-scan-reports/wifi-switch.log`. Lines starting with `pong from` mean the guard check passed. [V]
- Owner, read-only: `nmcli -t -f NAME,DEVICE connection show --active` — which Wi-Fi is up. [V]
- Owner, read-only, tunnels: `screen -ls | grep expose-` and `ls /tmp/expose-*.log`. [V] (src: proxy-share.sh:41-42)

## Known problems and fixes
- **The guard flaps Wi-Fi when the MacBook is away, asleep, or its key expired.** The check target is one laptop, not the internet. When it does not answer, the guard cycles through all three profiles every 10 minutes. Evidence: 2,680 guard failures in `wifi-switch.log`, only 16 recoveries, 10,646 "On Wayne Manor 5G but Mesh VPN (e.g. Tailscale) check still failing" lines. 144 failures per day (every run) on 2026-10-12 → 2026-10-19. 4,028 lines say "peer's node key has expired"; 3,860 say the ping timed out. [V] (cmd: grep -c on wifi-switch.log) Today it failed at 21:10, 21:20, 21:30, 21:40, then passed. [V] Fix (owner): re-authenticate the MacBook in Mesh VPN (e.g. Tailscale) or disable key expiry for it; or change `TAILSCALE_CHECK_IP` in the config file to a node that is always on; or add an `internet_ok` check before switching (the function exists but is unused). DUM-E has no action for this; the owner edits `~/.config/wifi-switch.conf` or the script.
- **`internet_ok()` is defined but never called.** [V] (src: wifi-safe-switch.sh:43-45) The guard never tests the internet, only the one Mesh VPN (e.g. Tailscale) peer.
- **Logs grow without rotation.** 9.6 MB so far, plus duplication between the two logs. [V] Fix (owner): logrotate rule or truncate by hand. DUM-E has no action for this.
- **Plaintext Wi-Fi password in the disabled script.** [V] (src: wifi-safe-lan-scan.sh.DISABLED:75) Fix (owner): remove the default value, rotate the password if the file was ever shared. Plaintext Wi-Fi passwords also sit in `homelab/kindle-dash/CLIENT_SETUP_PROMPT.md` (see manual 30). [V]
- **Config file is group/world readable.** `~/.config/wifi-switch.conf` mode 664. `~/` is 750, so only user and group `(owner)` can reach it. [V] (cmd: stat; ls -ld ~/) Matters if DUM-E's `dume` user is ever put in group `(owner)`. [I]
- **`share-stop-all` kills all cloudflared processes**, not only quick tunnels. No other cloudflared runs today. [V] (src: ~/.bashrc:461; cmd: /proc check)
- **Quick tunnels expose the whole backend**, not only the shared path. `proxy-share.sh` tunnels `scheme://host:port` and appends the path only to the printed URL. Anyone with the URL can browse the whole service. [V] (src: proxy-share.sh:5,19-21,56,66)
- **Tunnel whitelist covers only 100.64.x for Mesh VPN (e.g. Tailscale).** Other Mesh VPN (e.g. Tailscale) addresses (100.65–100.127) are refused. [V] (src: proxy-share.sh:31)
- **netwatch is stale.** Not scheduled; last log 2026-02-21. It would fight the guard if re-enabled (both switch Wi-Fi). [V] dates; [I] conflict.
- **`analyze_*.py` need input files that are not there.** They print "No … detected" or crash on a missing file. [I] (src: analyze_internet.py:29; analyze_network.py:34)

## Logs
- `~/wifi-scan-reports/wifi-switch.log` — main guard log. Good: `pong from hritiks-macbook-pro-1`. Bad: `[guard] Mesh VPN (e.g. Tailscale) check failed`, `Mesh VPN (e.g. Tailscale) check FAILED on <profile>`, `WARNING: On Wayne Manor 5G but Mesh VPN (e.g. Tailscale) check still failing`, `nmcli failed for:`, `peer's node key has expired`. [V]
- `~/wifi-scan-reports/wifi-guard-cron.log` — cron output; same messages plus nmcli output (`Connection successfully activated`). [V]
- `~/wifi-scan-reports/wifi-switch-detached.log` — background runs. [V]
- `~/homelab/netwatch/wifi_manager.log` — netwatch, stale since 2026-02-21. [V]
- `/tmp/expose-<id>.log` — a running tunnel's log. [V]

## Rules for DUM-E here
- DUM-E must never run `wifi-safe-switch.sh` in any mode, `wifi-emergency-home.sh`, `wifi_manager.py`, `cron_setup.py install|remove`, or any `nmcli` write. A wrong switch can cut the owner's remote access. [V] (task rules)
- DUM-E has no action for Wi-Fi changes. The owner runs: `~/bin/wifi-emergency-home.sh` (to force "Wayne Manor 5G") or `~/bin/wifi-safe-switch.sh detach switch "<profile>"`.
- DUM-E must never start or stop tunnels. DUM-E has no action for this; the owner runs: `expose <url>` or `share-stop-all`.
- DUM-E must never open `~/.config/wifi-switch.conf` or `wifi-safe-lan-scan.sh.DISABLED` contents, and never quote the nmap reports (PRIVATE).
- DUM-E may read `wifi-switch.log` tails and `mesh-vpn status`. When reporting `mesh-vpn status`, name only the owner's nodes.
- DELETES operations that exist here:
  - `proxy-share.sh` runs `rm -f /tmp/expose-<id>.log`. [V] (src: proxy-share.sh:53)
  - `share-stop-all` runs `screen -wipe` (removes dead screen sessions). [V] (src: ~/.bashrc:461)
  - `cron_setup.py remove` deletes its crontab line; `install` rewrites the crontab. [V] (src: cron_setup.py:20-32)
  - `wifi-safe-switch.sh switch/scan-*` overwrites saved Wi-Fi passwords in NetworkManager profiles. [V] (src: wifi-safe-switch.sh:51,54)
  - `deep_scan_network` overwrites a report file only if the same timestamp repeats (`>`). [V] (src: wifi-safe-switch.sh:146-155)

## Open questions
- What does `~/.config/wifi-switch.conf` override? (Target IP? Candidate list?) [U] Settle: the owner reads it himself; DUM-E must not.
- Is the MacBook's Mesh VPN (e.g. Tailscale) key still expired? Today's later guard runs got `pong`, so it may be renewed. [U] Settle: `mesh-vpn status` shows no "expired" note for `hritiks-macbook-pro-1`.
- Are Mesh VPN (e.g. Tailscale) `serve` or `funnel` rules active (for `/ff` OAuth callbacks)? [U] Settle: owner runs `mesh-vpn serve status` and `mesh-vpn funnel status`.
- Is a DHCP reservation set for `192.168.1.41`? The Kindle depends on it. [U] Settle: router admin page (owner).
- Why did the guard run on 2026-10-20 and 2026-10-29 only a few times? Host was likely off 2026-10-20 → 2026-10-29. [I] (src: DUM-E.md F6)
