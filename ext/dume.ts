/**
 * DUM-E pi extension. Loaded with: pi --no-tools --no-extensions --no-skills -e /opt/dume/ext/dume.ts
 *
 * The model gets ONLY these tools. Each one calls the gateway as the owner through a single sudoers rule:
 *   sudo -n -H -u <owner> $DUME_GATEWAY/bin/dume-tool <tool>   (JSON args on stdin)
 * The gateway does all validation, redaction and auditing; this file only forwards.
 */

import { spawn } from "node:child_process";
import { StringEnum, Type } from "@mariozechner/pi-ai";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const DUME_OWNER = process.env.DUME_OWNER ?? "owner";
const GATEWAY = process.env.DUME_GATEWAY ?? "/opt/dume/gateway-path-not-set";

function callGateway(tool: string, args: unknown, signal?: AbortSignal): Promise<string> {
	return new Promise((resolve) => {
		const child = spawn("sudo", ["-n", "-H", "-u", DUME_OWNER, "--", GATEWAY, tool], {
			stdio: ["pipe", "pipe", "pipe"],
		});
		let out = "";
		let err = "";
		const timer = setTimeout(() => child.kill("SIGTERM"), 450_000);
		signal?.addEventListener("abort", () => child.kill("SIGTERM"));
		child.stdout.on("data", (d) => (out += d.toString()));
		child.stderr.on("data", (d) => (err += d.toString()));
		child.on("close", (code) => {
			clearTimeout(timer);
			if (code === 0) resolve(out.trim());
			else resolve(`Gateway error (exit ${code}): ${(out + err).trim().slice(0, 2000)}`);
		});
		child.stdin.end(JSON.stringify(args ?? {}));
	});
}

const NONE = Type.Object({});

const TOOLS = [
	{
		name: "snapshot",
		label: "Snapshot",
		description:
			"One-screen overview: uptime, memory, disks, GPU and who uses it, AI brain, VRAM watchdog, Ollama, Homelab services, incidents in the last 24 h, waiting proposals. Start here for 'how is everything'.",
		parameters: NONE,
	},
	{
		name: "gpu",
		label: "GPU",
		description: "GPU memory, utilisation, temperature, power, and every process on the GPU named by container.",
		parameters: NONE,
	},
	{
		name: "ai_brain",
		label: "AI brain",
		description:
			"The local LLM server (:8081): real model file, context, slots; the VRAM watchdog rules, pause state and live gates; Ollama models; the brain menu and boot default.",
		parameters: NONE,
	},
	{
		name: "services",
		label: "Services",
		description:
			"Homelab services (control/services.yaml): running or not, default, in boot profile, GPU. With id: details, start/stop commands, dependents.",
		parameters: Type.Object({ id: Type.Optional(Type.String({ description: "service id, e.g. ai_llama, cine_immich" })) }),
	},
	{
		name: "health",
		label: "Health",
		description:
			"Homelab Control health checks (read-only, sends no alerts). Cached 30 min; refresh=true reruns (can take ~5 min because of the restic check).",
		parameters: Type.Object({ refresh: Type.Optional(Type.Boolean()) }),
	},
	{
		name: "incidents",
		label: "Incidents",
		description: "Incident log grouped by source and message, with counts and first/last time.",
		parameters: Type.Object({
			hours: Type.Optional(Type.Number({ description: "look back this many hours (default 24)" })),
			source: Type.Optional(Type.String({ description: "filter by source, e.g. vault_offsite" })),
		}),
	},
	{
		name: "containers",
		label: "Containers",
		description:
			"Without name: all Docker containers with status and compose project. With name: state, health-check output, restart policy, ports, and optionally the last log lines (redacted).",
		parameters: Type.Object({
			name: Type.Optional(Type.String()),
			log_lines: Type.Optional(Type.Number({ description: "0-100 log lines" })),
		}),
	},
	{
		name: "schedules",
		label: "Schedules",
		description: "The user crontab, running user systemd services and timers, and key system units.",
		parameters: NONE,
	},
	{
		name: "ports",
		label: "Ports",
		description: "Listening TCP ports, what they bind to, and what each one is.",
		parameters: NONE,
	},
	{
		name: "disk_memory",
		label: "Disk & memory",
		description: "Filesystems usage, RAM, swap, and the size of known large log files.",
		parameters: NONE,
	},
	{
		name: "image_cleanup_preview",
		label: "Image cleanup preview",
		description: "Dry run of the weekly Docker image cleanup: which stopped containers and images it WOULD remove and what it keeps. Deletes nothing. Volumes are never touched. Show this to the owner before proposing docker_image_cleanup_run.",
		parameters: NONE,
	},
	{
		name: "log_tail",
		label: "Log tail",
		description:
			"Last lines of a registered log. Logs: image_cleanup, incidents, health_cron, boot, llama, watchdog, feed_cron, feed_learn, feed_api, feed_llama, kindle_render, wifi_guard, wifi_switch, vault_backup, vault_cron_daily, vault_bootstrap, vault_bootstrap_photos, restic_forget, dume_audit.",
		parameters: Type.Object({
			log: Type.String(),
			lines: Type.Optional(Type.Number({ description: "1-200, default 40" })),
			contains: Type.Optional(Type.String({ description: "only lines containing this text" })),
		}),
	},
	{
		name: "backup",
		label: "Backup",
		description: "Off-site backup (vault-backup/restic): lock holder, last log lines, newest logs, backup incidents of the last 7 days, schedule, retention. Read-only (does not call vault-backup status).",
		parameters: NONE,
	},
	{
		name: "shell_index",
		label: "Shell index",
		description: "The owner's bashrc aliases and functions (names, comments, commands; secrets never shown). Use to learn what an alias does.",
		parameters: Type.Object({ query: Type.Optional(Type.String({ description: "filter text" })) }),
	},
	{
		name: "manual",
		label: "Manual",
		description:
			"DUM-E's knowledge: manuals, runbooks (runbook:<name>), glossary of the owner's phrases, and the homelab docs library. action=list | read (name, optional section) | search (query).",
		parameters: Type.Object({
			action: StringEnum(["list", "read", "search"] as const),
			name: Type.Optional(Type.String()),
			section: Type.Optional(Type.String()),
			query: Type.Optional(Type.String()),
		}),
	},
	{
		name: "graph",
		label: "Graph",
		description:
			"Knowledge graph of the homelab (services, brains, scripts, cron jobs, aliases, containers, ports, docs). action=search (query) | node (id, depth 1-2) to see relations like DEPENDS_ON, CALLS, USES_GPU.",
		parameters: Type.Object({
			action: StringEnum(["search", "node"] as const),
			id: Type.Optional(Type.String()),
			query: Type.Optional(Type.String()),
			depth: Type.Optional(Type.Number()),
		}),
	},
	{
		name: "propose_action",
		label: "Propose action",
		description:
			"PROPOSE a change for the owner to approve. Nothing runs until the owner types `dume approve <ID>` in their own terminal. Actions: llama_start, llama_stop, llama_restart, ollama_unload, service_start (args.service_id), service_stop (args.service_id), watchdog_restart, watchdog_clear_pause, backup_run_daily, docker_image_cleanup_run.",
		parameters: Type.Object({
			action: StringEnum([
				"llama_start",
				"llama_stop",
				"llama_restart",
				"ollama_unload",
				"service_start",
				"service_stop",
				"watchdog_restart",
				"watchdog_clear_pause",
				"backup_run_daily",
				"docker_image_cleanup_run",
			] as const),
			args: Type.Optional(Type.Object({ service_id: Type.Optional(Type.String()) })),
		}),
	},
	{
		name: "action_status",
		label: "Action status",
		description: "Status and output of a proposal (pending, done, failed, rejected, expired).",
		parameters: Type.Object({ id: Type.String() }),
	},
	{
		name: "propose_knowledge_edit",
		label: "Propose knowledge edit",
		description:
			"ONLY when the owner explicitly asks you to improve, correct, teach or remember something: PROPOSE a change to exactly one section of one DUM-E knowledge file (manual, runbook, or glossary). The owner reviews the diff and approves with `dume approve <ID>`. op=replace_section | add_section | glossary_add (section = the owner's phrase).",
		parameters: Type.Object({
			op: StringEnum(["replace_section", "add_section", "glossary_add"] as const),
			file: Type.Optional(Type.String({ description: "manual/runbook name, e.g. 02-ai-brain or runbook:ai-down" })),
			section: Type.String({ description: "exact heading text of the section (or the new heading / glossary phrase)" }),
			text: Type.String({ description: "the complete new body of that section" }),
			reason: Type.String({ description: "what the owner asked, in their words" }),
		}),
	},
];

const ALLOWED = new Set(TOOLS.map((t) => t.name));

export default function (pi: ExtensionAPI) {
	for (const t of TOOLS) {
		pi.registerTool({
			name: t.name,
			label: t.label,
			description: t.description,
			parameters: t.parameters,
			async execute(_id, params, signal) {
				const text = await callGateway(t.name, params, signal);
				return { content: [{ type: "text", text }], details: { tool: t.name } };
			},
		});
	}

	// Defence in depth: refuse any tool that is not DUM-E's own (pi's built-ins are already off via --no-tools).
	pi.on("tool_call", async (event) => {
		if (!ALLOWED.has(event.toolName)) {
			return { block: true, reason: `DUM-E may only use its own tools; '${event.toolName}' is not allowed.` };
		}
		return undefined;
	});
}
