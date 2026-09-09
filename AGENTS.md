# Agent protocol

This repository uses an Astra parent and isolated subagents.

| Difficulty | Default execution model | Typical work |
| --- | --- | --- |
| Tiny + warm | Astra direct | 1-2 tightly coupled edits |
| Low | Luna | search, mechanical edits, tests, boilerplate |
| Medium | Terra | clear multi-file implementation, moderate ambiguity |
| High | Sol | hard debugging, cross-module root cause, concurrency/performance |
| Authority | Astra | architecture/contracts/security/integration/final acceptance |

Rules:
1. Start at the cheapest tier likely to succeed *and be verifiable*.
2. Escalate Luna -> Terra -> Sol -> Astra; do not loop cheap failures.
3. Subagents must be isolated and non-recursive.
4. Parallel writers require disjoint file ownership. Default fan-out <= 3.
5. Search/read narrowly; do not paste parent transcripts or full files across agents.
6. Run deterministic validation before semantic review where possible.
7. Security, privacy, irreversible migrations, public contracts, and model disagreement return to Astra.
8. No adjacent cleanup outside acceptance criteria.

Parent packet: `GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`.

Worker result: `STATUS`, `SUMMARY` (<= 6 bullets), `CHANGED`, `VALIDATION`, `RISKS`, `NEXT`.

A task is complete only after evidence-based validation and Astra final acceptance for cross-file, high-risk, or architectural work.
