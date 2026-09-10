from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
MODEL_REGISTRY_PATH = ROOT / "config" / "model-registry.json"
ROLE_ORDER = ("scout", "research", "execute", "debug", "verify")
ROLE_TITLES = {
    "scout": "Scout",
    "research": "Research",
    "execute": "Execute",
    "debug": "Debug",
    "verify": "Verify",
}
VALID_SLOTS = {"all", "lowest", "middle", "highest"}
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def probability(value, *, label: str) -> float:
    result = float(value)
    if not 0 <= result <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def validate_registry(data: dict) -> dict:
    if data.get("schema_version") != 1:
        raise ValueError("unsupported model-registry schema")
    models = data.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("model-registry models must be a non-empty object")
    for model_id, spec in models.items():
        if not MODEL_ID_RE.match(model_id):
            raise ValueError(f"invalid model id: {model_id!r}")
        for key in ("display_name", "copilot_model", "tier_guidance", "capability_rank", "seed_prior"):
            if key not in spec:
                raise ValueError(f"model {model_id}: missing {key}")
        if not isinstance(spec["capability_rank"], (int, float)):
            raise ValueError(f"model {model_id}: capability_rank must be numeric")
        seed = spec["seed_prior"]
        for state in ("direct", "after_any"):
            if state not in seed:
                raise ValueError(f"model {model_id}: missing seed_prior.{state}")
            probability(seed[state].get("p_correct"), label=f"{model_id}.{state}.p_correct")
            probability(seed[state].get("detection_rate"), label=f"{model_id}.{state}.detection_rate")

    route = data.get("route_order")
    if not isinstance(route, list) or not route or len(route) != len(set(route)):
        raise ValueError("route_order must be a non-empty unique list")
    if any(model_id not in models for model_id in route):
        raise ValueError("route_order references unknown model")
    authority = data.get("authority_model")
    if authority not in models or authority != route[-1]:
        raise ValueError("authority_model must exist and be the final route_order model")
    ranks = [models[model_id]["capability_rank"] for model_id in route]
    if any(left >= right for left, right in zip(ranks, ranks[1:])):
        raise ValueError("route_order capability_rank values must be strictly increasing")

    policies = data.get("role_policies")
    if not isinstance(policies, dict) or set(policies) != set(ROLE_ORDER):
        raise ValueError(f"role_policies must define exactly {list(ROLE_ORDER)}")
    for role, policy in policies.items():
        slots = policy.get("slots")
        if not isinstance(slots, list) or not slots or any(slot not in VALID_SLOTS for slot in slots):
            raise ValueError(f"role {role}: invalid slots")
        if "all" in slots and len(slots) != 1:
            raise ValueError(f"role {role}: all must be the only slot")
        minimum_workers = policy.get("min_worker_count", 1)
        if not isinstance(minimum_workers, int) or minimum_workers < 0:
            raise ValueError(f"role {role}: min_worker_count must be a non-negative integer")

    human = data.get("human_oracle_seed", {})
    probability(human.get("detection_rate", 0.5), label="human_oracle_seed.detection_rate")
    if float(human.get("mean_validation_seconds", 0)) < 0:
        raise ValueError("human_oracle_seed.mean_validation_seconds must be non-negative")
    return data


def load_model_registry(path: Path = MODEL_REGISTRY_PATH) -> dict:
    return validate_registry(json.loads(path.read_text(encoding="utf-8")))


def active_model_ids(registry: dict) -> list[str]:
    return list(registry["route_order"])


def authority_model_id(registry: dict) -> str:
    return str(registry["authority_model"])


def worker_model_ids(registry: dict) -> list[str]:
    authority = authority_model_id(registry)
    return [model_id for model_id in active_model_ids(registry) if model_id != authority]


def model_display_name(registry: dict, model_id: str) -> str:
    return str(registry["models"][model_id]["display_name"])


def model_agent_suffix(registry: dict, model_id: str) -> str:
    # File ids are intentionally stable even when display names change.
    return model_id


def _slot_values(eligible: list[str], slot: str) -> Iterable[str]:
    if not eligible:
        return []
    if slot == "all":
        return eligible
    if slot == "lowest":
        return [eligible[0]]
    if slot == "highest":
        return [eligible[-1]]
    if slot == "middle":
        return [eligible[len(eligible) // 2]]
    raise ValueError(f"unsupported role slot: {slot}")


def select_role_model_ids(registry: dict, role: str) -> list[str]:
    policy = registry["role_policies"][role]
    workers = worker_model_ids(registry)
    if len(workers) < int(policy.get("min_worker_count", 1)):
        return []
    eligible = workers
    selected: list[str] = []
    for slot in policy["slots"]:
        for model_id in _slot_values(eligible, slot):
            if model_id not in selected:
                selected.append(model_id)
    return selected


def role_agent_name(registry: dict, role: str, model_id: str) -> str:
    return f"{ROLE_TITLES[role]} {model_display_name(registry, model_id)}"


def role_agent_filename(registry: dict, role: str, model_id: str) -> str:
    return f"{role}-{model_agent_suffix(registry, model_id)}.agent.md"


def validate_route_subset(registry: dict, route: list[str]) -> None:
    active = active_model_ids(registry)
    if not route or len(route) != len(set(route)):
        raise ValueError("route must contain unique model ids")
    if route[-1] != authority_model_id(registry):
        raise ValueError(f"route must end in authority model {authority_model_id(registry)!r}")
    positions = []
    for model_id in route:
        if model_id not in active:
            raise ValueError(f"route model {model_id!r} is not active in model-registry")
        positions.append(active.index(model_id))
    if positions != sorted(positions):
        raise ValueError("route must preserve model-registry capability order")
