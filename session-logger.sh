#!/bin/bash
# ~/.claude/session-logger.sh
# Writes a session stub to the project's vault/Sessions/ when a session ends.
# Skips silently if no vault exists — vault creation is the vault-manager's job.

# Read hook JSON input from stdin
INPUT=$(cat)

# Extract fields
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

# Run in background — exit fast
(
  SESSIONS_DIR="$CWD/vault/Sessions"

  # Skip if no vault exists in this project
  if [[ ! -d "$SESSIONS_DIR" ]]; then
    echo "$(date -u +%FT%TZ) no vault/Sessions/ in $CWD — skipping" >> "$HOME/.claude/session-logger.log"
    exit 0
  fi

  TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
  DATE=$(date -u +"%Y-%m-%d")
  SESSION_FILE="$SESSIONS_DIR/${DATE}-${SESSION_ID:0:8}.md"

  cat > "$SESSION_FILE" <<MARKDOWN
---
date: $DATE
tags: [session]
session_id: $SESSION_ID
cwd: $CWD
transcript: $TRANSCRIPT_PATH
related: []
---

## What we did

## What changed

## Decisions made

## Next steps
- [ ] 
MARKDOWN

  echo "$(date -u +%FT%TZ) wrote $SESSION_FILE" >> "$HOME/.claude/session-logger.log"
) &>/dev/null &

exit 0
