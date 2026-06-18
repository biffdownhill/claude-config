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

### Git

- **Never rewrite history unless I explicitly ask for it.** Do not `git commit --amend`, `git rebase`, `git reset` that discards commits, or force-push unless I have directly told you to amend, rebase, or go back on a commit. Rewriting loses history and leaves the branch diverged from its remote — which then needs a force-push to recover. Avoid putting the repo in that state.
- **Default to additive commits.** To fix, extend, or correct an earlier commit — including review fixes — make a *new* commit on top. A linear, slightly messy history is fine; a rewritten one is not.
- If a commit I've already made genuinely seems to need changing and I haven't asked for a rewrite, make a follow-up commit and tell me — let me decide whether to squash or amend later.

## Lessons learned

<!-- Cross-project lessons: pitfalls encountered, approaches that worked -->
<!-- e.g. "Drizzle schema changes require explicit migration generation step." -->

- **"Code-complete" ≠ "done".** A feature that adds configuration or integrates an external
  service/account is not usable until the required config is documented where devs expect it
  (`.env.example` / sample / setup doc, with secrets flagged and never committed) AND there is
  a written path to enable and verify it end-to-end. Trace **every** acceptance criterion to
  met / deferred-to-named-owner explicitly — a criterion only verifiable outside the dev
  environment (real account, device/cloud build, paid service) is an outstanding owner-action,
  never silently "done". (ShelfLife Sentry #8: shipped the SDK wiring with no DSN/org/token
  configured and no `.env.example` entries — reported "done" while not connected to any account.)
- A `WeakSet` cycle-guard in a recursive scrubber / deep-clone / transformer leaks on
  **shared (diamond) references**, not just true cycles: the second path to an
  already-seen sub-object returns the *original* node (e.g. unredacted secrets, or a
  pre-transform value). Use a `WeakMap<original, transformedCopy>` and register the new
  copy **before** recursing into its children — that resolves cycles to the in-progress
  copy and shared refs to the same redacted/cloned copy on every path, in one mechanism.
  A "does not throw" test passes either way, so assert on the *output* of a shared-ref
  input. (Found in the ShelfLife Sentry PII scrubber, #8.)
- A fresh `git worktree` does not copy gitignored files (`node_modules/`, `.env`,
  `.claude/`). Run `npm ci` (or the project's install) in a new worktree before any
  tooling that needs deps present — e.g. `npx expo install` requires the `expo`
  module to detect the SDK. Also copy/recreate gitignored local config the task
  needs (e.g. `.claude/pm.json`) into the worktree.
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
- **Commit an idempotency flag only AFTER the side-effecting init succeeds.** A
  `start()`/`init()` with an early-return guard that sets `started = true` (or
  assigns the client) *before* the SDK constructor and first call can throw will
  wedge the service permanently on a synchronous throw: `started` is true but the
  client is null, so every later `start()` early-returns, the client is never
  built, the first event never fires, and only `teardown()` recovers. Build into
  locals, commit `started`/`client` only on the success path, and roll back +
  rethrow in a `catch` (matching the bootstrap's rollback-and-rethrow contract).
  A "does not throw" test passes either way — assert that after a thrown init the
  flag is false and a *retry* succeeds. (Found by codex in the ShelfLife PostHog
  module, #9.)
- **An offline pre-build config verifier must mirror BOTH arms of a symmetric
  schema invariant.** If the runtime schema enforces "config present iff
  (enabled AND bundled)", a verifier that checks only the positive arm
  (enabled+bundled ⇒ key present) and skips the inverse (config present for a
  NOT-bundled env ⇒ error) returns a misleading green on a config that dies at
  startup. When a `superRefine`/validator has present-and-absent invariants, the
  verifier must check both arms. (ShelfLife `verify-posthog.ts`, #9.)
- **A source-of-truth DB write inside `Promise.allSettled` is silently lost under
  a durable-step runner (Inngest/queue worker).** When a settled write rejects,
  the rejection is logged but the surrounding step still *resolves* — the runner
  memoises the step as done and never retries, so the durable write is dropped
  while disposable side effects "succeeded". Only put genuinely disposable emits
  (analytics, telemetry) in `allSettled`; await the durable write separately and
  **throw** so the step fails and the runner retries it. A related rule for the
  same class of consumer: a step that loads a row by id *after* a state-transition
  event must re-assert the triggering state in the load query (`.eq('state', …)`)
  — event emission and step execution are separated in time, so a race can change
  the row first; a non-matching row is a graceful logged no-op, not an error.
  (Machined article-quality scoring, Phase A.)
- **`z.coerce.number()` is fail-OPEN.** It coerces `false`→0, `null`→0, `''`→0, so
  a malformed upstream value (e.g. an LLM judge returning a non-numeric score)
  passes validation and is silently scored `0` instead of being rejected. When `0`
  is itself a meaningful value, use strict `z.number()` (or a regex-guarded string
  parse) so a bad response fails closed and degrades to an explicit error path
  rather than a plausible-looking zero. (Machined holistic judge, Phase A.)

## Frameworks evaluated

Decisions about external frameworks I considered adopting but ultimately didn't, so future-me can find the reasoning instead of re-evaluating from scratch. Full evaluation: `~/.claude/plans/i-want-you-to-calm-reddy.md` (2026-04-28).

- **Karpathy `llm-council` (multi-model deliberation)** — not adopted. Three-stage chairman synthesis is genuinely useful for open-ended judgement (essay quality, "library A vs B"), but for code review it adds noise — code has ground truth and I want raw reviewer reports, not a synthesised opinion. The existing `code-reviewer` + `codex-reviewer` + `security-auditor` pipeline already covers multi-perspective review at the right cost. **Revisit only** if Tier 3 architecture decisions routinely produce conflicting reviewer verdicts I can't arbitrate, or evaluation tasks become common enough that confirmation-bias mitigation is worth the cost. Implementation, if it ever happens, is *not* the upstream web app — it's a small `council-judge` agent that fans plans out via OpenRouter and returns rankings (no chairman).
- **Karpathy "LLM Wiki" pattern (Obsidian as a research wiki)** — not adopted wholesale. The vault-manager system is more rigorous than the gist (typed templates, mandatory frontmatter, lazy folders, grep-before-create, 7-day health checks). Borrowed only `index.md` (note catalogue) and `log.md` (chronological feed) into vault-manager. The "ingest external research sources" framing is a different problem domain — the vault is a project memory, not a literature wiki.
