# Copilot Astra

For substantial work, prefer **Astra Orchestrator**. Optimize risk-adjusted cost per validated correct task, not cheapest-first calls.

The active capability ladder and authority model come from `config/model-registry.json`; never assume a fixed four-model topology or fixed model ids. Delegate isolated work to the lowest risk-feasible generated physical profile.

Use transition-aware empirical priors when available: direct-start model quality and quality after earlier failures are different distributions. `config/routing-priors.local.json` is an optional local calibration overlay.

Treat automatic and human/device validation as explicit oracles. Pending/blocked/unattributed validation is not a model failure.

Keep context/cache stable: search before broad reads, use compact packets/results, and avoid mid-task parent model/reasoning/context/tool/MCP changes merely to save credits.

Use Scout only when information can change routing/scope. Writer fan-out: default 1, conditional 2, exceptional cap 3. Never recursively delegate.

Generated agent files and seed priors must match the registry. After model/pricing changes run `python scripts/sync_model_config.py --write` then `python scripts/validate_all.py`.

Canonical local acceptance: `python scripts/validate_all.py`. Do not add GitHub Actions.

Detailed policy: `docs/model-registry.md` and `docs/astra-routing.md`. ADR: `docs/adr/0005-registry-driven-model-topology.md`.
