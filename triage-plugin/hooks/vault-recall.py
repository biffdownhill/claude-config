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


def rebuild_map(vault: Path) -> None:
    """Run the bundled builder to regenerate the map. The builder sits beside this
    hook in the plugin layout (<plugin>/hooks/vault-recall.py ->
    <plugin>/scripts/vault-recall-build.py), so parent.parent / "scripts" resolves
    to it. A broken path is logged to stderr rather than swallowed — a silent miss
    here is the bug this self-heal exists to avoid (a stale/dead map served forever)."""
    builder = Path(__file__).resolve().parent.parent / "scripts" / "vault-recall-build.py"
    if builder.is_file():
        subprocess.run([sys.executable, str(builder), str(vault.parent)],
                       timeout=10, capture_output=True)
    else:
        print(f"vault-recall: builder not found at {builder} — "
              "recall map may be stale", file=sys.stderr)


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
            rebuild_map(vault)
    except Exception as e:
        print(f"vault-recall: self-heal rebuild failed: {e}", file=sys.stderr)
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        # The map is present but malformed (corrupt/partial JSON). Don't silently
        # disable recall for the session — rebuild once and re-read.
        try:
            rebuild_map(vault)
            return json.loads(mp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"vault-recall: rebuild after parse failure failed: {e}", file=sys.stderr)
            return None


def matches_for(tool: str, tinput: dict, root: Path, rmap: dict):
    """Return (hits, log_target). `log_target` is a NON-SENSITIVE descriptor safe
    to persist: a file path for edits, or the matched trigger pattern for Bash —
    never the raw command string (which can carry secrets)."""
    hits, seen = [], set()
    log_target = ""
    matched_patterns: list[str] = []

    def add(entry):
        if entry["note"] not in seen:
            seen.add(entry["note"])
            hits.append(entry)

    if tool in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
        fp = tinput.get("file_path") or tinput.get("path") or ""
        if not fp:
            return [], ""
        try:
            rel = Path(fp).resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            # Path is outside the project root (or unresolvable). Don't fall back
            # to the raw unvalidated string as a glob operand — return no hits.
            return [], ""
        log_target = rel
        for g in rmap.get("by_file_glob", []):
            if glob_match(rel, g["glob"]):
                add(g)
    elif tool == "Bash":
        cmd = (tinput.get("command") or "").lower()
        triggers = rmap.get("bash_triggers", [])
        if not isinstance(triggers, list):                     # guard malformed map
            triggers = []
        for trig in triggers:
            if not isinstance(trig, dict):                     # guard malformed entries
                continue
            pat = str(trig.get("pattern", "")).lower()
            if pat and pat in cmd:
                matched_patterns.append(pat)
                for entry in rmap.get("by_area", {}).get(trig.get("area", ""), []):
                    add(entry)
        # Log only the matched trigger pattern(s) — never the raw command.
        log_target = "bash-trigger:" + ",".join(matched_patterns)
    return hits[:MAX_NOTES], log_target


def log_injection(vault: Path, tool: str, target: str, hits: list) -> None:
    """Append one line per injection for the periodic precision check. Best-effort.
    `target` must already be a non-sensitive descriptor (see matches_for)."""
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
        if tool not in ("Edit", "MultiEdit", "Write", "NotebookEdit", "Bash", "EnterPlanMode"):
            return 0
        root = root_from(data)
        vault = root / "vault"
        rmap = fresh_map(vault)
        if not rmap:
            return 0

        if tool == "EnterPlanMode":                    # planning — nudge a vault search
            areas = sorted(rmap.get("by_area", {}).keys())
            if not areas:
                return 0
            ctx = ("📓 This project has a knowledge vault covering: " + ", ".join(areas)
                   + ". Search it as part of planning — read vault/_registry.md or grep vault/ "
                   "for prior decisions, patterns, and gotchas in the areas this plan touches, "
                   "and fold them in before finalising.")
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "additionalContext": ctx}}))
            return 0

        tinput = data.get("tool_input", {})
        hits, log_target = matches_for(tool, tinput, root, rmap)
        if not hits:
            return 0

        log_injection(vault, tool, log_target, hits)

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
