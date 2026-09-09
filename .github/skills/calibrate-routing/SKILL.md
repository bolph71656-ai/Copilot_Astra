---
name: calibrate-routing
description: Calibrate transition-aware Astra/Luna/Terra/Sol routing from metadata-only observations, including path-conditioned model correctness, automatic/human oracle strength, attribution, retries, Scout value, and latency.
argument-hint: "[metadata-only observations]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Tune **risk-adjusted validated-task economics**, not model usage percentages.

Record task/risk class, model, exact `reached_after` path, oracle strength, per-call usage, validation state, failure attribution, automatic/human detection, hidden defects, retry/escalation, Scout use, latency, and Auto-vs-fixed mode.

Strict rules:
- pending human validation is not failure,
- blocked is not model failure,
- device/environment/infrastructure/procedure/operator failures do not update model correctness,
- unknown attribution remains unassigned,
- contradictory human-validation records are rejected,
- Astra is calibrated like every other model.

Generate a machine-readable local overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Then use `scripts/route_cost.py`; it loads the seed priors plus the local overlay automatically.

Direct and post-failure priors remain separate. Do not assume a model has the same success probability after lower-tier failures.

Before changing always-on policy:
1. update observations,
2. regenerate priors,
3. inspect candidate economics,
4. update fixtures only for intentional policy changes,
5. run `python scripts/validate_all.py`.

Do not mix Auto/fixed measurements unless the resolved model is recorded.
