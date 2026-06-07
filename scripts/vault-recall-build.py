#!/usr/bin/env python3
"""Ambient vault recall — deterministic map/registry generator.

Scans a project's vault/ for note frontmatter and emits two artefacts:
  vault/_registry.md      human-readable catalogue (commit this)
  vault/.recall-map.json  fast lookup for the PreToolUse hook (gitignore this)

No intelligence here — pure frontmatter->data transform. The *authoring* of
frontmatter (areas/files/symptoms) is the vault-manager agent's job; this script
only mechanises what already exists. Runs anywhere, no third-party deps.

Project root resolution order: CLAUDE_PROJECT_DIR env -> argv[1] -> cwd.
No-ops silently when there is no vault/ directory.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """Write via temp + os.replace so a concurrent reader never sees a partial file."""
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR")
                or (sys.argv[1] if len(sys.argv) > 1 else "")
                or os.getcwd())


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML-frontmatter parser. Handles `key: scalar` and
    `key: [a, "b c"]` flow lists. Good enough for our controlled schema;
    deliberately not a full YAML implementation."""
    if not text.startswith("---"):
        return {}
    m = re.search(r"\n---[ \t]*(?:\n|$)", text)   # line-anchored closing terminator
    if not m:
        return {}
    block = text[3:m.start()].strip("\n")
    fm: dict = {}
    pending_key = None  # a `key:` with empty value may be followed by block-list items
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and pending_key:          # block-style list item
            item = stripped[2:].strip().strip('"').strip("'").strip()
            if item:
                if not isinstance(fm.get(pending_key), list):
                    fm[pending_key] = []
                fm[pending_key].append(item)
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not key:
            continue
        pending_key = None
        if val.startswith("[") and val.endswith("]"):          # flow-style list
            inner = val[1:-1].strip()
            items = []
            for part in re.findall(r'"[^"]*"|\'[^\']*\'|[^,]+', inner):
                p = part.strip().strip('"').strip("'").strip()
                if p:
                    items.append(p)
            fm[key] = items
        elif val == "":                                        # maybe a block list follows
            fm[key] = ""
            pending_key = key
        else:
            fm[key] = val.strip('"').strip("'")
    return fm


def first_sentence(body: str) -> str:
    for raw in body.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", "---", "![", "<!--", "|", "- [", "* [")):
            continue
        if s.startswith(">"):                       # blockquote / Obsidian callout
            s = s.lstrip(">").strip()
            s = re.sub(r"^\[![^\]]*\][-+]?\s*", "", s)  # drop "[!summary]" marker, keep any title
            if not s:
                continue
        s = re.sub(r"[*_`]", "", s)                 # strip emphasis
        s = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", s)  # unwrap wikilinks
        # skip short label/status lines like "Status: Confirmed", "Phase: 0"
        if re.match(r"^[A-Z][\w /&-]{0,24}:\s*\S.*$", s) and len(s.split()) <= 4:
            continue
        if len(s.split()) < 4:                       # too short to be a real summary
            continue
        # drop a leading status/label clause ("Status: Confirmed. <real prose>")
        s2 = re.sub(r"^(status|phase|date|owner|decision|result|outcome|verdict|context)\b[^.!?]*[.!?:]\s+",
                    "", s, flags=re.I)
        if len(s2.split()) >= 4:
            s = s2
        m = re.search(r"^(.*?[.!?])(\s|$)", s)
        return (m.group(1) if m else s)[:200]
    return ""


def title_of(path: Path, body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def aslist(v) -> list:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [x for x in v if x not in ("", None)]
    return [v]


def main() -> int:
    root = project_root()
    vault = root / "vault"
    if not vault.is_dir():
        return 0  # no-op: not a vault project

    notes = []
    for md in sorted(vault.rglob("*.md")):
        rel = md.relative_to(vault).as_posix()
        name = md.name
        if name.startswith("_") or name in ("_registry.md", "log.md") or rel.startswith(".obsidian"):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        term = re.search(r"\n---[ \t]*(?:\n|$)", text) if text.startswith("---") else None
        body = text[term.end():] if term else text
        summary = fm.get("description") or first_sentence(body)
        notes.append({
            "note": rel,
            "title": title_of(md, body),
            "areas": [a.lower() for a in aslist(fm.get("areas"))],
            "files": aslist(fm.get("files")),
            "symptoms": aslist(fm.get("symptoms")),
            "failure_mode": fm.get("failure_mode", ""),
            "frameworks": aslist(fm.get("frameworks")),
            "status": fm.get("status", ""),
            "summary": summary,
            "folder": str(Path(rel).parent) if "/" in rel else "",
        })

    # --- lookup map (hook reads this) ---
    by_file_glob, by_area = [], {}
    for n in notes:
        entry = {"note": n["note"], "title": n["title"], "key": n["summary"]}
        for g in n["files"]:
            by_file_glob.append({"glob": g, **entry})
        for a in n["areas"]:
            by_area.setdefault(a, []).append(entry)

    # Bash triggers are OPT-IN per project to avoid noise (Codex caution):
    # read vault/.recall-triggers.json if present, else empty.
    bash_triggers = []
    trig = vault / ".recall-triggers.json"
    if trig.is_file():
        try:
            bash_triggers = json.loads(trig.read_text(encoding="utf-8"))
        except Exception:
            bash_triggers = []

    recall_map = {
        "version": 1,
        "note_count": len(notes),
        "by_file_glob": by_file_glob,
        "by_area": by_area,
        "bash_triggers": bash_triggers,
    }
    atomic_write(vault / ".recall-map.json",
                 json.dumps(recall_map, indent=2, ensure_ascii=False) + "\n")

    # --- human-readable registry ---
    folders: dict = {}
    for n in notes:
        folders.setdefault(n["folder"] or ".", []).append(n)
    lines = ["---", "tags: [index, generated]", "---", "",
             "# Vault registry",
             "",
             f"_Auto-generated by `vault-recall-build.py` — do not edit by hand. {len(notes)} notes._",
             ""]
    for folder in sorted(folders):
        lines.append(f"## {folder}" if folder != "." else "## (root)")
        lines.append("")
        lines.append("| Note | Areas | Summary |")
        lines.append("|------|-------|---------|")
        for n in sorted(folders[folder], key=lambda x: x["title"].lower()):
            areas = ", ".join(n["areas"]) or "—"
            summ = (n["summary"] or "").replace("|", "\\|")[:120]
            lines.append(f"| [[{Path(n['note']).stem}]] | {areas} | {summ} |")
        lines.append("")
    atomic_write(vault / "_registry.md", "\n".join(lines))

    return 0


if __name__ == "__main__":
    sys.exit(main())
