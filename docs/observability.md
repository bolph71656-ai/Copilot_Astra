# Measurement and calibration

Measure **validated-task economics**, not target model mix.

## Required metadata

Record when available: task/risk class, requested/resolved model, `reached_after` (`direct`, `luna`, `luna>terra`, `sol`, ...), oracle strength, warm/cold parent state, per-call fresh/cached/cache-write/output/context tokens, credits/estimated units, validation state, `failure_attribution`, automatic failure detection, hidden/late defect, human/device validation kind/performed flag/duration/defect detection, retry/escalation path, Scout use/effect, wall-clock latency, client/surface, and Auto-vs-fixed mode.

Prefer metadata-only collection. Do not store prompt/response/source content unless explicitly required and safe.

## Strict validation states

Allowed validation states are `auto_validated`, `human_validated`, `needs_human_validation`, `failed`, and `blocked`.

Examples of contradictions rejected by `calibrate_routing.py`: `human_validated` without a performed human validation, `validated_correct=true` while required human validation is pending, or `human_detected_defect=true` without a performed human check.

Do not silently coerce contradictory records.

## Failure attribution

Allowed attribution: `implementation`, `device`, `environment`, `infrastructure`, `validation-procedure`, `operator`, `unknown`.

Only `implementation` failures update model correctness priors. `unknown` remains unresolved instead of defaulting to implementation.

## Calibration loop

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

## Human oracle calibration

Human/device defect detection is estimated separately from model correctness. A human pass with no known underlying defect does not prove detection power; informative cases are defects caught by the human procedure or defects discovered later after a human pass.

## Scout value

Track more than `P(changed tier | Scout used)`. Where feasible estimate avoided rework + avoided parent cold reads + avoided wrong-tier cost - Scout execution cost - parent ingestion cost.

## Privacy

Keep content capture off by default. Ignore/local-only files such as observations and `config/routing-priors.local.json` must not be committed.
