# claude-config

Global Claude Code configuration, shared across all devices and projects.

## What's in here

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Global instructions loaded automatically by Claude Code every session |
| `agents/` | Orchestrator and specialist agents |
| `templates/` | Obsidian note templates (decision, session log, API contract) |
| `commands/` | Custom slash commands |
| `settings.template.json` | Starter settings — copy to `settings.json` and customise |
| `bootstrap.sh` | New machine setup script |

## New machine setup

```bash
git clone git@github.com:biffdownhill/claude-config.git ~/.claude
~/.claude/bootstrap.sh
```

Then add the shell setup below to your `~/.zshrc` (or `~/.bashrc`).

## Shell setup

Add this to your shell profile (`~/.zshrc` or `~/.bashrc`) and `source` it:

```bash
# Enable custom agents (triage-orchestrator, vault-manager, etc.)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# `co` opens Claude Code straight into the triage-orchestrator agent,
# which classifies the request and dispatches to the right specialist.
alias co="claude --agent triage-orchestrator"
```

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

After Claude updates config files (agents, CLAUDE.md, templates):
```bash
cd ~/.claude && git add -p && git commit -m "update config" && git push
```
