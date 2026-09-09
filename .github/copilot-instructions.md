# Copilot Astra

For substantial work, prefer **Astra Orchestrator**. Optimize risk-adjusted cost per validated correct task, not cheapest-first calls.

Keep architecture/integration/final authority in Astra, but do not assume Astra is infallible. Delegate isolated work to the lowest risk-feasible physical profile.

Use transition-aware empirical priors when available: direct-start model quality and quality after earlier failures are different distributions. `config/routing-priors.local.json` is an optional local calibration overlay.

Treat automatic and human/device validation as explicit oracles. Pending/blocked/unattributed validation is not a model failure.

Keep context/cache stable: search before broad reads, use compact packets/results, and avoid mid-task parent model/reasoning/context/tool/MCP changes merely to save credits.

Use Scout only when information can change routing/scope. Writer fan-out: default 1, conditional 2, exceptional cap 3. Never recursively delegate.

Canonical local acceptance: `python scripts/validate_all.py`. Do not add GitHub Actions.

Detailed policy: `docs/astra-routing.md`. Research review: `docs/research/2026-09-10-routing-review.md`. ADR: `docs/adr/0004-transition-aware-empirical-routing.md`.
