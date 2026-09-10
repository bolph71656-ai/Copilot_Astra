#!/usr/bin/env python3
"""Generate/check model-dependent agent profiles and seed priors from one registry."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_registry import (
    MODEL_REGISTRY_PATH,
    ROLE_ORDER,
    ROLE_TITLES,
    active_model_ids,
    authority_model_id,
    load_model_registry,
    model_display_name,
    role_agent_filename,
    role_agent_name,
    select_role_model_ids,
)

AGENT_DIR = ROOT / ".github" / "agents"
TEMPLATE_DIR = ROOT / ".github" / "agent-templates"
SEED_PRIORS_PATH = ROOT / "config" / "routing-priors.json"
GATEWAY_FILENAME = "astra-gateway.agent.md"
PARENT_FILENAME = "astra-orchestrator.agent.md"


@dataclass(frozen=True)
class RoleMeta:
    tools: tuple[str, ...]
    description_prefix: str
    writable: bool = False


ROLE_META = {
    "scout": RoleMeta(("read", "search"), "Read-only repository scout"),
    "research": RoleMeta(("web", "read", "search"), "Read-only external/source researcher"),
    "execute": RoleMeta(("read", "search", "edit", "execute"), "Scoped implementation worker", True),
    "debug": RoleMeta(("read", "search", "edit", "execute"), "Root-cause debugging worker", True),
    "verify": RoleMeta(("read", "search", "execute"), "Read-only independent verifier"),
}


@dataclass(frozen=True)
class AgentSpec:
    filename: str
    name: str
    role: str
    model_id: str
    model: str
    tools: tuple[str, ...]
    writable: bool


def _replace_tokens(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace(f"<<{key}>>", value)
    if "<<" in text or ">>" in text:
        raise ValueError("unresolved agent-template token")
    return text


def gateway_model_id(registry: dict) -> str | None:
    """Return the cheapest active non-authority entry model, if one exists."""
    route = active_model_ids(registry)
    authority = authority_model_id(registry)
    return route[0] if route and route[0] != authority else None


def desired_agent_specs(registry: dict) -> list[AgentSpec]:
    specs: list[AgentSpec] = []
    for role in ROLE_ORDER:
        meta = ROLE_META[role]
        for model_id in select_role_model_ids(registry, role):
            model = registry["models"][model_id]
            specs.append(
                AgentSpec(
                    filename=role_agent_filename(registry, role, model_id),
                    name=role_agent_name(registry, role, model_id),
                    role=role,
                    model_id=model_id,
                    model=str(model["copilot_model"]),
                    tools=meta.tools,
                    writable=meta.writable,
                )
            )
    return specs


def _profile_bullets(registry: dict, specs: list[AgentSpec]) -> str:
    lines = [
        f"- Authority / integration / final acceptance -> parent on `{model_display_name(registry, authority_model_id(registry))}`"
    ]
    for spec in specs:
        guidance = registry["models"][spec.model_id]["tier_guidance"]
        lines.append(f"- `{spec.name}` -> {guidance}")
    return "\n".join(lines)


def _frontmatter_line(key: str, value) -> str:
    if isinstance(value, (list, tuple)):
        return f"{key}: {json.dumps(list(value), ensure_ascii=False)}"
    if isinstance(value, bool):
        return f"{key}: {'true' if value else 'false'}"
    return f"{key}: {value}"


def render_parent(registry: dict, specs: list[AgentSpec], *, template_dir: Path = TEMPLATE_DIR) -> str:
    authority_id = authority_model_id(registry)
    authority = registry["models"][authority_id]
    name = str(registry.get("parent_agent_name", "Astra Orchestrator"))
    description = (
        f"Registry-driven transition-aware parent coordinator using {authority['display_name']} as current authority; "
        "dispatch generated fixed-model subagents only when expected validated value exceeds orchestration cost."
    )
    front = [
        "---",
        _frontmatter_line("name", name),
        _frontmatter_line("description", json.dumps(description, ensure_ascii=False)),
        'argument-hint: "[goal] [constraints] [acceptance criteria]"',
        "target: vscode",
        _frontmatter_line("model", authority["copilot_model"]),
        _frontmatter_line("tools", ["agent", "read", "search", "edit", "execute", "todo"]),
        _frontmatter_line("agents", [spec.name for spec in specs]),
        "user-invocable: true",
        "disable-model-invocation: true",
        "---",
        "",
        "<!-- GENERATED: edit config/model-registry.json or .github/agent-templates, then run scripts/sync_model_config.py --write. -->",
        "",
    ]
    body = (template_dir / "orchestrator.md").read_text(encoding="utf-8")
    body = _replace_tokens(
        body,
        {
            "AUTHORITY_DISPLAY": str(authority["display_name"]),
            "AUTHORITY_ID": authority_id,
            "ROUTE_ORDER": " -> ".join(active_model_ids(registry)),
            "PROFILE_BULLETS": _profile_bullets(registry, specs),
        },
    )
    return "\n".join(front) + body.rstrip() + "\n"


def render_gateway(registry: dict, *, template_dir: Path = TEMPLATE_DIR) -> str | None:
    gateway_id = gateway_model_id(registry)
    if gateway_id is None:
        return None
    gateway = registry["models"][gateway_id]
    authority_id = authority_model_id(registry)
    authority = registry["models"][authority_id]
    parent_name = str(registry.get("parent_agent_name", "Astra Orchestrator"))
    description = (
        f"Fail-closed low-cost admission controller on {gateway['display_name']}; complete only obvious low-risk "
        f"machine-verifiable work, otherwise escalate intact to {parent_name}."
    )
    front = [
        "---",
        "name: Astra Gateway",
        _frontmatter_line("description", json.dumps(description, ensure_ascii=False)),
        'argument-hint: "[goal] [constraints] [acceptance criteria]"',
        "target: vscode",
        _frontmatter_line("model", gateway["copilot_model"]),
        _frontmatter_line("tools", ["agent", "read", "search", "edit", "execute", "todo"]),
        _frontmatter_line("agents", [parent_name]),
        "user-invocable: true",
        "disable-model-invocation: true",
        "---",
        "",
        "<!-- GENERATED: edit .github/agent-templates/gateway.md or config/model-registry.json, then run scripts/sync_model_config.py --write. -->",
        "",
    ]
    body = (template_dir / "gateway.md").read_text(encoding="utf-8")
    body = _replace_tokens(
        body,
        {
            "GATEWAY_DISPLAY": str(gateway["display_name"]),
            "GATEWAY_ID": gateway_id,
            "AUTHORITY_NAME": parent_name,
            "AUTHORITY_DISPLAY": str(authority["display_name"]),
        },
    )
    return "\n".join(front) + body.rstrip() + "\n"


def render_subagent(registry: dict, spec: AgentSpec, *, template_dir: Path = TEMPLATE_DIR) -> str:
    model = registry["models"][spec.model_id]
    meta = ROLE_META[spec.role]
    description = f"{meta.description_prefix} on {model['display_name']}. {model['tier_guidance']}"
    front = [
        "---",
        _frontmatter_line("name", spec.name),
        _frontmatter_line("description", json.dumps(description, ensure_ascii=False)),
        "target: vscode",
        _frontmatter_line("model", model["copilot_model"]),
        _frontmatter_line("tools", list(spec.tools)),
        "agents: []",
        "user-invocable: false",
        "disable-model-invocation: true",
        "---",
        "",
        "<!-- GENERATED: edit config/model-registry.json or .github/agent-templates, then run scripts/sync_model_config.py --write. -->",
        "",
    ]
    body = (template_dir / f"{spec.role}.md").read_text(encoding="utf-8")
    body = _replace_tokens(
        body,
        {
            "AGENT_NAME": spec.name,
            "MODEL_DISPLAY": str(model["display_name"]),
            "MODEL_ID": spec.model_id,
            "TIER_GUIDANCE": str(model["tier_guidance"]),
        },
    )
    return "\n".join(front) + body.rstrip() + "\n"


def desired_agent_files(registry: dict, *, template_dir: Path = TEMPLATE_DIR) -> dict[str, str]:
    specs = desired_agent_specs(registry)
    result = {PARENT_FILENAME: render_parent(registry, specs, template_dir=template_dir)}
    gateway = render_gateway(registry, template_dir=template_dir)
    if gateway is not None:
        result[GATEWAY_FILENAME] = gateway
    for spec in specs:
        result[spec.filename] = render_subagent(registry, spec, template_dir=template_dir)
    return result


def seed_prior_document(registry: dict) -> dict:
    entries = []
    for index, model_id in enumerate(active_model_ids(registry)):
        seed = registry["models"][model_id]["seed_prior"]
        entries.append(
            {
                "task_class": "*",
                "oracle_strength": "*",
                "model": model_id,
                "reached_after": "direct",
                "p_correct": seed["direct"]["p_correct"],
                "detection_rate": seed["direct"]["detection_rate"],
                "source_kind": "registry-seed",
                "samples": 0,
            }
        )
        if index > 0:
            entries.append(
                {
                    "task_class": "*",
                    "oracle_strength": "*",
                    "model": model_id,
                    "reached_after": "after:any",
                    "p_correct": seed["after_any"]["p_correct"],
                    "detection_rate": seed["after_any"]["detection_rate"],
                    "source_kind": "registry-seed",
                    "samples": 0,
                }
            )
    human = registry.get("human_oracle_seed", {})
    return {
        "schema_version": 1,
        "as_of": registry.get("as_of"),
        "generated_from": "config/model-registry.json",
        "purpose": "Generated low-confidence cold-start priors. Calibrated local overlays replace fields where evidence exists.",
        "entries": entries,
        "human_oracles": [
            {
                "task_class": "*",
                "human_validation_kind": "*",
                "detection_rate": human.get("detection_rate", 0.5),
                "mean_validation_seconds": human.get("mean_validation_seconds", 0.0),
                "source_kind": human.get("source_kind", "conservative-seed"),
                "samples": 0,
            }
        ],
        "notes": [
            "Generated from the active model registry; do not hand-edit seed model entries.",
            "Seed probabilities are policy assumptions, not benchmark claims.",
            "The authority model is final authority but must not be modeled as infallible.",
            "Use scripts/calibrate_routing.py --routing-priors-out config/routing-priors.local.json for local evidence overlays.",
        ],
    }


def desired_seed_priors_text(registry: dict) -> str:
    return json.dumps(seed_prior_document(registry), indent=2, ensure_ascii=False) + "\n"


def check_generated(root: Path = ROOT, registry: dict | None = None) -> list[str]:
    registry = registry or load_model_registry(root / "config" / "model-registry.json")
    template_dir = root / ".github" / "agent-templates"
    desired = desired_agent_files(registry, template_dir=template_dir)
    agent_dir = root / ".github" / "agents"
    errors: list[str] = []
    actual_names = {path.name for path in agent_dir.glob("*.agent.md")}
    desired_names = set(desired)
    for missing in sorted(desired_names - actual_names):
        errors.append(f"missing generated agent: {missing}")
    for stale in sorted(actual_names - desired_names):
        errors.append(f"stale generated agent: {stale}")
    # Existing profiles may retain richer hand-tuned bodies while the active
    # topology is unchanged. Structural/model/tool validation lives in
    # validate_config.py. `--write` is the canonical migration step when the
    # registry changes and rewrites the complete generated matrix.
    priors = root / "config" / "routing-priors.json"
    if not priors.exists() or priors.read_text(encoding="utf-8") != desired_seed_priors_text(registry):
        errors.append("generated seed priors drift: config/routing-priors.json")
    return errors


def write_generated(root: Path = ROOT, registry: dict | None = None) -> None:
    registry = registry or load_model_registry(root / "config" / "model-registry.json")
    template_dir = root / ".github" / "agent-templates"
    desired = desired_agent_files(registry, template_dir=template_dir)
    agent_dir = root / ".github" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    for path in agent_dir.glob("*.agent.md"):
        if path.name not in desired:
            path.unlink()
    for filename, content in desired.items():
        (agent_dir / filename).write_text(content, encoding="utf-8")
    (root / "config" / "routing-priors.json").write_text(desired_seed_priors_text(registry), encoding="utf-8")


def topology_summary(registry: dict) -> str:
    authority = authority_model_id(registry)
    gateway = gateway_model_id(registry)
    parent_name = str(registry.get("parent_agent_name", "Astra Orchestrator"))
    lines = [
        f"authority: {authority} ({model_display_name(registry, authority)})",
        "route: " + " -> ".join(active_model_ids(registry)),
        (
            f"gateway: {gateway} ({model_display_name(registry, gateway)}) -> {parent_name}"
            if gateway is not None
            else "gateway: disabled (authority-only topology)"
        ),
    ]
    for role in ROLE_ORDER:
        selected = select_role_model_ids(registry, role)
        labels = [role_agent_name(registry, role, model_id) for model_id in selected]
        lines.append(f"{ROLE_TITLES[role].lower()}: " + (", ".join(labels) if labels else "parent-only"))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="rewrite generated agents and seed priors")
    action.add_argument("--summary", action="store_true", help="print the active topology")
    parser.add_argument("--registry", type=Path, default=MODEL_REGISTRY_PATH)
    args = parser.parse_args()
    registry = load_model_registry(args.registry)
    if args.summary:
        print(topology_summary(registry))
        return 0
    if args.write:
        if args.registry != MODEL_REGISTRY_PATH:
            parser.error("--write only supports the repository registry")
        write_generated(ROOT, registry)
        print(topology_summary(registry))
        print("generated model-dependent files updated")
        return 0
    errors = check_generated(ROOT, registry)
    if errors:
        print("Generated model configuration is out of sync:")
        for error in errors:
            print(f"- {error}")
        print("Run: python scripts/sync_model_config.py --write")
        return 1
    print(topology_summary(registry))
    print("generated model-dependent files are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
