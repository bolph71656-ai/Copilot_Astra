# Copilot Astra

Cost-aware GitHub Copilot orchestration for VS Code with a **registry-driven model topology** and a conservative two-stage entry path.

The default low-cost entry is **Astra Gateway**, generated on the lowest active non-authority model. It is not a general-purpose parent. A direct completion is allowed only when the semantic safety gates are clear and `scripts/gateway_policy.py` returns `ALLOW_DIRECT` before edits; otherwise the task is escalated intact to **Astra Orchestrator**, where the configured authority model preserves long-horizon intent and can dispatch fixed-model workers.

The objective is **minimum risk-adjusted expected cost per validated correct task**. The router is not cheapest-first, not tied to any one model family, and not restricted to four tiers.

## Entry path

For normal repository work, start with `Astra Gateway` unless you already know the task requires authority-level judgment.

```text
User
  |
  v
Astra Gateway (lowest active worker, currently Luna)
  |
  |-- hard semantic gates clear
  |   + executable policy ALLOW_DIRECT ------------> direct work + decisive automatic validation
  |
  `-- any uncertainty / policy denial ------------> Astra Orchestrator
                                                     |
                                                     `--> generated workers / verification
```

The gateway is deliberately **fail-closed**. False down-routing is treated as more costly than over-escalation. It cannot invoke normal workers; it may only escalate to the authority parent.

Cold-start behavior is intentionally narrow:

- bootstrap direct completion: `exploratory` risk + `deterministic` oracle only,
- `standard` direct completion: disabled until local gateway calibration clears conservative confidence bounds,
- `high` / `critical`: never complete directly at the gateway,
- worker `p_correct` seed priors: never treated as evidence that the same model is a safe router.

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

The gateway is an admission layer in front of this route model, not permission to bypass its risk constraints. If a task does not satisfy the gateway's strict direct-completion policy, the normal authority routing policy applies.

## Generated physical agents

Roles are stable while model count changes:

- Gateway — lowest active non-authority model, user-invocable, conservative direct work or authority escalation only,
- Scout — lowest eligible worker,
- Research — lowest + middle eligible worker positions,
- Execute — all eligible workers,
- Debug — highest worker meeting a minimum worker-count requirement,
- Verify — all eligible workers,
- parent — authority model.

If a reduced topology lacks a sufficiently capable Debug worker, no weak Debug subagent is generated; the parent keeps that work.

All generated worker profiles explicitly target `vscode`, are non-recursive, and are protected from general model invocation. The authority parent receives the exact generated worker allowlist. The gateway receives only the authority parent in its allowlist.

## Worker priors and gateway calibration are separate

`config/routing-priors.json` is generated from the active registry and contains low-confidence cold-start assumptions for **worker routing**. It is deliberately not a benchmark claim.

Generate a local worker evidence overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

Gateway admission is calibrated independently. Generate the ignored local gateway calibration file from metadata-only observations:

```bash
python scripts/calibrate_gateway.py observations.jsonl \
  --out config/gateway-calibration.local.json
```

Current `config/gateway-policy.json` requires conservative confidence bounds before standard-risk direct completion can be enabled. The default policy requires at least the configured sample floor, a sufficiently high confidence level, a low false-downroute upper bound, a high validated-correct lower bound, a low authority-rescue upper bound, and a favorable gateway-vs-authority cost ratio.

Global rollback thresholds can pause gateway direct completion when safety or economics regress. Any observed high/critical false down-route is an immediate rollback trigger.

Both local calibration files remain uncommitted. Do not infer gateway safety from worker `p_correct` priors.

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
  --output 2500
```

When dispatch, handoff, failure, defect, or latency-value arguments are omitted, `route_cost.py` loads engineering defaults from `config/operational-costs.json`. Dispatch/handoff/rework and defect cost therefore no longer silently collapse to zero. The file records whether those defaults are measured; the committed defaults are explicitly conservative bootstrap assumptions, not billing facts.

Explicit CLI values still override the defaults, including an explicit zero for controlled experiments.

`--models` can evaluate a monotone subset of the active route but must still end in the configured authority model. `--ladder` remains available for explicit probability experiments. Risk classes are executable policy in `config/risk-policy.json`.

Gateway-first economics must be compared against authority-direct at the **task level**, including gateway classification, duplicated context on escalation, handoff ingestion, rework, and latency. Cheap model token price alone is not a break-even proof.

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

The suite checks generated-model synchronization, gateway/parent/worker structure, registry/pricing/priors/risk configuration, calibrated gateway policy/economics guardrails, unit tests, explicit two/three-model compatibility, future-model synthetic pricing, and offline routing regression.

## Design records

- `docs/model-registry.md` — model/pricing change procedure and 2/3/4-model examples
- `docs/adr/0005-registry-driven-model-topology.md` — variable-topology decision
- `docs/adr/0006-calibrated-gateway-admission.md` — fail-closed bootstrap, evidence-gated expansion, and rollback decision
- `docs/astra-routing.md` — executable routing mathematics, gateway admission, and fallback rules
- `docs/human-device-validation.md` — human/device oracle state machine
- `docs/observability.md` — measurement and strict calibration schema
- `docs/model-routing-surfaces.md` — Copilot surface behavior
- `docs/local-validation.md` — no-Actions local acceptance contract
- `docs/research/2026-09-10-routing-review.md` — prior review findings and platform checks

The routing system is an auditable decision aid. Model inventory, prices, gateway evidence, and operational economics should evolve as data without turning seed assumptions into asserted facts.
