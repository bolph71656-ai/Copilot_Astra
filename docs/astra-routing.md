# Astra / Luna cost routing

This document turns the repository's routing policy into an explicit cost model. The numbers below are the working cost assumptions for this repository and should be updated if Copilot pricing changes.

## Cost assumptions

Cost units per 1M tokens:

| Model / mode | Input | Output | Cache read | Cache write |
| --- | ---: | ---: | ---: | ---: |
| Astra default | 1000 | 5000 | 100 | 1250 |
| Astra long | 2000 | 7500 | 200 | 2500 |
| Luna default | 20 | 120 | 2 | 25 |
| Luna long | 40 | 180 | 4 | 50 |

In default mode, Astra is about 50x Luna for input/cache traffic and about 41.7x Luna for output. Long mode preserves roughly the same ratios while increasing absolute cost.

## Direct Astra cost

For token counts expressed in millions:

```text
C_Astra = 1000*I + 5000*O + 100*R + 1250*W
```

Where:

- `I` = fresh input,
- `O` = output,
- `R` = cache-read tokens,
- `W` = cache-write tokens.

For long mode, substitute the long-mode prices from the table.

## Delegated cost

A practical expected-cost model is:

```text
E[C_delegate] = H_Astra + C_Luna + p_retry*C_retry + p_fail*C_escalation
```

`H_Astra` is the parent cost of dispatching the task, ingesting the compact result, and integrating it. This is why delegating every tiny edit is not optimal even when Luna's per-token price is much lower.

Delegate when:

```text
C_Astra_direct_saved > H_Astra + C_Luna + expected_failure_overhead
```

## Useful break-even intuition

### Output-heavy work

Astra default output costs 5000 units/1M tokens versus Luna at 120. The difference is 4880 units/1M, or about 4.88 units per 1k output tokens.

If a typical handoff/integration costs about 9 units, output savings alone cover that overhead at roughly:

```text
9 / 4.88 ~= 1.84k output tokens
```

Therefore, tasks expected to generate several thousand tokens of code are strong Luna candidates even when Astra already has warm input context.

### Cold-context work

Under a typical compact-handoff assumption, cold-context delegation tends to break even around the order of 10k tokens. Efficient handoffs can justify Luna nearer 6k; verbose handoffs plus retries can push the break-even above 20k.

Use these as routing bands, not hard thresholds:

- `< 6k`: usually keep in warm Astra unless the work is mechanical/high-output.
- `6k-20k`: inspect cache warmth, expected output, independence, and retry risk.
- `> 20k cold/new context`: usually delegate or split into Luna tasks.

### Warm-cache read-heavy work

When Astra already has the relevant context cached, its marginal read cost is much lower than fresh input. In read-dominated tasks with little output, delegation can remain more expensive until very large token volumes. Under one typical handoff assumption, the threshold can move to roughly 200k tokens.

This is not a universal threshold: Astra output volume, cache misses, result-ingestion cost, and retry probability can move it substantially.

## Routing matrix

| Task shape | Default route | Reason |
| --- | --- | --- |
| Small edit in 1-2 warm files | Astra | Avoid handoff/re-ingestion overhead |
| Architecture or interface decision | Astra | High coupling to parent intent |
| Repository exploration | Luna Scout | Cold-read volume |
| Mechanical refactor across files | Luna Worker | Cheap repetitive execution |
| Boilerplate or large code generation | Luna Worker | Astra output is expensive |
| Test generation / repeated test loops | Luna Test | Repetitive output + command cycles |
| Final cross-module integration | Astra | Requires parent global intent |
| Large independent modules | Parallel Luna Workers | Independent cold contexts |

## Context and cache discipline

1. Keep Astra as the parent model for the session instead of switching models midstream.
2. Delegate through subagents so each worker gets a scoped fresh context rather than inheriting the parent's entire transcript.
3. Send paths/symbols/acceptance criteria instead of copied source whenever the worker can read the repository itself.
4. Return compact structured summaries so Astra does not pay to ingest verbose worker narration.
5. Split very large work before either model enters long-context pricing unnecessarily.
6. Do not parallelize workers with overlapping write scopes.

## Retry policy

Cheap workers can become expensive when failure loops are unbounded. Use this default:

- first attempt,
- at most one targeted retry for the same local root cause,
- then escalate to Astra or redefine the task.

For a task with non-trivial failure probability, include expected retry cost explicitly rather than treating Luna's sticker price as the total cost.

## Operational target

A useful initial target is to place roughly 70-90% of bulk work tokens in Luna while keeping 10-30% in Astra for intent, architecture, integration, warm micro-edits, and final acceptance. Measure successful-task cost and adjust; the optimal split depends on repository structure and retry rates.
