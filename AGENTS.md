# Agent protocol

This repository uses one Astra parent and physical fixed-model subagents.

Rules:
1. Select the lowest **risk-feasible physical route**, not merely the cheapest first call.
2. Routing considers `p(correct)`, failure detection/oracle strength, hidden-defect cost, context warmth, dispatch/rework cost, and latency sensitivity.
3. Capability escalation is monotone, but intermediate tiers may be skipped (`Luna -> Sol -> Astra` is valid).
4. Same-tier retry is conditional on positive expected value; no conceptual retry after disconfirming evidence.
5. Every writer self-validates with the cheapest decisive check. Do not automatically duplicate it with `Verify Luna`.
6. Use Scout only when expected information value exceeds Scout + ingestion cost.
7. Default writer fan-out is 1; use 2 conditionally; 3 is exceptional cap.
8. Parallel writers require disjoint ownership and stable interfaces.
9. Subagents are isolated/non-recursive (`agents: []`, no `agent` tool).
10. Search/read narrowly; never copy parent transcript into a worker.
11. Security/privacy policy, irreversible decisions, public contracts, architecture, disagreement, and final acceptance return to Astra.
12. Keep Auto runs separate from fixed-tier calibration unless resolved model is recorded.
13. Repository validation is local-only. Do not add GitHub Actions workflows. Before final acceptance of repository changes, run `python scripts/validate_all.py` successfully.

Parent packet: `GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`.

Worker result: `STATUS`, `SUMMARY` (<= 6 bullets), `CHANGED`, `VALIDATION`, `RISKS`, `NEXT`.

Research/design rationale: `docs/research/2026-09-09-deep-routing-research.md`, `docs/adr/0001-risk-aware-routing.md`, and `docs/adr/0002-local-validation-no-github-actions.md`.
