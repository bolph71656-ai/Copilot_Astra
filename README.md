# Copilot Astra

A cost-aware GitHub Copilot orchestration system that keeps **GPT-6 Astra** as the long-horizon parent and routes isolated work through a difficulty ladder:

```text
warm micro-edit -> Astra direct
routine/mechanical -> Luna
general multi-file -> Terra
hard debugging/reasoning -> Sol
architecture/integration/final acceptance -> Astra
```

The objective is not "use Luna as much as possible." It is **minimum expected AI-credit cost per validated correct task**, including handoff, retries, cache churn, and defects.

## Quick start

1. Open the repository in a recent VS Code with GitHub Copilot.
2. Start a new agent session with **Astra Orchestrator**.
3. Give it the goal, constraints, and acceptance criteria. Do not manually pre-split ordinary tasks.
4. The parent keeps architecture/global intent warm in Astra and uses focused subagents with explicit model tiers when isolation is economical.
5. Review the final Astra acceptance summary.

Example request:

```text
Implement issue X. Preserve the public API. Acceptance: unit tests pass and the old compatibility case still works.
```

## Routing

| Work | Default |
| --- | --- |
| Tiny edit in already-warm files | Astra direct |
| Search, classification, boilerplate, simple refactor, tests | Luna |
| Clear but non-trivial multi-file implementation | Terra |
| Hard debugging, concurrency/performance, migrations, cross-module root cause | Sol |
| Architecture, security/privacy, contracts, integration, final approval | Astra |

Failures escalate monotonically **Luna -> Terra -> Sol -> Astra**. Cheap retries are bounded; plausible-but-unverified output escalates sooner.

## Specialists

- `Scout` — low-cost read-only repository discovery.
- `Researcher` — current external docs/APIs and source evidence.
- `Executor` — scoped implementation; Astra may invoke it with Luna, Terra, or Sol.
- `Debugger` — Sol-first hypothesis-driven root cause analysis.
- `Verifier` — read-only independent acceptance/regression review.
- `Astra Orchestrator` — the only coordinator; owns architecture, model selection, merge/integration, and final acceptance.

Subagents are non-recursive and receive compact packets rather than the parent transcript.

## Why this shape is efficient

Copilot subagents run in isolated sessions, so using a cheaper model for focused work does not require switching the parent model mid-session. The parent stays warm on Astra while workers pay only for scoped context. Always-on instructions are intentionally short; detailed economics are docs/skills loaded only when needed.

The system also avoids broad MCP/tool sets, overlapping writer agents, unbounded retry loops, and unnecessary extended context/reasoning.

## Client compatibility

Precise subagent model routing is strongest in VS Code, where the coordinator can request a model for a subagent and custom agents can define their own model/tools. Model availability depends on Copilot plan/policy and changes over time.

GitHub.com/cloud-agent custom-agent properties are not identical to VS Code. If a client does not honor the qualified `Model Name (copilot)` profile or explicit subagent model request, select Astra/Auto at the parent surface and use the role/risk rules as guidance rather than assuming exact tier enforcement.

## Cost calculator

Compare the same token shape across the working model prices and estimate a failure/escalation ladder:

```bash
python scripts/route_cost.py \
  --fresh-input 10000 \
  --cached-input 50000 \
  --output 3000 \
  --ladder luna:0.80,terra:0.95,sol:0.99,astra:1 \
  --handoff-units 0.5 \
  --failure-penalty 1
```

Machine-readable output:

```bash
python scripts/route_cost.py --fresh-input 10000 --output 2000 --json
```

The calculator is a routing estimator, not GitHub billing telemetry. Recheck promotional/plan-specific prices before financial reporting.

## Validation

```bash
python scripts/validate_config.py
python -m unittest discover -s tests -v
```

CI runs both on pull requests and `main`.

## Repository map

```text
.github/
  agents/
    astra-orchestrator.agent.md
    scout.agent.md
    researcher.agent.md
    executor.agent.md
    debugger.agent.md
    verifier.agent.md
  instructions/
    agent-profiles.instructions.md
  skills/
    calibrate-routing/SKILL.md
  workflows/
    validate.yml
  copilot-instructions.md
AGENTS.md
docs/
  astra-routing.md
  copilot-features.md
  observability.md
scripts/
  route_cost.py
  validate_config.py
tests/
  test_route_cost.py
```

See `docs/astra-routing.md` for the quantitative model, `docs/copilot-features.md` for feature tradeoffs, and `docs/observability.md` for measurement/calibration.
