---
name: calibrate-routing
description: Calibrate registry-defined, transition-aware routing from metadata-only observations, including path-conditioned model correctness, automatic/human oracle strength, attribution, retries, Scout value, latency, and model cost.
argument-hint: "[metadata-only observations]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Tune **risk-adjusted validated-task economics**, not model usage percentages.

Active model ids, capability order, authority, and role placement come from `config/model-registry.json`. Historical observations may reference inactive models, but the default router evaluates only active `route_order` models.

Record task/risk class, model, exact `reached_after` path, oracle strength, per-call usage, validation state, failure attribution, automatic/human detection, hidden defects, retry/escalation, Scout use, latency, and Auto-vs-fixed mode.

Strict rules:
- pending human validation is not failure,
- blocked is not model failure,
- device/environment/infrastructure/procedure/operator failures do not update model correctness,
- unknown attribution remains unassigned,
- contradictory human-validation records are rejected,
- the authority model is calibrated like every other model,
- direct and post-failure priors remain separate,
- retired-model posteriors are never copied blindly to a replacement model.

Generate a machine-readable local overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Then use `scripts/route_cost.py`; it loads the seed priors plus the local overlay automatically.

When a new model replaces an old one, keep the new model's conservative registry seed until direct evidence accumulates. Keep fixed-model and Auto-selected observations separate unless the resolved model is recorded.

Before changing always-on routing policy:
1. update observations,
2. regenerate priors,
3. inspect candidate economics,
4. update fixtures only for intentional policy changes,
5. run `python scripts/validate_all.py`.

Model inventory or pricing changes are separate configuration operations:
1. edit `config/model-registry.json` and/or `config/pricing.json`,
2. run `python scripts/sync_model_config.py --write`,
3. run `python scripts/validate_all.py`.
