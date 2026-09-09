# Cost-aware Astra multi-model routing

This policy optimizes expected AI-credit cost per validated successful task while preserving GPT-6 Astra for long-horizon intent, architecture, integration, and final authority.

> Pricing is volatile. Astra/Luna values are this repository's working assumptions; Terra/Sol must be rechecked against the current Copilot plan/promotions before financial reporting. The calculator is a routing estimator, not a billing API.

## Working cost units

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

`C = (fresh*r_fresh + cached*r_cached + write*r_write + output*r_output) / 1,000,000`

## Physical capability matrix

| Capability | Profile |
| --- | --- |
| Tiny warm / authority / integration | Astra direct |
| Cold repository discovery | Scout Luna |
| Narrow research | Research Luna |
| Research synthesis | Research Terra |
| Mechanical writer | Execute Luna |
| General writer | Execute Terra |
| Deep bounded writer | Execute Sol |
| Difficult debugging | Debug Sol |
| Deterministic verification | Verify Luna |
| Semantic verification | Verify Terra |
| Deep high-risk verification | Verify Sol |

The matrix is physical: each profile pins one model. The parent chooses the profile instead of normally overriding a generic worker's model.

## Cheap-first economics

For a detected two-stage failure:

`E[C_cheap_first] = C_cheap + (1 - p_success_cheap) * C_expensive`

Cheap-first beats immediate expensive execution when `p_success_cheap > C_cheap / C_expensive`, but this rule is invalid for silent failures unless validation/rework/defect cost is included.

A practical ladder is:

`E = C1 + (1-p1)*(failure_penalty1 + handoff12 + C2 + (1-p2)*(...))`

Start Terra/Sol directly when weak validation or silent-failure cost makes the cheap-first expected value worse.

## Astra direct versus delegation

Delegation includes Astra dispatch + worker cost + result ingestion/integration + expected validation/retry/escalation. Keep tiny warm edits in Astra when that fixed overhead exceeds direct work.

Astra output is especially expensive relative to Luna. With the working default prices, the output-cost difference is 4.88 units per 1K tokens. Under an illustrative 9-unit handoff/integration overhead, output savings alone cover the overhead at about 1.84K generated tokens; worker input/failure cost still matters.

Cold-context delegation often becomes attractive around the order of 10K tokens, with an approximate 6K-20K gray band depending on handoff quality/retry risk. Warm cached read-heavy work can remain cheaper in Astra far longer.

## Escalation

- One obvious local/mechanical Luna failure: at most one short Luna correction.
- Luna conceptual/repeated/weakly-verifiable failure: matching Terra profile.
- Terra unresolved/reasoning-heavy task: matching Sol profile.
- Sol architecture/security/contract ambiguity or model disagreement: Astra.

Do not restart the full task on escalation; preserve evidence and transfer only the delta/root cause.

## Parallelism and context

- Parallel read-only Scout/Research work is usually safe.
- Parallel Execute/Debug writers require disjoint paths and stable interfaces.
- Default fan-out <= 3 because result-ingestion/merge cost grows with fan-out.
- Subagents cannot recursively delegate.
- Search/read narrowly and return compact structured results.
- Keep Astra parent model/reasoning/context/tools/MCP stable during the task.
- Split natural modules before long-context pricing; extended context/high reasoning are exceptions.

## Verification

Use `Verify Luna` for reproducible commands first. Pay for `Verify Terra` only when semantic reasoning is needed and `Verify Sol` when subtle high-risk correctness remains. For exceptional risk, a different-provider read-only review can reduce correlated blind spots if available.

## Surface caveat

Physical files reduce override dependence, but Copilot CLI `Auto` can still cause subagents to inherit the resolved session model. See `docs/model-routing-surfaces.md` and measure exact routing only in a surface/configuration that honors the fixed tier.

## Calibrate

Track validated cost/task, first-pass success by task class/model, retries/escalations, hidden defects, fresh-vs-cached context, and output volume. Use `/calibrate-routing` and change thresholds only when repeated data supports it.
