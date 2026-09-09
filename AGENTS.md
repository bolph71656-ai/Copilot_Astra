# Agent operating rules

This repository uses a parent/worker topology:

| Role | Model | Responsibility |
| --- | --- | --- |
| Astra Orchestrator | Astra | Intent, architecture, decomposition, integration, final acceptance |
| Luna Scout | Luna | Read-only discovery and repository evidence |
| Luna Worker | Luna | Scoped implementation and mechanical changes |
| Luna Test | Luna | Repetitive validation and bounded repair loops |

## Shared principles

1. Optimize for total successful-task cost, including handoff, retries, and re-reading—not just worker token price.
2. Minimize duplicated context between agents.
3. Prefer file paths, symbols, interfaces, and acceptance criteria over pasted source or transcript history.
4. Keep worker scope small enough that a fresh context can solve it without reconstructing the full parent session.
5. Never hide uncertainty. Return `needs-parent` when a decision exceeds delegated authority.
6. Do not perform adjacent cleanup unless it is required for the delegated acceptance criteria.

## Astra parent rules

- Keep design decisions and integration in the parent.
- Preserve warm context; avoid unnecessary mid-session model changes.
- Directly perform small warm-context edits when the handoff would be larger than the work.
- Delegate large cold reads, repetitive implementation, high-volume output, and broad test loops.
- Prefer parallel Luna tasks only when their write scopes do not overlap.
- After a worker returns, inspect the compact summary first and re-read only integration-critical files.

## Luna worker rules

- Do not recursively delegate to other agents.
- Stay within the explicit scope.
- Search first; read narrowly; edit minimally; validate cheaply.
- Use at most one retry for the same local root cause.
- Escalate architecture, interface, security, or cross-cutting ambiguity.
- Return compact structured results; never paste full files unless explicitly requested.

## Handoff contract

A parent-to-worker packet should contain:

- `GOAL`: one outcome.
- `SCOPE`: exact files/directories or discovery boundary.
- `CONSTRAINTS`: invariants and interfaces that must remain stable.
- `ACCEPTANCE`: observable success conditions.
- `VALIDATION`: commands/checks to run when known.

A worker-to-parent response should contain:

- `STATUS`: done | blocked | needs-parent
- `SUMMARY`: at most 6 bullets
- `CHANGED`: exact paths, or none
- `VALIDATION`: commands + outcome
- `RISKS`: unresolved risks only
- `NEXT`: one next action, or none

## Completion criteria

A task is complete only when:

- implementation satisfies the delegated acceptance criteria,
- validation has been run at the appropriate scope,
- unresolved risks are surfaced,
- Astra performs final integration/acceptance reasoning for cross-file or architectural work.
