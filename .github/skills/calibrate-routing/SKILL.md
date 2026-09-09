---
name: calibrate-routing
description: Calibrate Astra/Luna/Terra/Sol routing from observed GitHub Copilot AI-credit usage, token/cache data, retries, escalations, validation failures, and task outcomes. Use when tuning thresholds or reviewing whether cheap-first routing is actually economical.
argument-hint: "[usage observations, debug log summary, or task sample]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Do not tune from intuition alone. Use observed successful-task cost.

## Collect

For a representative task sample record:
- task class and risk level,
- parent model and worker model,
- cold vs warm context,
- approximate fresh/cached/cache-write/output tokens when available,
- AI credits,
- first-attempt success,
- retries/escalations,
- validation signal strength,
- hidden defects found later,
- latency only as a secondary metric.

Use VS Code subagent credit hover, Agent Debug Logs/Cache Explorer, Copilot usage views, or OpenTelemetry when available. Do not capture prompt/response content unless explicitly required and safe.

## Analyze

1. Group tasks by shape, not only by file count.
2. Compare cost per *validated successful task*.
3. Separate detectable failures from silent/late defects.
4. Use `python scripts/route_cost.py` to test candidate ladders and pricing assumptions.
5. Raise a tier when low-tier retries, weak validation, or hidden defects erase savings.
6. Lower a tier when deterministic validation makes cheap execution reliably safe.
7. Keep thresholds broad; avoid false precision from small samples.

## Change policy

Only change always-on routing rules when evidence is repeated across multiple tasks. Put experimental thresholds in `docs/astra-routing.md` first. Keep `.github/copilot-instructions.md` small.
