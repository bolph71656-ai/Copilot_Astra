---
name: Agent profile standards
description: Structural rules for Copilot custom agent profiles in this repository.
applyTo: '.github/agents/**/*.agent.md'
---

- One physical profile per role + model tier.
- Every profile must set `target: vscode`.
- Only `Astra Orchestrator` may include the `agent` tool.
- Every subagent must set `agents: []`, `user-invocable: false`, and `disable-model-invocation: true`.
- `Astra Orchestrator` must explicitly allowlist every physical subagent it may invoke.
- Use qualified model names in `Model Name (copilot)` form.
- Research/Scout/Verify profiles are read-only and must not include `edit`.
- Writers use `DONE | NEEDS_HUMAN_VALIDATION | FAILED | BLOCKED | NEEDS_PARENT`.
- Read-only discovery/research uses `DONE | BLOCKED | NEEDS_PARENT`.
- Verifiers use `PASS | FAIL | BLOCKED | NEEDS_PARENT`.
- Pending real-device/manual acceptance must never be reported as `DONE`.
- Human/device failure is not automatically an implementation/model failure; preserve attribution uncertainty.
- Keep outputs compact and machine-scannable; never echo files already on disk.
- Update `scripts/validate_config.py`, README, routing docs, and regression tests whenever the matrix or status contract changes.
