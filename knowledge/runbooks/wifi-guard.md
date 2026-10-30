---
title: Wi-Fi keeps switching or the network drops
symptom: The network drops, or Wi-Fi keeps switching between networks
last_verified: 2026-10-30
related: 29-wifi-and-network-guard, 08-network-and-ports
---

# Wi-Fi keeps switching or the network drops

## Symptom
- Wi-Fi changes network every few minutes, or connections drop. [V]
- The guard log repeats "WARNING: On Wayne Manor 5G but Mesh VPN (e.g. Tailscale) check still failing." [V]

## Quick check
1. `log_tail {"log":"wifi_guard","lines":60}` - look for: "Mesh VPN (e.g. Tailscale) check failed", "Rollback", "Recovered".
2. `log_tail {"log":"wifi_switch","lines":40}` - look for: which network was chosen.

## Diagnosis
1. A cron job runs every 10 minutes: `~/bin/wifi-safe-switch.sh guard`. [V]
2. The guard decides "network is down" from one check: a ping to one MacBook over Mesh VPN (e.g. Tailscale) (`TAILSCALE_CHECK_IP`, default 100.126.168.42 in the script). [V]
3. The script has an `internet_ok()` function. The guard path shown in the script does not use it as the decision. [I]
4. If that MacBook is off, asleep or its Mesh VPN (e.g. Tailscale) key expired, the guard thinks the network failed and tries other profiles. [I]
5. So repeated "Mesh VPN (e.g. Tailscale) check still failing" with working internet -> cause A: the check target is unreachable, not the Wi-Fi.

## Fix
The owner decides. DUM-E has no action here.
- Re-authenticate that MacBook in Mesh VPN (e.g. Tailscale), or
- change `TAILSCALE_CHECK_IP` to a host that is always on, or
- remove the cron line marked `wifi-mesh-vpn-guard`.

## Verify
- `log_tail {"log":"wifi_guard","lines":10}` shows no new "check still failing" lines for 30 minutes.

## Do not
- Do not run `wifi-safe-switch.sh`. It switches Wi-Fi with sudo `nmcli` and can cut your own connection.
- Do not edit the cron line for the owner.

## Sources
- `crontab -l` (wifi-mesh-vpn-guard)
- `~/bin/wifi-safe-switch.sh`
- `~/wifi-scan-reports/wifi-guard-cron.log`
- manual 29-wifi-and-network-guard
