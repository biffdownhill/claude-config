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
vault-manager agent handles all vault interactions:

- **On session start:** scan `vault/` if it exists, read the folder structure,
  and infer conventions already in use before touching anything.
- **New vaults:** initialised with `Sessions/`, `Decisions/`, and `Context.md`.
  Always subfolders from day one — never flat.
- **Placing files:** existing folder structure is the guide. Never create
  folders that clash with or duplicate existing ones.
- **Reorganisation:** flagged to the user when a folder exceeds ~20 files;
  always proposed, never imposed.

Claude should never impose vault structure — read what exists and work within it.
