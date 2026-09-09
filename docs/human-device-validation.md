# Human and real-device validation

## Purpose

Some work cannot be fully accepted by an agent alone: mobile permission flows, Bluetooth reconnect behavior, camera/microphone access, hardware integrations, visual quality, animation feel, browser/device quirks, external peripherals, and other real-environment behavior.

Copilot Astra treats this as a routing input rather than an afterthought.

The central rule is:

> **Implementation complete is not validation complete.**

A required human/device check creates a pending validation state. It is neither agent success nor agent failure until the required evidence exists.

## State machine

| State | Meaning | Model calibration |
| --- | --- | --- |
| `DONE` / `auto_validated` | all required acceptance evidence is available and no human check remains | resolved success |
| `NEEDS_HUMAN_VALIDATION` | automatic work passed, required human/device check has not run | exclude from success/failure prior |
| `human_validated` | required human/device procedure passed | resolved success |
| `FAILED` | confirmed implementation defect or acceptance failure | resolved failure when attributed to implementation |
| `BLOCKED` | device/environment/permission/test setup prevents validation | exclude from model prior |
| `NEEDS_PARENT` | authority/design decision is required | routing/authority event, not worker correctness failure |

Do not collapse `NEEDS_HUMAN_VALIDATION` into `FAILED`, and do not treat it as `DONE`.

## Routing variables

For each task class, estimate:

- `p`: probability the worker implementation is actually correct.
- `d_auto`: probability automation detects an incorrect implementation before acceptance.
- `d_human`: probability the required human/device procedure detects an incorrect result **conditional on that defect escaping automation**.
- `H_cost`: human setup/operator/retest burden expressed in routing units.
- `H_latency`: expected elapsed seconds for one human validation cycle.
- `L_defect`: loss/penalty for a defect that survives both automatic and human checks.

For one stage, pre-human hidden risk is:

```text
(1 - p) * (1 - d_auto)
```

Post-human hidden risk is:

```text
(1 - p) * (1 - d_auto) * (1 - d_human)
```

Combined detection probability for an incorrect result is:

```text
d_total = d_auto + (1 - d_auto) * d_human
```

A human check is required only when automatic validation did not already reject the candidate. Its expected frequency at a reached stage is:

```text
p + (1 - p) * (1 - d_auto)
```

The route estimator therefore charges human cost/latency on every candidate that reaches the human oracle, including repeated cycles after an escalated implementation.

## Selection consequences

### Strong, cheap human oracle

A visual/layout adjustment with a precise checklist and a quick real-device pass can have weak automation but high `d_human`. If defect consequence is low and a retry is cheap, `Execute Luna` may remain optimal.

### Expensive manual retest

A Bluetooth/peripheral test that requires hardware reset, pairing, walking away from range, reconnecting, and collecting logs may take several minutes. Even with high human detection power, starting too low can create repeated expensive human cycles. Terra or Sol direct can have lower total expected cost.

### Weak or subjective human oracle

"Looks fine to me" is not a high-confidence oracle for authorization, payment, persistence, data loss, race conditions, or security-sensitive behavior. Human validation does not compensate for weak implementation reasoning. Route these tasks to Sol/Astra and add automated invariants where possible.

## Human validation packet

When a worker cannot perform a required check, it returns `STATUS=NEEDS_HUMAN_VALIDATION` and a compact packet:

- `WHY`: why automatic evidence is insufficient.
- `SETUP`: device/OS/build/account/peripheral preconditions.
- `STEPS`: numbered minimal procedure.
- `EXPECTED`: objective expected result for each relevant step.
- `EVIDENCE`: screenshot/video/log/state/value to capture.
- `ATTRIBUTION_HINTS`: evidence that separates implementation failure from device/environment/infrastructure/procedure/operator failure.

Do not ask the operator for broad exploratory testing when a narrow discriminating procedure exists.

## Handling human failure

A human/device failure is evidence, not immediate proof of model failure.

Classify attribution:

- `implementation`: code/config produced by the worker is responsible.
- `device`: hardware/OS/device-specific external state caused the failure.
- `environment`: local environment, permission, network, account, or external service caused it.
- `infrastructure`: build/test backend or service outage caused it.
- `validation-procedure`: the test steps or setup were invalid.
- `operator`: execution error in the manual procedure.
- `unknown`: evidence is insufficient.

Only confirmed implementation-attributed failures update the worker/model correctness posterior as failures. Unknown or external failures remain separate until resolved.

## Calibration schema

Recommended metadata-only fields:

```json
{
  "task_class": "bluetooth-reconnect",
  "start_model": "terra",
  "reached_after": "direct",
  "oracle_strength": "human-device",
  "human_validation_required": true,
  "human_validation_kind": "android-device",
  "validation_state": "needs_human_validation",
  "human_validation_performed": false,
  "human_validation_seconds": 0,
  "human_detected_defect": false,
  "failure_attribution": "unknown"
}
```

After a resolved manual pass/fail, update the observation rather than inventing a model outcome before the check.

`calibrate_routing.py` keeps pending/blocked states out of model success priors and estimates human oracle detection from cases where defects were either caught by the human procedure or later discovered after a human pass.

## Risk guardrails

Do not lower execution tier merely because a person will test when any of the following are true:

- irreversible state change or data loss,
- authentication/authorization/security/privacy boundary,
- payment/financial consequences,
- migration or destructive operation,
- safety-relevant behavior,
- broad device/OS state space with narrow manual coverage,
- subjective or poorly repeatable validation,
- unknown human detection rate with high hidden-defect cost.

In these cases, the human procedure is an additional oracle, not a substitute for stronger implementation reasoning and automated evidence.
