# Routing review — 2026-09-10

This review follows the human/device-validation work and records the remaining material weaknesses found in the routing architecture.

## Official platform checks

Checked against current official documentation on 2026-09-10:

- GitHub custom agents support `target: vscode` and `target: github-copilot`.
- VS Code custom agents support explicit `agents` allowlists and fixed model selection for subagents.
- Explicitly listing an agent in a coordinator allowlist can make a protected subagent available to that coordinator.
- GitHub's pricing table lists GPT-5.6 Luna long-context threshold at 200K input tokens and Terra/Sol/Astra thresholds at 272K.
- Pricing/model availability can change, so the repository keeps a dated source URL rather than treating rates as immutable constants.

Primary sources:
- https://docs.github.com/en/copilot/reference/custom-agents-configuration
- https://code.visualstudio.com/docs/agent-customization/custom-agents
- https://code.visualstudio.com/docs/agents/run/subagents
- https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing

## Findings corrected

### 1. Astra was implicitly perfect

Static fixtures and default examples ended in Astra with `p_correct=1`. This guaranteed eventual recovery and understated the cost/risk of cheap-first routes.

Correction: Astra is now below 1.0 in seed priors and is empirically calibrated.

### 2. Calibration and routing were disconnected

Calibration grouped by `reached_after`, but route evaluation used one success probability per model.

Correction: route evaluation now resolves priors using exact path context (`direct`, `luna`, `luna>terra`, etc.) with `after:any` fallback.

### 3. Calibration output required manual transcription

Correction: `calibrate_routing.py --routing-priors-out ...` writes the same schema consumed by `route_cost.py`.

### 4. Terminal failure was not a first-class constraint

Correction: risk policy separately constrains hidden accepted defects, detected terminal failure, and minimum validated-correct probability.

### 5. Observation contradictions could contaminate priors

Correction: invalid human-validation state combinations now raise instead of being silently repaired. Missing attribution defaults to `unknown`, not `implementation`.

### 6. Multi-stage human event metrics were mislabeled

Correction: repeatable events are named expected counts. Only mutually exclusive route exit measures retain probability terminology.

### 7. Context fallback omitted cache-write tokens

Correction: exact provider `context_tokens` are preferred; otherwise input context is conservatively approximated as fresh + cached + cache-write tokens.

### 8. Surface intent was implicit

Correction: all physical profiles now set `target: vscode`.

## Remaining uncertainty

The system is still a decision model, not ground truth. Seed probabilities and risk budgets are policy assumptions. The architecture should become more empirical as representative observations accumulate.

A future improvement may use hierarchical priors so sparse exact paths shrink toward `after:any` and model/task-class parents more formally. The current layered fallback is intentionally simpler and auditable.
