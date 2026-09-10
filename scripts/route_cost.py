#!/usr/bin/env python3
"""Registry-driven transition-aware risk/cost estimator for Copilot Astra routing."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_registry import (
    MODEL_REGISTRY_PATH,
    active_model_ids,
    authority_model_id,
    load_model_registry,
    validate_route_subset,
)
from scripts.routing_core import Stage, candidate_routes, expected_route_metrics, route_options
from scripts.routing_pricing import (
    CallShape,
    PRICING,
    calls_cost,
    model_cost,
    non_negative_float,
    non_negative_int,
    probability,
)
from scripts.routing_priors import (
    DEFAULT_PRIORS_PATH,
    LOCAL_PRIORS_PATH,
    default_prior_paths,
    load_prior_bundle,
    resolve_human_oracle,
    resolve_model_prior,
)

RISK_POLICY_PATH = ROOT / "config" / "risk-policy.json"
OPERATIONAL_COSTS_PATH = ROOT / "config" / "operational-costs.json"
REGISTRY = load_model_registry(MODEL_REGISTRY_PATH)


def parse_ladder(value: str):
    stages = []
    seen = set()
    for raw in value.split(","):
        if not raw.strip():
            continue
        parts = [part.strip() for part in raw.split(":")]
        if len(parts) not in {2, 3}:
            raise argparse.ArgumentTypeError("ladder entries must be model:p_correct[:detection_rate]")
        model = parts[0].lower()
        if model not in PRICING:
            raise argparse.ArgumentTypeError(f"unknown model in ladder: {model}")
        if model in seen:
            raise argparse.ArgumentTypeError(f"duplicate model in ladder: {model}")
        seen.add(model)
        stages.append(
            (
                model,
                probability(parts[1]),
                probability(parts[2]) if len(parts) == 3 else 1.0,
            )
        )
    if not stages:
        raise argparse.ArgumentTypeError("ladder must contain at least one stage")
    try:
        validate_route_subset(REGISTRY, [model for model, _, _ in stages])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return stages


def parse_models(value: str, *, registry: dict = REGISTRY) -> list[str]:
    models = [part.strip().lower() for part in value.split(",") if part.strip()]
    validate_route_subset(registry, models)
    return models


def cheap_first_success_threshold(cheap_cost: float, expensive_cost: float):
    return None if expensive_cost <= 0 else cheap_cost / expensive_cost


def parse_latency(value: str):
    out = {}
    if not value:
        return out
    for raw in value.split(","):
        model, seconds = raw.split(":", 1)
        model = model.strip().lower()
        if model not in PRICING:
            raise argparse.ArgumentTypeError(f"unknown latency model: {model}")
        out[model] = non_negative_float(seconds)
    return out


def load_risk_policy(path: Path = RISK_POLICY_PATH):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported risk-policy schema")
    return raw


def load_operational_costs(path: Path = OPERATIONAL_COSTS_PATH) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported operational-costs schema")
    defaults = raw.get("defaults")
    defect = raw.get("defect_penalty_units_by_risk")
    if not isinstance(defaults, dict) or not isinstance(defect, dict):
        raise ValueError("operational-costs requires defaults and defect_penalty_units_by_risk")
    for key in ("dispatch_units", "handoff_units", "failure_penalty_units", "latency_weight"):
        defaults[key] = non_negative_float(str(defaults.get(key)))
    for key, value in list(defect.items()):
        defect[key] = non_negative_float(str(value))
    return raw


def resolve_risk_constraints(args):
    policy = load_risk_policy()
    name = getattr(args, "risk_class", None) or policy.get("default_class", "standard")
    if name not in policy["classes"]:
        raise ValueError(f"unknown risk class: {name}")
    out = dict(policy["classes"][name])
    for key in ("max_hidden_failure", "max_terminal_failure", "min_validated_correct"):
        value = getattr(args, key, None)
        if value is not None:
            out[key] = value
    return {"risk_class": name, **out}


def resolve_operational_costs(args, *, risk_class: str) -> dict:
    cfg = load_operational_costs()
    defaults = cfg["defaults"]

    def choose(attr: str, default_key: str) -> tuple[float, str]:
        value = getattr(args, attr, None)
        if value is not None:
            return float(value), "cli"
        return float(defaults[default_key]), "config"

    dispatch, dispatch_source = choose("dispatch_units", "dispatch_units")
    handoff, handoff_source = choose("handoff_units", "handoff_units")
    failure, failure_source = choose("failure_penalty", "failure_penalty_units")
    latency_weight, latency_source = choose("latency_weight", "latency_weight")
    if getattr(args, "defect_penalty", None) is not None:
        defect = float(args.defect_penalty)
        defect_source = "cli"
    else:
        by_risk = cfg["defect_penalty_units_by_risk"]
        if risk_class not in by_risk:
            raise ValueError(f"operational-costs missing defect penalty for risk class {risk_class!r}")
        defect = float(by_risk[risk_class])
        defect_source = "config"
    return {
        "dispatch_units": dispatch,
        "handoff_units": handoff,
        "failure_penalty_units": failure,
        "defect_penalty_units": defect,
        "latency_weight": latency_weight,
        "source_kind": cfg.get("source_kind", "unknown"),
        "measured": bool(cfg.get("measured", False)),
        "sources": {
            "dispatch_units": dispatch_source,
            "handoff_units": handoff_source,
            "failure_penalty_units": failure_source,
            "defect_penalty_units": defect_source,
            "latency_weight": latency_source,
        },
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("fresh-input", "cached-input", "cache-write", "output"):
        parser.add_argument("--" + flag, type=non_negative_int, default=0)
    parser.add_argument("--context-tokens", type=non_negative_int, default=None)
    parser.add_argument("--tier", default="auto", help="auto or a pricing tier name present for every selected model")
    parser.add_argument("--ladder", type=parse_ladder, default=None)
    parser.add_argument(
        "--models",
        default=None,
        help="optional monotone subset of the active registry route; must end in the configured authority model",
    )
    parser.add_argument("--task-class", default="default")
    parser.add_argument("--oracle-strength", default="mixed")
    parser.add_argument("--priors", type=Path, action="append", default=[])
    parser.add_argument("--risk-class", default=None)
    parser.add_argument("--max-hidden-failure", type=probability, default=None)
    parser.add_argument("--max-terminal-failure", type=probability, default=None)
    parser.add_argument("--min-validated-correct", type=probability, default=None)
    parser.add_argument("--dispatch-units", type=non_negative_float, default=None)
    parser.add_argument("--handoff-units", type=non_negative_float, default=None)
    parser.add_argument("--failure-penalty", type=non_negative_float, default=None)
    parser.add_argument("--defect-penalty", type=non_negative_float, default=None)
    parser.add_argument("--latency-weight", type=non_negative_float, default=None)
    parser.add_argument("--latency", type=parse_latency, default={})
    parser.add_argument("--human-validation-required", action="store_true")
    parser.add_argument("--human-validation-kind", default="default")
    parser.add_argument("--human-detection-rate", type=probability, default=None)
    parser.add_argument("--human-validation-units", type=non_negative_float, default=0)
    parser.add_argument("--human-validation-seconds", type=non_negative_float, default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def _selected_models(args) -> list[str]:
    if args.ladder is not None:
        models = [model for model, _, _ in args.ladder]
        validate_route_subset(REGISTRY, models)
        return models
    if getattr(args, "models", None):
        return parse_models(args.models)
    return active_model_ids(REGISTRY)


def evaluate(args):
    selected_models = _selected_models(args)
    missing_pricing = [model for model in selected_models if model not in PRICING]
    if missing_pricing:
        raise ValueError(f"active route models missing pricing: {missing_pricing}")

    costs = {}
    for model in selected_models:
        units, selected_tier = model_cost(
            model,
            args.fresh_input,
            args.cached_input,
            args.cache_write,
            args.output,
            tier=args.tier,
            context_tokens=args.context_tokens,
        )
        costs[model] = {"units": units, "usd": units / 100, "tier": selected_tier}

    bundle = None
    entries = None
    if args.ladder is not None:
        stages = [
            Stage(model, costs[model]["units"], p_correct, detection_rate, args.latency.get(model, 0))
            for model, p_correct, detection_rate in args.ladder
        ]
    else:
        bundle = load_prior_bundle(default_prior_paths(args.priors))
        entries = bundle["entries"]
        stages = [Stage(model, costs[model]["units"], latency_seconds=args.latency.get(model, 0)) for model in selected_models]

    human_detection = 0 if args.human_detection_rate is None else args.human_detection_rate
    human_seconds = 0 if args.human_validation_seconds is None else args.human_validation_seconds
    human_prior = None
    if args.human_validation_required and args.human_detection_rate is None:
        bundle = bundle or load_prior_bundle(default_prior_paths(args.priors))
        human_prior = resolve_human_oracle(
            bundle["human_oracles"],
            task_class=args.task_class,
            validation_kind=args.human_validation_kind,
        )
        human_detection = human_prior["detection_rate"]
        if args.human_validation_seconds is None:
            human_seconds = human_prior.get("mean_validation_seconds", 0)

    risk = resolve_risk_constraints(args)
    operational = resolve_operational_costs(args, risk_class=risk["risk_class"])
    options, best = route_options(
        stages,
        prior_entries=entries,
        task_class=args.task_class,
        oracle_strength=args.oracle_strength,
        dispatch_units=operational["dispatch_units"],
        handoff_units=operational["handoff_units"],
        failure_penalty_units=operational["failure_penalty_units"],
        defect_penalty_units=operational["defect_penalty_units"],
        latency_weight=operational["latency_weight"],
        max_hidden_failure=risk["max_hidden_failure"],
        max_terminal_failure=risk["max_terminal_failure"],
        min_validated_correct=risk["min_validated_correct"],
        human_validation_required=args.human_validation_required,
        human_detection_rate=human_detection,
        human_validation_units=args.human_validation_units,
        human_validation_seconds=human_seconds,
    )
    return {
        "models": costs,
        "model_registry": {
            "authority_model": authority_model_id(REGISTRY),
            "active_route": active_model_ids(REGISTRY),
            "evaluated_route": selected_models,
        },
        "routing_context": {"task_class": args.task_class, "oracle_strength": args.oracle_strength, **risk},
        "operational_costs": operational,
        "human_validation": {
            "required": args.human_validation_required,
            "kind": args.human_validation_kind,
            "detection_rate": human_detection,
            "validation_units": args.human_validation_units,
            "validation_seconds": human_seconds,
            "prior": human_prior,
        },
        "start_options": options,
        "recommended_route": best,
    }


def main():
    args = build_parser().parse_args()
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    registry = result["model_registry"]
    context = result["routing_context"]
    operational = result["operational_costs"]
    print(
        f"authority={registry['authority_model']} active={' -> '.join(registry['active_route'])} "
        f"evaluated={' -> '.join(registry['evaluated_route'])}"
    )
    print(f"risk={context['risk_class']} task={context['task_class']} oracle={context['oracle_strength']}")
    print(
        "operational-costs="
        f"{operational['source_kind']} measured={operational['measured']} "
        f"dispatch={operational['dispatch_units']} handoff={operational['handoff_units']} "
        f"failure={operational['failure_penalty_units']} defect={operational['defect_penalty_units']}"
    )
    print("Candidate routes")
    for option in result["start_options"]:
        suffix = "" if option["viable"] else " [rejected: " + ",".join(option["rejection_reasons"]) + "]"
        print(
            f"{' -> '.join(option['path']):<36} "
            f"correct={option['validated_correct_probability']:.4%} "
            f"hidden={option['hidden_failure_probability']:.4%} "
            f"terminal={option['terminal_detected_failure_probability']:.4%} "
            f"score={option['risk_adjusted_units_per_correct']}{suffix}"
        )
    best = result["recommended_route"]
    print("recommended route:", " -> ".join(best["path"]) if best else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
