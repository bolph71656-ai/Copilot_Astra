# ADR 0003: Treat human and real-device validation as a first-class routing oracle

- Status: Accepted
- Date: 2026-09-09

## Context

Some implementation tasks cannot be fully validated in the agent environment. Examples include mobile permission flows, hardware/peripheral behavior, visual/interaction quality, device-specific networking, camera/microphone behavior, and other real-environment effects.

Two naive policies are both wrong:

1. treat "needs human validation" as worker failure and escalate immediately;
2. assume that because a human will test later, the cheapest worker is always acceptable.

The first corrupts model-success calibration. The second ignores manual retest cost and the possibility that the human procedure itself has weak defect-detection power.

## Decision

Human/device validation is modeled as a second, explicit oracle after automatic validation.

Routing uses:
- worker correctness probability `p`,
- automatic detection rate `d_auto`,
- conditional human/device detection rate `d_human`,
- human validation cost and latency,
- hidden-defect consequence/risk budget.

A required but unperformed human/device check produces `NEEDS_HUMAN_VALIDATION`, not success or failure.

If the human procedure detects a defect, the parent first classifies failure attribution. Only confirmed implementation-attributed failures update model correctness priors or justify capability escalation. Device/environment/infrastructure/procedure/operator failures remain separate.

The route estimator includes expected repeated human-validation cycles after escalations. This allows a high manual retest burden to justify starting at Terra/Sol even when Luna is cheap.

## Consequences

Positive:
- no false failure signal from merely pending human checks;
- lower tiers remain available when a strong, cheap human oracle makes them safe;
- expensive manual loops are visible in economics;
- weak human checks cannot hide high-consequence risk;
- calibration can learn human oracle quality separately from model quality.

Costs:
- observations need explicit validation state and attribution;
- `d_human` is initially uncertain and must be calibrated conservatively;
- human time must be represented in routing units or latency value.

## Rejected alternatives

### Always treat human validation as decisive
Rejected because manual checks can be subjective, incomplete, or narrow relative to the defect state space.

### Always route human-required work to Sol/Astra
Rejected because many visual/device acceptance tasks are cheap, reversible, and strongly observable by a narrow manual procedure.

### Count pending human validation as failure
Rejected because no evidence has disproved the implementation; this would systematically understate lower-tier correctness.

## Revalidation triggers

Revisit this decision if:
- Copilot gains reliable direct access to the relevant real-device environment,
- calibration shows manual validation cost is negligible across task classes,
- human oracle detection cannot be estimated reliably,
- the project adopts a different acceptance-state or quality-risk model.

See `docs/human-device-validation.md`.
