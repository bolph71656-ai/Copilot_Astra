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

## Long-context pricing

Long-context tiering is per call. Prefer exact provider `context_tokens`; otherwise infer conservatively as `fresh_input + cached_input + cache_write`. Pricing metadata records its official source URL and check date.

## Qualitative cold-start policy

Until enough calibrated evidence exists:
- Luna: low ambiguity + strong oracle + cheap recovery,
- Terra: normal coupled implementation,
- Sol: weak oracle, difficult debugging, subtle invariants/concurrency/migration,
- Astra: authority, integration, security/privacy/public contracts, high-consequence final judgment.

These are priors, not quotas.

## Scout VOI

Scout should run only when expected avoided wrong-tier/rework/cold-read cost exceeds Scout execution + parent ingestion. `P(changed tier | Scout used)` is diagnostic, not the final value metric.

## Auto baseline

GitHub Auto is a separate platform-managed router. Keep Auto and fixed-tier observations separate unless the resolved model is recorded. Compare validated economics rather than assuming either policy is universally superior.
