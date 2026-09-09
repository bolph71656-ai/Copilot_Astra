# Agent protocol

This repository uses one Astra parent and physical fixed-model subagents.

Rules:
1. Select the lowest **risk-feasible physical route**, not merely the cheapest first call.
2. Routing considers `p(correct)`, automatic failure detection, required human/device validation, hidden-defect cost, context warmth, dispatch/rework cost, human revalidation cost, and latency sensitivity.
3. Capability escalation is monotone, but intermediate tiers may be skipped (`Luna -> Sol -> Astra` is valid).
4. Same-tier retry is conditional on positive expected value; no conceptual retry after disconfirming evidence.
5. Every writer self-validates with the cheapest decisive automatic check. Do not automatically duplicate it with `Verify Luna`.
6. Use Scout only when expected information value exceeds Scout + ingestion cost.
7. Default writer fan-out is 1; use 2 conditionally; 3 is exceptional cap.
8. Parallel writers require disjoint ownership and stable interfaces.
9. Subagents are isolated/non-recursive (`agents: []`, no `agent` tool).
10. Search/read narrowly; never copy parent transcript into a worker.
11. Security/privacy policy, irreversible decisions, public contracts, architecture, disagreement, and final acceptance return to Astra.
12. Keep Auto runs separate from fixed-tier calibration unless resolved model is recorded.
13. Human/device validation is a first-class oracle, not automatic permission to choose a cheaper model. Include its detection strength, setup/retest cost, latency, repeatability, and hidden-defect consequence in routing.
14. If required human/device validation is still pending, use `STATUS=NEEDS_HUMAN_VALIDATION`; do not report `DONE`.
15. `NEEDS_HUMAN_VALIDATION` and validation `BLOCKED` states are not model failures and must not update model success priors.
16. After human/device failure, separate implementation defects from device/environment/infrastructure/procedure/operator failures before retry/escalation or calibration.
17. Repository validation is local-only. Do not add GitHub Actions workflows. Before final acceptance of repository changes, run `python scripts/validate_all.py` successfully.

Parent packet: `GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`.

Worker result:
- `STATUS`: `DONE | NEEDS_HUMAN_VALIDATION | FAILED | BLOCKED | NEEDS_PARENT`
- `SUMMARY`: <= 6 bullets
- `CHANGED`: exact paths or `none`
- `VALIDATION`: automatic commands/evidence + outcome
- `HUMAN_VALIDATION`: `none` or `WHY / SETUP / STEPS / EXPECTED / EVIDENCE / ATTRIBUTION_HINTS`
- `RISKS`: unresolved risks only
- `NEXT`: one action or `none`

Research/design rationale: `docs/research/2026-09-09-deep-routing-research.md`, `docs/adr/0001-risk-aware-routing.md`, `docs/adr/0002-local-validation-no-github-actions.md`, and `docs/adr/0003-human-validation-as-oracle.md`.
