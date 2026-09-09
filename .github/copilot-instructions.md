# Copilot Astra efficiency policy

This repository is optimized for a cost-aware Astra parent with Luna execution subagents.

## Parent behavior

When operating as the parent/orchestrator:

- Keep architecture, decomposition, interface decisions, integration, security-sensitive reasoning, and final acceptance in Astra.
- Preserve warm parent context. Do not switch the parent model mid-session merely to reduce token price.
- Perform small, tightly coupled warm-context edits directly in Astra when delegation overhead would exceed the work.
- Delegate cold, repetitive, high-output, or parallelizable work to the repository Luna agents through the `agent` tool.

Use the narrowest specialist:

- `luna-scout`: repository search, dependency tracing, evidence gathering, classification.
- `luna-worker`: scoped implementation, boilerplate, mechanical refactors, local fixes.
- `luna-test`: test generation, command execution, failure classification, bounded repair/re-run.

## Default routing

Prefer Luna when any of these apply:

- roughly 10k+ tokens of new/cold context must be read,
- roughly 2k+ tokens of code/output are likely to be generated,
- more than 3 mostly independent files are involved,
- work is repetitive or mechanical,
- multiple independent subtasks can be processed separately.

Prefer Astra when the relevant context is already warm, the edit is small (typically 1-2 tightly coupled files), output is short, and the work depends on architectural intent or integration.

For ambiguous 6k-20k token tasks, route cold context to Luna and keep warm, read-dominated work in Astra.

## Handoff discipline

Every subagent task must be narrow and include: goal, scope, constraints, acceptance criteria, validation command(s), and a compact return format.

Do not send the full parent transcript. Prefer file paths, symbols, invariants, and exact acceptance criteria.

Worker responses should contain only `STATUS`, `SUMMARY`, `CHANGED`, `VALIDATION`, `RISKS`, and `NEXT`. Avoid full file dumps, long logs, and repeated diffs.

## Retry discipline

Allow at most one Luna retry for the same local root cause. On a second failure, architecture ambiguity, security concern, or cross-module contract decision, escalate to Astra instead of continuing a cheap-but-unbounded loop.

## Verification

Use Luna for broad/repetitive validation and Astra for final acceptance reasoning. Re-open only the files required to integrate or verify worker results.
