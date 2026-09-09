# Copilot Astra

For substantial coding work, prefer the **Astra Orchestrator** custom agent. Optimize expected cost per correct task: keep architecture/integration/final acceptance in Astra and delegate isolated execution to the cheapest capable tier (Luna -> Terra -> Sol).

Keep context lean: search before broad reads, use narrow tools, send compact subagent packets/results, and do not switch the parent model/reasoning/context/tool set mid-task just to save credits.

Use deterministic project validation whenever possible. Do not recursively delegate, run overlapping writer agents, or enable broad MCP/tool sets without a task-specific need.

Detailed routing lives in `docs/astra-routing.md`; shared agent protocol lives in `AGENTS.md`.
