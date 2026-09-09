# Deep research record: cost-efficient Copilot subagent orchestration

**Research date:** 2026-09-09  
**Scope:** GitHub Copilot custom agents, subagents, Auto model selection, cache/context economics, CLI controls, validation economics, and multi-model routing.

This document preserves the evidence and reasoning behind Copilot Astra. It intentionally separates **documented platform behavior** from **project inference/engineering policy**. Revalidate platform facts when GitHub changes Copilot behavior or pricing.

## Executive conclusion

The best architecture for this project is **not** Astra-only, Luna-first for every task, a fixed adjacent `Luna -> Terra -> Sol -> Astra` cascade, or a pure difficulty classifier.

Recommended architecture:

1. keep one high-capability parent for long-horizon intent/authority when warm context has continuing value,
2. delegate focused isolated work to the cheapest physical profile with adequate correct-completion probability,
3. make verification strength and failure-detection probability first-class routing inputs,
4. skip intermediate tiers when their expected value is negative,
5. preserve evidence when escalating,
6. treat Scout/research/verification as optional information actions whose value must exceed cost,
7. calibrate priors from observed runs rather than a target Luna percentage,
8. compare this fixed-tier policy against GitHub Auto as a separate baseline.

## Official platform findings

### Cheaper models for subagents

GitHub's AI-usage optimization guidance says subagents execute in their own session and do not inherit the main agent conversation history. Focused subagent context often permits a lighter model without disturbing the main agent cache like a mid-session model switch.

**Design consequence:** focused search, routine implementation, and bounded validation are strong delegation candidates.

Source: https://docs.github.com/en/copilot/tutorials/optimize-ai-usage

### Cache preservation

GitHub documents that changing model, reasoning effort, context size, or active tools/MCP during a session can invalidate cache and recommends keeping these stable.

**Design consequence:** do not repeatedly reconfigure Astra mid-task merely to save credits.

Source: https://docs.github.com/en/copilot/tutorials/optimize-ai-usage

### Auto is a legitimate competing router

GitHub Auto uses a small router based on task intent, routes at natural cache boundaries, considers reliability/availability, and currently offers a model-cost discount on paid plans.

**Design consequence:** fixed physical routing is valuable for policy control, model attribution, and reproducible experiments, but is not claimed universally superior to Auto.

Sources:
- https://docs.github.com/en/copilot/concepts/models/auto-model-selection
- https://docs.github.com/en/copilot/tutorials/optimize-ai-usage

### Custom-agent model and invocation controls

Custom-agent configuration supports `model`, `tools`, `user-invocable`, and `disable-model-invocation`; some properties are surface-specific.

Source: https://docs.github.com/en/copilot/reference/custom-agents-configuration

### CLI per-subagent controls

Copilot CLI supports per-agent `model`, `effortLevel`, and `contextTier`, plus `subagents.maxConcurrency` and `subagents.maxDepth`. Concurrency overrides are billing/plan dependent.

Sources:
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference

### Agentic work is multi-call

GitHub billing guidance notes agentic features can involve multiple model calls and model choice materially changes usage.

**Design consequence:** model long-context pricing at the **call level**, not from aggregate task tokens.

Source: https://docs.github.com/en/copilot/concepts/billing/usage-based-billing-for-individuals

### Context should follow task boundaries

GitHub recommends retaining a conversation while context remains relevant and starting fresh when switching problems; longer threads process more context.

Source: https://docs.github.com/en/copilot/tutorials/optimize-chat-usage

## Engineering findings

These are project inferences, not product guarantees.

### Difficulty alone is insufficient

A large mechanical edit with strong tests can be economical on Luna. A ten-line security-sensitive change with weak observability may need Sol/Astra.

Use: `task class + authority + ambiguity/coupling + oracle strength + hidden-failure cost + context warmth + expected output + latency sensitivity`.

### Verification is an economic oracle

Let `p` be probability a worker result is correct and `d` be probability an incorrect result is detected before acceptance. Cheap execution is attractive when `d` is high. Weak detection can make a route look inexpensive while accumulating hidden-defect risk.

### Risk-constrained objective

Use:

`min risk_adjusted_expected_units / P(validated correct completion)`

subject to:

`P(hidden failure) <= risk budget`

Optional latency and hidden-defect penalties can be included in risk-adjusted units.

### Intermediate tiers are optional

Monotone capability means never decrease required capability after substantive failure; it does not mean visiting every tier. `Luna -> Sol -> Astra` may dominate `Luna -> Terra -> Sol -> Astra`.

### Scout is a value-of-information action

Use Scout when expected avoided misroute/rework exceeds Scout + parent-ingestion cost. It is not compulsory preflight.

### Avoid duplicate verification

Execute profiles already run targeted deterministic checks. Separate `Verify Luna` should normally isolate bulky deterministic output, run a distinct acceptance command, or add independent execution evidence.

### Conservative parallelism

Default writer fan-out is 1; use 2 for clearly disjoint modules when latency value justifies it; 3 is exceptional cap.

## Alternatives considered

### Astra-only

Strong context continuity, but expensive for mechanical/output-heavy work. Retained for tiny warm edits, authority, integration, final acceptance.

### Always Luna-first

Low first-call cost, but retry/rework and weak-oracle hidden failures can dominate. Rejected globally.

### Fixed adjacent cascade

Simple, but may pay for an intermediate tier with little value. Retain monotone capability while allowing skips.

### Pure Auto

Strong platform router with availability/cache advantages, but less deterministic model attribution/control. Keep as benchmark and ordinary-session alternative.

### Generic workers with runtime overrides

Fewer files, but weaker auditability and more surface/runtime ambiguity. Retain physical role+tier profiles.

## What is intentionally not claimed

- Pricing snapshot is not authoritative billing.
- One-off tasks are not assigned invented precise probabilities.
- Eleven profiles are not intrinsically optimal; they are retained because role+authority boundaries are distinct and experiments become reproducible.
- Cross-model verification is not automatically independent.
- More parallel agents do not imply lower cost.

## Revalidation checklist

Repeat research when supported models, pricing, long-context thresholds, Auto behavior/discounts, custom-agent semantics, subagent inheritance, CLI controls, cache behavior, billing, or local calibration evidence changes materially.
