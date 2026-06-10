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

- A fresh `git worktree` does not copy gitignored files (`node_modules/`, `.env`,
  `.claude/`). Run `npm ci` (or the project's install) in a new worktree before any
  tooling that needs deps present — e.g. `npx expo install` requires the `expo`
  module to detect the SDK. Also copy/recreate gitignored local config the task
  needs (e.g. `.claude/pm.json`) into the worktree.
- **bun gotchas (from the ShelfLife npm→bun migration):**
  - bun ≥1.2 writes a **text** `bun.lock` (lockfileVersion 1), not the old binary
    `bun.lockb`. Don't expect a `.lockb`. Railway Nixpacks needs **≥1.36.0** to detect
    the text format (older Nixpacks only read `bun.lockb`); EAS Build and
    `oven-sh/setup-bun` detect it fine.
  - `bun test` runs bun's **native** test runner and bypasses the `"test"` package.json
    script — use `bun run test` to invoke vitest/jest. Any script whose name collides
    with a bun builtin needs `bun run`, not bare `bun`.
  - bun **does not run dependency postinstall scripts** unless the package is listed in
    `"trustedDependencies"`. After `bun install`, check the "Blocked N postinstall"
    output and trust only deps a CI/runtime step actually exercises (e.g. a NAPI binding
    a linter loads); leave the rest blocked if they have a JS fallback.
  - EAS Build and Railway Nixpacks auto-detect the package manager from the lockfile —
    deleting `package-lock.json` and committing `bun.lock` is enough; no config flag
    needed. The `packageManager` field is a secondary signal.
  - In CI, keep `actions/setup-node` (for the Node version pin some tooling resolves
    against) **alongside** `oven-sh/setup-bun` — bun runs the JS but doesn't replace Node.
- **Expo/RN runtime config & environment switching (from ShelfLife #27 app-architecture):**
  - No mechanism reliably relaunches the **OS process** cross-platform: `expo-updates`
    `reloadAsync`, `react-native-restart`, and `DevSettings.reload()` all reload the JS
    bundle, not the native process, and iOS has **no public self-kill API**. So any
    "switch environment/config at runtime" feature must be a JS-tree remount **plus a
    cold-start seam** for native-init-once SDKs (Sentry's native crash handler, etc.) that
    genuinely cannot re-init in-process. Model it with two persisted fields — `activeEnv`
    (running now) and `pendingEnv` (promoted on next cold launch) — and a per-module
    capability flag (`runtime` vs `cold-start`); never hot-swap live native singletons or
    silently pin them to a build-default env (both are debugging traps).
  - `app.config.ts` should be the **single** reader of `process.env`; runtime code reads
    resolved values from `expo-constants` (`Constants.expoConfig.extra`). Expo passes the
    static `app.json` into `app.config.ts` as `ConfigContext.config` automatically — layer
    dynamic values on top, no manual import. Verify with `expo config --json`.
  - Multi-env safety is best enforced by **omission at build time** (a public/prod build
    never receives the non-prod env vars, so they can't be bundled), with a zod schema as a
    second guard. Validate env values as **grouped per-env objects** (URL+key as a pair) and
    check a non-secret **project-ref sentinel** so one env can't be pointed at another's
    backend. Reject secret-prefixed keys (`sb_secret_…`) at **build time**, not just at
    launch, so a secret never compiles into the binary.
  - An unstable inline callback in a React `useMemo`/`useCallback` dependency array
    silently busts the memo with **no type or lint signal** — wrap callbacks passed as memo
    deps in `useCallback` with stable deps (e.g. a `useState` setter).

## Frameworks evaluated

Decisions about external frameworks I considered adopting but ultimately didn't, so future-me can find the reasoning instead of re-evaluating from scratch. Full evaluation: `~/.claude/plans/i-want-you-to-calm-reddy.md` (2026-04-28).

- **Karpathy `llm-council` (multi-model deliberation)** — not adopted. Three-stage chairman synthesis is genuinely useful for open-ended judgement (essay quality, "library A vs B"), but for code review it adds noise — code has ground truth and I want raw reviewer reports, not a synthesised opinion. The existing `code-reviewer` + `codex-reviewer` + `security-auditor` pipeline already covers multi-perspective review at the right cost. **Revisit only** if Tier 3 architecture decisions routinely produce conflicting reviewer verdicts I can't arbitrate, or evaluation tasks become common enough that confirmation-bias mitigation is worth the cost. Implementation, if it ever happens, is *not* the upstream web app — it's a small `council-judge` agent that fans plans out via OpenRouter and returns rankings (no chairman).
- **Karpathy "LLM Wiki" pattern (Obsidian as a research wiki)** — not adopted wholesale. The vault-manager system is more rigorous than the gist (typed templates, mandatory frontmatter, lazy folders, grep-before-create, 7-day health checks). Borrowed only `index.md` (note catalogue) and `log.md` (chronological feed) into vault-manager. The "ingest external research sources" framing is a different problem domain — the vault is a project memory, not a literature wiki.

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

**Ambient recall.** Vault notes surface automatically, with no conscious "search
the vault" step:
- A global `PreToolUse` hook (`~/.claude/hooks/vault-recall.py`) fires before
  `Edit/MultiEdit/Write/NotebookEdit/Bash`. It reads `vault/.recall-map.json` and
  injects a `📓` reminder with the note(s) whose `files:` glob matches the file
  being edited (or whose `area` matches an opt-in Bash trigger). Precision-first:
  ≤2 notes, silent on weak matches. **When a `📓` note appears, read it before
  proceeding** — it's flagging a past mistake.
- **Planning is a recall trigger too.** On `EnterPlanMode` the hook injects the
  vault's area list with a directive to search it before finalising the plan. And
  the triage-orchestrator's own Tier 2/3 planning phases require a vault search as
  a step (it doesn't use plan mode). So however a plan is formed — Claude Code plan
  mode or the orchestrator — prior decisions/patterns/gotchas inform it.
- A `SessionStart` hook regenerates the lookup map + `vault/_registry.md` (the
  human-readable catalogue) via `~/.claude/scripts/vault-recall-build.py`. The
  recall hook also self-heals a stale map mid-session.
- Both no-op silently in projects with no `vault/`, so this needs **zero per-project
  setup** — vault-manager just adds the `areas`/`files` frontmatter and a short
  `CLAUDE.md` vault stanza when a vault exists. Schema + ownership: vault-manager.
- `vault/_registry.md` is committed; `vault/.recall-map.json` (rebuildable) and
  `vault/.recall-log.jsonl` (injection log for the precision check) are gitignored.

**Vault notes travel with their PR.** When vault updates come out of work that's
going into a PR (a feature, fix, refactor), commit those `vault/` changes onto the
same branch so they land in the same PR as the code. The PR should carry both the
work and the context that goes with it — they go hand in hand, not in separate
commits or separate PRs. Stage vault files in their own commit within the branch
(e.g. `docs(vault): …`) to keep the diff readable, but keep them on the branch.

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
