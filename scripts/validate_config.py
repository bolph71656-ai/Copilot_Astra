#!/usr/bin/env python3
"""Static guardrails for Copilot Astra repository customizations."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".github" / "agents"
SUBAGENTS = {"Scout", "Researcher", "Executor", "Debugger", "Verifier"}
ORCHESTRATOR = "Astra Orchestrator"


def frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter start")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("missing YAML frontmatter end")
    return text[4:end]


def scalar(fm: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", fm)
    return match.group(1).strip().strip("'\"") if match else None


def validate_agent(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        fm = frontmatter(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: {exc}"]
    name = scalar(fm, "name")
    model = scalar(fm, "model")
    tools_line = scalar(fm, "tools") or ""
    agents_line = scalar(fm, "agents")
    if not name:
        errors.append(f"{path}: missing name")
    if not scalar(fm, "description"):
        errors.append(f"{path}: missing description")
    if not model or "(copilot)" not in model:
        errors.append(f"{path}: model should use qualified '(copilot)' name")
    if name == ORCHESTRATOR:
        if "'agent'" not in tools_line and "\"agent\"" not in tools_line:
            errors.append(f"{path}: orchestrator must include agent tool")
        if agents_line is None or "Scout" not in agents_line:
            errors.append(f"{path}: orchestrator must restrict allowed agents")
    elif name in SUBAGENTS:
        if scalar(fm, "user-invocable") != "false":
            errors.append(f"{path}: subagent must set user-invocable: false")
        if agents_line != "[]":
            errors.append(f"{path}: subagent must set agents: []")
        if "'agent'" in tools_line or "\"agent\"" in tools_line:
            errors.append(f"{path}: subagent must not include agent tool")
    else:
        errors.append(f"{path}: unexpected agent name {name!r}")
    return errors


def validate_skill() -> list[str]:
    path = ROOT / ".github" / "skills" / "calibrate-routing" / "SKILL.md"
    if not path.exists():
        return [f"{path}: missing"]
    fm = frontmatter(path.read_text(encoding="utf-8"))
    if scalar(fm, "name") != path.parent.name:
        return [f"{path}: skill name must match directory"]
    return []


def main() -> int:
    errors: list[str] = []
    agents = sorted(AGENT_DIR.glob("*.agent.md"))
    if len(agents) != 6:
        errors.append(f"expected 6 agent profiles, found {len(agents)}")
    for path in agents:
        errors.extend(validate_agent(path))
    errors.extend(validate_skill())
    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Configuration validation passed: {len(agents)} agents + routing skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
