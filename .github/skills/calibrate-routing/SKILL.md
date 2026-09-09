---
name: calibrate-routing
description: Calibrate Astra/Luna/Terra/Sol start-tier routing from observed GitHub Copilot AI-credit usage, token/cache data, retries, escalations, validation failures, misroutes, and task outcomes. Use when tuning whether tasks should start at Luna, Terra, Sol, or Astra.
argument-hint: "[usage observations, debug log summary, or task sample]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Tune **start-tier selection**, not a target Luna percentage. The objective is minimum validated successful-task cost with acceptable defect risk.

## Collect

For each representative task record:
- task class and risk level,
- starting profile/model,
- whether `Scout Luna` was used and whether it changed the selected tier,
- cold vs warm parent context,
- approximate fresh/cached/cache-write/output tokens when available,
- AI credits,
- first-attempt success,
- retries and escalation path,
- validation signal strength,
- hidden/late defects,
- latency only as a secondary metric.

Use VS Code subagent credit hover, Agent Debug Logs/Cache Explorer, Copilot usage views, or OpenTelemetry when available. Do not capture prompt/response content unless explicitly required and safe.

## Classify routing quality

For each task, mark one of:
- `right-sized`: selected tier succeeded with adequate evidence.
- `under-routed`: started too low and retry/escalation/rework erased expected savings.
- `over-routed`: selected a higher tier when a lower tier with strong validation likely would have succeeded.
- `insufficient-information`: routing depended on repo facts that should have been discovered by a narrow Scout pass.
- `authority-task`: correctly kept in Astra regardless of worker price.

Do not call a task over-routed merely because it succeeded. Require evidence that the lower tier would likely have had adequate success **and** adequate validation.

## Analyze

1. Group by task shape, not only file count.
2. Estimate first-pass success by **starting tier and task class**.
3. Compare cost per validated successful task, including dispatch, validation, failure penalty, and escalation.
4. Use `python scripts/route_cost.py` with observed class-level probabilities to compare every possible starting suffix.
5. Raise the starting tier when under-routing, weak validation, or hidden defects erase savings.
6. Lower the starting tier when deterministic validation makes cheaper execution reliably safe.
7. If Scout often returns facts that do not change routing, reduce Scout usage for that class.
8. If parent cold reads are large merely to classify, increase Scout usage for that class.
9. Keep thresholds broad; avoid false precision from small samples.

## Change policy

Only change always-on routing rules when evidence repeats across multiple tasks. Put experimental thresholds and class priors in `docs/astra-routing.md` first. Keep `.github/copilot-instructions.md` small.

Do not mix fixed-tier runs with Auto-selected runs when calculating Luna/Terra/Sol success priors unless the actual model used is recorded and the analysis explicitly separates them.
