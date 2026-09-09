---
name: Agent profile standards
description: Structural rules for Copilot custom agent profiles in this repository.
applyTo: '.github/agents/**/*.agent.md'
---

Keep agent descriptions mutually distinct so role/tier routing is unambiguous.

- Use **one physical profile per role + model tier**. Do not create a generic profile that relies on runtime model override for Luna/Terra/Sol selection.
- Use the narrowest tool set required by the role.
- Only `Astra Orchestrator` may include the `agent` tool.
- Every subagent must set `agents: []`, `user-invocable: false`, and must not recursively delegate.
- Use qualified model names in `Model Name (copilot)` form and pin the intended model in each profile.
- Luna profiles handle cheap/deterministically verifiable work; Terra profiles handle moderate synthesis/coupling; Sol profiles handle deep reasoning/high-risk bounded work.
- Research/Scout/Verify profiles are read-only and must not include `edit`.
- Do not add MCP servers unless that exact role requires the integration.
- Worker `STATUS` values are `DONE`, `NEEDS_HUMAN_VALIDATION`, `FAILED`, `BLOCKED`, or `NEEDS_PARENT`.
- A writer whose required real-device/visual/manual acceptance step cannot be executed by the agent must return `NEEDS_HUMAN_VALIDATION`, not `DONE`, with a compact human-validation packet.
- Human/device validation failure is not automatically an implementation/model failure; preserve evidence and attribution uncertainty.
- Keep outputs compact and machine-scannable; never echo files already on disk.
- Update `README.md`, routing docs, tests, and validation guardrails whenever the physical matrix or status contract changes.
