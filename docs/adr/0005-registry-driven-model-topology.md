# ADR 0005: Registry-driven variable model topology

- Status: Accepted
- Date: 2026-09-10

## Context

The initial routing implementation encoded a four-model ladder in several places: CLI defaults, authority-name checks, validator constants, physical agent filenames, parent allowlists, documentation, and tests. That made a provider model retirement, price change, or deliberate reduction to three/two models require coordinated code edits.

A cost router should treat model inventory as changing operational data, not application structure.

## Decision

Introduce `config/model-registry.json` as the source of truth for model identity and active topology.

The registry defines:

- arbitrary model ids and Copilot model strings,
- strictly ordered capability ranks,
- an active `route_order`,
- the final `authority_model`,
- topology-relative role policies,
- conservative seed priors.

`config/pricing.json` remains a separate source for cost information and now supports arbitrary named context/pricing tiers.

`python scripts/sync_model_config.py --write` generates:

- the parent agent's model and exact subagent allowlist,
- all physical role+model `.agent.md` profiles,
- seed `config/routing-priors.json`.

The routing engine reads the active route from the registry. It does not special-case a model named Astra and does not require an intermediate model count.

## Role degradation policy

Reducing model count must not automatically assign a high-risk role to the only remaining cheap worker.

Role policies therefore combine relative slots (`lowest`, `middle`, `highest`, `all`) with optional `min_worker_count`. If no worker satisfies a role's minimum, that role becomes parent-only.

## Pricing policy

Pricing is operational metadata. Active models must have pricing; inactive/historical models may remain priced. Pricing schema v2 allows any number of context tiers selected by `min_context_tokens`.

## Validation

Regression tests use synthetic model ids and synthetic pricing rather than asserting today's Luna/Terra/Sol/Astra rates. Dedicated tests cover:

- three-model topology,
- two-model topology,
- arbitrary future model/authority names,
- arbitrary pricing-tier counts,
- generated allowlist/profile counts,
- generic monotone route enumeration.

Offline policy fixtures also use synthetic topology names.

## Consequences

Positive:

- model retirement/addition is a configuration operation,
- two/three/four-model configurations use one code path,
- pricing changes do not require routing-code edits,
- generated physical profiles cannot silently drift from the active route,
- tests survive provider pricing/model renames.

Costs:

- generated agent profiles must not be hand-edited,
- registry seed priors still require judgment for a genuinely new model,
- changing capability ranks/role thresholds is a policy decision and must be reviewed.

## Operational procedure

After changing the registry or pricing:

```bash
python scripts/sync_model_config.py --write
python scripts/validate_all.py
```

See `docs/model-registry.md` for examples.
