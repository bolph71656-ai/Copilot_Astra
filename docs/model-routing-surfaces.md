# Physical model routing across Copilot surfaces

The repository uses separate physical agent profiles because exact role+tier files are more auditable than a generic worker plus runtime model override. Exact runtime behavior remains client-specific.

## Repository source of truth: VS Code

Every `.github/agents/*.agent.md` profile explicitly sets `target: vscode`.

This repository therefore targets VS Code Copilot subagent orchestration as its calibrated source-of-truth surface. In that surface the design relies on fixed `model`, explicit `agents` allowlist on Astra, `disable-model-invocation: true` on protected specialists, restricted tool sets, and `agents: []` with no `agent` tool on specialists.

Leaving `target` implicit would suggest portability that the complete orchestration contract does not guarantee.

## VS Code custom agents

Select `Astra Orchestrator`; it dispatches exact profiles such as `Execute Luna`, `Execute Terra`, and `Execute Sol`.

Keep the Astra parent model/configuration stable during a task while warm context remains useful. Do not switch the parent model/reasoning/context/tools merely to save credits if doing so destroys useful cache/context continuity.

## Protected subagents

Specialists are hidden from direct user invocation and protected from general model invocation. Astra explicitly names the specialists it may invoke. This makes the physical routing matrix inspectable and limits accidental bypass of the router.

## Copilot CLI

CLI custom agents and subagents have their own runtime controls. Do not assume this repository's VS Code `target` files enforce identical exact-tier behavior in CLI.

For calibrated CLI experiments: record requested and resolved model, keep Auto runs separate, configure per-agent model/effort/context controls explicitly where supported, use `/subagents` or equivalent inspection controls when appropriate, use depth/concurrency limits only as defense-in-depth, and compare validated economics rather than nominal model labels.

A practical concurrency ceiling should remain consistent with repository policy: writer fan-out 1 by default, 2 conditionally, exceptional maximum 3.

## Auto model selection

Auto is useful for normal Copilot sessions when platform-managed task/reliability-aware selection is preferred over exact model attribution. It is a different optimization strategy from this repository's fixed-profile empirical routing.

Do not mix Auto runs into Luna/Terra/Sol priors unless the actual resolved model is known.

## GitHub.com / cloud agent

Custom-agent properties are not identical across surfaces. The repository does not claim that the full VS Code coordinator/subagent contract is portable to GitHub.com cloud agents. If a consuming workflow targets that surface, revalidate frontmatter semantics and tool/model behavior rather than treating these files as enforcement.

## Model availability and pricing

Model names, availability, long-context thresholds, and prices can change with plan, policy, region, preview/GA status, and client version.

`config/pricing.json` stores a dated official-source URL and check date. Revalidate it before financial reporting or after model/pricing changes.

## Revalidation triggers

Recheck this document when GitHub/VS Code changes `target`, `agents`, fixed `model`, `disable-model-invocation`, subagent inheritance, CLI model resolution, Auto behavior, or model availability/pricing.
