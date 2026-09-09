# Physical model routing across Copilot surfaces

The repository uses separate physical agent profiles because exact role+tier files are more robust than a generic worker plus runtime model override. Client behavior can still change the effective model.

## Supported IDE custom agents

GitHub documents the `model` property for custom agents in supported IDEs such as VS Code, JetBrains IDEs, Eclipse, and Xcode. In these environments, select `Astra Orchestrator`; it dispatches exact profiles such as `Execute Luna`, `Execute Terra`, and `Execute Sol`.

Keep the parent model/configuration stable during a task to preserve context/cache economics.

## Copilot CLI

CLI custom agents support a `model` field. Important exception: when the outer session uses server-selected `Auto`, subagents inherit the resolved session model regardless of the profile model. Therefore:

- use a non-Auto parent when measuring exact Luna/Terra/Sol routing;
- or configure per-agent settings under `subagents.agents` using the exact physical agent names;
- use `/subagents` to inspect/configure subagent settings interactively when appropriate;
- set `subagents.maxConcurrency` near the repository fan-out policy (3) when the plan honors it;
- `subagents.maxDepth` can be set to 1 as defense-in-depth, although repository subagents already lack the `agent` tool and set `agents: []`.

Do not add a repository-wide CLI config blindly: model availability, policies, effort levels, and context tiers are account/client specific.

## Auto model selection

Auto is useful for normal Copilot sessions: GitHub performs task-aware/reliability-aware model selection, and paid plans currently receive a model-cost discount for Auto. That is a different optimization strategy from this repository's calibrated fixed-tier experiment.

Use Auto when you value platform-managed selection more than exact model attribution. Use the Astra physical-profile workflow when you need deterministic role/tier intent, stable parent context, and measurable escalation economics.

## Cloud agent / GitHub.com

Agent-profile properties are not identical across every surface. Treat the fixed model names as routing intent unless the active client explicitly honors them. Role boundaries, tool restrictions, compact handoffs, non-recursion, and monotonic escalation still improve efficiency even when exact model pinning is unavailable.

## Model availability

Model names and availability can change with plan, policy, region, preview/GA status, and client version. If a qualified `Model Name (copilot)` value is rejected, replace it with the exact model identifier exposed by that client's selector/autocomplete and update `scripts/validate_config.py` consistently.
