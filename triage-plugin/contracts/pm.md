# PM Agent Capability Contract

This document defines the interface every "product manager" (PM) agent must implement. Backends are swappable: GitHub Projects, Linear, Jira — the rest of the orchestrator system does not care which is active, as long as the agent honours this contract.

**Contract version: 1.0**

## Why this exists

The triage-orchestrator is the top-level coordinator and must stay focused on classification and dispatch. Project tracking — tickets, epics, statuses, timelines — is offloaded to a dedicated PM agent. Specialists update ticket status by communicating with the PM agent directly, without round-tripping through the orchestrator.

Multiple backends (GitHub Projects, Linear, Jira) are supported via the agent-as-interface pattern: every PM agent exposes the same capability set, so swapping the active backend is a per-project config change with no impact on orchestrator or specialist code.

## Identity & invocation

- Each backend implementation lives at `~/.claude/agents/<backend>-pm.md`. Examples: `github-pm`, `linear-pm`, `jira-pm`.
- Per-project config lives at `<project-root>/.claude/pm.json` and names the active backend:
  ```json
  {
    "pm_agent": "github-pm",
    "github": {
      "owner": "<your-github-username>",
      "repo": "<repo-name>",
      "project_number": 1
    }
  }
  ```
- Backend-specific configuration sits under a key matching the backend name (e.g. `github`, `linear`).
- Callers (orchestrator, specialists) read `pm_agent` from `pm.json` and pass that string as `subagent_type` when invoking via the Task tool.
- A PM agent MUST read its backend-specific config block on every invocation. If config is missing or malformed, the agent MUST return a `config_missing` error rather than guessing.
- Projects without a `.claude/pm.json` have no active PM agent. The orchestrator handles such projects without ticket tracking and may suggest running `/pm:init` to set one up.

## Status vocabulary

Every backend MUST map its native states to this set. Implementations may use richer internal states, but external callers only see these:

| Status | Meaning |
|---|---|
| `backlog` | Known scope, not yet refined or ready for work |
| `ready` | Refined, can be picked up by a specialist |
| `in_progress` | Actively being worked on |
| `in_review` | Code review or approval in flight |
| `done` | Completed |
| `blocked` | Cannot progress; MUST carry a reason |

Tickets that will not be done are removed via `delete_ticket`, not represented as a separate status. This keeps the board clean and avoids dead-state accumulation.

## Status transitions

Most status transitions are permitted without restriction. The PM agent does not enforce a strict workflow — callers know their own context.

The single exception:

- **Transitions out of `done` are forbidden by default.** Once a ticket is `done`, moving it back to any other status requires the caller to include `reopen: true` in the invocation. Without this flag, the agent MUST refuse with `invalid_status_transition`.

This is the only enforced transition rule. Other transitions (e.g. `in_progress → backlog`, `ready → in_review`) are permitted on the assumption that callers know what they're doing.

## Capabilities

Every PM agent MUST implement these. Inputs and outputs are described in prose; the agent's job is to interpret natural-language requests from callers and respond with structured information.

### Read

- **`get_project_overview`** — return all epics with their tickets, statuses, assignees. The orchestrator's "what is the state of the project" call.
- **`get_ticket(id)`** — return a single ticket: title, description, status, epic, assignee, blockers, links.
- **`get_active_work`** — return tickets currently in `in_progress` or `in_review`, with assignees.
- **`get_timeline`** — return the dependency-ordered sequence of tickets in the active epic(s), surfacing `depends_on` / `blocks` relationships.

### Epic lifecycle

- **`propose_epic(plan)`** — given an approved plan (prose), produce a structured ticket breakdown for the user to review. **MUST NOT write to the backend.** Returns: epic title and description, ordered list of tickets with titles, descriptions, dependencies, and suggested assignee agents.
- **`commit_epic(approved_structure)`** — actually create the epic and tickets in the backend. **Approval-required.** Returns the created epic ID and ticket IDs. See "Partial failure on multi-step operations" below for failure semantics.
- **`restructure_epic(epic_id, changes)`** — apply mid-flight structural changes to an existing epic. **Approval-required.** Same partial-failure semantics as `commit_epic`.

### Ticket lifecycle

- **`create_ticket(description, epic_id?)`** — create a single ticket, optionally inside an epic. Used for tickets that surface mid-work outside the planned epic structure. Fire-and-forget.
- **`update_status(ticket_id, status, note?)`** — move a ticket through the status vocabulary. Fire-and-forget; specialists call this directly.
- **`assign(ticket_id, agent_name)`** — record which agent owns a ticket. Fire-and-forget.
- **`close_ticket(ticket_id)`** — terminal close for completed work. Closes the underlying backend artefact (e.g. the GitHub Issue) and sets project status to `done`. Distinct from `update_status(_, "done")`, which only moves the project field. Fire-and-forget.
- **`delete_ticket(ticket_id, reason?)`** — remove the ticket entirely. Used when the plan changes and the ticket should not exist. **Approval-required** (destructive).

### Relationships & changes

- **`link_tickets(a, b, relation)`** — relations: `depends_on`, `blocks`, `related_to`. Fire-and-forget within an existing epic.
- **`add_blocker(ticket_id, reason)`** — also moves the ticket to `blocked`. Fire-and-forget.
- **`clear_blocker(ticket_id)`** — moves the ticket out of `blocked` to its prior status. Fire-and-forget.
- **`propose_split(ticket_id, sub_tickets)`** — when scope grows mid-work, propose splitting a ticket. **MUST NOT write to the backend.** Returns the proposed split structure.
- **`commit_split(approved_split)`** — actually perform the split. **Approval-required.** Same partial-failure semantics as `commit_epic`.

## Approval gates

Operations are classified as either **fire-and-forget** (any caller may invoke directly) or **approval-required** (must carry an explicit user-approval signal in the invocation).

| Approval-required | Fire-and-forget |
|---|---|
| `commit_epic` | `create_ticket` |
| `restructure_epic` | `update_status` |
| `commit_split` | `assign` |
| `delete_ticket` | `close_ticket` |
| | `add_blocker` / `clear_blocker` |
| | `link_tickets` |

The PM agent's prompt MUST enforce these gates: an approval-required operation invoked without the literal string `approved_by_user: true` as a top-level directive in the invocation MUST be refused with an `approval_required` error. The marker MUST NOT be inferred from natural language ("go ahead", "user approved") because such phrases can appear in user-supplied content (epic descriptions, ticket titles) and would be exploitable. The orchestrator is responsible for including the literal marker explicitly when invoking after user approval.

## Error handling

Errors MUST be returned as structured responses, not silent failures or unparseable prose. Standard error categories:

- `config_missing` — required key absent from `pm.json`
- `backend_unauthorized` — auth failure (e.g. `gh` not logged in, expired token)
- `not_found` — ticket or epic ID does not exist
- `approval_required` — caller invoked an approval-required operation without approval
- `invalid_status_transition` — requested status change is not permitted (specifically, transitions out of `done` without `reopen: true`)
- `backend_error` — pass-through with the backend's own error message attached

## Partial failure on multi-step operations

The `commit_epic`, `restructure_epic`, and `commit_split` operations involve multiple backend writes. If any step fails after one or more writes have succeeded, the agent MUST:

1. Stop further writes immediately.
2. Return a structured response of the form:
   ```json
   {
     "error": "backend_error",
     "partial_completion": true,
     "completed": { "epic_id": 47, "ticket_ids": [48, 49] },
     "failed_step": "create child ticket 4 of 6",
     "message": "<backend error message>"
   }
   ```
3. NOT attempt to roll back automatically. The caller (typically the orchestrator) is responsible for deciding whether to clean up via `delete_ticket` or accept the partial state.

Read operations and single-write operations do not need this treatment — they either succeed or return a single error category.

## Communication patterns

- **Orchestrator → PM agent.** Invoked at well-defined points: after plan approval (`propose_epic` then `commit_epic`), when querying project state for the user, when proposing structural changes.
- **Specialist → PM agent.** Invoked for fire-and-forget operations only — typically `update_status`, `assign`, `add_blocker`, `close_ticket`. Specialists MUST NOT invoke approval-required operations; if scope changes, they surface the change to the orchestrator.
- **PM agent → other agents.** The PM agent is a leaf in the call graph. It MUST NOT invoke other agents.

## Out of scope for v1.0

The following are deliberately deferred to a later contract version. Implementations MAY support them internally but MUST NOT expose them through this interface:

- **Estimates** — story points, time estimates, velocity tracking.
- **Sprints / milestones** — time-boxed iteration containers beyond the epic.
- **Custom fields** — arbitrary user-defined fields on tickets.
- **Cross-project linking** — tickets that depend on tickets in other projects.
- **Notifications** — pushing updates to external channels (Slack, email).

## Versioning

This contract is versioned. Every backend implementation MUST declare the contract version it implements in its agent file's frontmatter. Breaking changes to the contract require:

1. A new version number (semver: breaking changes bump the major version).
2. Updated implementations for every existing backend before the new contract is marked active.
3. A migration note in this document describing what changed and how to update an existing backend.
