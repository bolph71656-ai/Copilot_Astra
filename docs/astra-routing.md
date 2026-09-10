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

The gateway is not a free-form replacement for the authority parent. It is intentionally **fail-closed**:

```text
obvious low-risk
+ explicit scope/acceptance
+ local bounded surface
+ decisive automatic oracle available now
+ no authority trigger
+ no prior substantive failure
        |
        v
complete directly on gateway model

anything uncertain / high-risk / weak-oracle / integration-heavy
        |
        v
escalate intact to authority parent
```

The gateway may invoke only the authority parent. It cannot directly dispatch normal workers. This prevents a cheap model from making fine-grained Terra/Sol/Astra tier decisions while still removing authority startup cost from clearly mechanical work.

Authority triggers include security/privacy/auth/payment/trust boundaries; destructive or irreversible data changes; architecture/public contracts; cross-component or subtle concurrency/distributed invariants; weak/subjective oracles; high/critical risk; long-horizon integration/final acceptance; and substantive implementation or validation failure.

False down-routing is treated as a more serious error than over-escalation. Any uncertainty about a direct-completion condition resolves upward.

Known authority/high-risk work may bypass the gateway and invoke the authority parent directly.

### Gateway economics

Gateway-first operation is beneficial only when the savings from directly completed cheap tasks exceed:

- the gateway model call itself,
- classification reads/search,
- escalation handoff/ingestion cost,
- any rework caused by a false down-route,
- latency cost.

Therefore compare gateway-first and authority-direct using measured **task-level** cost, not gateway token price alone. Until dedicated telemetry is wired into the estimator, include measured gateway/escalation overhead in `dispatch_units` / `handoff_units` assumptions for scenario analysis.

The gateway's safety metrics are separate from model correctness priors. Track at least:

```text
direct_completion_rate
escalation_rate
false_downroute_rate
validated_correct_rate
authority_rescue_rate
mean_gateway_units
mean_escalation_handoff_units
end_to_end_units_per_validated_correct
```

The primary guardrail is `false_downroute_rate`, especially for standard/high consequence work. Worker `p_correct` does not establish that the same model is a safe classifier.

## Transition-aware priors

Direct-start capability and post-failure capability are different distributions. For `Luna -> Sol -> Astra`, lookup uses `direct`, then `luna`, then `luna>sol` as `reached_after`.

Lookup prefers exact task class + oracle strength + exact path, then exact/generic combinations with `after:any`, then wildcard seed fallback. Later prior files override same-specificity fields; partial calibrated entries can override one field while retaining seed values for missing fields.

This prevents using `P(Sol succeeds | direct)` after lower-tier failures have selected a harder residual task set.

## Astra is not perfect

Astra is the authority boundary, not mathematical certainty. Seed priors keep Astra below 1.0 and calibration updates Astra exactly like other models. A detected Astra failure that remains unresolved is a real terminal task failure.

## Priors pipeline

Cold start: `config/routing-priors.json`.

Local evidence overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Normal routing consumes both. Do not commit user/task telemetry or the local overlay.

## Strict observation attribution

A failed observation enters model correctness calibration only when `failure_attribution = implementation`. Pending human validation, blocked states, device/environment/infrastructure/procedure/operator failures, and unknown attribution stay outside the model posterior. Contradictory human-validation states are rejected rather than silently repaired.

## Human/device oracle

For an incorrect result:

```text
d_total = d_auto + (1 - d_auto) * d_human
```

A human check occurs only for candidates not already rejected automatically, so cascades can create repeated manual validation cost. Metrics that can occur multiple times are named as expected event counts: `expected_auto_escaped_defect_events`, `expected_human_detected_defect_events`, and `expected_human_validation_count`. Only route exit measures are probabilities.

The gateway does not use subjective human/device checking as justification for direct completion. If decisive automatic validation is unavailable, it escalates.

## Long-context pricing

Long-context tiering is per call. Prefer exact provider `context_tokens`; otherwise infer conservatively as `fresh_input + cached_input + cache_write`. Pricing metadata records its official source URL and check date.

## Qualitative cold-start policy

Until enough calibrated evidence exists:
- Gateway: obvious low-risk, bounded, machine-verifiable work only; otherwise authority escalation,
- Luna: low ambiguity + strong oracle + cheap recovery,
- Terra: normal coupled implementation,
- Sol: weak oracle, difficult debugging, subtle invariants/concurrency/migration,
- Astra: authority, integration, security/privacy/public contracts, high-consequence final judgment.

These are priors, not quotas.

## Scout VOI

Scout should run only when expected avoided wrong-tier/rework/cold-read cost exceeds Scout execution + parent ingestion. `P(changed tier | Scout used)` is diagnostic, not the final value metric.

## Auto baseline

GitHub Auto is a separate platform-managed router. Keep Auto and fixed-tier observations separate unless the resolved model is recorded. Compare validated economics rather than assuming either policy is universally superior.
