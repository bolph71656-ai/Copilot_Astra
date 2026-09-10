# Copilot Astra

Cost-aware GitHub Copilot orchestration for VS Code with a **registry-driven model topology** and a conservative two-stage entry path.

The default low-cost entry is **Astra Gateway**, generated on the lowest active non-authority model. It directly completes only obvious low-risk, machine-verifiable work. Anything ambiguous, high-consequence, integration-heavy, weak-oracle, or previously failed is escalated intact to **Astra Orchestrator**, where the configured authority model preserves long-horizon intent and can dispatch fixed-model workers.

The objective is **minimum risk-adjusted expected cost per validated correct task**. The router is not cheapest-first, not tied to any one model family, and not restricted to four tiers.

## Entry path

For normal repository work, start with `Astra Gateway` unless you already know the task requires authority-level judgment.

```text
User
  |
  v
Astra Gateway (lowest active worker, currently Luna)
  |-- obvious low-risk + strong automatic oracle --> complete directly
  |
  `-- any uncertainty / authority trigger --------> Astra Orchestrator
                                                    |
                                                    `--> generated workers / verification
```

`Astra Gateway` is deliberately **fail-closed**. False down-routing is treated as more costly than over-escalation. It cannot invoke normal workers; it may only escalate to the authority parent. This keeps Luna from acting as a general-purpose parent while still avoiding Astra startup cost on clearly mechanical work.

Known authority/high-risk work may invoke `Astra Orchestrator` directly and skip the gateway.

## Model inventory is configuration

`config/model-registry.json` is the source of truth for:

- active model ids and capability order,
- the authority model,
- exact Copilot model strings,
- topology-relative role/profile selection,
- cold-start correctness/detection seed assumptions.

The active route can contain two, three, four, or more models. Routing code does not special-case `luna`, `terra`, `sol`, or `astra`.

When at least one non-authority model exists, `sync_model_config.py` also generates `Astra Gateway` on the lowest active non-authority model. A one-model authority-only topology omits the gateway because it would provide no cost advantage.

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

`sync_model_config.py` regenerates the gateway, authority parent allowlist, physical role+model profiles, and seed routing priors. Generated `.github/agents/*.agent.md` files should not be hand-edited.

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

The gateway is an admission layer in front of this route model, not permission to bypass its risk constraints. If a task does not satisfy the gateway's strict direct-completion gate, the normal authority routing policy applies.

## Generated physical agents

Roles are stable while model count changes:

- Gateway — lowest active non-authority model, user-invocable, direct low-risk work or authority escalation only,
- Scout — lowest eligible worker,
- Research — lowest + middle eligible worker positions,
- Execute — all eligible workers,
- Debug — highest worker meeting a minimum worker-count requirement,
- Verify — all eligible workers,
- parent — authority model.

If a reduced topology lacks a sufficiently capable Debug worker, no weak Debug subagent is generated; the parent keeps that work.

All generated worker profiles explicitly target `vscode`, are non-recursive, and are protected from general model invocation. The authority parent receives the exact generated worker allowlist. The gateway receives only the authority parent in its allowlist.

## Seed priors and empirical overlays

`config/routing-priors.json` is generated from the active registry and contains low-confidence cold-start assumptions. It is deliberately not a benchmark claim.

Generate a local evidence overlay from metadata-only observations:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

`config/routing-priors.local.json` remains local/uncommitted and overrides generated seed fields where evidence is more specific.

The gateway should be evaluated separately with **false-downroute rate**, direct-completion rate, escalation rate, validated-correct rate, and end-to-end cost. Do not infer gateway safety from worker `p_correct` priors.

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

Gateway admission overhead is real orchestration cost. Until dedicated telemetry is available, include measured gateway/escalation overhead in dispatch/handoff assumptions when comparing gateway-first with authority-direct operation.

## Human/device validation

Human validation is a second oracle, not automatic permission to choose a cheaper worker.

Residual hidden-failure probability for a reached stage is based on:

```text
(1 - p_correct) * (1 - d_auto) * (1 - d_human)
```

Pending required human validation is `NEEDS_HUMAN_VALIDATION`, not success/failure. Device/environment/infrastructure/procedure/operator and unknown failures are excluded from model correctness priors until attribution is resolved.

Gateway direct completion requires a decisive automatic oracle and does not use subjective human/device validation as justification for down-routing.

## Local validation only

This repository intentionally uses no GitHub Actions. Canonical acceptance:

```bash
python scripts/validate_all.py
```

The suite checks generated-model synchronization, gateway/parent/worker structure, registry/pricing/priors/risk configuration, unit tests, explicit two/three-model compatibility, future-model synthetic pricing, and offline routing regression.

## Design records

- `docs/model-registry.md` — model/pricing change procedure and 2/3/4-model examples
- `docs/adr/0005-registry-driven-model-topology.md` — variable-topology decision
- `docs/astra-routing.md` — executable routing mathematics, gateway admission, and fallback rules
- `docs/human-device-validation.md` — human/device oracle state machine
- `docs/observability.md` — measurement and strict calibration schema
- `docs/model-routing-surfaces.md` — Copilot surface behavior
- `docs/local-validation.md` — no-Actions local acceptance contract
- `docs/research/2026-09-10-routing-review.md` — prior review findings and platform checks

The routing system is an auditable decision aid. Model inventory and prices are operational data and should evolve without requiring structural code rewrites.
