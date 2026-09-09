# Agent protocol

This repository uses one warm Astra parent and **physical fixed-model subagents**.

| Role/tier | Profile | Authority |
| --- | --- | --- |
| Tiny warm / architecture / integration | Astra Orchestrator direct | Parent authority |
| Discovery | Scout Luna | Read-only |
| Narrow research | Research Luna | Read-only |
| Synthesis research | Research Terra | Read-only |
| Mechanical writer | Execute Luna | Scoped writes |
| General writer | Execute Terra | Scoped writes |
| Deep bounded writer | Execute Sol | Scoped writes |
| Difficult debugging | Debug Sol | Scoped writes |
| Deterministic verification | Verify Luna | Read-only + commands |
| Semantic verification | Verify Terra | Read-only + commands |
| Deep high-risk verification | Verify Sol | Read-only + commands |

Rules:
1. Select the cheapest **physical profile** likely to succeed and be verifiable; do not depend on runtime model override.
2. Escalate capability monotonically Luna -> Terra -> Sol -> Astra; at most one short Luna correction for an obvious local failure.
3. Subagents are isolated and non-recursive (`agents: []`, no `agent` tool).
4. Parallel writers require disjoint file ownership and stable interfaces. Default fan-out <= 3.
5. Search/read narrowly; never copy the parent transcript into a worker.
6. Deterministic validation precedes semantic verification where possible.
7. Security/privacy policy, irreversible decisions, public contracts, architecture, model disagreement, and final acceptance return to Astra.
8. No adjacent cleanup outside acceptance criteria.
9. In Copilot CLI `Auto`, exact profile model pinning may be overridden by the resolved session model; see `docs/model-routing-surfaces.md`.

Parent packet: `GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`.

Worker result: `STATUS`, `SUMMARY` (<= 6 bullets), `CHANGED`, `VALIDATION`, `RISKS`, `NEXT`.

A task is complete only after evidence-based validation and Astra final acceptance for cross-file, high-risk, or architectural work.
