# Copilot Astra

Cost-aware GitHub Copilot orchestration for VS Code with a **registry-driven model topology**. One warm parent holds long-horizon intent/authority; generated fixed-model subagents handle isolated work when delegation has positive expected value.

The objective is **minimum risk-adjusted expected cost per validated correct task**. The router is not cheapest-first, not tied to any one model family, and not restricted to four tiers.

## Model inventory is configuration

`config/model-registry.json` is the source of truth for:

- active model ids and capability order,
- the authority model,
- exact Copilot model strings,
- topology-relative role/profile selection,
- cold-start correctness/detection seed assumptions.

The active route can contain two, three, four, or more models. Routing code does not special-case `luna`, `terra`, `sol`, or `astra`.

Inspect the current topology:

```bash
python scripts/sync_model_config.py --summary
```

Change models/prices safely:

```bash
$EDITOR config/model-registry.json
$EDITOR config/pricing.json
python scripts/sync_model_config.py --write
python scripts/validate_all.py
```

`sync_model_config.py` regenerates the parent allowlist, physical role+model profiles, and seed routing priors. Generated `.github/agents/*.agent.md` files should not be hand-edited.

See `docs/model-registry.md` for explicit four/three/two-model examples.

## Transition-aware routing

Model quality is **path-conditioned**:

```text
P(model correct | direct)
!=
P(model correct | lower models already failed)
```

The authority model is final authority but is **not modeled as 100% correct**. The policy separately tracks:

- hidden incorrect result accepted,
- detected failure unresolved at the final stage,
- total probability of validated correct completion.

Intermediate tiers are optional. For an active route `low -> high -> authority`, valid candidates include `low -> high -> authority`, `low -> authority`, `high -> authority`, and `authority`.

## Generated physical agents

Roles are stable while model count changes:

- Scout — lowest eligible worker,
- Research — lowest + middle eligible worker positions,
- Execute — all eligible workers,
- Debug — highest worker meeting a minimum worker-count requirement,
- Verify — all eligible workers,
- parent — authority model.

If a reduced topology lacks a sufficiently capable Debug worker, no weak Debug subagent is generated; the parent keeps that work.

All generated profiles explicitly target `vscode`, are non-recursive, and are protected from general model invocation. The parent receives the exact generated subagent allowlist.

## Seed priors and empirical overlays

`config/routing-priors.json` is generated from the active registry and contains low-confidence cold-start assumptions. It is deliberately not a benchmark claim.

Generate a local evidence overlay from metadata-only observations:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

`config/routing-priors.local.json` remains local/uncommitted and overrides generated seed fields where evidence is more specific.

## Pricing evolution

`config/pricing.json` is separate from model topology. Schema v2 supports:

- arbitrary model ids,
- one or more named pricing/context tiers per model,
- arbitrary `min_context_tokens` thresholds,
- inactive/historical priced models.

Every active registry model must have pricing, but pricing may contain extra inactive models. Provider rate/tier changes should therefore require data edits, not routing-code edits.

Prefer explicit `context_tokens`; when unavailable, the estimator conservatively uses:

```text
fresh_input + cached_input + cache_write
```

## Route estimator

Without `--models` or `--ladder`, the estimator reads the active route from the registry:

```bash
python scripts/route_cost.py \
  --task-class coupled \
  --oracle-strength mixed \
  --risk-class standard \
  --fresh-input 12000 \
  --output 2500 \
  --dispatch-units 0.5 \
  --handoff-units 0.5 \
  --failure-penalty 2
```

`--models` can evaluate a monotone subset of the active route but must still end in the configured authority model. `--ladder` remains available for explicit probability experiments.

Risk classes are executable policy in `config/risk-policy.json`.

## Human/device validation

Human validation is a second oracle, not automatic permission to choose a cheaper worker.

Residual hidden-failure probability for a reached stage is based on:

```text
(1 - p_correct) * (1 - d_auto) * (1 - d_human)
```

Pending required human validation is `NEEDS_HUMAN_VALIDATION`, not success/failure. Device/environment/infrastructure/procedure/operator and unknown failures are excluded from model correctness priors until attribution is resolved.

## Local validation only

This repository intentionally uses no GitHub Actions. Canonical acceptance:

```bash
python scripts/validate_all.py
```

The suite checks generated-model synchronization, registry/pricing/priors/risk configuration, unit tests, explicit two/three-model compatibility, future-model synthetic pricing, and offline routing regression.

## Design records

- `docs/model-registry.md` — model/pricing change procedure and 2/3/4-model examples
- `docs/adr/0005-registry-driven-model-topology.md` — variable-topology decision
- `docs/astra-routing.md` — executable routing mathematics and fallback rules
- `docs/human-device-validation.md` — human/device oracle state machine
- `docs/observability.md` — measurement and strict calibration schema
- `docs/model-routing-surfaces.md` — Copilot surface behavior
- `docs/local-validation.md` — no-Actions local acceptance contract
- `docs/research/2026-09-10-routing-review.md` — prior review findings and platform checks

The routing system is an auditable decision aid. Model inventory and prices are operational data and should evolve without requiring structural code rewrites.
