# Agent protocol

This repository uses a conservative two-stage entry path: a generated **Astra Gateway** on the lowest active non-authority model, plus one warm **registry-defined authority parent** with generated fixed-model subagents targeted at VS Code.

## Configuration contract

1. `config/model-registry.json` defines active model ids, capability order, authority model, Copilot model strings, role selection, and seed priors.
2. `config/pricing.json` defines costs/context tiers independently from topology.
3. `.github/agents/*.agent.md` and `config/routing-priors.json` are generated; do not hand-edit them.
4. `config/gateway-policy.json` defines conservative gateway bootstrap, calibrated expansion, and rollback constraints.
5. `config/operational-costs.json` defines default dispatch/handoff/rework/defect economics for route estimation when CLI values are omitted.
6. After model/topology/pricing or gateway-template changes, run `python scripts/sync_model_config.py --write` then `python scripts/validate_all.py`.
7. Never assume four models or any particular model id. Capability escalation follows the configured `route_order`.
8. When at least one non-authority model exists, `Astra Gateway` is generated on the lowest active non-authority model. Authority-only topologies omit it.

## Gateway contract

1. `Astra Gateway` is a **fail-closed admission controller**, not a general-purpose parent and not final authority.
2. Prompt-level judgment alone does not authorize direct work. Before edits, a candidate direct task must pass the hard semantic gates and `python scripts/gateway_policy.py ...` must return `ALLOW_DIRECT`.
3. Cold-start/bootstrap direct completion is limited to `exploratory` risk with a decisive `deterministic` oracle, explicit acceptance, and a local bounded surface.
4. `standard` direct completion requires local `config/gateway-calibration.local.json` evidence that clears the configured minimum sample count, confidence level, safety bounds, authority-rescue bound, and cost break-even.
5. `high` and `critical` work never completes directly at the gateway.
6. Any uncertainty, authority trigger, weak oracle, required human/device acceptance, long-horizon integration need, or substantive failure escalates intact to the authority parent before speculative edits.
7. The gateway may delegate only to the configured authority parent. It must not directly invoke generated Scout/Research/Execute/Debug/Verify workers.
8. False down-routing is more costly than over-escalation. Optimize for low false-downroute rate first, then direct-completion rate.
9. Known authority/high-risk work may invoke the authority parent directly and skip the gateway.
10. Gateway correctness must be measured separately from worker model correctness priors; seed worker priors never unlock gateway expansion.
11. Gateway rollback conditions are executable policy. Any observed high/critical false down-route pauses direct completion globally.

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
11. Generated worker subagents have `agents: []`, no `agent` tool, `target: vscode`, and `disable-model-invocation: true`.
12. Only the authority parent explicitly allowlists generated physical workers.
13. Human/device validation is a first-class oracle, not permission to down-route by default.
14. Pending human validation and validation `BLOCKED` states are not model failures.
15. Unknown/external failure attribution must not update model correctness priors.
16. Security/privacy, payment/auth, destructive migration, irreversible data change, architecture, public contracts, material disagreement, and final acceptance remain authority-parent responsibilities.
17. Repository validation is local-only. Do not add GitHub Actions workflows.
18. `scripts/route_cost.py` uses conservative nonzero operational defaults from `config/operational-costs.json` when values are omitted; explicit CLI values including zero remain available for controlled experiments.

## Reduced topology behavior

When a model is removed, do not invent a semantic replacement tier. The generator selects role profiles from remaining workers using topology-relative slots. A role with an unmet `min_worker_count` becomes parent-only.

A two-model setup intentionally has one gateway model plus one authority model; it can have no Debug subagent while still having Scout/Research/Execute/Verify on the single worker. A one-model authority-only setup has no gateway.

## Status contracts

Gateway:
`DONE | BLOCKED | NEEDS_PARENT`

Writer:
`DONE | NEEDS_HUMAN_VALIDATION | FAILED | BLOCKED | NEEDS_PARENT`

Read-only scout/research:
`DONE | BLOCKED | NEEDS_PARENT`

Verifier:
`PASS | FAIL | BLOCKED | NEEDS_PARENT`

## Delegation packet

Normal parent-to-worker packet:

`GOAL`, `SCOPE`, `KNOWN`, `CONSTRAINTS`, `ACCEPTANCE`, `VALIDATION`, `STOP`

Gateway-to-parent adds:

`GATE_REASON`

## Worker result

`STATUS`, `SUMMARY` (<= 6 bullets), `CHANGED`, `VALIDATION`, `HUMAN_VALIDATION`, `RISKS`, `NEXT`

`HUMAN_VALIDATION` is `none` unless required.

## Calibration

Generate a local worker-routing overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Generate a local gateway-admission calibration:

```bash
python scripts/calibrate_gateway.py observations.jsonl \
  --out config/gateway-calibration.local.json
```

Both local files are ignored and must not be committed. Gateway telemetry must separately record direct completion, escalation, false down-routing, validation outcome, authority rescue/rework, and gateway-vs-authority economics.

Canonical validation:

```bash
python scripts/validate_all.py
```

See `docs/model-registry.md`, `docs/astra-routing.md`, `docs/human-device-validation.md`, `docs/observability.md`, `docs/adr/0005-registry-driven-model-topology.md`, and `docs/adr/0006-calibrated-gateway-admission.md`.
