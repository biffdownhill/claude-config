# orchestrator

A Claude Code plugin that makes a tiered **triage orchestrator** your default
main-thread agent. It classifies every request into a tier and dispatches the
right amount of ceremony — answer trivial things directly, hand real work to
bundled specialists, and run review / project-tracking / knowledge-vault phases
**only when a project opts into them**.

> **Plugin name vs agent name.** The installable **plugin** is named
> `orchestrator` — it namespaces the plugin's commands (e.g. `/orchestrator:init`).
> The **agent** it ships is named `triage-orchestrator` — that's the value used in
> `settings.json` `"agent"` and passed as `subagent_type` when dispatching to it.
> They are not the same string; don't conflate them.

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

Plugins are installed from a **marketplace**. This plugin ships its own
marketplace manifest at `triage-plugin/.claude-plugin/marketplace.json` (the
marketplace is named `downhill-tools` and lists one plugin, `orchestrator`), so
there's nothing to author — you just point Claude Code at the directory.

### 1. Add the marketplace and install the plugin

Replace `<repo-root>` with the path to your clone of this repo (the directory
that contains `triage-plugin/`):

```
/plugin marketplace add <repo-root>/triage-plugin     # local path to the plugin dir
/plugin install orchestrator@downhill-tools
```

A friend installs the same way from their clone:

```
/plugin marketplace add /path/to/their/clone/triage-plugin
/plugin install orchestrator@downhill-tools
```

Or, if the repo is on GitHub (the marketplace lives in the `triage-plugin`
subdirectory):

```
/plugin marketplace add <github-user>/<repo>
/plugin install orchestrator@downhill-tools
```

### 2. Make the orchestrator the default agent

The plugin's bundled `settings.json` sets `{ "agent": "triage-orchestrator" }`,
so once enabled the orchestrator is offered as the default main-thread agent.

A fresh install needs no cutover — once the plugin is enabled, its bundled
settings take effect. If you previously ran a *standalone* copy of these files in
`~/.claude`, remove any pinned `"agent"` key and the standalone vault-recall hook
entries from your user `~/.claude/settings.json`; a user-level `"agent"` wins over
the plugin's bundled one, so the plugin's settings only take effect once those are
gone.

## The manifest: `.claude/orchestrator.json`

A project opts into orchestration phases with a flat role→agent map at
`<project-root>/.claude/orchestrator.json`. The orchestrator reads it with the
Read tool — plugins can't enforce a nested config schema, so the file is plain
data, not validated config. A ready-to-copy example lives in
[`orchestrator.example.json`](./orchestrator.example.json); the fields and their
rules are documented below.

```json
{
  "pm": "github-pm",
  "vault": "vault-manager",
  "reviewers": ["code-reviewer", "design-reviewer", "codex-reviewer"],
  "security": "security-auditor"
}
```

Fields:

- **`pm`** — names the PM agent for ticket/epic tracking (e.g. `"github-pm"`).
  `null`/omitted disables all PM phases.
- **`vault`** — names the vault agent (e.g. `"vault-manager"`). `null`/omitted
  disables the active vault search, the vault-worthy-findings scan, and
  vault-manager enrichment. (It does **not** disable the ambient `📓` recall hook,
  which runs whenever the plugin is enabled.)
- **`reviewers`** — presence-only list of review agents to run after
  implementation. An empty list or omitted disables all review passes.
- **`security`** — names the security review agent (e.g. `"security-auditor"`).
  Runs only on sensitive changes (auth, secrets, persistence, migrations,
  external APIs, deserialisation, file I/O, shell). `null`/omitted disables it.

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
