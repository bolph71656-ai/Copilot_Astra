# Copilot Astra

For substantial work, prefer **Astra Orchestrator**. Optimize risk-adjusted cost per validated correct task, not cheapest-first calls.

Keep architecture/integration/final authority in Astra. Delegate isolated work to the lowest risk-feasible physical profile. Treat deterministic validation as an oracle; do not duplicate decisive worker checks by default. Capability may skip intermediate tiers when economically justified.

Keep context/cache stable: search before broad reads, use compact packets/results, and avoid mid-task parent model/reasoning/context/tool/MCP changes merely to save credits.

Use Scout only when information can change routing/scope. Default writer fan-out is 1; use 2 conditionally; 3 is exceptional. Never recursively delegate.

Detailed policy: `docs/astra-routing.md`. Research basis: `docs/research/2026-09-09-deep-routing-research.md`. Architecture decision: `docs/adr/0001-risk-aware-routing.md`.
