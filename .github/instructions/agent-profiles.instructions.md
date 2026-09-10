---
name: Agent profile standards
description: Structural rules for generated Copilot custom agent profiles in this repository.
applyTo: '.github/agents/**/*.agent.md'
---

- `.github/agents/*.agent.md` is generated from `config/model-registry.json` plus `.github/agent-templates/*.md`; do not hand-edit generated profiles.
- Change model inventory/role selection in the registry, then run `python scripts/sync_model_config.py --write`.
- One generated physical profile exists per selected role + active worker model.
- Every profile must set `target: vscode`.
- Only `Astra Orchestrator` may include the `agent` tool.
- Every subagent must set `agents: []`, `user-invocable: false`, and `disable-model-invocation: true`.
- The parent must explicitly allowlist every generated physical subagent.
- Use exact `copilot_model` values from the registry.
- Research/Scout/Verify profiles are read-only and must not include `edit`.
- Writers use `DONE | NEEDS_HUMAN_VALIDATION | FAILED | BLOCKED | NEEDS_PARENT`.
- Read-only discovery/research uses `DONE | BLOCKED | NEEDS_PARENT`.
- Verifiers use `PASS | FAIL | BLOCKED | NEEDS_PARENT`.
- Pending real-device/manual acceptance must never be reported as `DONE`.
- Human/device failure is not automatically an implementation/model failure; preserve attribution uncertainty.
- Keep outputs compact and machine-scannable; never echo files already on disk.
