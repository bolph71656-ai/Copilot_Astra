# ADR-0001: Risk-aware economic routing with physical model profiles

- **Status:** Accepted
- **Date:** 2026-09-09

## Context

Copilot Astra must minimize AI-credit usage without converting cheap model attempts into rework loops or hidden correctness risk. Copilot behavior/pricing also varies by surface.

## Decision

Use a warm GPT-6 Astra parent for long-horizon intent/authority and a physical role+tier matrix for isolated subagents.

Routing uses authority, context warmth, task-class priors, probability of correct completion, probability an incorrect result is detected, hidden-defect cost/risk, dispatch/handoff/rework cost, and optional latency sensitivity.

Choose the lowest **risk-feasible economically efficient route**, not simply the cheapest first call. Intermediate tiers may be skipped while escalation remains capability-monotone.

## Consequences

Positive:
- reproducible fixed-tier experiments,
- cache-friendly parent behavior,
- cheap workers remain useful with strong oracles,
- hidden-failure risk is explicit,
- Terra is not paid merely because it sits between Luna and Sol,
- offline fixtures make routing drift testable.

Negative:
- more agent files,
- priors require calibration,
- estimator remains an approximation,
- exact model behavior stays client/surface dependent.

## Operational defaults

- Writer fan-out 1; conditional 2; exceptional max 3.
- No recursive delegation.
- Worker self-validation first.
- Separate Verify Luna only when independent/bulky deterministic execution adds value.
- Terra/Sol semantic verification only when deterministic evidence is insufficient for risk class.
- Scout only when value of information is positive.
- Auto runs are analyzed separately from fixed-tier runs.

## Superseded assumptions

This supersedes universal Luna-first routing, mandatory adjacent cascade, cost-per-apparent-success as sole objective, and interpreting fan-out <=3 as a target.
