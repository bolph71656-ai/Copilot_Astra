# Copilot feature decisions

The system deliberately uses Copilot customization features that improve cost or correctness without permanently inflating context.

## Used

### Custom agents
Role-specific tools and defaults: Astra coordinator, Scout, Researcher, Executor, Debugger, Verifier.

### Isolated subagents
Subagents receive focused context rather than the parent transcript. The Astra parent explicitly chooses task/model tier where the client supports subagent model selection.

### Agent allowlist and no nesting
The coordinator lists exactly which specialists it may invoke. Specialists use `agents: []`, preventing recursive cost explosions.

### Path-specific instructions
`.github/instructions/agent-profiles.instructions.md` is loaded only when editing agent profiles, avoiding an always-on instruction tax.

### Agent skill
`/calibrate-routing` loads on demand. Skills are preferred for occasional workflows because they progressively load context.

### Deterministic CI guardrails
This repository validates its calculator/tests/configuration in CI. Deterministic checks should also be added in consuming repositories for their actual lint/test/security commands.

## Deliberately not enabled globally

### Handoffs
Handoffs change the active agent/model. The core topology instead keeps Astra warm and uses subagents that return results. Handoffs can be useful for user-guided workflows but are not the cost-optimal default here.

### Broad MCP
Every enabled tool/MCP schema adds context and can invalidate cache when changed. Add a server only to the specialist that needs it, and keep that set stable for the session.

### Generic agent hooks
Hooks are valuable for deterministic lifecycle actions, but commands are repository-specific and agent-scoped hooks remain client/setting dependent. In consuming repos, add hooks only for known-safe, fast checks; do not run an unknown full test suite after every edit.

### Prompt files
Prompt files are useful locally but are not used by every Agent Host surface. Recurring portable workflows belong in Agent Skills instead.

### Nested subagents
Disabled. Nested fan-out makes cost and ownership harder to bound. The Astra parent owns orchestration.

## Optional high-value features

### Auto model selection
Use Auto for ordinary sessions when manual Astra orchestration is unnecessary. Paid plans can receive a model-cost discount, and Auto changes models at cache-safe boundaries.

### Extended context / higher reasoning
Use only when the task genuinely needs them. Larger context and deeper reasoning increase credit use; natural sharding is preferred when coupling allows.

### Independent cross-model verification
For risky semantic/security changes, run Verifier on another available provider/model. For routine work, deterministic checks are preferred.

### MCP
Add task-specific MCP tools (databases, observability, issue trackers) to a narrowly scoped specialist, not to every agent.

### Hooks
In a consuming repository with stable commands, hooks can enforce formatting/tests/security checks deterministically and reduce expensive model retry loops.
