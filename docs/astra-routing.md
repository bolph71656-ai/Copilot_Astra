# Cost-aware Astra multi-model routing

This is the quantitative policy behind **Astra Orchestrator**. It optimizes expected AI-credit cost per validated successful task while preserving GPT-6 Astra for the decisions where its long-horizon reasoning has the highest value.

> Pricing is volatile. The table below is the repository's working snapshot. The user-supplied Astra/Luna values are authoritative for this project; Terra/Sol should be rechecked against the current Copilot pricing page/plan before financial reporting. Use the calculator as a routing estimator, not a billing API.

## 1. Working cost units

Units per 1M tokens (`100 units = $1`):

| Model | Tier | Fresh input | Cached input | Cache write | Output | Long threshold |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Luna | default | 20 | 2 | 25 | 120 | <= 200K |
| Luna | long | 40 | 4 | 50 | 180 | > 200K |
| Terra | default | 200 | 20 | 250 | 1200 | <= 272K |
| Terra | long | 400 | 40 | 500 | 1800 | > 272K |
| Sol | default | 400 | 40 | 500 | 2000 | <= 272K |
| Sol | long | 800 | 80 | 1000 | 3000 | > 272K |
| Astra | default | 1000 | 100 | 1250 | 5000 | <= 272K |
| Astra | long | 2000 | 200 | 2500 | 7500 | > 272K |

For each model:

```text
C = (fresh*r_fresh + cached*r_cached + write*r_write + output*r_output) / 1,000,000
```

## 2. Capability ladder

| Tier | Model | Default task shape |
| --- | --- | --- |
| 0 | Astra direct | Tiny edit in warm parent context |
| 1 | Luna | Simple/repetitive/mechanical, cold discovery, boilerplate, tests |
| 2 | Terra | General coding, several coupled files, moderate ambiguity |
| 3 | Sol | Deep debugging, cross-module reasoning, concurrency/performance/migrations |
| 4 | Astra | Architecture, security/privacy, contracts, irreversible choices, integration/final acceptance |

Risk can increase the tier even when token volume is small. Strong deterministic validation can decrease the execution tier.

## 3. Why cheap-first can work

For a two-stage ladder where a cheap failure is detected and immediately escalated:

```text
E[C_cheap_first] = C_cheap + (1 - p_success_cheap) * C_expensive
```

Cheap-first beats using the expensive model immediately when:

```text
p_success_cheap > C_cheap / C_expensive
```

For the same default token mix, Luna is approximately one tenth of Terra, so Luna-first can be economically rational even at modest first-pass success rates.

**Do not use this rule for silent failures.** Add validation/rework/defect cost:

```text
E = C1
  + (1-p1) * (failure_penalty1 + handoff12 + C2
  + (1-p2) * (failure_penalty2 + handoff23 + C3 ...))
```

A cheap model that produces plausible wrong code can be more expensive than starting at Terra/Sol.

## 4. Astra direct versus delegation

Delegation is not free:

```text
E[C_delegate] =
  Astra_dispatch
  + worker_cost
  + Astra_result_ingestion/integration
  + expected_validation/retry/escalation
```

Keep a tiny warm edit in Astra when this fixed overhead exceeds the work.

### Output-heavy break-even intuition

Astra output costs 5000 units/1M vs Luna 120, a difference of 4880 units/1M = 4.88 units per 1K output tokens.

With an illustrative fixed handoff/integration overhead of 9 units:

```text
9 / 4.88 ~= 1.84K output tokens
```

So multi-thousand-token code generation is often worth delegating even if Astra's input context is warm. This ignores worker input, result ingestion, and failure cost, so treat it as intuition rather than a universal threshold.

### Cold-read band

A compact handoff can make Luna attractive around the order of 10K cold tokens; an efficient packet can move that toward ~6K, while verbose packets/retries can push it beyond ~20K. Use 6K-20K as a gray band, not a hard trigger.

### Warm read-heavy work

Cached Astra input is much cheaper than fresh Astra input. When output is tiny and the relevant context is already cached, continuing in Astra can beat delegation at far larger read volumes. This is why "delegate everything" is not optimal.

## 5. Escalation policy

Use monotonic escalation:

- Luna local/mechanical failure with obvious fix: at most one short Luna correction.
- Luna conceptual failure, uncertainty with weak tests, or repeated root cause: Terra.
- Terra unresolved cross-module root cause: Sol.
- Sol architecture/security/contract ambiguity or model disagreement: Astra.

Do not pay for repeated failures at the same capability tier.

## 6. Parallelism

Parallelize isolated context, not shared mutable state.

- Parallel read-only Scout/Researcher tasks are usually safe.
- Parallel Executor tasks require disjoint paths and stable interfaces.
- Default fan-out <= 3; higher fan-out increases parent result-ingestion and merge-conflict cost.
- Batch tiny related operations into one packet.
- Never recursively delegate.

## 7. Context and cache

- Keep the Astra parent model stable during the task.
- Avoid changing reasoning level, context size, enabled tools, or MCP set mid-session.
- Send paths/symbols/constraints instead of source dumps.
- Keep subagent outputs compact.
- Split natural modules before crossing long-context pricing thresholds.
- Use extended 1M context only when sharding would destroy essential coupling.
- Use high reasoning only for tasks that need it.

## 8. Model diversity

Independent verification can reduce correlated blind spots. For high-risk semantic changes, consider a read-only verifier on a different provider/model if available. Do not use diversity for routine deterministic checks: tests/lint/type checks are cheaper and more reproducible.

## 9. Calibrate from real usage

The correct target is not a fixed "90% Luna" ratio. Track:
- validated cost per task,
- first-pass success by task class/model,
- retries and escalation,
- hidden defects,
- fresh-vs-cached context,
- output volume.

Invoke `/calibrate-routing` with a representative sample and change thresholds only when the data repeats.
