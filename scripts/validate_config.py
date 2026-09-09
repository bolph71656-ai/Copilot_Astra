#!/usr/bin/env python3
"""Static guardrails for the physical Copilot Astra agent matrix."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".github" / "agents"
ORCHESTRATOR = "Astra Orchestrator"
EXPECTED = {
    "astra-orchestrator.agent.md": ("Astra Orchestrator", "GPT-6 Astra (copilot)", True, True),
    "scout-luna.agent.md": ("Scout Luna", "GPT-5.6 Luna (copilot)", False, False),
    "research-luna.agent.md": ("Research Luna", "GPT-5.6 Luna (copilot)", False, False),
    "research-terra.agent.md": ("Research Terra", "GPT-5.6 Terra (copilot)", False, False),
    "execute-luna.agent.md": ("Execute Luna", "GPT-5.6 Luna (copilot)", False, True),
    "execute-terra.agent.md": ("Execute Terra", "GPT-5.6 Terra (copilot)", False, True),
    "execute-sol.agent.md": ("Execute Sol", "GPT-5.6 Sol (copilot)", False, True),
    "debug-sol.agent.md": ("Debug Sol", "GPT-5.6 Sol (copilot)", False, True),
    "verify-luna.agent.md": ("Verify Luna", "GPT-5.6 Luna (copilot)", False, False),
    "verify-terra.agent.md": ("Verify Terra", "GPT-5.6 Terra (copilot)", False, False),
    "verify-sol.agent.md": ("Verify Sol", "GPT-5.6 Sol (copilot)", False, False),
}
LEGACY = {"scout.agent.md", "researcher.agent.md", "executor.agent.md", "debugger.agent.md", "verifier.agent.md"}
SUBAGENT_NAMES = [v[0] for k, v in EXPECTED.items() if v[0] != ORCHESTRATOR]


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


def list_value(fm: str, key: str) -> list[str] | None:
    raw = scalar(fm, key)
    if raw is None:
        return None
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, list) and all(isinstance(x, str) for x in value) else None


def validate_agent(path: Path) -> tuple[list[str], str | None, str | None]:
    errors: list[str] = []
    spec = EXPECTED.get(path.name)
    if spec is None:
        return [f"{path}: unexpected physical profile"], None, None
    expected_name, expected_model, is_parent, can_edit = spec
    try:
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
    except Exception as exc:
        return [f"{path}: {exc}"], None, None

    name = scalar(fm, "name")
    description = scalar(fm, "description")
    model = scalar(fm, "model")
    tools = list_value(fm, "tools")
    agents = list_value(fm, "agents")

    if name != expected_name:
        errors.append(f"{path}: name {name!r} != {expected_name!r}")
    if model != expected_model:
        errors.append(f"{path}: model {model!r} != fixed {expected_model!r}")
    if not description:
        errors.append(f"{path}: missing description")
    if tools is None:
        errors.append(f"{path}: tools must be an explicit list")
        tools = []

    if is_parent:
        if scalar(fm, "user-invocable") != "true":
            errors.append(f"{path}: orchestrator must be user-invocable")
        if scalar(fm, "disable-model-invocation") != "true":
            errors.append(f"{path}: orchestrator must require explicit selection")
        if "agent" not in tools:
            errors.append(f"{path}: orchestrator must include agent tool")
        if agents != SUBAGENT_NAMES:
            errors.append(f"{path}: orchestrator agents list must exactly match physical matrix")
    else:
        if scalar(fm, "user-invocable") != "false":
            errors.append(f"{path}: subagent must set user-invocable: false")
        if scalar(fm, "disable-model-invocation") != "false":
            errors.append(f"{path}: subagent must remain programmatically dispatchable")
        if agents != []:
            errors.append(f"{path}: subagent must set agents: []")
        if "agent" in tools:
            errors.append(f"{path}: subagent must not include agent tool")
        if can_edit and "edit" not in tools:
            errors.append(f"{path}: writer/debugger must include edit")
        if not can_edit and "edit" in tools:
            errors.append(f"{path}: read-only profile must not include edit")

    return errors, name, description


def validate_skill() -> list[str]:
    path = ROOT / ".github" / "skills" / "calibrate-routing" / "SKILL.md"
    if not path.exists():
        return [f"{path}: missing"]
    fm = frontmatter(path.read_text(encoding="utf-8"))
    return [] if scalar(fm, "name") == path.parent.name else [f"{path}: skill name must match directory"]


def validate_context_budget() -> list[str]:
    path = ROOT / ".github" / "copilot-instructions.md"
    if not path.exists():
        return [f"{path}: missing"]
    size = len(path.read_text(encoding="utf-8"))
    return [] if size <= 2500 else [f"{path}: always-on instructions too large ({size} chars > 2500)"]


def main() -> int:
    errors: list[str] = []
    paths = sorted(AGENT_DIR.glob("*.agent.md"))
    filenames = {p.name for p in paths}
    expected_files = set(EXPECTED)

    missing = expected_files - filenames
    extra = filenames - expected_files
    if missing:
        errors.append(f"missing physical profiles: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected profiles: {sorted(extra)}")
    if LEGACY & filenames:
        errors.append(f"legacy generic profiles must be removed: {sorted(LEGACY & filenames)}")

    names: list[str] = []
    descriptions: list[str] = []
    for path in paths:
        agent_errors, name, description = validate_agent(path)
        errors.extend(agent_errors)
        if name:
            names.append(name)
        if description:
            descriptions.append(description)

    if len(names) != len(set(names)):
        errors.append("agent names must be unique")
    if len(descriptions) != len(set(descriptions)):
        errors.append("agent descriptions must be unique")

    errors.extend(validate_skill())
    errors.extend(validate_context_budget())

    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Configuration validation passed: {len(paths)} fixed-model profiles + routing skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
