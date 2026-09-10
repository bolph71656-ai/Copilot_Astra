# Measurement and calibration

Measure **validated-task economics**, not target model mix.

## Required worker-routing metadata

Record when available: task/risk class, requested/resolved model, `reached_after` (`direct`, `luna`, `luna>terra`, `sol`, ...), oracle strength, warm/cold parent state, per-call fresh/cached/cache-write/output/context tokens, credits/estimated units, validation state, `failure_attribution`, automatic failure detection, hidden/late defect, human/device validation kind/performed flag/duration/defect detection, retry/escalation path, Scout use/effect, wall-clock latency, client/surface, and Auto-vs-fixed mode.

Prefer metadata-only collection. Do not store prompt/response/source content unless explicitly required and safe.

## Gateway telemetry is a separate dataset

Do not infer gateway classifier quality from worker `p_correct` priors. For gateway decisions record, when available:

- `gateway_action`: `direct | escalate`,
- `task_class`,
- `risk_class`,
- `oracle_strength`,
- `final_validated_correct` for direct attempts,
- `false_downroute`,
- `authority_rescue_required`,
- `gateway_path_units`,
- `authority_direct_estimated_units`,
- optional latency/context/cache metadata for deeper economics analysis.

A false down-route means the gateway completed or began a direct path that should have been authority-owned under the policy, even if later rescue recovered the task. Keep this metric separate from ordinary implementation failures.

Generate conservative Wilson-bound calibration locally:

```bash
python scripts/calibrate_gateway.py observations.jsonl \
  --out config/gateway-calibration.local.json
```

The local gateway calibration is ignored by Git. `scripts/gateway_policy.py` uses it only for calibrated expansion; missing, malformed, under-sampled, insufficient-confidence, or unsafe evidence resolves upward to the authority parent.

Current policy uses bootstrap admission only for exploratory + deterministic-oracle work. Standard-risk direct completion requires the bucket-specific evidence in `config/gateway-policy.json` to clear sample, confidence, safety, rescue, and cost thresholds. High/critical work never completes directly at the gateway.

## Gateway rollback telemetry

Track global direct-attempt safety/economics continuously enough to detect regression:

```text
false_downroute_rate
authority_rescue_rate
mean_cost_ratio_vs_authority_direct
high_or_critical_false_downroutes
```

`config/gateway-policy.json` defines rollback thresholds. Any high/critical false down-route is an immediate global pause trigger; rate/cost regressions trigger after the configured sample floor.

The bootstrap and rollback policies are intentionally asymmetric: over-escalation is tolerated more readily than unsafe under-routing.

## Strict worker validation states

Allowed validation states are `auto_validated`, `human_validated`, `needs_human_validation`, `failed`, and `blocked`.

Examples of contradictions rejected by `calibrate_routing.py`: `human_validated` without a performed human validation, `validated_correct=true` while required human validation is pending, or `human_detected_defect=true` without a performed human check.

Do not silently coerce contradictory records.

## Failure attribution

Allowed attribution: `implementation`, `device`, `environment`, `infrastructure`, `validation-procedure`, `operator`, `unknown`.

Only `implementation` failures update worker model correctness priors. `unknown` remains unresolved instead of defaulting to implementation.

## Worker calibration loop

1. collect metadata-only observations,
2. validate and group by task class/model/oracle/`reached_after`,
3. generate a local overlay:

```bash
python scripts/calibrate_routing.py observations.jsonl \
  --routing-priors-out config/routing-priors.local.json
```

4. run route experiments with `scripts/route_cost.py`,
5. update representative fixtures only when policy expectations intentionally change,
6. run `python scripts/validate_all.py`,
7. change always-on policy only after repeated evidence.

Worker routing and gateway admission remain distinct calibration loops.

## Routing economics

`route_cost.py` uses `config/operational-costs.json` when dispatch/handoff/failure/defect/latency-value CLI arguments are omitted. The committed values are conservative engineering assumptions and are explicitly marked `measured: false`.

Replace those values with representative locally measured economics when available. Explicit CLI values, including zero, remain available for controlled sensitivity experiments.

For gateway-vs-authority comparison, measure task-level economics rather than token price alone. At minimum include gateway classification cost, escalation duplication/handoff, authority cost after escalation, rescue/rework, and the validated-correct outcome.

## Human oracle calibration

Human/device defect detection is estimated separately from model correctness. A human pass with no known underlying defect does not prove detection power; informative cases are defects caught by the human procedure or defects discovered later after a human pass.

## Scout value

Track more than `P(changed tier | Scout used)`. Where feasible estimate avoided rework + avoided parent cold reads + avoided wrong-tier cost - Scout execution cost - parent ingestion cost.

## Privacy

Keep content capture off by default. Ignore/local-only files such as observations, `config/routing-priors.local.json`, and `config/gateway-calibration.local.json` must not be committed.
