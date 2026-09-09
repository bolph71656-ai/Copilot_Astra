# Copilot feature decisions

The system deliberately uses Copilot customization features that improve expected cost or correctness without permanently inflating context. The repository is optimized for VS Code Copilot subagent orchestration and local validation.

## Used

### Physical fixed-model custom agents

Use one profile per role + model tier instead of a generic worker plus runtime model override. The active matrix is:

- `Astra Orchestrator`
- `Scout Luna`
- `Research Luna` / `Research Terra`
- `Execute Luna` / `Execute Terra` / `Execute Sol`
- `Debug Sol`
- `Verify Luna` / `Verify Terra` / `Verify Sol`

Every profile explicitly targets `vscode`. The parent pins GPT-6 Astra; every specialist pins its intended Luna/Terra/Sol model.

### Isolated and protected subagents

Subagents receive focused context rather than the parent transcript. The Astra parent keeps global intent warm while workers consume only the context needed for one bounded task.

The coordinator explicitly allowlists the physical specialists. Every specialist sets `agents: []`, lacks the `agent` tool, sets `user-invocable: false`, and sets `disable-model-invocation: true`. This prevents recursive delegation and reduces unintended invocation outside the router.

### Transition-aware empirical routing

Model quality is conditioned on how the model was reached. The router does not assume `P(Sol correct | direct) = P(Sol correct | Luna already failed)`.

Seed priors live in `config/routing-priors.json`. Metadata-only observations can generate the local, uncommitted overlay `config/routing-priors.local.json`, which `route_cost.py` consumes automatically.

Astra is final authority but is not modeled as infallible. Risk policy independently constrains hidden accepted failure, detected unresolved terminal failure, and minimum validated-correct probability.

### Human/device validation as a second oracle

Required human or real-device validation is not automatically success, failure, or permission to choose a cheaper worker. The router models automatic detection, conditional human detection, manual setup/retest cost, and validation latency.

`NEEDS_HUMAN_VALIDATION` and environment/device `BLOCKED` states stay outside model correctness posteriors until the outcome and attribution are resolved.

### Path-specific instructions

`.github/instructions/agent-profiles.instructions.md` is loaded only when editing agent profiles, avoiding an always-on instruction tax.

### Agent Skill

`/calibrate-routing` loads on demand. Skills are preferred for occasional calibration because they progressively load context instead of enlarging every request.

### Local deterministic guardrails

This repository intentionally does **not** use GitHub Actions. `python scripts/validate_all.py` is the canonical local acceptance command. It rejects GitHub Actions workflow files, validates the physical matrix and VS Code target, validates pricing provenance/seed priors/risk policy/fixtures/design records, runs all unit tests, and runs offline routing-policy regression.

Consuming repositories should add their real lint/test/schema/security commands where deterministic validation is cheap and stable.

## Client-specific model controls

### VS Code custom agents

The repository agent profiles explicitly set `target: vscode`. Use `Astra Orchestrator`; it dispatches exact profiles such as `Execute Luna`, `Execute Terra`, and `Execute Sol`.

Keep the parent model/configuration stable during a task when warm context remains useful. Avoid changing Astra model, reasoning, context tier, or tool set merely to save credits because those changes can defeat the warm-parent/cache strategy.

### Copilot CLI

CLI supports its own per-agent subagent configuration. Useful optional controls include `subagents.agents.<name>.model`, `effortLevel`, `contextTier`, `subagents.maxConcurrency`, and `subagents.maxDepth`.

For exact calibrated routing, record requested and resolved models and avoid assuming VS Code profile semantics transfer unchanged to CLI. Use a non-Auto parent and/or per-agent CLI configuration when exact tier attribution matters.

Keep `contextTier` normal/default unless a subtask genuinely needs long context. Do not raise reasoning effort by default. Repository structural no-recursion is the primary defense; CLI depth/concurrency settings are defense-in-depth.

### Auto model selection

Auto is useful for ordinary sessions when exact physical-tier attribution is not required. Treat Auto as a separate optimization baseline and keep its observations separate from fixed-tier priors unless the actual resolved model is recorded.

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

Writer fan-out defaults to 1, is conditionally 2 for disjoint stable ownership, and has an exceptional cap of 3. More parallel calls are not automatically cheaper or faster once duplicate reads and parent integration cost are included.
