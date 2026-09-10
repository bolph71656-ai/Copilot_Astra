#!/usr/bin/env python3
"""Static guardrails for registry-driven agents, pricing, priors, risk policy, and local validation."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_registry import (
    ROLE_ORDER,
    active_model_ids,
    authority_model_id,
    load_model_registry,
)
from scripts.routing_pricing import _load as load_pricing
from scripts.sync_model_config import (
    GATEWAY_FILENAME,
    PARENT_FILENAME,
    check_generated,
    desired_agent_specs,
    gateway_model_id,
)

AGENT_DIR = ROOT / ".github" / "agents"


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
    return value if isinstance(value, list) and all(isinstance(item, str) for item in value) else None


def validate_agents(registry: dict) -> list[str]:
    errors = check_generated(ROOT, registry)
    specs = desired_agent_specs(registry)
    by_filename = {spec.filename: spec for spec in specs}
    parent_name = str(registry.get("parent_agent_name", "Astra Orchestrator"))

    parent_path = AGENT_DIR / PARENT_FILENAME
    if not parent_path.exists():
        return errors + ["missing parent agent"]
    parent_text = parent_path.read_text(encoding="utf-8")
    parent_fm = frontmatter(parent_text)
    if scalar(parent_fm, "target") != "vscode":
        errors.append("parent target must be vscode")
    if scalar(parent_fm, "model") != registry["models"][authority_model_id(registry)]["copilot_model"]:
        errors.append("parent model must match registry authority model")
    if list_value(parent_fm, "agents") != [spec.name for spec in specs]:
        errors.append("parent generated allowlist mismatch")
    parent_tools = list_value(parent_fm, "tools") or []
    if "agent" not in parent_tools:
        errors.append("parent missing agent tool")
    if scalar(parent_fm, "user-invocable") != "true" or scalar(parent_fm, "disable-model-invocation") != "true":
        errors.append("parent invocation controls invalid")

    gateway_id = gateway_model_id(registry)
    gateway_path = AGENT_DIR / GATEWAY_FILENAME
    if gateway_id is None:
        if gateway_path.exists():
            errors.append("gateway must be absent for authority-only topology")
    elif not gateway_path.exists():
        errors.append("missing generated gateway")
    else:
        gateway_text = gateway_path.read_text(encoding="utf-8")
        gateway_fm = frontmatter(gateway_text)
        if scalar(gateway_fm, "name") != "Astra Gateway":
            errors.append("gateway generated name mismatch")
        if scalar(gateway_fm, "target") != "vscode":
            errors.append("gateway target must be vscode")
        if scalar(gateway_fm, "model") != registry["models"][gateway_id]["copilot_model"]:
            errors.append("gateway model must match lowest active non-authority model")
        if list_value(gateway_fm, "agents") != [parent_name]:
            errors.append("gateway may only allowlist the authority parent")
        gateway_tools = list_value(gateway_fm, "tools") or []
        if "agent" not in gateway_tools:
            errors.append("gateway missing agent tool")
        if scalar(gateway_fm, "user-invocable") != "true" or scalar(gateway_fm, "disable-model-invocation") != "true":
            errors.append("gateway invocation controls invalid")
        if "fail-closed" not in gateway_text.lower():
            errors.append("gateway must document fail-closed behavior")

    for path in AGENT_DIR.glob("*.agent.md"):
        if path.name in {PARENT_FILENAME, GATEWAY_FILENAME}:
            continue
        spec = by_filename.get(path.name)
        if spec is None:
            errors.append(f"unexpected generated subagent {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if scalar(fm, "name") != spec.name:
            errors.append(f"{path.name}: wrong generated name")
        if scalar(fm, "model") != spec.model:
            errors.append(f"{path.name}: wrong generated model")
        if scalar(fm, "target") != "vscode":
            errors.append(f"{path.name}: target must be vscode")
        if list_value(fm, "agents") != []:
            errors.append(f"{path.name}: agents must be []")
        tools = list_value(fm, "tools") or []
        if "agent" in tools:
            errors.append(f"{path.name}: recursive agent tool forbidden")
        if scalar(fm, "user-invocable") != "false" or scalar(fm, "disable-model-invocation") != "true":
            errors.append(f"{path.name}: invocation controls invalid")
        if spec.writable != ("edit" in tools):
            errors.append(f"{path.name}: edit capability does not match role")
    return errors


def validate_pricing(registry: dict) -> list[str]:
    path = ROOT / "config" / "pricing.json"
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") not in {1, 2}:
        errors.append(f"{path}: unsupported schema_version")
    for key in ("as_of", "source_url", "source_checked_at", "source_policy"):
        if not data.get(key):
            errors.append(f"{path}: missing {key}")
    try:
        pricing = load_pricing(path)
    except Exception as exc:
        return errors + [f"{path}: {exc}"]
    for model_id in active_model_ids(registry):
        if model_id not in pricing:
            errors.append(f"{path}: active model {model_id!r} missing pricing")
    for model_id, spec in pricing.items():
        previous = -1
        for tier in spec.tiers:
            if tier.min_context_tokens <= previous:
                errors.append(f"{path}: {model_id} tier thresholds must strictly increase")
            previous = tier.min_context_tokens
            for key in ("fresh_input", "cached_input", "cache_write", "output"):
                if getattr(tier.rates, key) < 0:
                    errors.append(f"{path}: {model_id}.{tier.name}.{key} must be non-negative")
    return errors


def validate_priors(registry: dict) -> list[str]:
    path = ROOT / "config" / "routing-priors.json"
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + [f"{path}: entries must be non-empty"]
    active = active_model_ids(registry)
    direct = set()
    after = set()
    for row in entries:
        model_id = row.get("model")
        if model_id not in active:
            errors.append(f"{path}: seed prior for inactive/unknown model {model_id!r}")
        reached = str(row.get("reached_after", ""))
        if reached == "direct":
            direct.add(model_id)
        if reached == "after:any":
            after.add(model_id)
        for key in ("p_correct", "detection_rate"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"{path}: invalid {model_id}.{key}")
    if direct != set(active):
        errors.append(f"{path}: every active model needs exactly a direct seed prior")
    if after != set(active[1:]):
        errors.append(f"{path}: every non-first active model needs an after:any seed prior")
    authority = authority_model_id(registry)
    authority_rows = [row for row in entries if row.get("model") == authority]
    if any(row.get("p_correct") == 1 for row in authority_rows):
        errors.append(f"{path}: authority model must not be modeled as infallible")
    if not data.get("human_oracles"):
        errors.append(f"{path}: human oracle fallback required")
    return errors


def validate_risk_policy() -> list[str]:
    path = ROOT / "config" / "risk-policy.json"
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    classes = data.get("classes", {})
    if data.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    if data.get("default_class") not in classes:
        errors.append(f"{path}: default_class missing from classes")
    for name, row in classes.items():
        for key in ("max_hidden_failure", "max_terminal_failure", "min_validated_correct"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"{path}: {name}.{key} invalid")
    return errors


def validate_fixtures() -> list[str]:
    path = ROOT / "config" / "routing-fixtures.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        return [f"{path}: expected non-empty list"]
    errors: list[str] = []
    names = []
    has_human = False
    has_transition = False
    has_two = False
    has_three = False
    for row in rows:
        names.append(row.get("name"))
        stages = row.get("stages")
        expected = row.get("expected_path")
        if not isinstance(stages, list) or not stages:
            errors.append(f"{path}: fixture missing stages")
            continue
        models = [str(stage.get("model", "")) for stage in stages]
        if any(not model for model in models) or len(models) != len(set(models)):
            errors.append(f"{path}: fixture stage models must be non-empty and unique")
        terminal = models[-1]
        if not isinstance(expected, list) or not expected or expected[-1] != terminal:
            errors.append(f"{path}: expected_path must end in fixture terminal model")
        if len(models) == 2:
            has_two = True
        if len(models) == 3:
            has_three = True
        if row.get("human_validation_required"):
            has_human = True
        if row.get("prior_entries"):
            has_transition = True
            if any(item.get("model") not in models for item in row["prior_entries"]):
                errors.append(f"{path}: prior_entries must reference fixture stage models")
        for stage in stages:
            if stage.get("model") == terminal and stage.get("p_correct") == 1.0:
                errors.append(f"{path}: static terminal fixture must not use p_correct=1")
    if len(names) != len(set(names)):
        errors.append(f"{path}: fixture names must be unique")
    if not has_human:
        errors.append(f"{path}: human validation fixture required")
    if not has_transition:
        errors.append(f"{path}: transition-aware fixture required")
    if not has_two or not has_three:
        errors.append(f"{path}: explicit two-model and three-model topology fixtures are required")
    return errors


def validate_docs_and_ignore() -> list[str]:
    errors: list[str] = []
    required = [
        ROOT / "docs" / "research" / "2026-09-09-deep-routing-research.md",
        ROOT / "docs" / "research" / "2026-09-10-routing-review.md",
        ROOT / "docs" / "adr" / "0001-risk-aware-routing.md",
        ROOT / "docs" / "adr" / "0002-local-validation-no-github-actions.md",
        ROOT / "docs" / "adr" / "0003-human-validation-as-oracle.md",
        ROOT / "docs" / "adr" / "0004-transition-aware-empirical-routing.md",
        ROOT / "docs" / "adr" / "0005-registry-driven-model-topology.md",
        ROOT / "docs" / "model-registry.md",
        ROOT / "docs" / "human-device-validation.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"{path}: missing")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    if "config/routing-priors.local.json" not in ignore:
        errors.append(".gitignore must ignore config/routing-priors.local.json")
    return errors


def main() -> int:
    errors: list[str] = []
    try:
        registry = load_model_registry(ROOT / "config" / "model-registry.json")
    except Exception as exc:
        print(f"Configuration validation failed:\n- model-registry: {exc}")
        return 1
    errors += validate_agents(registry)
    errors += validate_pricing(registry)
    errors += validate_priors(registry)
    errors += validate_risk_policy()
    errors += validate_fixtures()
    errors += validate_docs_and_ignore()
    skill = ROOT / ".github" / "skills" / "calibrate-routing" / "SKILL.md"
    if not skill.exists() or scalar(frontmatter(skill.read_text(encoding="utf-8")), "name") != skill.parent.name:
        errors.append("routing skill invalid")
    instructions = ROOT / ".github" / "copilot-instructions.md"
    if not instructions.exists() or len(instructions.read_text(encoding="utf-8")) > 3000:
        errors.append("always-on instructions missing/too large")
    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    profile_count = 1 + len(desired_agent_specs(registry)) + (1 if gateway_model_id(registry) is not None else 0)
    print(
        "Configuration validation passed: "
        f"{len(active_model_ids(registry))} active models, "
        f"{profile_count} generated VS Code profiles, "
        "fail-closed gateway + transition-aware priors + risk policy"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
