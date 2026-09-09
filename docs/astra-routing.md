# Risk-aware Astra multi-model routing

Optimize **risk-adjusted expected AI-credit cost per validated correct task**.

For route `π`, estimate expected cost `E[Cπ]`, validated-correct probability `Pcorrect(π)`, hidden-failure probability `Phidden(π)`, and optional latency `E[Tπ]`.

Rank viable routes by:

`(E[Cπ] + λ_defect * Phidden(π) + λ_latency * E[Tπ]) / Pcorrect(π)`

subject to `Phidden(π) <= risk_budget`.

## Success and detection are different

For each stage: `p = P(correct)` and `d = P(incorrect result is detected before acceptance | incorrect)`.

- correct exit: `reach * p`
- hidden failure: `reach * (1-p) * (1-d)`
- detected escalation: `reach * (1-p) * d`

Cheap execution is attractive when failures are detectable. Weak oracles can make a cheap route unsafe.

## Per-call pricing

`config/pricing.json` is an engineering snapshot. Long-context thresholds apply **per model call**. Two 150K Luna calls are not one aggregated 300K long-context call.

## Routing features

Use authority, warm/cold context, task class, coupling/ambiguity, oracle strength, hidden-defect/blast-radius cost, output volume, dispatch/rework overhead, and latency sensitivity. Task size alone is insufficient.

## Scout value of information

Use Scout only when `expected avoided misroute/rework > Scout cost + Astra ingestion`. Reclassify once after Scout.

## Direct start

- Luna: explicit/mechanical, strong deterministic oracle, cheap detectable failure.
- Terra: ordinary coupled multi-file reasoning, moderate ambiguity.
- Sol/Debug Sol: unclear root cause, concurrency/migration/performance/invariants, weak validation, expensive silent failure.
- Astra: authority/integration or tiny warm edit cheaper than dispatch.

## Intermediate tiers are optional

Capability escalation is monotone, but routes need not visit every tier. `Luna -> Sol -> Astra` may dominate an adjacent cascade. `scripts/route_cost.py` enumerates monotone routes ending at final authority.

## Retry EV

Retry Luna only for obvious local/mechanical failure with unchanged scope, short correction, decisive deterministic validation, and expected retry cost below escalation. Conceptual failure escalates.

## Verification

Execute/Debug profiles self-validate. `Verify Luna` is optional for bulky/distinct independent deterministic evidence. Use Verify Terra/Sol when residual uncertainty is semantic.

## Parallelism

Writer default 1; conditional 2 for disjoint modules/stable interfaces; exceptional cap 3. Overlapping contracts/files/migrations serialize.

## Bayesian calibration

`scripts/calibrate_routing.py` estimates priors separately by task class, start model, `reached_after`, and oracle strength. Do not assume a model has the same success rate direct versus after earlier failure evidence.

## Offline policy search

`config/routing-fixtures.json` encodes representative scenarios. `python scripts/policy_search.py` is routing regression, not benchmark proof.

## Auto baseline

GitHub Auto is a separate external router with cache-boundary and availability advantages. Compare validated cost, defects, latency, attribution, and operational complexity; do not claim superiority without evidence.

Research basis: `docs/research/2026-09-09-deep-routing-research.md` and `docs/adr/0001-risk-aware-routing.md`.
