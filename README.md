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

## Keeping in sync

Pull changes from another device:
```bash
cd ~/.claude && git pull
```

After Claude updates config files (agents, CLAUDE.md, templates):
```bash
cd ~/.claude && git add -p && git commit -m "update config" && git push
```
