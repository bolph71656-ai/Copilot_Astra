# Agent protocol

This repository uses one warm **registry-defined authority parent** and generated physical fixed-model subagents targeted at VS Code.

## Configuration contract

1. `config/model-registry.json` defines active model ids, capability order, authority model, Copilot model strings, role selection, and seed priors.
2. `config/pricing.json` defines costs/context tiers independently from topology.
3. `.github/agents/*.agent.md` and `config/routing-priors.json` are generated; do not hand-edit them.
4. After model/topology/pricing changes, run `python scripts/sync_model_config.py --write` then `python scripts/validate_all.py`.
5. Never assume four models or any particular model id. Capability escalation follows the configured `route_order`.

## Routing contract

1. Select the lowest **risk-feasible route**, not merely the cheapest first call.
2. Use task class, oracle strength, authority, context warmth, hidden-defect consequence, dispatch/rework cost, and human/device validation economics.
3. Use transition-aware priors. Direct-start quality is not assumed equal to quality after earlier failures.
4. The configured authority model is final authority, **not an infallible fallback**. Its success/detection probabilities are calibrated too.
5. Capability escalation is monotone, but intermediate tiers may be skipped or absent entirely.
6. Same-tier retry is conditional on positive expected value; do not repeat a disproven conceptual approach.
7. Every writer self-validates with the cheapest decisive automatic check.
8. Use Scout only when expected information value exceeds Scout + ingestion cost.
9. Default writer fan-out is 1; use 2 conditionally; 3 is exceptional.
10. Parallel writers require disjoint ownership and stable interfaces.
11. Generated subagents have `agents: []`, no `agent` tool, `target: vscode`, and `disable-model-invocation: true`.
12. Only the parent explicitly allowlists generated physical subagents.
13. Human/device validation is a first-class oracle, not permission to down-route by default.
14. Pending human validation and validation `BLOCKED` states are not model failures.
15. Unknown/external failure attribution must not update model correctness priors.
16. Security/privacy, payment/auth, destructive migration, irreversible data change, architecture, public contracts, material disagreement, and final acceptance remain authority-parent responsibilities.
17. Repository validation is local-only. Do not add GitHub Actions workflows.

## Reduced topology behavior

When a model is removed, do not invent a semantic replacement tier. The generator selects role profiles from remaining workers using topology-relative slots. A role with an unmet `min_worker_count` becomes parent-only.

This means a two-model setup can intentionally have no Debug subagent while still having Scout/Research/Execute/Verify on the single worker.

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

Canonical validation:

```bash
python scripts/validate_all.py
```

See `docs/model-registry.md`, `docs/astra-routing.md`, `docs/human-device-validation.md`, and `docs/adr/0005-registry-driven-model-topology.md`.
