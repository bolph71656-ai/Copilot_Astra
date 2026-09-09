# Measure and calibrate Copilot routing

Optimization requires measured *successful-task* cost.

## What to observe

For each representative task:
- task class, risk, and chosen tier,
- parent and subagent model,
- AI credits,
- fresh/cached/cache-write/output tokens when visible,
- first-attempt success,
- retry/escalation count,
- deterministic validation result,
- defects found later,
- latency (secondary).

## VS Code inspection

Useful surfaces include:
- subagent sections/credit displays,
- Agent Debug Logs for model turns, tools, and handoffs,
- Cache Explorer when diagnosing cache churn,
- Copilot usage/AI-credit views.

OpenTelemetry can export agent telemetry. Keep content capture disabled by default because prompts/responses can contain source code or secrets.

Recommended settings when intentionally instrumenting a local test workspace:

```json
{
  "github.copilot.chat.otel.enabled": true,
  "github.copilot.chat.otel.exporterType": "file",
  "github.copilot.chat.otel.outfile": ".copilot-otel.jsonl",
  "github.copilot.chat.otel.captureContent": false
}
```

Do not commit telemetry containing user/source content.

## Calibration loop

1. Sample enough tasks to separate random failures from a pattern.
2. Group by task shape (mechanical, multi-file implementation, debugging, architecture), not only size.
3. Compare validated cost per success.
4. Penalize hidden/late defects more heavily than immediately detected test failures.
5. Run `python scripts/route_cost.py` with observed token shapes and success probabilities.
6. Adjust routing bands in `docs/astra-routing.md`.
7. Change always-on instructions only if the pattern is stable.

The `/calibrate-routing` skill packages this process.
