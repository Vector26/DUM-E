"""DUM-E knowledge: manuals, runbooks, glossary, the homelab docs library, and the graph.

Learning is owner-directed only: DUM-E may PROPOSE a change to exactly one section of one
knowledge file, and only `dume approve <ID>` (owner, own terminal) applies it. The previous
version of the file is always kept in knowledge/.history/.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
from pathlib import Path

from . import core

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
MAX_EDIT_CHARS = 8000


# ---------------------------------------------------------------- files

def _knowledge_files() -> list[Path]:
    files = sorted(p for p in core.MANUALS.glob("*.md") if not p.name.startswith("_"))
    files += sorted(core.RUNBOOKS.glob("*.md"))
    if core.GLOSSARY.exists():
        files.append(core.GLOSSARY)
    return files


def _library_files() -> list[Path]:
    out = []
    for p in core.LIBRARY.rglob("*.md"):
        if not core.is_protected(p):
            out.append(p)
    return sorted(out)


def _front_matter(text: str) -> dict:
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end].splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    return meta


def resolve(name: str) -> Path | None:
    """Map a short name to a knowledge or library file. Never leaves those two trees."""
    name = (name or "").strip()
    if not name:
        return None
    if name.lower() in {"glossary", "glossary.md"}:
        return core.GLOSSARY
    if name.startswith("library/"):
        path = core.FORTRESS / name
        if path.exists() and core.inside(path, core.LIBRARY) and not core.is_protected(path):
            return path
        return None
    key = name.lower().removeprefix("runbook:").removeprefix("runbooks/").removeprefix("manuals/")
    key = key.removesuffix(".md")
    candidates = _knowledge_files()
    for p in candidates:
        if p.stem.lower() == key:
            return p
    for p in candidates:  # "ai-brain" matches "02-ai-brain"
        if re.sub(r"^\d+-", "", p.stem.lower()) == key:
            return p
    matches = [p for p in candidates if key in p.stem.lower()]
    return matches[0] if len(matches) == 1 else None


def sections(text: str) -> list[dict]:
    """Headings with their line spans. A section runs until the next heading of the same or higher level."""
    lines = text.splitlines()
    heads = []
    in_code = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        m = HEADING.match(line)
        if m:
            heads.append({"level": len(m.group(1)), "title": m.group(2), "start": i})
    for idx, h in enumerate(heads):
        end = len(lines)
        for nxt in heads[idx + 1:]:
            if nxt["level"] <= h["level"]:
                end = nxt["start"]
                break
        h["end"] = end
    return heads


def _find_section(text: str, wanted: str) -> dict | None:
    wanted_l = wanted.strip().lstrip("#").strip().lower()
    heads = sections(text)
    for h in heads:
        if h["title"].lower() == wanted_l:
            return h
    partial = [h for h in heads if wanted_l in h["title"].lower()]
    return partial[0] if len(partial) == 1 else None


def _rel(path: Path) -> str:
    for root, label in ((core.KNOWLEDGE, "knowledge"), (core.FORTRESS, "fortress")):
        try:
            return f"{label}/{path.relative_to(root)}"
        except ValueError:
            continue
    return str(path)


# ---------------------------------------------------------------- manual tool

def manual(args: dict) -> str:
    action = str(args.get("action", "list")).lower()
    if action == "list":
        lines = ["MANUALS (read with action=read name=<file>):"]
        for p in sorted(core.MANUALS.glob("*.md")):
            if p.name.startswith("_"):
                continue
            meta = _front_matter(p.read_text(errors="replace"))
            lines.append(f"  {p.stem}: {meta.get('title', '')} - {meta.get('scope', '')}")
        lines.append("RUNBOOKS (symptom -> checks -> fix):")
        for p in sorted(core.RUNBOOKS.glob("*.md")):
            meta = _front_matter(p.read_text(errors="replace"))
            lines.append(f"  runbook:{p.stem}: {meta.get('title', '')} - {meta.get('symptom', meta.get('scope', ''))}")
        if core.GLOSSARY.exists():
            terms = [h["title"] for h in sections(core.GLOSSARY.read_text()) if h["level"] == 2]
            lines.append(f"GLOSSARY ({len(terms)} owner phrases; read name=glossary): " + ", ".join(terms))
        shelves = sorted({p.relative_to(core.LIBRARY).parts[0] for p in _library_files()
                          if len(p.relative_to(core.LIBRARY).parts) > 1})
        lines.append("FORTRESS DOCS LIBRARY (search it, or read name=library/<path>): " + ", ".join(shelves))
        return "\n".join(lines)
    if action == "read":
        path = resolve(str(args.get("name", "")))
        if not path or not path.exists():
            return "Not found. Use manual action=list to see names."
        text = path.read_text(errors="replace")
        section = str(args.get("section", "") or "")
        if section:
            h = _find_section(text, section)
            if not h:
                titles = [("#" * s["level"]) + " " + s["title"] for s in sections(text)]
                return f"No unique section '{section}' in {_rel(path)}. Sections:\n" + "\n".join(titles)
            body = "\n".join(text.splitlines()[h["start"]:h["end"]])
            return f"[{_rel(path)} # {h['title']}]\n{core.cap(body)}"
        if len(text) > core.MAX_OUTPUT:
            titles = [("  " * (s["level"] - 1)) + s["title"] for s in sections(text)]
            return (f"[{_rel(path)}] is long ({len(text)} chars). Read one section at a time"
                    " (action=read, name, section=<title>). Sections:\n" + "\n".join(titles))
        return f"[{_rel(path)}]\n{text}"
    if action == "search":
        return search(str(args.get("query", "")))
    return "action must be list, read or search."


def _chunks(path: Path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    heads = sections(text)
    if not heads:
        yield ("(top)", lines, 0)
        return
    if heads[0]["start"] > 0:
        yield ("(top)", lines[:heads[0]["start"]], 0)
    for idx, h in enumerate(heads):
        end = heads[idx + 1]["start"] if idx + 1 < len(heads) else len(lines)
        yield (h["title"], lines[h["start"]:end], h["start"])


def search(query: str, limit: int = 10) -> str:
    words = [w for w in re.findall(r"[a-z0-9_.:/-]{2,}", query.lower()) if w not in _STOP]
    if not words:
        return "Give a few keywords."
    scored = []
    for weight, files in ((3.0, _knowledge_files()), (1.0, _library_files())):
        for path in files:
            w = weight * (0.4 if "99-third-party" in str(path) else 1.0)
            for title, lines, start in _chunks(path):
                blob = (title + "\n" + "\n".join(lines)).lower()
                hits = sum(min(blob.count(word), 5) for word in words)
                covered = sum(1 for word in words if word in blob)
                if not covered:
                    continue
                title_bonus = sum(2 for word in words if word in title.lower())
                score = w * (hits + 3 * covered * covered / len(words) + title_bonus)
                snippet = [l.strip() for l in lines if any(word in l.lower() for word in words)][:3]
                scored.append((score, path, title, start, snippet))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return f"Nothing found for '{query}'. Try other words, or manual action=list."
    out = [f"Top matches for '{query}' (read with manual action=read name=<file> section=<section>):"]
    for score, path, title, start, snippet in scored[:limit]:
        name = path.stem if core.inside(path, core.KNOWLEDGE) else _rel(path).removeprefix("homelab/")
        if core.inside(path, core.RUNBOOKS):
            name = "runbook:" + path.stem
        out.append(f"- {name} # {title}")
        for s in snippet:
            out.append(f"    {s[:200]}")
    return core.redact("\n".join(out))


_STOP = set("the a an and or of to in on for is are was it this that with how what why when where do does can i my me "
            "be by at as from not".split())


# ---------------------------------------------------------------- graph tool

def _load_graph() -> dict | None:
    return core.load_json(core.GRAPH_JSON)


def _stale(graph: dict, source: str) -> bool:
    path = source.split(":")[0]
    want = graph.get("sources", {}).get(path)
    if not want or not Path(path).exists():
        return False
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() != want


def graph(args: dict) -> str:
    g = _load_graph()
    if not g:
        return "No graph built yet. The owner can build it with: dume rebuild-graph"
    action = str(args.get("action", "search")).lower()
    nodes = {n["id"]: n for n in g["nodes"]}
    if action == "search":
        q = str(args.get("query", "")).lower()
        hits = [n for n in g["nodes"] if q and (q in n["id"].lower() or q in n.get("name", "").lower())][:30]
        if not hits:
            return f"No node matches '{q}'. Node types: " + ", ".join(sorted({n['type'] for n in g['nodes']}))
        return "\n".join(f"{n['id']} ({n['type']}): {n.get('name', '')}" for n in hits)
    node_id = str(args.get("id", ""))
    if node_id not in nodes:
        return f"Unknown node '{node_id}'. Use graph action=search query=<text>."
    depth = max(1, min(2, int(args.get("depth", 1) or 1)))
    frontier, seen, lines = {node_id}, {node_id}, []
    n = nodes[node_id]
    lines.append(f"{n['id']} ({n['type']}): {n.get('name', '')}  [source {n.get('source', '?')}]")
    if n.get("props"):
        lines.append("  " + json.dumps(n["props"])[:800])
    if n.get("source") and _stale(g, n["source"]):
        lines.append("  NOTE: the source file changed since the graph was built; facts may be stale"
                     " (owner: dume rebuild-graph).")
    for level in range(depth):
        nxt = set()
        for e in g["edges"]:
            if e["from"] in frontier or e["to"] in frontier:
                lines.append(f"  {'  ' * level}{e['from']} -[{e['type']}]-> {e['to']}  ({e.get('source', '')})")
                for x in (e["from"], e["to"]):
                    if x not in seen:
                        seen.add(x)
                        nxt.add(x)
        frontier = nxt
    lines.append(f"(graph built {g.get('built_at', '?')})")
    return core.cap("\n".join(lines))


# ---------------------------------------------------------------- owner-directed learning

def _editable(path: Path) -> bool:
    if not path or not path.exists():
        return False
    if path.name.startswith("_"):
        return False
    return core.inside(path, core.MANUALS) or core.inside(path, core.RUNBOOKS) or path == core.GLOSSARY


def propose_edit(args: dict) -> str:
    from . import actions
    op = str(args.get("op", "")).strip()
    name = str(args.get("file", "")).strip()
    section = str(args.get("section", "")).strip().lstrip("#").strip()
    text = str(args.get("text", "")).rstrip()
    reason = str(args.get("reason", "")).strip()[:500]
    if op not in {"replace_section", "add_section", "glossary_add"}:
        return "op must be replace_section, add_section or glossary_add."
    if op == "glossary_add":
        name = "glossary"
    path = resolve(name)
    if not _editable(path):
        return "Only DUM-E knowledge files (manuals, runbooks, glossary) can be edited. Use manual action=list."
    if not section or not text or not reason:
        return "Need section (heading text), text (new content) and reason (what the owner asked)."
    if len(text) > MAX_EDIT_CHARS:
        return f"Text too long ({len(text)} chars, max {MAX_EDIT_CHARS}). Change one section at a time."
    if core.redact(text) != text:
        return "Refused: the new text contains something that looks like a secret."
    old = path.read_text()
    lines = old.splitlines()
    if op == "replace_section":
        h = _find_section(old, section)
        if not h:
            return f"No unique section '{section}' in {path.name}. Read the file's sections first."
        for line in text.splitlines():
            m = HEADING.match(line)
            if m and len(m.group(1)) <= h["level"]:
                return "The new text may not contain headings at the same or a higher level (one section only)."
        new_lines = lines[:h["start"] + 1] + text.splitlines() + [""] + lines[h["end"]:]
        section_title = h["title"]
    else:
        if any(s["title"].lower() == section.lower() for s in sections(old)):
            return f"Section '{section}' already exists; use replace_section."
        for line in text.splitlines():
            if HEADING.match(line) and HEADING.match(line).group(1) in ("#", "##"):
                return "The new text may not contain level-1 or level-2 headings."
        new_lines = lines + ["", f"## {section}", *text.splitlines()]
        section_title = section
    new = "\n".join(new_lines).rstrip() + "\n"
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", n=2))
    record = actions.save_pending({
        "kind": "knowledge_edit", "op": op, "file": str(path), "section": section_title,
        "new_text": text, "new_content": new, "reason": reason,
        "base_sha256": hashlib.sha256(old.encode()).hexdigest(), "diff": diff, "deletes": [f"previous text of section '{section_title}' in {path.name}"
                                  " (kept in knowledge/.history)"] if op == "replace_section" else "none",
        "class": "housekeeping"})
    return (f"Knowledge edit proposal {record['id']} created. NOTHING IS CHANGED YET.\n"
            f"File: {_rel(path)}  Section: {section_title}  Op: {op}\nReason: {reason}\n"
            f"Diff:\n{core.cap(diff, 6000)}\n"
            f"Tell the owner to review and approve it with:  dume approve {record['id']}")


def approve_edit(record: dict, finish) -> int:
    path = Path(record["file"])
    if not _editable(path):
        finish(record, "rejected: file not editable")
        print("Refused: not a DUM-E knowledge file.")
        return 1
    current = path.read_text()
    if hashlib.sha256(current.encode()).hexdigest() != record["base_sha256"]:
        finish(record, "rejected: file changed since proposal")
        print("The file changed since DUM-E proposed this edit. Refused; ask DUM-E to propose it again.")
        return 1
    print("=" * 72)
    print(f"DUM-E knowledge edit {record['id']}: {record['op']} in {path.name} # {record['section']}")
    print(f"Reason given: {record['reason']}")
    print("=" * 72)
    print(record["diff"])
    print("=" * 72)
    if record["op"] == "replace_section":
        print(f"Replaces the old text of that section. The old file is kept in {core.HISTORY}.")
    answer = input("Apply it? Type y to apply, anything else cancels: ").strip().lower()
    if answer != "y":
        finish(record, "rejected by owner")
        print("Cancelled. Nothing changed.")
        return 1
    core.HISTORY.mkdir(parents=True, exist_ok=True)
    stamp = __import__("time").strftime("%Y%m%d-%H%M%S")
    backup = core.HISTORY / f"{path.stem}.{stamp}.{record['id']}.md"
    backup.write_text(current)
    # The file is unchanged since the proposal (hash checked above), so the stored result is
    # exactly what the shown diff produces.
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(record["new_content"])
    os.replace(tmp, path)
    finish(record, "done", 0, f"applied to {path}; previous version saved as {backup}")
    print(f"Applied. Previous version: {backup}")
    return 0
