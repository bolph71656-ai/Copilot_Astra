# Copilot Astra

Cost-aware GitHub Copilot orchestration for using Astra as the parent reasoning model and Luna as low-cost execution subagents.

## What this repository provides

- `Astra Orchestrator`: parent agent for intent, architecture, decomposition, integration, and final acceptance.
- `Luna Scout`: read-only repository discovery and evidence gathering.
- `Luna Worker`: scoped implementation and mechanical refactoring.
- `Luna Test`: repetitive validation and bounded repair loops.
- Repository-wide routing rules in `.github/copilot-instructions.md` and `AGENTS.md`.
- A quantitative routing model in `docs/astra-routing.md`.
- A dependency-free calculator in `scripts/route_cost.py` for comparing estimated Astra-direct and Luna-delegated cost.

## Use in GitHub Copilot

1. Open this repository in a Copilot-supported IDE or Copilot agent surface that supports repository custom agents.
2. Select **Astra Orchestrator** as the parent agent.
3. Give the parent your normal coding task. It keeps warm, tightly coupled reasoning in Astra and delegates cold/repetitive/high-output work to the Luna subagents.
4. Review the final Astra integration and validation summary.

The custom agent profiles use `model: Astra` and `model: Luna`. If your Copilot client exposes fully qualified model identifiers instead of these aliases, replace those values with the exact names shown by that client's model selector/autocomplete.

## Routing defaults

- Small, warm, tightly coupled edits: Astra.
- Cold repository exploration: Luna Scout.
- Mechanical implementation/refactoring or large code output: Luna Worker.
- Broad/repetitive testing: Luna Test.
- Architecture, interfaces, integration, and final acceptance: Astra.

The 6k-20k token range is intentionally treated as a gray zone: favor Luna for cold context and Astra for warm, read-dominated context. See `docs/astra-routing.md` for the cost equations and break-even assumptions.

## Cost calculator

Example:

```bash
python scripts/route_cost.py \
  --direct-input 12000 \
  --direct-output 2500 \
  --luna-input 12000 \
  --luna-output 2500 \
  --astra-handoff-units 9
```

The calculator reports the estimated direct Astra cost, expected Luna-delegated cost, and a routing recommendation. Token prices are assumptions encoded from this repository's current cost model, not a billing API.

## Files

```text
.github/
  agents/
    astra-orchestrator.agent.md
    luna-scout.agent.md
    luna-worker.agent.md
    luna-test.agent.md
  copilot-instructions.md
AGENTS.md
docs/astra-routing.md
scripts/route_cost.py
```
