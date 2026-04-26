#!/usr/bin/env bash
# bootstrap.sh — Set up ~/.claude/ on a new machine.
# Safe to run multiple times (idempotent).

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✓${RESET} $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET} $*"; }
err()  { echo -e "${RED}  ✗${RESET} $*"; }
section() { echo -e "\n${BOLD}$*${RESET}"; }

# ─── Preflight checks ────────────────────────────────────────────────────────

section "Checking prerequisites"

if command -v claude &>/dev/null; then
  CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
  ok "Claude Code found: $CLAUDE_VERSION"
else
  err "Claude Code not found. Install it from https://claude.ai/code before continuing."
  exit 1
fi

if command -v git &>/dev/null; then
  GIT_VERSION=$(git --version)
  ok "git found: $GIT_VERSION"
else
  err "git not found. Install git before continuing."
  exit 1
fi

# ─── Existing content warning ─────────────────────────────────────────────────

section "Checking ~/.claude/"

if [[ -d "$CLAUDE_DIR" ]]; then
  EXISTING_FILES=$(find "$CLAUDE_DIR" -maxdepth 1 -not -name '.*' -not -path "$CLAUDE_DIR" | wc -l | tr -d ' ')
  if [[ "$EXISTING_FILES" -gt 0 ]]; then
    warn "~/.claude/ already exists and contains files."
    warn "This script will not overwrite existing files — it only fills in missing pieces."
  else
    ok "~/.claude/ exists but is empty — proceeding."
  fi
else
  warn "~/.claude/ does not exist. Claude Code may not have been run yet."
  warn "Run 'claude' once to let it initialise, then re-run this script."
  exit 1
fi

# ─── settings.json ────────────────────────────────────────────────────────────

section "Configuring settings.json"

SETTINGS="$CLAUDE_DIR/settings.json"
TEMPLATE="$CLAUDE_DIR/settings.template.json"

if [[ -f "$SETTINGS" ]]; then
  ok "settings.json already exists — skipping (not overwritten)."
elif [[ -f "$TEMPLATE" ]]; then
  cp "$TEMPLATE" "$SETTINGS"
  ok "Copied settings.template.json → settings.json"
else
  warn "settings.template.json not found — cannot create settings.json."
  warn "Make sure this repo was cloned into ~/.claude/ correctly."
fi

# ─── agents/ check ────────────────────────────────────────────────────────────

section "Checking agents"

AGENTS_DIR="$CLAUDE_DIR/agents"
for agent in triage-orchestrator codex-reviewer vault-manager code-reviewer security-auditor github-pm; do
  if [[ -f "$AGENTS_DIR/$agent.md" ]]; then
    ok "Agent present: $agent"
  else
    warn "Agent missing: $agent.md — check your clone is complete."
  fi
done

# ─── templates/ check ─────────────────────────────────────────────────────────

section "Checking templates"

TEMPLATES_DIR="$CLAUDE_DIR/templates"
for tmpl in decision session-log api-contract pattern bug gotcha; do
  if [[ -f "$TEMPLATES_DIR/$tmpl.md" ]]; then
    ok "Template present: $tmpl.md"
  else
    warn "Template missing: $tmpl.md — check your clone is complete."
  fi
done

# ─── Manual steps checklist ───────────────────────────────────────────────────

section "Manual steps remaining"

cat <<'CHECKLIST'

  Complete these steps by hand — they cannot be automated safely:

  [ ] 1. Open ~/.claude/settings.json and verify the permissions lists
         match your workflow. Adjust allow/ask/deny as needed.

  [ ] 2. If you use the session-logger hook, create or symlink
         ~/.claude/session-logger.sh and make it executable:
           chmod +x ~/.claude/session-logger.sh

  [ ] 3. Add your SSH key to GitHub/GitLab so you can push this repo:
           ssh-keygen -t ed25519 -C "your@email.com"
           # then add ~/.ssh/id_ed25519.pub to your git host

  [ ] 4. If this machine uses any Claude API keys or MCP tokens,
         add them to your shell profile (~/.zshrc or ~/.zprofile),
         NOT to settings.json.

  [ ] 5. Initialise ~/.claude/ as a git repo if not already done:
           cd ~/.claude
           git init
           git remote add origin <your-remote-url>
           git add CLAUDE.md agents/ templates/ settings.template.json bootstrap.sh .gitignore
           git commit -m "Initial claude-config"
           git push -u origin main

CHECKLIST

echo -e "${GREEN}${BOLD}Bootstrap complete.${RESET} Review the checklist above before starting work.\n"
