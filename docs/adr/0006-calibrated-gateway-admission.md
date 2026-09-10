# ADR 0006: Calibrated fail-closed gateway admission

Status: Accepted

Date: 2026-09-11

## Context

PR #6 introduced `Astra Gateway` on the lowest active non-authority model (currently Luna) to avoid paying the Astra authority startup cost for obviously safe work. Subsequent review found that the architecture was directionally sound but still too permissive at cold start: the gateway prompt allowed exploratory **or standard** work to complete directly without requiring measured classifier evidence, while worker correctness priors were seed assumptions rather than gateway-routing measurements. The route estimator also defaulted dispatch, handoff, failure, and defect penalties to zero when callers omitted them.

The main failure to avoid is a false down-route: work that should have reached authority but is completed at the gateway. This loss is asymmetric. Over-escalation mainly costs tokens/latency; under-escalation can accept an incorrect or unsafe change.

## Decision

Keep the two-stage architecture, but make it conservative and evidence-gated.

1. `Astra Gateway` remains an admission controller, not a general-purpose parent.
2. Every candidate direct completion must pass hard semantic gates and the executable `scripts/gateway_policy.py` check **before edits**.
3. Cold-start/bootstrap direct completion is limited to:
   - `risk_class = exploratory`,
   - `oracle_strength = deterministic`,
   - explicit acceptance criteria,
   - local bounded surface,
   - no authority trigger, unresolved design, human/device acceptance, or prior substantive failure.
4. `standard` direct completion is disabled until local gateway calibration clears all configured conservative bounds.
5. `high` and `critical` work never completes directly at the gateway.
6. Worker routing priors do not authorize gateway expansion. Gateway classifier safety is calibrated separately with `scripts/calibrate_gateway.py`.
7. Calibration uses confidence bounds, not point estimates alone. Current policy requires at least 100 samples and additionally requires:
   - false-downroute upper bound <= 2%,
   - validated-correct lower bound >= 94%,
   - authority-rescue upper bound <= 5%,
   - mean gateway-path cost <= 95% of estimated authority-direct cost.
8. Global rollback pauses direct completion when observed false-downroute/rescue/cost regressions exceed policy, and any high/critical false down-route triggers an immediate pause.
9. `scripts/route_cost.py` now loads conservative nonzero orchestration/rework defaults from `config/operational-costs.json` when the caller does not provide explicit values. Explicit CLI values, including zero for experiments, still override the defaults.

## Why this architecture

The gateway remains useful because Luna is much cheaper than Astra for short bounded work, but the benefit exists only when the direct-completion fraction is large enough to offset gateway classification, duplicated context on escalation, handoff ingestion, rework, and latency. A cheap model is therefore not automatically the optimal parent.

The architecture deliberately separates two questions:

- **Semantic admission:** Is this task safe enough to allow a cheap direct attempt?
- **Worker routing:** Once authority owns the task, which monotone worker path minimizes risk-adjusted expected cost?

Keeping those decisions separate reduces the amount of fine-grained routing judgment delegated to the cheapest model.

## Break-even model

For gateway-first operation, a simplified expected-cost comparison is:

```text
C_gateway = C_gate
          + q_direct * C_direct
          + (1 - q_direct) * (C_handoff + C_authority)
          + q_false * C_rework

C_authority_direct = C_authority
```

Gateway-first is economically favorable only when:

```text
C_gateway < C_authority_direct
```

Therefore `q_direct` alone is insufficient. The system must also track gateway cost, escalation duplication, false-downroute rework, and end-to-end cost per validated correct task.

## Telemetry contract

For gateway calibration, record metadata-only observations when available:

- `gateway_action`: `direct | escalate`
- `task_class`
- `risk_class`
- `oracle_strength`
- `final_validated_correct` for direct attempts
- `false_downroute`
- `authority_rescue_required`
- `gateway_path_units`
- `authority_direct_estimated_units`

Generate the local, ignored calibration file with:

```bash
python scripts/calibrate_gateway.py observations.jsonl \
  --out config/gateway-calibration.local.json
```

Do not commit prompt/response/source content for this purpose.

## Rollout

Treat gateway expansion as an experiment, not a permanent assumption.

1. Start with bootstrap exploratory/deterministic direct completion only.
2. Collect at least the configured sample floor.
3. Expand a specific task/risk/oracle bucket only when its conservative bounds clear policy.
4. Compare end-to-end cost and validated correctness against authority-direct operation.
5. Revert to authority-first for the affected bucket, or globally, when rollback thresholds fire.

## Consequences

Benefits:

- lower false-downroute exposure at cold start,
- no use of worker seed priors as evidence of classifier quality,
- economically meaningful nonzero routing defaults,
- explicit rollback path,
- auditable expansion criteria.

Costs:

- more early over-escalation,
- extra policy command before direct edits,
- slower expansion of standard-risk direct completion,
- local telemetry is required to realize the full cost-saving potential.

These costs are intentional because the dominant failure mode is unsafe under-routing, not excessive escalation.
