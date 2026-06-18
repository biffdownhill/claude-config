---
description: Scaffold or update .claude/orchestrator.json — the per-project manifest that opts a project into orchestration machinery (reviews, PM tracking, knowledge vault). Also the re-entry point to re-enable capabilities after a previous decline.
allowed-tools: Read, Write, Glob, Bash(git log:*), Bash(ls:*), Bash(test:*)
---

# /orchestrator:init

You are scaffolding (or updating) the triage-orchestrator manifest for the
current project. The manifest lives at `<project-root>/.claude/orchestrator.json`
and is a flat role→agent map that opts the project into orchestration phases.
A role that is `null` or omitted disables the phase(s) that depend on it.

This command is also the **re-entry point after a decline** — if a previous
session recorded a decline (an empty manifest or `{"declined": true}`), running
this command re-enables whichever capabilities the user now wants. A decline is
never a one-way door.

## The manifest schema

```jsonc
{
  "pm":        "github-pm" | null,         // ticket/epic tracking agent — names the agent only
  "vault":     "vault-manager" | null,     // project knowledge-vault agent
  "reviewers": ["code-reviewer", ...] | null,  // PRESENCE-ONLY; order ignored (orchestrator owns ordering)
  "security":  "security-auditor" | null   // conditional security pass on sensitive changes
}
```

- **`reviewers` is presence-only.** Listing an agent enables that review. The
  orchestrator decides the order they run in — do not try to encode ordering here.
- **`pm` names the agent only.** Backend config (repo, project id, etc.) stays in
  `.claude/pm.json` — the PM contract is unchanged. `orchestrator.json`'s `"pm"`
  value just tells the orchestrator which PM agent to invoke.
- Any role may be `null` or omitted to switch its phases off.
- A manifest with no enabled roles (e.g. `{}`) or `{"declined": true}` is a
  recorded decline: the orchestrator stays silent and will not re-prompt.

## What to do

1. **Resolve the project root and existing state.**
   - Determine `<project-root>` (the directory the user is working in).
   - Read `.claude/orchestrator.json` if it already exists — you are editing, not
     clobbering. Show the user the current contents.

2. **Detect what the project already has, so defaults are sensible:**
   - `test -f .claude/pm.json` → if present, the project already tracks tickets.
     **Migration:** default `"pm"` to the `pm_agent` value declared inside
     `pm.json` (read it). The orchestrator manifest only NAMES the agent; the
     backend config stays in `pm.json`.
   - `test -d vault` → if a `vault/` directory exists, the project already keeps a
     knowledge vault. **Migration:** default `"vault"` to `"vault-manager"`.
   - Reviewers default to the bundled set: `code-reviewer`, `design-reviewer`,
     `codex-reviewer`. Security defaults to `security-auditor`.

3. **Confirm with the user before writing.** Present the manifest you intend to
   write and let them trim it. Make the tiering explicit:
   - **Reviewers** are stateless and leave zero project footprint — reasonable to
     enable by default.
   - **PM and vault** are a separate, heavier opt-in (they create tickets / write
     files). Only enable them if the user wants them, or if migration detected an
     existing `pm.json` / `vault/`.

4. **Write `.claude/orchestrator.json`.** Create the `.claude/` directory if
   needed. Write valid JSON (no comments). Omit or `null` any role the user
   declined. If the user wants nothing enabled, write `{}` (a recorded decline) so
   the orchestrator stays silent — and tell them this command re-enables later.

5. **Report** the final manifest path and contents, and remind the user that:
   - editing the file by hand is fine (it is read with the Read tool, not enforced);
   - `/orchestrator:init` can be re-run any time to change what is enabled;
   - PM backend setup still lives in `.claude/pm.json`.

## Migration cheat-sheet

| Project already has… | Set in `orchestrator.json` |
|----------------------|-----------------------------|
| `.claude/pm.json`    | `"pm": "<pm_agent from pm.json>"` |
| `vault/` directory   | `"vault": "vault-manager"` |
| neither              | leave `pm`/`vault` out; enable reviewers only if wanted |

$ARGUMENTS
