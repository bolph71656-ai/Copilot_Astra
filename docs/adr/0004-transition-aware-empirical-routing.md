# ADR 0004: Transition-aware empirical routing

- Status: Accepted
- Date: 2026-09-10

## Context

Earlier routing treated each model as if it had one task-independent success probability and treated Astra as a perfect terminal fallback. That is too optimistic.

After Luna/Terra fail, the remaining task population is selected toward harder cases. Therefore `P(model succeeds | direct)` is generally not interchangeable with `P(model succeeds | lower-tier failure evidence)`. The previous calibration code already recorded `reached_after`, but the route evaluator did not consume it.

## Decision

Routing priors are now path-conditioned by task class, oracle strength, model, and `reached_after`. Astra is calibrated like every other model and is not assigned `p_correct=1`.

A route is rejected if any configured risk constraint is violated: hidden accepted failure probability, detected terminal failure probability, or minimum validated-correct probability.

Calibration emits a machine-readable prior overlay consumed directly by the route estimator. Generic seed priors remain only as cold-start fallbacks.

## Consequences

Positive:
- escalation economics account for selection bias after prior failures,
- no artificial guarantee that Astra always recovers the task,
- observed calibration can change routing without manually transcribing probabilities,
- partial calibrated fields can safely overlay generic seed fields,
- provenance of assumptions is visible per stage.

Costs:
- more metadata must be recorded consistently,
- path-specific groups can be sparse,
- low-sample posteriors require shrinkage and generic fallbacks,
- route results are only as trustworthy as attribution and observation quality.

## Additional safeguards

- contradictory validation observations are rejected,
- unattributed failures do not default to implementation failure,
- exact `context_tokens` are preferred; fallback context inference is conservative,
- event counts in multi-stage human validation are not mislabeled as probabilities,
- all custom agents explicitly target VS Code,
- subagents are protected from general model invocation and explicitly allowlisted by Astra.

## Revalidation

Revisit when GitHub changes custom-agent/subagent semantics, model pricing/thresholds change, enough observations justify richer hierarchical/Bayesian modeling, path sparsity makes exact route conditioning unstable, or empirical data shows a simpler policy performs equivalently.
