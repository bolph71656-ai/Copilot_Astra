---
name: calibrate-routing
description: Calibrate Astra/Luna/Terra/Sol routing from observed Copilot cost, per-call token/cache data, correctness, automatic and human/device oracle strength, hidden defects, Scout value, retries, escalation, and latency.
argument-hint: "[metadata-only observations or measurement summary]"
user-invocable: true
disable-model-invocation: true
---

# Calibrate routing

Tune **risk-adjusted validated-task economics**, not Luna percentage.

Collect task/risk class, starting/resolved model, `reached_after`, automatic oracle strength, per-call token/cache counts, credits/units, validated correctness, detected vs hidden failures, retry/escalation, Scout use/change, latency, and Auto-vs-fixed mode. Keep source/prompt/response content out unless explicitly needed and safe.

For human/device-required work also record:
- `validation_state`: `needs_human_validation`, `human_validated`, `failed`, or `blocked`
- `human_validation_required` / `human_validation_performed`
- `human_validation_kind`
- `human_validation_seconds`
- `human_detected_defect`
- `failure_attribution`

Do **not** count pending or blocked human validation as model failure. Do not penalize a model for device/environment/infrastructure/procedure/operator failures. Unknown human failures remain unassigned until evidence resolves attribution.

Run `python scripts/calibrate_routing.py observations.jsonl`. The tool uses Beta posteriors, keeps direct starts separate from stages reached after prior evidence, and calibrates human/device defect detection separately from model correctness.

Diagnose repeated patterns as `right-sized`, `under-routed`, `over-routed`, `weak-oracle`, `expensive-human-retest`, `insufficient-information`, or `authority-task`.

Before changing always-on policy: update priors, test economics with `scripts/route_cost.py`, update fixtures, run `scripts/policy_search.py`, then change prose. Do not mix Auto/fixed measurements unless resolved model is recorded.
