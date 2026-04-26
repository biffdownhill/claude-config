# Global Claude Code Instructions

These apply to every Claude Code session. Project-level CLAUDE.md files
override these when they conflict.

## Quality bar

- Compile-time errors preferred over runtime errors whenever the language
  supports it
- Thorough tests: unit AND integration; smoke tests alone are not enough
- Reuse patterns already present in the codebase rather than inventing new ones
- Never disable a test, type check, or linter to make something pass
- Never commit secrets, .env files, or credentials
- Match the existing code style of the project; don't rewrite in a different style

## About me

- I am in Singapore timezone.
- I am originally a Swift/SwiftUI developer, so if you need to explain any technical concept in a language I am unfamiliar with and having a tough time understanding, try using a Swift analogy to explain your answer.

### How I like output

- Direct and concrete over hedged and exhaustive.
- Show the actual change, not a summary of what will change.
- When offering options, name the tradeoffs plainly.

## Patterns

<!-- Coding patterns and conventions used across projects -->
<!-- e.g. "Always use named exports. Prefer functional components in React." -->

### General

- If you are unsure of an approach, you should show your indecisiveness in your response. Don't be unnecessarily confident if the answer isn't obvious. I'd rather you say you aren't sure than be very confidently wrong.
- When I make a suggestion or question an approach, don't just accept what I've said. Weigh up and evaluate all options and make a decision based on what is most beneficial for that case.
- If you require more context to ensure your output/response is high quality, feel free to ask any questions to me surrounding areas you are unsure about or feel that more information would be helpful.
- Always write using British English, NOT US English unless explicitly told otherwise.
- Plan before implementing on anything non-trivial — surface tradeoffs and decisions, don't hide them.
- Keep me in the loop on irreversible actions; otherwise just proceed.

### Coding

- Only add in-line comments if you're copying them from pre-existing code or if they provide context to functionality the code may not immediately reflect, or for strange implementations that require explanation.
- Always be mindful of the code quality. Ensure that your code is correctly laid out in the relevant files/directories and aligned with the style of the rest of the code in the codebase.
- Before running code, check the package manager of the project (e.g., yarn/bun/npm).

## Lessons learned

<!-- Cross-project lessons: pitfalls encountered, approaches that worked -->
<!-- e.g. "Drizzle schema changes require explicit migration generation step." -->

## Orchestration

If you are in a plain Claude session and the request is non-trivial, suggest
switching to the **triage-orchestrator** agent — it classifies work into tiers
and dispatches to the right specialists. For quick questions or small edits,
handle directly without ceremony.

## Project vaults

Each project keeps its own Obsidian vault at `<project-root>/vault/`. The
**vault-manager** agent owns all vault interactions and conventions — see
`~/.claude/agents/vault-manager.md` for the rules.

The auto-session-logger writes minimal session stubs to `<cwd>/vault/Sessions/`
when a vault exists, and skips silently otherwise. Vault-manager later enriches
those stubs in place.

## Project tracking

Projects may have a `<project-root>/.claude/pm.json` file declaring an active PM
agent for ticket and epic management. The triage-orchestrator reads this file and
invokes the named agent (e.g. `github-pm`) for Tier 2/3 work.

- **Contract:** `~/.claude/contracts/pm.md` — defines the capability set every PM
  agent implements (status vocabulary, approval gates, error categories).
- **Implementations:** `~/.claude/agents/<backend>-pm.md` — currently `github-pm`
  (GitHub Projects via the `gh` CLI).
- **Setup:** `/pm:init` (forthcoming) creates `pm.json` and configures the backend.
- **Adding a backend:** copy an existing `*-pm.md`, point it at the new tooling,
  implement every contract operation.

Projects without `pm.json` operate without tracking. Don't impose ticketing on
projects that haven't asked for it.
