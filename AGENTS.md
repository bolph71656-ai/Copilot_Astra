# Agent protocol

This repository uses one warm Astra parent and **physical fixed-model subagents** targeted at VS Code.

## Routing contract

1. Select the lowest **risk-feasible route**, not merely the cheapest first call.
2. Use task class, oracle strength, authority, context warmth, hidden-defect consequence, dispatch/rework cost, and human/device validation economics.
3. Use transition-aware priors. `P(Sol succeeds | direct)` is not assumed equal to `P(Sol succeeds | Luna/Terra already failed)`.
4. Astra is final authority, **not an infallible fallback**. Its success/detection probabilities are calibrated too.
5. Capability escalation is monotone, but intermediate tiers may be skipped.
6. Same-tier retry is conditional on positive expected value; no repeated disproven conceptual approach.
7. Every writer self-validates with the cheapest decisive automatic check.
8. Use Scout only when expected information value exceeds Scout + ingestion cost.
9. Default writer fan-out is 1; use 2 conditionally; 3 is exceptional.
10. Parallel writers require disjoint ownership and stable interfaces.
11. Subagents have `agents: []`, no `agent` tool, `target: vscode`, and `disable-model-invocation: true`.
12. Only `Astra Orchestrator` explicitly allowlists the physical subagents.
13. Keep Auto-selected runs separate from fixed-tier calibration unless resolved model is recorded.
14. Human/device validation is a first-class oracle, not permission to down-route by default.
15. Pending human validation and validation `BLOCKED` states are not model failures.
16. Unknown/external failure attribution must not update model correctness priors.
17. Security/privacy, payment/auth, destructive migration, irreversible data change, architecture, public contracts, disagreement, and final acceptance return to Astra.
18. Repository validation is local-only. Do not add GitHub Actions workflows.

## Status contracts

Writer:
`DONE | NEEDS_HUMAN_VALIDATION | FAILED | BLOCKED | NEEDS_PARENT`

Read-only scout/research:
`DONE | BLOCKED | NEEDS_PARENT`

Verifier:
`PASS | FAIL | BLOCKED | NEEDS_PARENT`

## Delegation packet

`GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`

## Worker result

`STATUS`, `SUMMARY` (<= 6 bullets), `CHANGED`, `VALIDATION`, `HUMAN_VALIDATION`, `RISKS`, `NEXT`

`HUMAN_VALIDATION` is `none` unless required.

## Calibration

Generate a local overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

The router loads `config/routing-priors.json` and, when present, the local overlay automatically.

Canonical validation:

```bash
python scripts/validate_all.py
```

See `docs/astra-routing.md`, `docs/human-device-validation.md`, `docs/adr/0004-transition-aware-empirical-routing.md`, and `docs/research/2026-09-10-routing-review.md`.
