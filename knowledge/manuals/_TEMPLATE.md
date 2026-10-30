---
title: <Subsystem name>
scope: <one line: what this manual covers>
last_verified: <YYYY-MM-DD>
sources: <comma-separated main files read>
---

# <Subsystem name>

Evidence tags: [V] verified by reading a file or running a read-only command; [I] inferred from verified facts; [U] unverified.
Every fact names its source in brackets, e.g. (src: homelab/control/services.yaml:84) or (cmd: docker ps).

## What it is
Two to five plain sentences. What it does for the owner and why it exists.

## How the owner refers to it
Names, aliases and phrases found in .bashrc, docs or service names. Skip if none found.

## Components
Containers, host processes, ports, compose file path, systemd units. One bullet each.

## Files and data
Important paths. Secret-bearing files are named only, never opened, and marked SECRET.
Personal-data paths are marked PRIVATE.

## Commands
Each command: exact text, what it does, and its class:
READ (no side effects) | MUTATES (changes state) | DELETES (removes or overwrites data).

## Depends on
GPU? The AI brain on :8081? Ollama :11434? Other services? The notifier :8001?

## How to check it (read-only)
Which DUM-E tool answers it (snapshot, gpu, ai_brain, services, health, incidents,
containers, schedules, ports, disk_memory, log_tail, backup, manual, graph, shell_index)
and which plain read-only command the owner can run.

## Known problems and fixes
Each: symptom, cause, evidence, fix. Fixes that change things say who runs them
(the owner, or DUM-E through an approved action).

## Logs
Paths and what to look for.

## Rules for DUM-E here
What DUM-E must never do in this subsystem. List every DELETES operation that exists here.

## Open questions
What could not be verified and how to settle it.
