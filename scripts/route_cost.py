#!/usr/bin/env python3
"""Estimate cost-aware multi-model routing for GitHub Copilot agents.

Costs are repository routing units per 1M tokens. 100 units = $1 at the
documented token prices used by this project. This is an estimator, not a
billing API.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Iterable


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


PRICING = {
    "luna": ModelPricing(Rates(20, 2, 25, 120), Rates(40, 4, 50, 180), 200_000),
    "terra": ModelPricing(Rates(200, 20, 250, 1200), Rates(400, 40, 500, 1800), 272_000),
    "sol": ModelPricing(Rates(400, 40, 500, 2000), Rates(800, 80, 1000, 3000), 272_000),
    "astra": ModelPricing(Rates(1000, 100, 1250, 5000), Rates(2000, 200, 2500, 7500), 272_000),
}


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("token counts must be non-negative")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("cost values must be non-negative")
    return parsed


def probability(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("probability must be between 0 and 1")
    return parsed


def tier_for(model: str, requested: str, context_tokens: int) -> str:
    if requested in {"default", "long"}:
        return requested
    return "long" if context_tokens > PRICING[model].long_threshold else "default"


def model_cost(model: str, fresh_input: int, cached_input: int, cache_write: int, output: int, *, tier: str = "auto", context_tokens: int | None = None) -> tuple[float, str]:
    if model not in PRICING:
        raise ValueError(f"unknown model: {model}")
    inferred_context = fresh_input + cached_input if context_tokens is None else context_tokens
    selected = tier_for(model, tier, inferred_context)
    rates = getattr(PRICING[model], selected)
    units = (fresh_input * rates.fresh_input + cached_input * rates.cached_input + cache_write * rates.cache_write + output * rates.output) / 1_000_000
    return units, selected


def parse_ladder(value: str) -> list[tuple[str, float]]:
    stages: list[tuple[str, float]] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            model, p_text = raw.split(":", 1)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("ladder entries must be model:success_probability") from exc
        model = model.strip().lower()
        if model not in PRICING:
            raise argparse.ArgumentTypeError(f"unknown model in ladder: {model}")
        p = probability(p_text)
        stages.append((model, p))
    if not stages:
        raise argparse.ArgumentTypeError("ladder must contain at least one stage")
    return stages


def expected_ladder_cost(stages: Iterable[tuple[str, float, float]], *, handoff_units: float = 0.0, failure_penalty_units: float = 0.0) -> tuple[float, float]:
    """Return expected units and probability of eventual success."""
    stage_list = list(stages)
    reach = 1.0
    expected = 0.0
    success = 0.0
    for index, (_, cost, p_success) in enumerate(stage_list):
        if index:
            expected += reach * handoff_units
        expected += reach * cost
        success += reach * p_success
        reach *= 1.0 - p_success
        if index < len(stage_list) - 1:
            expected += reach * failure_penalty_units
    return expected, success


def cheap_first_success_threshold(cheap_cost: float, expensive_cost: float) -> float | None:
    """Minimum success probability for cheap-first to beat direct expensive."""
    if expensive_cost <= 0:
        return None
    return cheap_cost / expensive_cost


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-input", type=non_negative_int, default=0)
    parser.add_argument("--cached-input", type=non_negative_int, default=0)
    parser.add_argument("--cache-write", type=non_negative_int, default=0)
    parser.add_argument("--output", type=non_negative_int, default=0)
    parser.add_argument("--context-tokens", type=non_negative_int, default=None, help="Context length for automatic long-tier selection. Defaults to fresh+cached input.")
    parser.add_argument("--tier", choices=("auto", "default", "long"), default="auto")
    parser.add_argument("--ladder", type=parse_ladder, default=parse_ladder("luna:0.80,terra:0.95,sol:0.99,astra:1.0"), help="Escalation ladder as model:conditional-success entries.")
    parser.add_argument("--handoff-units", type=non_negative_float, default=0.0, help="Fixed parent/handoff cost paid before each escalation stage.")
    parser.add_argument("--failure-penalty", type=non_negative_float, default=0.0, help="Expected validation/rework cost charged after a failed stage before escalation.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def evaluate(args: argparse.Namespace) -> dict:
    costs: dict[str, dict] = {}
    for model in PRICING:
        units, selected_tier = model_cost(model, args.fresh_input, args.cached_input, args.cache_write, args.output, tier=args.tier, context_tokens=args.context_tokens)
        costs[model] = {"units": units, "usd": units / 100.0, "tier": selected_tier}

    ladder_stages = [(model, costs[model]["units"], p_success) for model, p_success in args.ladder]
    ladder_units, ladder_success = expected_ladder_cost(ladder_stages, handoff_units=args.handoff_units, failure_penalty_units=args.failure_penalty)
    expected_per_success = ladder_units / ladder_success if ladder_success > 0 else None

    thresholds: dict[str, float | None] = {}
    for cheap, expensive in (("luna", "terra"), ("terra", "sol"), ("sol", "astra")):
        thresholds[f"{cheap}_before_{expensive}"] = cheap_first_success_threshold(costs[cheap]["units"], costs[expensive]["units"])

    return {"tokens": {"fresh_input": args.fresh_input, "cached_input": args.cached_input, "cache_write": args.cache_write, "output": args.output, "context_tokens": args.context_tokens}, "models": costs, "ladder": {"stages": [{"model": m, "success_probability": p} for m, p in args.ladder], "expected_units": ladder_units, "expected_usd": ladder_units / 100.0, "success_probability": ladder_success, "expected_units_per_success": expected_per_success}, "cheap_first_success_thresholds": thresholds}


def main() -> int:
    args = build_parser().parse_args()
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print("Model cost for the same token shape")
    print("model   tier      units       USD")
    for model, row in result["models"].items():
        print(f"{model:<7} {row['tier']:<7} {row['units']:>10.4f}  ${row['usd']:.6f}")
    ladder = result["ladder"]
    print("\nEscalation ladder")
    print(" -> ".join(f"{s['model']}({s['success_probability']:.0%})" for s in ladder["stages"]))
    print(f"expected cost:        {ladder['expected_units']:.4f} units (${ladder['expected_usd']:.6f})")
    print(f"eventual success:     {ladder['success_probability']:.4%}")
    if ladder["expected_units_per_success"] is not None:
        print(f"cost / success:       {ladder['expected_units_per_success']:.4f} units")
    print("\nCheap-first minimum success probability (detectable failures; zero failure penalty)")
    for pair, threshold in result["cheap_first_success_thresholds"].items():
        text = "n/a" if threshold is None else f"{threshold:.2%}"
        print(f"{pair.replace('_', ' '):<24} {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
