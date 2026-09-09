# Cost-aware Astra multi-model routing

This policy optimizes **expected AI-credit cost per validated successful task**, not model price per call and not Luna usage rate. GPT-6 Astra remains the warm parent for long-horizon intent, architecture, integration, and final authority.

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

The matrix is physical: each profile pins one model. The parent chooses a profile instead of normally overriding a generic worker's model.

## Start-tier optimization: do not default to Luna

The parent should choose the **lowest tier with sufficiently high expected success and verifiability**. Luna is the default only for low-difficulty shapes, not for every delegated task.

For a lower tier `L` followed by a higher tier `H`, the lower-first path has approximate expected cost:

`E[L->H] = C_L + (1-p_L) * (failure_penalty + handoff_LH + C_H)`

Skip `L` and start directly at `H` when:

`E[L->H] >= C_H`

The familiar zero-penalty threshold `p_L > C_L / C_H` is only a simplified special case. Real routing should include:
- validation/rework after a failed attempt,
- escalation handoff,
- duplicated reads or edits,
- silent-failure risk,
- parent ingestion/integration cost.

The calculator now evaluates **every starting suffix** of the configured ladder and reports the lowest expected cost per successful completion. This makes `Terra->Sol->Astra`, `Sol->Astra`, or direct Astra first-class options rather than treating Luna as mandatory.

Example:

```bash
python scripts/route_cost.py \
  --fresh-input 12000 \
  --output 2500 \
  --ladder luna:0.25,terra:0.92,sol:0.99,astra:1 \
  --dispatch-units 0.5 \
  --handoff-units 0.5 \
  --failure-penalty 2
```

Read `recommended start` as an estimator outcome for the supplied probabilities, not as an automatic billing oracle.

## Four routing gates

Use a small parent classification pass before execution.

### 1. Authority gate

Keep in Astra:
- architecture and decomposition that defines public/internal contracts,
- security/privacy authority,
- irreversible migrations/product/data decisions,
- integration and model disagreement,
- final acceptance.

A tiny warm-context edit can also stay in Astra when delegation overhead exceeds the work.

### 2. Information gate

Use `Scout Luna` only when **missing repository facts could change the execution tier**.

Examples:
- affected-file count or coupling is unknown,
- call graph/ownership boundary is unclear,
- test surface is unknown,
- parent would otherwise need broad cold reads merely to classify.

After Scout returns, reclassify once and dispatch directly to the correct Execute/Debug profile.

Do **not** use Scout when the task shape is already obvious from warm context or the user request. Scout is information acquisition, not a compulsory preflight.

### 3. Execution gate

Start **Execute Luna** when:
- scope is explicit,
- reasoning depth is shallow,
- mechanical/repetitive work dominates,
- deterministic validation is strong,
- failure is cheaply detectable.

Start **Execute Terra** when:
- several coupled files or local APIs must be reasoned about,
- moderate ambiguity exists,
- Luna rework is likely enough to erase its price advantage,
- implementation is ordinary but not mechanical.

Start **Execute Sol** or **Debug Sol** when:
- root cause is genuinely unclear,
- concurrency/performance/migration/invariant reasoning dominates,
- several contracts interact,
- lower-tier silent failure would be expensive,
- validation is weak or semantic correctness is subtle.

### 4. Verification gate

Choose verification separately from execution:
- `Verify Luna` for deterministic test/lint/type/schema/build evidence,
- `Verify Terra` for semantic regression/contract review,
- `Verify Sol` for subtle high-risk correctness.

A Sol implementation can still use Luna verification when commands are decisive. A Luna implementation can require Terra/Sol verification when tests cannot establish semantics.

## Delegation economics

Delegation includes:

`Astra dispatch + worker cost + result ingestion/integration + validation + expected retry/escalation`

This means two different effects coexist:

- **Output-heavy/cold tasks:** cheap worker execution becomes attractive quickly.
- **Warm read-heavy/tiny tasks:** Astra can remain cheaper because cached context and zero handoff dominate.

With the working default prices, Astra output versus Luna differs by 4.88 units per 1K output tokens. Under an illustrative 9-unit fixed handoff/integration overhead, output savings alone cover that overhead at about 1.84K generated tokens. Worker input/failure cost still matters.

Cold-context delegation often becomes attractive around the order of 10K tokens, with an approximate 6K-20K gray band depending on handoff quality and retry risk. Warm cached read-heavy work can remain cheaper in Astra far longer.

## Escalation without restart

- One obvious local/mechanical Luna failure: at most one short Luna correction.
- Luna conceptual/repeated/weakly-verifiable failure: matching Terra profile.
- Terra unresolved/reasoning-heavy task: matching Sol profile.
- Sol architecture/security/contract ambiguity or model disagreement: Astra.

Preserve successful discovery, failed hypotheses, validation evidence, and the smallest root-cause delta. Do not restart the full task or resend the parent transcript.

## Parallelism and context

- Parallel read-only Scout/Research work is usually safe.
- Parallel Execute/Debug writers require disjoint paths and stable interfaces.
- Default fan-out <= 3 because result-ingestion/merge cost grows with fan-out.
- Subagents cannot recursively delegate.
- Search/read narrowly and return compact structured results.
- Keep Astra parent model/reasoning/context/tools/MCP stable during the task.
- Split natural modules before long-context pricing; extended context/high reasoning are exceptions.

## Surface caveat and Auto

Physical files reduce runtime override dependence, but exact model semantics remain client-specific. Copilot CLI can be configured per-agent for model, effort level, and context tier; an outer Auto session can change exact attribution.

For fixed-tier calibration, label or exclude runs where the client did not honor the intended profile model. For ordinary sessions where exact attribution is unnecessary, GitHub Auto is a legitimate separate optimization mode and should be measured separately rather than mixed into Luna/Terra/Sol calibration.

See `docs/model-routing-surfaces.md`.

## Calibrate from actual misroutes

Track more than average credits:

- selected starting profile,
- task class and risk,
- whether Scout changed the selected tier,
- first-pass success,
- under-routing: started too low and escalated/reworked,
- over-routing: higher tier succeeded but a lower validated tier likely would have sufficed,
- validation strength,
- hidden/late defects,
- fresh-vs-cached context,
- output volume,
- total validated cost/task.

Use `/calibrate-routing` to tune broad class-level priors. Do not fabricate precise probabilities for a one-off task.
