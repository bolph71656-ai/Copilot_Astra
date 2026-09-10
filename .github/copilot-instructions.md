# Copilot Astra

For normal repository work, prefer **Astra Gateway** as the low-cost entry. It is fail-closed: direct completion is allowed only when the hard semantic gates are clear **and** `python scripts/gateway_policy.py ...` returns `ALLOW_DIRECT` before edits. Otherwise escalate intact to **Astra Orchestrator**. Known authority/high-risk work may start at Astra Orchestrator directly.

Cold-start gateway policy is deliberately narrow: only exploratory work with a decisive deterministic oracle may complete directly. Standard-risk direct completion requires sufficient local `config/gateway-calibration.local.json` evidence clearing conservative bounds. High/critical work never completes at the gateway. Worker correctness seed priors do not authorize gateway expansion.

The active capability ladder and authority model come from `config/model-registry.json`; never assume a fixed four-model topology or fixed model ids. The gateway uses the lowest active non-authority model when one exists. Only the authority parent may dispatch generated physical workers.

Optimize risk-adjusted cost per validated correct task, not cheapest-first calls. False down-routing is more costly than over-escalation. `scripts/route_cost.py` uses conservative nonzero orchestration/rework defaults from `config/operational-costs.json` unless explicit CLI values override them.

Use transition-aware empirical priors when available: direct-start model quality and quality after earlier failures are different distributions. `config/routing-priors.local.json` is an optional local calibration overlay. Gateway safety is measured separately from worker priors.

Treat automatic and human/device validation as explicit oracles. Pending/blocked/unattributed validation is not a model failure. Human testing is not permission to down-route weak-oracle or high-consequence work.

Keep context/cache stable: search before broad reads, use compact packets/results, and avoid mid-task authority model/reasoning/context/tool/MCP changes merely to save credits.

Use Scout only when information can change routing/scope. Writer fan-out: default 1, conditional 2, exceptional cap 3. Generated workers never recursively delegate.

Generated agent files and seed priors must match the registry/templates. After model/pricing/gateway-template changes run `python scripts/sync_model_config.py --write` then `python scripts/validate_all.py`.

Canonical local acceptance: `python scripts/validate_all.py`. Do not add GitHub Actions.

Detailed policy: `docs/model-registry.md` and `docs/astra-routing.md`. Gateway decision record: `docs/adr/0006-calibrated-gateway-admission.md`.
