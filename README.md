# Copilot Astra

Cost-aware GitHub Copilot orchestration with GPT-6 Astra as long-horizon parent when warm context is valuable and exact fixed-model subagents for isolated work.

The objective is **minimum risk-adjusted expected cost per validated correct task**. This is not Luna-first and not a mandatory adjacent cascade.

## Core policy

Astra routes using authority, context warmth, task class, empirical `p(correct)`, automatic and human/device oracle strength, hidden-defect cost, dispatch/rework cost, output volume, human revalidation burden, and optional latency value.

The parent selects the lowest **risk-feasible economic route**. Intermediate tiers may be skipped: `Luna -> Sol -> Astra` is valid.

## Physical agent matrix

| Profile | Model | Purpose |
| --- | --- | --- |
| Astra Orchestrator | GPT-6 Astra | intent, architecture, integration, authority, final acceptance |
| Scout Luna | GPT-5.6 Luna | cold repository discovery |
| Research Luna | GPT-5.6 Luna | narrow current-doc/API lookup |
| Research Terra | GPT-5.6 Terra | multi-source/compatibility synthesis |
| Execute Luna | GPT-5.6 Luna | mechanical/repetitive implementation |
| Execute Terra | GPT-5.6 Terra | coupled ordinary multi-file implementation |
| Execute Sol | GPT-5.6 Sol | reasoning-heavy bounded implementation |
| Debug Sol | GPT-5.6 Sol | difficult root-cause analysis/fix |
| Verify Luna | GPT-5.6 Luna | optional isolated deterministic evidence |
| Verify Terra | GPT-5.6 Terra | semantic regression/contract review |
| Verify Sol | GPT-5.6 Sol | subtle high-risk correctness review |

## Verification economics

Execute/Debug profiles self-validate first. `Verify Luna` is not compulsory; use it when a separate context isolates bulky output or adds distinct independent command evidence. Use Terra/Sol semantic review only when deterministic evidence cannot establish required correctness.

### Human/device validation

Human validation is modeled as a **second oracle**, not as automatic permission to choose a cheaper worker.

If an incorrect result survives automatic checks with probability `(1 - d_auto)`, and the required human/device procedure detects such escaped defects with probability `d_human`, residual hidden-failure risk for that stage is:

```text
(1 - p_correct) * (1 - d_auto) * (1 - d_human)
```

The router also charges expected human setup/retest cost and latency. This produces three useful behaviors:

- a strong, cheap, repeatable device/visual oracle can make Luna economical;
- an expensive manual retest can make Terra/Sol direct cheaper than repeated Luna cycles;
- a weak/subjective human oracle does not justify Luna for high-consequence work.

Required human validation creates `NEEDS_HUMAN_VALIDATION`, not success or failure. Pending/blocked human validation is excluded from model correctness calibration. See `docs/human-device-validation.md`.

## Scout and parallelism

Scout is a value-of-information action, not compulsory preflight. Writer fan-out defaults to **1**, is conditionally **2**, and has exceptional cap **3**.

## Risk-aware estimator

Pricing lives in `config/pricing.json`; long-context tiering is applied per call.

```bash
python scripts/route_cost.py \
  --fresh-input 12000 --output 2500 \
  --ladder luna:0.70:0.80,terra:0.93:0.95,sol:0.985:0.995,astra:1:1 \
  --dispatch-units 0.5 --handoff-units 0.5 --failure-penalty 2 \
  --defect-penalty 200 --max-hidden-failure 0.01 \
  --human-validation-required --human-detection-rate 0.95 \
  --human-validation-units 3 --human-validation-seconds 120
```

Each ladder entry is `model:p_correct:auto_detection_rate`.

## Calibration

```bash
python scripts/calibrate_routing.py observations.jsonl
python scripts/policy_search.py
```

Keep Auto-selected runs separate unless resolved model is known. Human-required observations use explicit validation states and failure attribution so device/environment failures do not contaminate model priors.

## Local validation — no GitHub Actions

This repository intentionally contains **no GitHub Actions workflows**. The canonical acceptance command is:

```bash
python scripts/validate_all.py
```

It enforces the no-Actions policy, validates agent/policy configuration, runs all unit tests, and runs the offline policy regression. See `docs/local-validation.md` and `docs/adr/0002-local-validation-no-github-actions.md`.

## Research and decisions

- `docs/research/2026-09-09-deep-routing-research.md` — official findings, engineering inferences, alternatives, revalidation checklist
- `docs/adr/0001-risk-aware-routing.md` — accepted routing architecture decision
- `docs/adr/0002-local-validation-no-github-actions.md` — accepted local-only validation decision
- `docs/adr/0003-human-validation-as-oracle.md` — accepted human/device validation routing decision
- `docs/human-device-validation.md` — state machine, mathematics, operator packet, calibration schema
- `docs/astra-routing.md` — routing mathematics/policy
- `docs/observability.md` — measurement/calibration schema
- `docs/model-routing-surfaces.md` — client/surface behavior
- `docs/local-validation.md` — canonical repository validation contract

The pricing snapshot is an engineering estimator, not authoritative billing.
