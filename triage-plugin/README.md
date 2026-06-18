# triage-orchestrator

A Claude Code plugin that makes a tiered **triage orchestrator** your default
main-thread agent. It classifies every request into a tier and dispatches the
right amount of ceremony — answer trivial things directly, hand real work to
bundled specialists, and run review / project-tracking / knowledge-vault phases
**only when a project opts into them**.

The design goal is restraint: mature repos should not get vault, PM, or review
machinery forced on them. Everything beyond plain classification is opt-in per
project via a small manifest the orchestrator reads at runtime.

## What's in the box

- **`triage-orchestrator`** — the main agent. Reads `.claude/orchestrator.json`,
  classifies into Tier 1/2/3, and runs only the phases the manifest declares.
- **Reviewers** — `code-reviewer`, `design-reviewer`, `codex-reviewer` (and
  `security-auditor` for sensitive changes). Stateless: they read the diff and
  report, leaving no project footprint.
- **`github-pm`** — ticket/epic management via GitHub Projects v2, implementing
  the bundled PM contract (`contracts/pm.md`).
- **`vault-manager`** — manages a per-project Obsidian knowledge vault.
- **Ambient recall hook** — surfaces relevant vault notes before edits and
  planning, and rebuilds the lookup map on session start. No-ops silently when a
  project has no `vault/`.
- **`/orchestrator:init`** — scaffolds or updates the per-project manifest.

## Tiers, in one line each

- **Tier 1** — questions, reading, trivial single-file edits. Handled directly,
  zero ceremony. On a project with no manifest the orchestrator behaves exactly
  like plain Claude here — it never prompts.
- **Tier 2** — one self-contained feature/fix/refactor → one specialist, then the
  declared reviews.
- **Tier 3** — multi-area work → inline plan-and-approval, optional epic
  breakdown (if PM is declared), implementation, then reviews.

## Install / enable

Plugins are installed from a **marketplace**. For a personal setup shared with a
friend, the simplest marketplace is this repo (or any directory) containing a
`.claude-plugin/marketplace.json` that lists the plugin.

### 1. Make a local marketplace

If your dotfiles repo doesn't already have one, add `.claude-plugin/marketplace.json`
at the repo root (sibling to `triage-plugin/`):

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "downhill-tools",
  "owner": { "name": "Edward Downhill", "email": "biffdownhill@gmail.com" },
  "plugins": [
    { "name": "triage-orchestrator", "source": "./triage-plugin" }
  ]
}
```

### 2. Add the marketplace and install the plugin

```
/plugin marketplace add /Users/edwarddownhill/.claude        # local path to the repo
/plugin install triage-orchestrator@downhill-tools
```

A friend installs the same way from their clone:

```
/plugin marketplace add /path/to/their/clone
/plugin install triage-orchestrator@downhill-tools
```

Or, if the repo is on GitHub:

```
/plugin marketplace add <github-user>/<repo>
/plugin install triage-orchestrator@downhill-tools
```

### 3. The plugin makes itself the default agent

The plugin's `settings.json` sets `{ "agent": "triage-orchestrator" }`, so once
enabled the orchestrator becomes the default main-thread agent globally. No
manual `settings.json` edit is needed.

> **Migrating off the standalone setup.** This repo also carries a top-level
> `agents/`, `hooks/`, and `scripts/` plus a machine-local `settings.json` that
> wired the orchestrator the old way. Those are intentionally left in place so
> nothing breaks mid-migration. Once the plugin is installed and verified, you
> can drop `"agent"` and the two hook entries from your `~/.claude/settings.json`
> — the plugin supplies all three. Verify first, cut over second.

## The manifest: `.claude/orchestrator.json`

A project opts into orchestration phases with a flat role→agent map at
`<project-root>/.claude/orchestrator.json`. The orchestrator reads it with the
Read tool — plugins can't enforce a nested config schema, so the file is plain
data, not validated config. The schema is documented in
[`orchestrator.schema.json`](./orchestrator.schema.json); a copy-and-trim
example is in [`orchestrator.example.json`](./orchestrator.example.json).

```json
{
  "pm": "github-pm",
  "vault": "vault-manager",
  "reviewers": ["code-reviewer", "design-reviewer", "codex-reviewer"],
  "security": "security-auditor"
}
```

Rules:

- **Any role may be `null` or omitted.** A role that isn't declared has its
  phases **silently skipped** — no announcement, no offer.
- **`reviewers` is presence-only.** Listing an agent enables that review. **List
  order is ignored** — the orchestrator owns review ordering
  (code → security → design → codex).
- **`"pm"` names the agent only.** PM backend config (repo, project id, …) stays
  in `.claude/pm.json` — the PM contract is unchanged. You need *both* a `"pm"`
  entry here and a `.claude/pm.json` to track tickets.
- **An empty manifest (`{}`) is a recorded decline.** The orchestrator treats it
  as opted-out and never re-prompts. Re-run `/orchestrator:init` to re-enable.

### Examples

Reviews only (the lightest useful setup — no project footprint):

```json
{ "reviewers": ["code-reviewer", "design-reviewer", "codex-reviewer"], "security": "security-auditor" }
```

Reviews plus tracking, no vault:

```json
{ "pm": "github-pm", "reviewers": ["code-reviewer", "codex-reviewer"], "security": "security-auditor" }
```

Opted out entirely (recorded decline):

```json
{}
```

## First-run behaviour (no manifest yet)

The orchestrator is deliberately quiet until work is big enough to warrant a
decision:

- **Tier 1 — silent.** Acts like plain Claude. Never prompts.
- **First Tier 2+ work — prompts once, tiered:**
  - **Reviews — default ON.** Stateless, zero footprint.
  - **PM tracking + knowledge vault — separate, explicit opt-in, default OFF.**
    These *write* to the project (tickets, vault files).
- **It persists your answer** to `.claude/orchestrator.json`, so it never asks
  again. Decline everything and it writes `{}` (a recorded decline) and tells you
  `/orchestrator:init` re-enables later. A decline is **not** a one-way door.

## Migrating an existing project

If a project already used the standalone setup, run `/orchestrator:init` — it
detects existing state and pre-fills the manifest:

| Project already has… | `/orchestrator:init` sets |
|----------------------|----------------------------|
| `.claude/pm.json`    | `"pm": "<pm_agent from pm.json>"` (backend config stays in `pm.json`) |
| `vault/` directory   | `"vault": "vault-manager"` |
| neither              | reviewers only (if you want them) |

You can also just hand-write `.claude/orchestrator.json` — it's plain data.

## Notes

- British English throughout.
- The ambient-recall hook and the map builder run on every session the plugin is
  enabled, but **no-op silently** in any project without a `vault/` directory —
  so an enabled plugin costs nothing on repos that haven't opted in.
- The bundled agents reference the plugin's own files via `${CLAUDE_PLUGIN_ROOT}`
  (contract, templates, hook, builder), so the plugin is self-contained.
