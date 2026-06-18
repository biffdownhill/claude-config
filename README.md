# claude-config

Global Claude Code configuration, shared across all devices and projects.

## What's in here

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Global instructions loaded automatically by Claude Code every session |
| `commands/` | Custom slash commands |
| `settings.template.json` | Starter settings — copy to `settings.json` and customise |
| `bootstrap.sh` | New machine setup script |

The triage-orchestrator, the specialist agents, the vault-recall hooks, and
the Obsidian note templates now live in the **`orchestrator@downhill-tools`
plugin** (installed via the plugin marketplace) — they are no longer kept in
`~/.claude/agents` or `~/.claude/templates`. See [Orchestrator plugin](#orchestrator-plugin).

## New machine setup

```bash
git clone git@github.com:biffdownhill/claude-config.git ~/.claude
~/.claude/bootstrap.sh
```

Then install the orchestrator plugin (see below) and add the shell setup below
to your `~/.zshrc` (or `~/.bashrc`).

## Orchestrator plugin

The triage-orchestrator agent, the specialist agents (code-reviewer,
codex-reviewer, design-reviewer, security-auditor, vault-manager, github-pm),
the vault-recall hooks (SessionStart + PreToolUse), and the
`/orchestrator:init` command are distributed as the `orchestrator@downhill-tools`
plugin rather than as standalone files in `~/.claude/`. Install it once per
machine:

```bash
claude plugin marketplace add git@github.com:biffdownhill/downhill-tools.git
claude plugin install orchestrator@downhill-tools
```

Or, interactively from inside Claude Code:

```
/plugin install orchestrator@downhill-tools
```

## Shell setup

Add this to your shell profile (`~/.zshrc` or `~/.bashrc`) and `source` it:

```bash
# Enable custom agents (triage-orchestrator, vault-manager, etc.)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# `co` opens Claude Code straight into the triage-orchestrator agent,
# which classifies the request and dispatches to the right specialist.
alias co="claude --agent triage-orchestrator"
```

The `triage-orchestrator` agent referenced by `co` is provided by the
`orchestrator@downhill-tools` plugin, so install the plugin (above) before
relying on the alias.

The `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` flag is required — without it
the `--agent` argument is ignored and `co` falls back to a plain session.

Verify after restarting the shell:
```bash
co --help   # should show Claude Code's help, not "command not found"
```

## Keeping in sync

Pull changes from another device:
```bash
cd ~/.claude && git pull
```

After Claude updates config files (CLAUDE.md, commands, settings template):
```bash
cd ~/.claude && git add -p && git commit -m "update config" && git push
```
