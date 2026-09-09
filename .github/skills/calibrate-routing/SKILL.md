---
name: calibrate-routing
description: Calibrate Astra/Luna/Terra/Sol routing from observed Copilot cost, per-call token/cache data, correctness, failure-detection strength, hidden defects, Scout value, retries, escalation, and latency.
argument-hint: "[metadata-only observations or measurement summary]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Tune **risk-adjusted validated-task economics**, not Luna percentage.

Collect task/risk class, starting/resolved model, `reached_after`, oracle strength, per-call token/cache counts, credits/units, validated correctness, detected vs hidden failures, retry/escalation, Scout use/change, latency, and Auto-vs-fixed mode. Keep source/prompt/response content out unless explicitly needed and safe.

Run `python scripts/calibrate_routing.py observations.jsonl`. The tool uses Beta posteriors and keeps direct starts separate from stages reached after prior evidence.

Diagnose repeated patterns as `right-sized`, `under-routed`, `over-routed`, `weak-oracle`, `insufficient-information`, or `authority-task`.

Before changing always-on policy: update priors, test economics with `scripts/route_cost.py`, update fixtures, run `scripts/policy_search.py`, then change prose. Do not mix Auto/fixed measurements unless resolved model is recorded.
