# Copilot feature decisions

The system deliberately uses Copilot customization features that improve expected cost or correctness without permanently inflating context.

## Used

### Physical fixed-model custom agents

Use one profile per role + model tier instead of a generic worker plus runtime model override. The active matrix is:

- `Astra Orchestrator`
- `Scout Luna`
- `Research Luna` / `Research Terra`
- `Execute Luna` / `Execute Terra` / `Execute Sol`
- `Debug Sol`
- `Verify Luna` / `Verify Terra` / `Verify Sol`

This makes normal routing explicit and inspectable: the parent selects a profile whose model is pinned in frontmatter.

### Isolated subagents

Subagents receive focused context rather than the parent transcript. The Astra parent keeps global intent warm while workers consume only the context needed for one bounded task.

### Exact allowlist and structural no-nesting

The coordinator lists exactly which physical specialists it may invoke. Every specialist sets `agents: []` and lacks the `agent` tool, preventing recursive cost explosions even before client runtime limits are considered.

### Path-specific instructions

`.github/instructions/agent-profiles.instructions.md` is loaded only when editing agent profiles, avoiding an always-on instruction tax.

### Agent Skill

`/calibrate-routing` loads on demand. Skills are preferred for occasional calibration because they progressively load context instead of enlarging every request.

### Deterministic CI guardrails

This repository validates the physical matrix, model pinning, tool authority, no-legacy-profile rule, instruction-size budget, calculator, and tests in CI. Consuming repositories should add their real lint/test/schema/security commands where deterministic validation is cheap and stable.

## Client-specific model controls

### Supported IDE custom agents

Where the client honors custom-agent `model`, use the fixed profile directly. Avoid changing Astra parent model/reasoning/context/tools mid-task merely to save credits because that defeats the warm-parent strategy.

### Copilot CLI

CLI supports per-agent subagent configuration. Useful optional controls include:

- `subagents.agents.<name>.model`
- `subagents.agents.<name>.effortLevel`
- `subagents.agents.<name>.contextTier`
- `subagents.maxConcurrency`
- `subagents.maxDepth`

For exact calibrated routing, avoid an outer session using server-selected `Auto`, because CLI subagents can inherit the resolved session model instead of the profile model. Use a non-Auto parent and/or per-agent configuration when exact model attribution matters.

Keep `contextTier` at the normal/default tier unless the subtask genuinely needs a long context. Do not increase `effortLevel` by default: first increase capability only when task ambiguity/risk justifies it. A practical runtime guardrail is concurrency near the repository fan-out policy (3) and depth 1; structural no-recursion remains the primary defense.

### Auto model selection

Auto is useful for ordinary sessions when exact physical-tier attribution is not required. GitHub performs platform-managed task/reliability-aware selection, and paid plans currently receive a model-cost discount for Auto. Treat that as an alternative optimization strategy, not something to mix into experiments that measure Luna/Terra/Sol escalation economics.

## Deliberately not enabled globally

### Handoffs

Handoffs change the active agent/model. The core topology keeps Astra warm and has subagents return compact results. Handoffs can help user-guided workflows but are not the default cost path.

### Broad MCP

Every enabled tool/MCP schema adds context and changing the set can disturb cache behavior. Add a server only to the specialist that needs it, and keep that set stable for the task.

### Generic agent hooks

Hooks are useful for deterministic lifecycle actions, but commands are repository-specific. Add known-safe, fast hooks in consuming repositories; do not run an unknown full suite after every edit.

### Prompt files

Prompt files can be useful locally but are not equally portable across Agent Host surfaces. Recurring portable workflows belong in Agent Skills instead.

### Nested subagents

Disabled. Nested fan-out makes ownership, context, and expected cost harder to bound. Astra owns orchestration.

### Generic multi-model workers

Disabled. There is intentionally no generic `Executor`, `Researcher`, or `Verifier` whose model must be overridden at runtime. Physical role+tier profiles make routing intent explicit and easier to validate.

## Optional high-value features

### Extended context / higher reasoning

Use only when the task genuinely needs them. Natural sharding is preferred when coupling allows. Long context and deeper reasoning should solve a demonstrated limitation, not be pre-enabled insurance.

### Independent cross-model/provider verification

For exceptional high-risk semantic/security changes, an additional read-only review by a materially different model/provider can reduce correlated blind spots. For routine work, deterministic checks are cheaper and more reproducible.

### MCP

Add task-specific MCP tools such as databases, observability, or issue trackers to a narrowly scoped specialist, not every agent.

### Hooks

In a consuming repository with stable commands, hooks can enforce formatting/tests/security checks deterministically and reduce expensive model retry loops.

### High parallelism

Use more than the default fan-out only for genuinely independent shards with disjoint ownership and low result-ingestion cost. More parallel calls are not automatically cheaper or faster once parent integration overhead is included.
