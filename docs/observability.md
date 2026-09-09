# Measure and calibrate Copilot routing

Measure **validated-task economics**, not target model mix.

Record metadata when available: task/risk class, start model, `reached_after`, oracle strength, requested/resolved model, warm/cold parent state, fresh/cached/cache-write/output tokens **per call**, credits/estimated units, validated correctness, `failure_detected`, retry/escalation path, hidden/late defect, Scout used/changed tier, latency, client/surface, Auto-vs-fixed mode.

Do not store prompt/response/source content unless explicitly required and safe.

## Why per-call telemetry matters

Agentic tasks contain multiple model calls; long-context pricing/cache state apply to individual requests, so aggregate task tokens can misprice a route.

## Instrumentation

Useful surfaces can include subagent usage displays, Agent Debug Logs, Cache Explorer, usage views, and OpenTelemetry.

Recommended local pattern:

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

1. gather metadata-only observations,
2. group by task class/start model/oracle/`reached_after`,
3. run `python scripts/calibrate_routing.py observations.jsonl`,
4. use posterior correctness/detection estimates in `scripts/route_cost.py`,
5. update representative fixtures,
6. run `python scripts/policy_search.py`,
7. change always-on policy only after repeated evidence.

Track Scout's `P(changed tier | used, task class)` alongside avoided cold reads/scope mistakes. Weight late hidden defects more heavily than immediately detected failures. Keep Auto measurements separate unless resolved models are recorded.
