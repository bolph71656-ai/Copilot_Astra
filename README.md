# Copilot Astra

Cost-aware GitHub Copilot orchestration for VS Code. GPT-6 Astra remains the long-horizon parent when warm context and authority matter; exact fixed-model subagents handle isolated work.

The objective is **minimum risk-adjusted expected cost per validated correct task**. This is not Luna-first, not Astra-only, and not a mandatory adjacent cascade.

## What changed in the mature router

The router now treats model quality as **path-conditioned**:

```text
P(Sol correct | direct)
!=
P(Sol correct | Luna already failed)
!=
P(Sol correct | Luna > Terra already failed)
```

Astra is final authority but is **not modeled as 100% correct**. The policy tracks three distinct acceptance risks:

- hidden incorrect result accepted,
- detected failure that remains unresolved at the final stage,
- total probability of validated correct completion.

## Physical model matrix

| Profile | Fixed model | Purpose |
| --- | --- | --- |
| Astra Orchestrator | GPT-6 Astra | intent, architecture, integration, authority, final acceptance |
| Scout Luna | GPT-5.6 Luna | cold repository discovery |
| Research Luna | GPT-5.6 Luna | narrow current-doc/API lookup |
| Research Terra | GPT-5.6 Terra | multi-source/compatibility synthesis |
| Execute Luna | GPT-5.6 Luna | mechanical/repetitive implementation |
| Execute Terra | GPT-5.6 Terra | coupled ordinary implementation |
| Execute Sol | GPT-5.6 Sol | reasoning-heavy bounded implementation |
| Debug Sol | GPT-5.6 Sol | difficult root-cause analysis/fix |
| Verify Luna | GPT-5.6 Luna | optional isolated deterministic evidence |
| Verify Terra | GPT-5.6 Terra | semantic regression/contract review |
| Verify Sol | GPT-5.6 Sol | subtle high-risk correctness review |

All profiles explicitly target `vscode`. Subagents are hidden, non-recursive, and protected from general model invocation. The Astra parent explicitly allowlists them.

## Seed priors and empirical overlays

`config/routing-priors.json` contains low-confidence cold-start assumptions. It is deliberately not a benchmark claim.

Generate a machine-readable local overlay from metadata-only observations:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

`route_cost.py` automatically loads the seed file and the local overlay when present. More specific/later calibrated entries override generic seed fields while missing fields fall back safely.

`config/routing-priors.local.json` should remain local and uncommitted.

## Route estimator

Without `--ladder`, route evaluation uses transition-aware priors:

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

For explicit experiments, `--ladder model:p_correct:detection_rate,...` remains available and bypasses priors.

Risk classes are executable policy in `config/risk-policy.json`.

## Human/device validation

Human validation is a second oracle, not automatic permission to choose a cheaper worker.

Residual hidden-failure probability for a reached stage is based on:

```text
(1 - p_correct) * (1 - d_auto) * (1 - d_human)
```

The estimator also includes expected manual validation count, human time/latency, and repeated revalidation after escalation.

Pending required human validation is `NEEDS_HUMAN_VALIDATION`, not success or failure. Device/environment/infrastructure/procedure/operator and unknown failures are excluded from model correctness priors until attribution is resolved.

## Pricing/context

`config/pricing.json` is an engineering snapshot checked against GitHub's official models-and-pricing table. Long-context selection is per call. Prefer explicit `context_tokens`; when unavailable, the estimator conservatively uses:

```text
fresh_input + cached_input + cache_write
```

## Scout and parallelism

Scout is a value-of-information action, not compulsory preflight.

Writer fan-out:
- default 1,
- conditional 2 for clearly disjoint modules,
- exceptional hard cap 3.

## Local validation only

This repository intentionally uses no GitHub Actions. Canonical acceptance:

```bash
python scripts/validate_all.py
```

It rejects GitHub Actions workflow files, validates the physical model/policy configuration, runs all tests, and executes offline policy regression.

## Design records

- `docs/astra-routing.md` — executable routing mathematics and fallback rules
- `docs/human-device-validation.md` — human/device oracle state machine
- `docs/observability.md` — measurement and strict calibration schema
- `docs/research/2026-09-10-routing-review.md` — latest review findings and official platform checks
- `docs/adr/0004-transition-aware-empirical-routing.md` — transition-aware empirical routing decision
- `docs/model-routing-surfaces.md` — client/surface behavior
- `docs/local-validation.md` — no-Actions local acceptance contract

The routing system is an auditable decision aid. It should become more empirical as observations accumulate, not more confident from unmeasured assumptions.
