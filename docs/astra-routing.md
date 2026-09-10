# Transition-aware risk/economic routing

## Objective

For route `π`, evaluate model + dispatch + handoff + rework + human-validation cost, validated-correct probability, hidden accepted failure probability, detected terminal unresolved failure probability, and latency.

The score is:

```text
(E[Cπ] + λ_defect * Phidden(π) + λ_latency * E[Tπ]) / Pcorrect(π)
```

A route is viable only when:

```text
Phidden <= max_hidden_failure
Pterminal <= max_terminal_failure
Pcorrect >= min_validated_correct
```

Risk classes live in `config/risk-policy.json`.

## Cheap admission gateway

`Astra Gateway` is a separate admission layer in front of the authority routing system. When at least one non-authority model exists, it is generated on the **lowest active non-authority model**. In the current topology that is Luna.

The gateway is not a free-form replacement for the authority parent. It is intentionally **fail-closed** and has two layers of admission:

1. semantic hard gates evaluated before edits,
2. executable policy in `scripts/gateway_policy.py`.

```text
semantic gates clear
+ explicit acceptance
+ local bounded surface
+ decisive deterministic oracle
+ gateway_policy.py => ALLOW_DIRECT
        |
        v
direct work + decisive automatic validation

anything uncertain / denied / policy unavailable
        |
        v
escalate intact to authority parent
```

The gateway may invoke only the authority parent. It cannot directly dispatch normal workers. This prevents the cheapest model from making fine-grained Terra/Sol/Astra worker decisions while still allowing cheap completion in narrowly safe cases.

Authority triggers include security/privacy/auth/payment/trust boundaries; permission changes; destructive or irreversible data changes; architecture/public contracts; cross-component or subtle concurrency/distributed invariants; weak/subjective oracles; required human/device acceptance; high/critical risk; long-horizon integration/final acceptance; and substantive implementation or validation failure.

False down-routing is treated as a more serious error than over-escalation. Any uncertainty about a direct-completion condition resolves upward.

Known authority/high-risk work may bypass the gateway and invoke the authority parent directly.

### Bootstrap versus calibrated admission

Worker capability priors and gateway-classifier evidence are different distributions. `config/routing-priors.json` therefore never authorizes gateway expansion.

Cold-start/bootstrap policy in `config/gateway-policy.json` currently permits direct completion only when:

```text
risk_class = exploratory
oracle_strength = deterministic
explicit acceptance = true
local bounded surface = true
no authority trigger
no unresolved design
no required human/device validation
no substantive prior failure
```

`standard` direct completion is evidence-gated. It becomes eligible only for a matching task/risk/oracle bucket when local `config/gateway-calibration.local.json` clears all configured requirements, including minimum samples, minimum confidence level, false-downroute upper bound, validated-correct lower bound, authority-rescue upper bound, and cost break-even.

`high` and `critical` work never completes directly at the gateway.

If policy/calibration is absent, malformed, insufficient, or worse than thresholds, the decision is `ESCALATE`.

### Gateway calibration

Create the ignored local calibration file from metadata-only observations:

```bash
python scripts/calibrate_gateway.py observations.jsonl \
  --out config/gateway-calibration.local.json
```

The calibration uses Wilson confidence intervals for gateway safety rates rather than trusting point estimates alone. A calibration generated at a confidence level below the policy requirement cannot unlock calibrated direct completion.

Track at least:

```text
direct_completion_rate
escalation_rate
false_downroute_rate
validated_correct_rate
authority_rescue_rate
mean_gateway_units
mean_escalation_handoff_units
mean_cost_ratio_vs_authority_direct
end_to_end_units_per_validated_correct
```

The primary safety guardrail is false down-routing. The primary economics guardrail is gateway-path cost relative to an authority-direct counterfactual.

### Rollback

Gateway expansion is reversible policy, not an assumption. `config/gateway-policy.json` defines global rollback conditions. Current policy immediately pauses direct completion after any observed high/critical false down-route and also pauses after configured sample floors when false-downroute, authority-rescue, or cost-regression thresholds are exceeded.

This rollback check runs before bootstrap/calibrated admission so known regression can disable even otherwise eligible cheap work.

### Gateway economics

Gateway-first operation is beneficial only when the savings from directly completed cheap tasks exceed:

- the gateway model call itself,
- classification reads/search,
- escalation handoff/ingestion cost,
- duplicated context on escalation,
- any rework caused by a false down-route,
- latency cost.

A simplified comparison is:

```text
C_gateway = C_gate
          + q_direct * C_direct
          + (1 - q_direct) * (C_handoff + C_authority)
          + q_false * C_rework

C_authority_direct = C_authority
```

Gateway-first is favorable only when `C_gateway < C_authority_direct`. Cheap model token price alone does not establish this.

## Operational cost defaults

`scripts/route_cost.py` uses `config/operational-costs.json` whenever operational cost CLI arguments are omitted. Dispatch, handoff, failure/rework, and defect penalties therefore do not silently become zero.

The committed defaults are marked `source_kind: conservative-bootstrap` and `measured: false`. They are engineering assumptions for safer scenario analysis, not billing facts. Explicit CLI arguments override them, including zero for controlled experiments.

Latency seconds are always reported when supplied. The committed latency economic weight remains zero until an operator assigns a meaningful local value.

## Transition-aware priors

Direct-start capability and post-failure capability are different distributions. For `Luna -> Sol -> Astra`, lookup uses `direct`, then `luna`, then `luna>sol` as `reached_after`.

Lookup prefers exact task class + oracle strength + exact path, then exact/generic combinations with `after:any`, then wildcard seed fallback. Later prior files override same-specificity fields; partial calibrated entries can override one field while retaining seed values for missing fields.

This prevents using `P(Sol succeeds | direct)` after lower-tier failures have selected a harder residual task set.

## Astra is not perfect

Astra is the authority boundary, not mathematical certainty. Seed priors keep Astra below 1.0 and calibration updates Astra exactly like other models. A detected Astra failure that remains unresolved is a real terminal task failure.

## Worker priors pipeline

Cold start: `config/routing-priors.json`.

Local evidence overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Normal worker routing consumes both. Do not commit user/task telemetry or the local overlay.

Worker-routing calibration and gateway-admission calibration remain intentionally separate.

## Strict observation attribution

A failed worker observation enters model correctness calibration only when `failure_attribution = implementation`. Pending human validation, blocked states, device/environment/infrastructure/procedure/operator failures, and unknown attribution stay outside the model posterior. Contradictory human-validation states are rejected rather than silently repaired.

Gateway false down-routing is a separate classifier outcome and must not be collapsed into worker implementation correctness.

## Human/device oracle

For an incorrect result:

```text
d_total = d_auto + (1 - d_auto) * d_human
```

A human check occurs only for candidates not already rejected automatically, so cascades can create repeated manual validation cost. Metrics that can occur multiple times are named as expected event counts: `expected_auto_escaped_defect_events`, `expected_human_detected_defect_events`, and `expected_human_validation_count`. Only route exit measures are probabilities.

The gateway does not use subjective human/device checking as justification for direct completion. If decisive automatic validation is unavailable, it escalates.

## Long-context pricing

Long-context tiering is per call. Prefer exact provider `context_tokens`; otherwise infer conservatively as `fresh_input + cached_input + cache_write`. Pricing metadata records its official source URL and check date.

## Qualitative cold-start worker policy

Until enough calibrated worker evidence exists:

- Luna: low ambiguity + strong oracle + cheap recovery,
- Terra: normal coupled implementation,
- Sol: weak oracle, difficult debugging, subtle invariants/concurrency/migration,
- Astra: authority, integration, security/privacy/public contracts, high-consequence final judgment.

These are priors, not quotas, and do not define gateway admission.

## Scout VOI

Scout should run only when expected avoided wrong-tier/rework/cold-read cost exceeds Scout execution + parent ingestion. `P(changed tier | Scout used)` is diagnostic, not the final value metric.

## Auto baseline

GitHub Auto is a separate platform-managed router. Keep Auto and fixed-tier observations separate unless the resolved model is recorded. Compare validated economics rather than assuming either policy is universally superior.
