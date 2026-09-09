# Copilot Astra

Cost-aware GitHub Copilot orchestration that keeps **GPT-6 Astra** as the warm long-horizon parent and dispatches exact fixed-model subagents.

```text
warm micro-edit / architecture / integration -> Astra direct
cheap discovery / routine work / deterministic checks -> Luna profiles
normal multi-file / synthesis / semantic review -> Terra profiles
deep bounded implementation / debugging / high-risk review -> Sol profiles
final authority -> Astra
```

The objective is **minimum expected AI-credit cost per validated correct task**, including handoff, retries, cache churn, verification, and defects.

## Quick start

1. Open the repository in a supported GitHub Copilot IDE and start **Astra Orchestrator**.
2. Give it the goal, constraints, and acceptance criteria; do not manually pre-split normal tasks.
3. Astra keeps global intent warm and selects an exact physical role+tier profile.
4. Workers return compact evidence; Astra integrates and owns final acceptance.

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

## Routing principles

- Tiny edits in already-warm parent context stay in Astra when handoff costs more than the edit.
- Luna is used when scope is clear and failure is cheaply detectable.
- Terra starts when coupling/ambiguity makes a Luna miss likely enough to erase savings.
- Sol starts when silent failure is expensive: subtle invariants, concurrency, migrations, complex algorithms, difficult debugging, or deep review.
- Failures escalate monotonically **Luna -> Terra -> Sol -> Astra**; cheap retries are bounded.
- Parallel writers require disjoint ownership; default fan-out is at most 3.
- Workers never recursively delegate and never receive the parent transcript.
- Verification starts with deterministic commands before paying for semantic review.

## Client compatibility

Physical profiles improve routing determinism, but client semantics still apply.

- Supported IDE custom agents can use each profile's fixed `model` field.
- Copilot CLI supports per-agent model configuration, but when the parent session uses `Auto`, custom subagents can inherit the resolved session model regardless of the profile `model` field.
- For exact calibrated tier routing in CLI, use a non-Auto parent model and/or configure the `subagents.agents` entries. `subagents.maxConcurrency` and `subagents.maxDepth` can add runtime guardrails; this repository already prevents recursion structurally.
- Auto remains useful for ordinary sessions because GitHub performs task-aware selection and paid plans receive its model-cost discount; it is not the mode to use when exact physical-tier enforcement is the experiment being measured.

See `docs/model-routing-surfaces.md`.

## Cost calculator and calibration

```bash
python scripts/route_cost.py \
  --fresh-input 10000 \
  --cached-input 50000 \
  --output 3000 \
  --ladder luna:0.80,terra:0.95,sol:0.99,astra:1 \
  --handoff-units 0.5 \
  --failure-penalty 1
```

Use `/calibrate-routing` with observed credits, cache behavior, retries, validation strength, and defects. The calculator is an engineering estimator, not billing telemetry.

## Validation

```bash
python scripts/validate_config.py
python -m unittest discover -s tests -v
```

CI validates the physical agent matrix and cost model on pull requests and `main`.

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
