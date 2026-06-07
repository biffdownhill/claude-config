#!/usr/bin/env python3
"""Ambient vault recall — PreToolUse hook.

Fires before Edit/MultiEdit/Write/NotebookEdit/Bash. Surfaces the vault note(s)
relevant to what the model is about to do, by querying vault/.recall-map.json.

Precision-first (Codex caution): only injects on an exact file-glob match, or an
opt-in Bash trigger. Silent on weak/no match. Caps at 2 notes. Self-heals stale
maps via an mtime check so manual edits / git pulls don't serve dead references.

Reads the hook event JSON on stdin; emits PreToolUse additionalContext on stdout.
Never blocks a tool — on any error it exits 0 silently.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_NOTES = 2
MAX_CHARS = 1600  # ~400 tokens


def root_from(data: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())


def glob_match(path: str, pattern: str) -> bool:
    """Glob match where `*` stays within a path segment and `**` spans separators.
    (No fnmatch fallback — fnmatch lets `*` cross `/`, which would over-match e.g.
    a bare `*.ts` glob against deeply-nested files.)"""
    rx = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.fullmatch(rx, path) is not None


def fresh_map(vault: Path) -> dict | None:
    mp = vault / ".recall-map.json"
    if not mp.is_file():
        return None
    # Self-heal: rebuild if any note is newer than the map.
    try:
        map_mtime = mp.stat().st_mtime
        stale = any(p.stat().st_mtime > map_mtime
                    for p in vault.rglob("*.md")
                    if not p.name.startswith("_") and p.name != "log.md")
        if stale:
            builder = Path(__file__).resolve().parent.parent / "scripts" / "vault-recall-build.py"
            if builder.is_file():
                subprocess.run([sys.executable, str(builder), str(vault.parent)],
                               timeout=10, capture_output=True)
    except Exception:
        pass
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return None


def matches_for(tool: str, tinput: dict, root: Path, rmap: dict) -> list:
    hits, seen = [], set()

    def add(entry):
        if entry["note"] not in seen:
            seen.add(entry["note"])
            hits.append(entry)

    if tool in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
        fp = tinput.get("file_path") or tinput.get("path") or ""
        if not fp:
            return []
        try:
            rel = Path(fp).resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            rel = fp
        for g in rmap.get("by_file_glob", []):
            if glob_match(rel, g["glob"]):
                add(g)
    elif tool == "Bash":
        cmd = (tinput.get("command") or "").lower()
        for trig in rmap.get("bash_triggers", []):
            pat = str(trig.get("pattern", "")).lower()
            if pat and pat in cmd:
                for entry in rmap.get("by_area", {}).get(trig.get("area", ""), []):
                    add(entry)
    return hits[:MAX_NOTES]


def log_injection(vault: Path, tool: str, target: str, hits: list) -> None:
    """Append one line per injection for the periodic precision check. Best-effort."""
    try:
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
               "tool": tool, "target": target[:200], "notes": [h["note"] for h in hits]}
        with open(vault / ".recall-log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        tool = data.get("tool_name", "")
        if tool not in ("Edit", "MultiEdit", "Write", "NotebookEdit", "Bash"):
            return 0
        root = root_from(data)
        vault = root / "vault"
        rmap = fresh_map(vault)
        if not rmap:
            return 0

        tinput = data.get("tool_input", {})
        hits = matches_for(tool, tinput, root, rmap)
        if not hits:
            return 0

        target = tinput.get("file_path") or tinput.get("path") or tinput.get("command") or ""
        log_injection(vault, tool, target, hits)

        parts = ["📓 Relevant vault note(s) — check before proceeding so a past mistake isn't repeated:"]
        for h in hits:
            parts.append(f"• \"{h['title']}\": {h['key']}  (vault/{h['note']})")
        ctx = "\n".join(parts)
        if len(ctx) > MAX_CHARS:                       # truncate on a whole-line boundary
            ctx = ctx[:MAX_CHARS].rsplit("\n", 1)[0]

        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": ctx,
        }}))
    except Exception:
        return 0  # never block a tool
    return 0


if __name__ == "__main__":
    sys.exit(main())
