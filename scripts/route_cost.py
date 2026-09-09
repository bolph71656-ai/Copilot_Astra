#!/usr/bin/env python3
"""Risk-aware cost estimator for Copilot Astra routing."""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
PRICING_PATH = ROOT / "config" / "pricing.json"


@dataclass(frozen=True)
class Rates:
    fresh_input: float
    cached_input: float
    cache_write: float
    output: float


@dataclass(frozen=True)
class ModelPricing:
    default: Rates
    long: Rates
    long_threshold: int


@dataclass(frozen=True)
class CallShape:
    fresh_input: int = 0
    cached_input: int = 0
    cache_write: int = 0
    output: int = 0
    context_tokens: int | None = None


@dataclass(frozen=True)
class Stage:
    model: str
    cost: float
    p_correct: float
    detection_rate: float = 1.0
    latency_seconds: float = 0.0
    human_detection_rate: float | None = None


def _load_pricing() -> dict[str, ModelPricing]:
    raw = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    return {
        model: ModelPricing(
            Rates(**spec["default"]),
            Rates(**spec["long"]),
            int(spec["long_threshold"]),
        )
        for model, spec in raw["models"].items()
    }


PRICING = _load_pricing()


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def probability(value: str | float) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("probability must be between 0 and 1")
    return parsed


def tier_for(model: str, requested: str, context_tokens: int) -> str:
    if requested in {"default", "long"}:
        return requested
    return "long" if context_tokens > PRICING[model].long_threshold else "default"


def model_cost(
    model: str,
    fresh_input: int,
    cached_input: int,
    cache_write: int,
    output: int,
    *,
    tier: str = "auto",
    context_tokens: int | None = None,
) -> tuple[float, str]:
    if model not in PRICING:
        raise ValueError(f"unknown model: {model}")
    context = fresh_input + cached_input if context_tokens is None else context_tokens
    selected = tier_for(model, tier, context)
    rates = getattr(PRICING[model], selected)
    units = (
        fresh_input * rates.fresh_input
        + cached_input * rates.cached_input
        + cache_write * rates.cache_write
        + output * rates.output
    ) / 1_000_000
    return units, selected


def calls_cost(model: str, calls: Sequence[CallShape], *, tier: str = "auto") -> tuple[float, list[str]]:
    total = 0.0
    tiers: list[str] = []
    for call in calls:
        cost, selected = model_cost(
            model,
            call.fresh_input,
            call.cached_input,
            call.cache_write,
            call.output,
            tier=tier,
            context_tokens=call.context_tokens,
        )
        total += cost
        tiers.append(selected)
    return total, tiers


def parse_ladder(value: str) -> list[tuple[str, float, float]]:
    stages: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    for raw in value.split(","):
        if not raw.strip():
            continue
        parts = [part.strip() for part in raw.split(":")]
        if len(parts) not in {2, 3}:
            raise argparse.ArgumentTypeError(
                "ladder entries must be model:p_correct[:detection_rate]"
            )
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
    return stages


def expected_route_metrics(
    stages: Iterable[Stage],
    *,
    handoff_units: float = 0.0,
    failure_penalty_units: float = 0.0,
    dispatch_units: float = 0.0,
    defect_penalty_units: float = 0.0,
    latency_weight: float = 0.0,
    human_validation_required: bool = False,
    human_detection_rate: float = 0.0,
    human_validation_units: float = 0.0,
    human_validation_seconds: float = 0.0,
) -> dict:
    """Evaluate one escalation route.

    `detection_rate` is the automatic failure-detection oracle. If human
    validation is required, a candidate that survives automatic checks is
    presented to the human/device oracle. A human-detected defect escalates;
    a missed defect becomes hidden failure. Human validation is therefore
    neither success nor failure by itself: it is a second oracle with explicit
    cost and latency.
    """
    sequence = list(stages)
    if not sequence:
        raise ValueError("route must contain at least one stage")

    reach = 1.0
    cost = dispatch_units if sequence[0].model != "astra" else 0.0
    latency = 0.0
    correct = 0.0
    hidden = 0.0
    pre_human_hidden = 0.0
    terminal_detected = 0.0
    human_detected_total = 0.0
    expected_human_validations = 0.0

    for index, stage in enumerate(sequence):
        cost += reach * stage.cost
        latency += reach * stage.latency_seconds

        ok = reach * stage.p_correct
        bad = reach * (1.0 - stage.p_correct)
        auto_detected = bad * stage.detection_rate
        auto_escaped = bad * (1.0 - stage.detection_rate)
        pre_human_hidden += auto_escaped

        if human_validation_required:
            stage_human_detection = (
                human_detection_rate
                if stage.human_detection_rate is None
                else stage.human_detection_rate
            )
            human_checks = ok + auto_escaped
            expected_human_validations += human_checks
            cost += human_checks * human_validation_units
            latency += human_checks * human_validation_seconds

            human_detected = auto_escaped * stage_human_detection
            escaped = auto_escaped * (1.0 - stage_human_detection)
        else:
            human_detected = 0.0
            escaped = auto_escaped

        correct += ok
        hidden += escaped
        human_detected_total += human_detected
        detected = auto_detected + human_detected

        if index < len(sequence) - 1:
            cost += detected * (failure_penalty_units + handoff_units)
            reach = detected
        else:
            terminal_detected = detected
            reach = 0.0

    adjusted = cost + defect_penalty_units * hidden + latency_weight * latency
    return {
        "expected_units": cost,
        "expected_latency_seconds": latency,
        "validated_correct_probability": correct,
        "pre_human_hidden_failure_probability": pre_human_hidden,
        "hidden_failure_probability": hidden,
        "human_detected_failure_probability": human_detected_total,
        "expected_human_validations": expected_human_validations,
        "terminal_detected_failure_probability": terminal_detected,
        "risk_adjusted_units": adjusted,
        "risk_adjusted_units_per_correct": adjusted / correct if correct > 0 else None,
    }


def candidate_routes(stages: Sequence[Stage]) -> list[list[Stage]]:
    if not stages:
        return []
    if len(stages) == 1:
        return [list(stages)]
    final = stages[-1]
    prefix = list(stages[:-1])
    routes: list[list[Stage]] = []
    for size in range(len(prefix) + 1):
        for combo in itertools.combinations(prefix, size):
            routes.append(list(combo) + [final])
    rank = {stage.model: index for index, stage in enumerate(stages)}
    routes.sort(key=lambda route: (rank[route[0].model], len(route), [rank[s.model] for s in route]))
    return routes


def route_options(
    stages: Sequence[Stage],
    *,
    dispatch_units: float = 0.0,
    handoff_units: float = 0.0,
    failure_penalty_units: float = 0.0,
    defect_penalty_units: float = 0.0,
    latency_weight: float = 0.0,
    max_hidden_failure: float = 1.0,
    human_validation_required: bool = False,
    human_detection_rate: float = 0.0,
    human_validation_units: float = 0.0,
    human_validation_seconds: float = 0.0,
) -> tuple[list[dict], dict | None]:
    options: list[dict] = []
    for route in candidate_routes(stages):
        metrics = expected_route_metrics(
            route,
            dispatch_units=dispatch_units,
            handoff_units=handoff_units,
            failure_penalty_units=failure_penalty_units,
            defect_penalty_units=defect_penalty_units,
            latency_weight=latency_weight,
            human_validation_required=human_validation_required,
            human_detection_rate=human_detection_rate,
            human_validation_units=human_validation_units,
            human_validation_seconds=human_validation_seconds,
        )
        viable = metrics["hidden_failure_probability"] <= max_hidden_failure
        options.append(
            {
                "start_model": route[0].model,
                "path": [stage.model for stage in route],
                "viable": viable,
                **metrics,
            }
        )
    viable = [
        option
        for option in options
        if option["viable"] and option["risk_adjusted_units_per_correct"] is not None
    ]
    best = min(viable, key=lambda option: option["risk_adjusted_units_per_correct"]) if viable else None
    return options, best


def cheap_first_success_threshold(cheap_cost: float, expensive_cost: float) -> float | None:
    return None if expensive_cost <= 0 else cheap_cost / expensive_cost


def parse_latency(value: str) -> dict[str, float]:
    out: dict[str, float] = {}
    if not value:
        return out
    for raw in value.split(","):
        model, seconds = raw.split(":", 1)
        model = model.strip().lower()
        if model not in PRICING:
            raise argparse.ArgumentTypeError(f"unknown latency model: {model}")
        out[model] = non_negative_float(seconds)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-input", type=non_negative_int, default=0)
    parser.add_argument("--cached-input", type=non_negative_int, default=0)
    parser.add_argument("--cache-write", type=non_negative_int, default=0)
    parser.add_argument("--output", type=non_negative_int, default=0)
    parser.add_argument("--context-tokens", type=non_negative_int, default=None)
    parser.add_argument("--tier", choices=("auto", "default", "long"), default="auto")
    parser.add_argument(
        "--ladder",
        type=parse_ladder,
        default=parse_ladder(
            "luna:0.80:0.99,terra:0.95:0.99,sol:0.99:0.995,astra:1:1"
        ),
    )
    parser.add_argument("--dispatch-units", type=non_negative_float, default=0.0)
    parser.add_argument("--handoff-units", type=non_negative_float, default=0.0)
    parser.add_argument("--failure-penalty", type=non_negative_float, default=0.0)
    parser.add_argument("--defect-penalty", type=non_negative_float, default=0.0)
    parser.add_argument("--max-hidden-failure", type=probability, default=1.0)
    parser.add_argument("--latency-weight", type=non_negative_float, default=0.0)
    parser.add_argument("--latency", type=parse_latency, default={})
    parser.add_argument("--human-validation-required", action="store_true")
    parser.add_argument("--human-detection-rate", type=probability, default=0.0)
    parser.add_argument("--human-validation-units", type=non_negative_float, default=0.0)
    parser.add_argument("--human-validation-seconds", type=non_negative_float, default=0.0)
    parser.add_argument("--json", action="store_true")
    return parser


def evaluate(args: argparse.Namespace) -> dict:
    costs = {}
    for model in PRICING:
        units, selected = model_cost(
            model,
            args.fresh_input,
            args.cached_input,
            args.cache_write,
            args.output,
            tier=args.tier,
            context_tokens=args.context_tokens,
        )
        costs[model] = {"units": units, "usd": units / 100, "tier": selected}

    stages = [
        Stage(
            model,
            costs[model]["units"],
            p_correct,
            detection_rate,
            args.latency.get(model, 0.0),
        )
        for model, p_correct, detection_rate in args.ladder
    ]
    options, best = route_options(
        stages,
        dispatch_units=args.dispatch_units,
        handoff_units=args.handoff_units,
        failure_penalty_units=args.failure_penalty,
        defect_penalty_units=args.defect_penalty,
        latency_weight=args.latency_weight,
        max_hidden_failure=args.max_hidden_failure,
        human_validation_required=getattr(args, "human_validation_required", False),
        human_detection_rate=getattr(args, "human_detection_rate", 0.0),
        human_validation_units=getattr(args, "human_validation_units", 0.0),
        human_validation_seconds=getattr(args, "human_validation_seconds", 0.0),
    )
    return {"models": costs, "start_options": options, "recommended_route": best}


def main() -> int:
    args = build_parser().parse_args()
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print("Candidate routes")
    for option in result["start_options"]:
        human = (
            f" human_checks={option['expected_human_validations']:.3f}"
            if args.human_validation_required
            else ""
        )
        print(
            " -> ".join(option["path"]),
            f"risk={option['hidden_failure_probability']:.4%}",
            f"score={option['risk_adjusted_units_per_correct']}",
            human,
            "" if option["viable"] else "[risk-rejected]",
        )
    best = result["recommended_route"]
    print("recommended route:", " -> ".join(best["path"]) if best else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
