# Copilot Astra

Cost-aware GitHub Copilot orchestration that keeps **GPT-6 Astra** as the warm long-horizon parent and dispatches exact fixed-model subagents.

```text
warm micro-edit / architecture / integration -> Astra direct
cheap discovery / routine work / deterministic checks -> Luna profiles
normal multi-file / synthesis / semantic review -> Terra profiles
deep bounded implementation / debugging / high-risk review -> Sol profiles
final authority -> Astra
```

The objective is **minimum expected AI-credit cost per validated correct task**, including dispatch, handoff, retries, cache churn, verification, escalation, and defects. The policy is not "Luna first": Astra performs one cheap routing pass and starts directly at the lowest tier with sufficiently high expected success and adequate validation.

## Quick start

1. Open the repository in a supported GitHub Copilot IDE and start **Astra Orchestrator**.
2. Give it the goal, constraints, and acceptance criteria; do not manually pre-split normal tasks.
3. Astra keeps global intent warm, classifies the task once, and selects an exact physical role+tier profile.
4. If missing repository topology could materially change the tier, Astra uses `Scout Luna` for a narrow information pass and reclassifies once. Scout is not a compulsory preflight.
5. Workers return compact evidence; Astra integrates and owns final acceptance.

## Physical agent matrix

| Profile | Fixed model | Purpose |
| --- | --- | --- |
| `Astra Orchestrator` | GPT-6 Astra | planning, architecture, integration, authority, final acceptance |
| `Scout Luna` | GPT-5.6 Luna | cold repository discovery |
| `Research Luna` | GPT-5.6 Luna | narrow current-doc/API lookup |
| `Research Terra` | GPT-5.6 Terra | multi-source/compatibility synthesis |
| `Execute Luna` | GPT-5.6 Luna | mechanical/repetitive implementation |
| `Execute Terra` | GPT-5.6 Terra | normal coupled multi-file implementation |
| `Execute Sol` | GPT-5.6 Sol | reasoning-heavy bounded implementation |
| `Debug Sol` | GPT-5.6 Sol | difficult root-cause analysis/fix |
| `Verify Luna` | GPT-5.6 Luna | deterministic validation |
| `Verify Terra` | GPT-5.6 Terra | semantic regression/contract review |
| `Verify Sol` | GPT-5.6 Sol | subtle high-risk correctness review |

There are intentionally **no generic `Executor`, `Researcher`, or `Verifier` profiles**. Model tier is encoded in the physical profile so ordinary orchestration does not depend on a runtime model override.

## Adaptive routing

Astra applies four small gates before execution:

1. **Authority** — architecture, public contracts, security/privacy authority, irreversible decisions, integration, disagreement, and final acceptance stay in Astra.
2. **Information** — use `Scout Luna` only when missing repo facts could change the tier; do not make Astra broadly cold-read merely to classify.
3. **Execution** — start directly at Luna, Terra, or Sol. Do not use Luna as a capability probe.
4. **Verification** — choose the verification tier independently from the implementation tier.

Routing principles:

- Tiny edits in already-warm parent context stay in Astra when dispatch costs more than the edit.
- Luna starts when scope is explicit, reasoning is shallow, and failure is cheaply/deterministically detectable.
- Terra starts when coupling or ambiguity makes Luna rework likely enough to erase its price advantage.
- Sol starts when silent failure is expensive: subtle invariants, concurrency, migrations, complex algorithms, difficult root cause, or weakly testable semantics.
- A Sol implementation may still use `Verify Luna` when deterministic commands are decisive; a Luna implementation may require `Verify Terra` or `Verify Sol` when semantics are hard to prove.
- Failures escalate monotonically **Luna -> Terra -> Sol -> Astra**; at most one short same-tier Luna correction is allowed for an obvious local/mechanical cause.
- Escalation carries forward useful evidence and the smallest root-cause delta instead of restarting the task.
- Parallel writers require disjoint ownership; default fan-out is at most 3.
- Workers never recursively delegate and never receive the parent transcript.

## Client compatibility

Physical profiles improve routing determinism, but client semantics still apply.

- Supported IDE custom agents can use each profile's fixed `model` field.
- Copilot CLI supports per-agent model configuration, but when the parent session uses `Auto`, custom subagents can inherit the resolved session model regardless of the profile `model` field.
- For exact calibrated tier routing in CLI, use a non-Auto parent model and/or configure the `subagents.agents` entries. `subagents.maxConcurrency` and `subagents.maxDepth` can add runtime guardrails; this repository already prevents recursion structurally.
- Auto remains useful for ordinary sessions because GitHub performs task-aware selection and paid plans receive its model-cost discount; it is a separate optimization mode from fixed-tier measurement.

See `docs/model-routing-surfaces.md`.

## Cost calculator and calibration

The calculator prices the same token shape on every model and compares **every possible starting suffix** of the configured escalation ladder. This allows a task to skip Luna and start at Terra/Sol/Astra when the lower-tier attempt is expected to cost more after failure, validation, and escalation.

```bash
python scripts/route_cost.py \
  --fresh-input 12000 \
  --output 2500 \
  --ladder luna:0.25,terra:0.92,sol:0.99,astra:1 \
  --dispatch-units 0.5 \
  --handoff-units 0.5 \
  --failure-penalty 2
```

The output lists all candidate starting tiers and a `recommended start`. Probabilities should come from broad observed task classes, not invented precision for a one-off request.

Use `/calibrate-routing` to classify runs as `right-sized`, `under-routed`, `over-routed`, `insufficient-information`, or `authority-task`, and tune start-tier priors from observed credits, cache behavior, retries, validation strength, and hidden defects. Keep Auto-selected runs separate unless the actual model is recorded.

The calculator is an engineering estimator, not billing telemetry.

## Validation

```bash
python scripts/validate_config.py
python -m unittest discover -s tests -v
```

CI validates the physical agent matrix and routing-cost model on pull requests and `main`.

## Repository map

```text
.github/agents/
  astra-orchestrator.agent.md
  scout-luna.agent.md
  research-luna.agent.md
  research-terra.agent.md
  execute-luna.agent.md
  execute-terra.agent.md
  execute-sol.agent.md
  debug-sol.agent.md
  verify-luna.agent.md
  verify-terra.agent.md
  verify-sol.agent.md
.github/instructions/agent-profiles.instructions.md
.github/skills/calibrate-routing/SKILL.md
.github/workflows/validate.yml
.github/copilot-instructions.md
AGENTS.md
docs/astra-routing.md
docs/model-routing-surfaces.md
docs/copilot-features.md
docs/observability.md
scripts/route_cost.py
scripts/validate_config.py
tests/test_route_cost.py
```
