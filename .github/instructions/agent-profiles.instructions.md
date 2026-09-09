---
name: Agent profile standards
description: Structural rules for Copilot custom agent profiles in this repository.
applyTo: '.github/agents/**/*.agent.md'
---

Keep agent descriptions mutually distinct so routing is unambiguous.

- Use the narrowest tool set needed by the role.
- Only the Astra coordinator may include the `agent` tool.
- Every subagent must set `agents: []` and must not recursively delegate.
- Worker/research/verifier profiles must set `user-invocable: false`.
- Use qualified VS Code model names in `Model Name (copilot)` form.
- Prefer a single inexpensive default model; let the Astra parent explicitly request a higher tier when needed.
- Do not add MCP servers to a profile unless the role needs that specific integration.
- Keep outputs compact and machine-scannable; do not echo files already on disk.
