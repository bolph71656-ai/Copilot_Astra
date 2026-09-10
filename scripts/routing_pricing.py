from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
PRICING_PATH = ROOT / "config" / "pricing.json"


@dataclass(frozen=True)
class Rates:
    fresh_input: float
    cached_input: float
    cache_write: float
    output: float


@dataclass(frozen=True)
class PricingTier:
    name: str
    min_context_tokens: int
    rates: Rates


@dataclass(frozen=True)
class ModelPricing:
    tiers: tuple[PricingTier, ...]

    def tier(self, name: str) -> PricingTier:
        for tier in self.tiers:
            if tier.name == name:
                return tier
        raise ValueError(f"unknown pricing tier {name!r}")


@dataclass(frozen=True)
class CallShape:
    fresh_input: int = 0
    cached_input: int = 0
    cache_write: int = 0
    output: int = 0
    context_tokens: int | None = None


def _rates(data: dict) -> Rates:
    return Rates(**{key: float(data[key]) for key in ("fresh_input", "cached_input", "cache_write", "output")})


def _load(path: Path = PRICING_PATH) -> dict[str, ModelPricing]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    version = raw.get("schema_version")
    result: dict[str, ModelPricing] = {}
    if version == 1:
        for model, spec in raw["models"].items():
            threshold = int(spec["long_threshold"])
            result[model] = ModelPricing(
                (
                    PricingTier("default", 0, _rates(spec["default"])),
                    PricingTier("long", threshold + 1, _rates(spec["long"])),
                )
            )
        return result
    if version != 2:
        raise ValueError(f"unsupported pricing schema: {version!r}")
    for model, spec in raw.get("models", {}).items():
        raw_tiers = spec.get("tiers")
        if not isinstance(raw_tiers, list) or not raw_tiers:
            raise ValueError(f"{model}: pricing tiers must be non-empty")
        tiers = []
        for row in raw_tiers:
            tiers.append(
                PricingTier(
                    str(row["name"]),
                    int(row["min_context_tokens"]),
                    _rates(row["rates"]),
                )
            )
        tiers.sort(key=lambda item: item.min_context_tokens)
        if tiers[0].min_context_tokens != 0:
            raise ValueError(f"{model}: first pricing tier must start at 0 context tokens")
        if len({tier.name for tier in tiers}) != len(tiers):
            raise ValueError(f"{model}: duplicate pricing tier name")
        if len({tier.min_context_tokens for tier in tiers}) != len(tiers):
            raise ValueError(f"{model}: duplicate pricing tier threshold")
        result[model] = ModelPricing(tuple(tiers))
    if not result:
        raise ValueError("pricing models must be non-empty")
    return result


PRICING = _load()


def non_negative_int(value: str) -> int:
    import argparse

    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def non_negative_float(value: str) -> float:
    import argparse

    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def probability(value: str | float) -> float:
    import argparse

    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("probability must be between 0 and 1")
    return parsed


def tier_for(
    model: str,
    requested: str,
    context_tokens: int,
    *,
    pricing: Mapping[str, ModelPricing] | None = None,
) -> str:
    pricing = pricing or PRICING
    if model not in pricing:
        raise ValueError(f"unknown model: {model}")
    spec = pricing[model]
    if requested != "auto":
        spec.tier(requested)
        return requested
    selected = spec.tiers[0]
    for tier in spec.tiers:
        if context_tokens >= tier.min_context_tokens:
            selected = tier
        else:
            break
    return selected.name


def model_cost(
    model: str,
    fresh_input: int,
    cached_input: int,
    cache_write: int,
    output: int,
    *,
    tier: str = "auto",
    context_tokens: int | None = None,
    pricing: Mapping[str, ModelPricing] | None = None,
):
    pricing = pricing or PRICING
    if model not in pricing:
        raise ValueError(f"unknown model: {model}")
    context = fresh_input + cached_input + cache_write if context_tokens is None else context_tokens
    selected = tier_for(model, tier, context, pricing=pricing)
    rates = pricing[model].tier(selected).rates
    units = (
        fresh_input * rates.fresh_input
        + cached_input * rates.cached_input
        + cache_write * rates.cache_write
        + output * rates.output
    ) / 1_000_000
    return units, selected


def calls_cost(
    model: str,
    calls: Sequence[CallShape],
    *,
    tier: str = "auto",
    pricing: Mapping[str, ModelPricing] | None = None,
):
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
            pricing=pricing,
        )
        total += cost
        tiers.append(selected)
    return total, tiers
