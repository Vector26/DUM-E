"""Build DUM-E's static knowledge graph from files on disk (owner runs: dume rebuild-graph).

Every node and edge carries a `source`. Live state (what is running now) is NOT stored here;
the live tools answer that. `sources` maps each parsed file to its sha256 so stale facts can be flagged.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import yaml

from . import core

SCRIPT_PATH = re.compile(r"(?:~|~/)/[\w./-]+\.(?:sh|py|cjs|mjs)|(?:~|~/)/bin/[\w.-]+")


class Graph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.sources: dict[str, str] = {}

    def src(self, path: Path) -> str:
        p = str(path)
        if p not in self.sources and path.is_file():
            self.sources[p] = hashlib.sha256(path.read_bytes()).hexdigest()
        return p

    def node(self, nid: str, ntype: str, name: str = "", source: str = "", **props) -> str:
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "type": ntype, "name": name, "source": source,
                               "props": {k: v for k, v in props.items() if v not in (None, "", [], {})}}
        return nid

    def edge(self, a: str, etype: str, b: str, source: str = "") -> None:
        e = {"from": a, "type": etype, "to": b, "source": source}
        if e not in self.edges:
            self.edges.append(e)


def _norm_script(path: str) -> str:
    return path.replace("~/", "~/")


def _script(g: Graph, path: str, source: str) -> str:
    path = _norm_script(path)
    return g.node(f"script:{path}", "Script", Path(path).name, source, path=path,
                  exists=Path(path).exists())


def build() -> dict:
    g = Graph()
    services_yaml = core.CONTROL / "services.yaml"
    ai_yaml = core.CONTROL / "ai_models.yaml"
    jobs_yaml = core.CONTROL / "host_jobs.yaml"

    # Services (control/services.yaml)
    s = g.src(services_yaml)
    for svc in yaml.safe_load(services_yaml.read_text())["services"]:
        sid = g.node(f"service:{svc['id']}", "Service", svc.get("name", ""), f"{s}#{svc['id']}",
                     kind=svc.get("kind"), gpu=bool(svc.get("gpu")), default=bool(svc.get("default")),
                     blurb=svc.get("blurb"), compose=svc.get("compose"))
        if svc.get("gpu"):
            g.edge(sid, "USES_GPU", g.node("gpu:rtx5070ti", "GPU", "NVIDIA discrete GPU (example: 16 GB VRAM) 16 GB", "nvidia-smi"), s)
        for dep in svc.get("depends_on") or []:
            g.edge(sid, "DEPENDS_ON", f"service:{dep}", s)
        if svc.get("compose"):
            g.edge(sid, "DEFINED_BY", g.node(f"compose:{svc['compose']}", "ComposeDir", svc["compose"], s), s)
        if svc.get("detect_container"):
            g.edge(sid, "DETECTED_BY", g.node(f"container:{svc['detect_container']}", "Container",
                                              svc["detect_container"], s), s)
        if svc.get("detect_port"):
            g.edge(sid, "DETECTED_BY", g.node(f"port:{svc['detect_port']}", "Port", str(svc["detect_port"]), s), s)
        for key, etype in (("start", "STARTS_WITH"), ("stop", "STOPS_WITH")):
            for path in SCRIPT_PATH.findall(svc.get(key) or ""):
                g.edge(sid, etype, _script(g, path, s), s)

    # AI brains (control/ai_models.yaml)
    a = g.src(ai_yaml)
    brains = yaml.safe_load(ai_yaml.read_text())["models"]
    for b in brains:
        bid = g.node(f"brain:{b['id']}", "Brain", b.get("label", ""), f"{a}#{b['id']}",
                     backend=b.get("backend"), quant=b.get("quant"), port=b.get("port"),
                     model_path=b.get("model_path"), ollama_model=b.get("model"), tip=b.get("tip"))
        if b.get("model_path"):
            g.edge(bid, "LOADS", g.node(f"model:{Path(b['model_path']).name}", "Model",
                                        Path(b["model_path"]).name, a, path=b["model_path"]), a)
        if b.get("model"):
            g.edge(bid, "LOADS", g.node(f"model:ollama:{b['model']}", "Model", b["model"], a), a)
    gpu_brains = [f"brain:{b['id']}" for b in brains if b.get("backend") in ("llama", "ollama")]
    for i, x in enumerate(gpu_brains):
        for y in gpu_brains[i + 1:]:
            g.edge(x, "CONFLICTS_WITH", y, f"{a} (only one GPU-heavy brain at a time)")

    # Host jobs
    j = g.src(jobs_yaml)
    for job in yaml.safe_load(jobs_yaml.read_text())["jobs"]:
        jid = g.node(f"job:{job['id']}", "HostJob", job.get("name", ""), f"{j}#{job['id']}",
                     blurb=job.get("blurb"), checks=job.get("checks"))
        if (job.get("checks") or {}).get("container_running"):
            g.edge(jid, "CHECKS", f"container:{job['checks']['container_running']}", j)

    # Core runtime facts (from reading the scripts; see manuals 02/03)
    llama = _script(g, "~/bin/llama-server-ctl", "bin/llama-server-ctl")
    g.src(core.LLAMA_CTL)
    g.edge("service:ai_llama", "SERVES", g.node("port:8081", "Port", "8081 AI brain (0.0.0.0)", str(core.LLAMA_CTL)),
           str(core.LLAMA_CTL))
    g.edge(llama, "UNLOADS", g.node("service:ollama", "SystemdUnit", "ollama.service (:11434)",
                                    "/etc/systemd/system/ollama.service"), f"{core.LLAMA_CTL} unload_ollama_gpu")
    g.edge("service:ollama", "SERVES", g.node("port:11434", "Port", "11434 Ollama (0.0.0.0)", "ollama override.conf"),
           "/etc/systemd/system/ollama.service.d/override.conf")
    wd = _script(g, str(core.WATCHDOG_SCRIPT), str(core.WATCHDOG_SCRIPT))
    g.src(core.WATCHDOG_SCRIPT)
    g.edge(wd, "STOPS", llama, str(core.WATCHDOG_SCRIPT))
    g.edge(wd, "STARTS", llama, str(core.WATCHDOG_SCRIPT))
    g.edge(wd, "NOTIFIES", g.node("port:8001", "Port", "8001 Alert notifier", "notifier/docker-compose.yml"),
           str(core.WATCHDOG_SCRIPT))
    g.edge(wd, "WRITES", g.node("state:ai-paused", "StateFile", str(core.WATCHDOG_DIR / "ai-paused"),
                                str(core.WATCHDOG_SCRIPT)), str(core.WATCHDOG_SCRIPT))

    # Who starts the AI brain: grep the homelab for callers of llama-server-ctl
    rc, out = core.run(["grep", "-rlE", "--include=*.sh", "--include=*.py", "--include=*.yaml", "--include=*.cjs",
                        "--exclude-dir=node_modules", "--exclude-dir=.venv", "--exclude-dir=vendor",
                        "--exclude-dir=pi-cyber", "--exclude-dir=backups", "--exclude-dir=DUM-E",
                        "llama-server-ctl", str(core.FORTRESS), str(core.HOME / "bin")], timeout=60)
    for path in out.splitlines():
        if not path.startswith("/"):
            continue  # grep warnings on stderr, not paths
        p = Path(path)
        if not p.is_file() or core.is_protected(p):
            continue
        g.src(p)
        caller = g.node(f"file:{p}", "File", p.name, str(p))
        g.edge(caller, "CALLS", llama, f"{p} (grep llama-server-ctl)")

    # Crontab
    rc, cron = core.run(["crontab", "-l"], timeout=10)
    for line in cron.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        sched = " ".join(parts[:1] if parts[0].startswith("@") else parts[:5])
        short = hashlib.sha256(line.encode()).hexdigest()[:6]
        cid = g.node(f"cron:{sched}:{short}", "CronJob", sched, "crontab -l", line=line)
        for path in SCRIPT_PATH.findall(line):
            g.edge(cid, "RUNS", _script(g, path, "crontab -l"), "crontab -l")
        if "homelab/control/fortress" in line:
            g.edge(cid, "RUNS", _script(g, "~/homelab/control/fortress", "crontab -l"), "crontab -l")
        for log in re.findall(r">>\s*(\S+)", line):
            g.edge(cid, "WRITES", g.node(f"log:{log}", "Log", log, "crontab -l"), "crontab -l")

    # Shell aliases/functions (names, comments, referenced scripts only; never secrets)
    bashrc = core.HOME / ".bashrc"
    b = g.src(bashrc)
    for number, raw in enumerate(bashrc.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        m = re.match(r"^alias\s+([\w.-]+)=", line)
        f = re.match(r"^([\w-]+)\s*\(\)\s*\{", line)
        if not (m or f):
            continue
        name = (m or f).group(1)
        comment = line.split("#", 1)[1].strip() if m and "  #" in line else ""
        nid = g.node(f"{'alias' if m else 'function'}:{name}", "Alias" if m else "Function", name,
                     f"{b}:{number}", comment=core.redact(comment))
        for path in SCRIPT_PATH.findall(line):
            g.edge(nid, "RUNS", _script(g, path, f"{b}:{number}"), f"{b}:{number}")

    # Containers and compose projects (structure only)
    rc, out = core.run(["docker", "ps", "-a", "--format",
                        "{{.Names}}\t{{.Label \"com.docker.compose.project\"}}\t"
                        "{{.Label \"com.docker.compose.project.working_dir\"}}"], timeout=20)
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, project, workdir = parts
        cid = g.node(f"container:{name}", "Container", name, "docker ps -a")
        if project:
            pid = g.node(f"project:{project}", "ComposeProject", project, "docker labels", workdir=workdir)
            g.edge(cid, "PART_OF", pid, "docker labels")

    # Manuals and runbooks: link each service to documents that mention it
    docs = [p for p in core.MANUALS.glob("*.md") if not p.name.startswith("_")] + list(core.RUNBOOKS.glob("*.md"))
    for doc in docs:
        did = g.node(f"doc:{doc.stem}", "Doc", doc.stem, str(doc.relative_to(core.ROOT)))
        text = doc.read_text(errors="replace").lower()
        for node in list(g.nodes.values()):
            if node["type"] == "Service":
                sid = node["id"].split(":", 1)[1]
                if re.search(rf"\b{re.escape(sid)}\b", text):
                    g.edge(node["id"], "DOCUMENTED_BY", did, str(doc.relative_to(core.ROOT)))

    graph = {"built_at": time.strftime("%Y-%m-%d %H:%M:%S %z"), "nodes": list(g.nodes.values()),
             "edges": g.edges, "sources": g.sources}
    core.GRAPH_JSON.write_text(json.dumps(graph, indent=1))
    return {"nodes": len(g.nodes), "edges": len(g.edges), "sources": len(g.sources)}
