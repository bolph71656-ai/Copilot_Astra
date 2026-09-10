# Model registry and topology changes

`config/model-registry.json` is the source of truth for **which models participate in routing** and which physical Copilot agent profiles are generated.

The routing engine does not require four models. The active topology is simply the ordered `route_order` ending in `authority_model`.

## Configuration split

Keep three different kinds of data separate:

- `config/model-registry.json` — model identity, active capability order, Copilot model string, role/profile selection, cold-start seed assumptions.
- `config/pricing.json` — token pricing/context-tier data. Pricing can contain inactive/historical models; every active model must have pricing.
- `config/routing-priors.local.json` — optional local empirical calibration. It is not committed.

`config/routing-priors.json` is **generated** from the model registry. Do not edit it by hand.

## Change workflow

After adding/removing/replacing a model or changing a Copilot model identifier:

```bash
# 1. edit registry and pricing
$EDITOR config/model-registry.json
$EDITOR config/pricing.json

# 2. regenerate physical agents + seed priors
python scripts/sync_model_config.py --write

# 3. inspect the resulting topology
python scripts/sync_model_config.py --summary

# 4. canonical local acceptance
python scripts/validate_all.py
```

No GitHub Actions are required or used.

## Four-model example

The current snapshot is conceptually:

```json
{
  "authority_model": "astra",
  "route_order": ["luna", "terra", "sol", "astra"]
}
```

The generator currently produces 10 subagents plus the parent.

## Three-model example

To remove the middle model while retaining low/high workers:

```json
{
  "authority_model": "astra",
  "route_order": ["luna", "sol", "astra"]
}
```

With the default role policy this yields:

- Scout: lowest worker only
- Research: lowest + middle position, which becomes low + high in a two-worker set
- Execute: all workers
- Debug: highest worker meeting the minimum worker-count requirement
- Verify: all workers
- parent: authority model

The router automatically enumerates monotone routes such as `luna -> sol -> astra`, `sol -> astra`, and `astra`.

## Two-model example

For one worker plus one authority model:

```json
{
  "authority_model": "astra",
  "route_order": ["luna", "astra"]
}
```

The default role policy generates Scout/Research/Execute/Verify on the worker. It **does not generate Debug** if the remaining worker is insufficient to satisfy Debug's `min_worker_count`; difficult debugging then stays in the authority parent. This is intentional: reducing model count must not silently assign high-risk work to an underpowered tier.

## Replacing models entirely

Model ids are internal stable slugs. The engine does not special-case `luna`, `terra`, `sol`, or `astra`.

A future configuration can use different ids, for example:

```json
{
  "authority_model": "future-max",
  "route_order": ["future-fast", "future-reasoner", "future-max"]
}
```

Each model entry supplies:

- `display_name` — used in generated agent names,
- `copilot_model` — exact VS Code Copilot model value,
- `capability_rank` — strictly increasing along `route_order`,
- `tier_guidance` — generated prompt guidance,
- `seed_prior.direct` and `seed_prior.after_any` — low-confidence cold-start assumptions.

The authority model must be the last active route entry and must not be seeded as infallible.

## Role selection semantics

`role_policies` use topology-relative slots instead of model names:

- `lowest` — cheapest/lowest-ranked eligible worker,
- `middle` — middle eligible worker (`len // 2`),
- `highest` — highest-ranked eligible worker,
- `all` — every eligible worker.

A role can set `min_worker_count`. If no active worker meets the threshold, no subagent for that role is generated and the parent retains the work.

This preserves role intent as the number of models changes.

## Pricing evolution

`config/pricing.json` schema v2 supports:

- arbitrary model ids,
- one or more named pricing tiers per model,
- arbitrary context thresholds through `min_context_tokens`,
- pricing models that are not currently active.

Example:

```json
{
  "tiers": [
    {"name": "base", "min_context_tokens": 0, "rates": {"fresh_input": 1, "cached_input": 1, "cache_write": 1, "output": 5}},
    {"name": "large", "min_context_tokens": 200001, "rates": {"fresh_input": 2, "cached_input": 2, "cache_write": 2, "output": 8}}
  ]
}
```

If the provider later adds a third context/pricing tier, add another tier row; routing code does not need modification.

## Historical calibration

Inactive models may remain in historical observation files and pricing metadata. The default router only uses active `route_order` models. When a model is removed or replaced, start its replacement with conservative seed priors until enough model-specific evidence exists; do not transfer calibrated correctness blindly across model families.
