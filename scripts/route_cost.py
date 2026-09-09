#!/usr/bin/env python3
"""Compare estimated Astra-direct and Luna-delegated cost.

Cost units are repository assumptions per 1M tokens. This is a routing aid,
not a billing calculator.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input: float
    output: float
    cache_read: float
    cache_write: float


PRICES = {
    "astra-default": Price(1000, 5000, 100, 1250),
    "astra-long": Price(2000, 7500, 200, 2500),
    "luna-default": Price(20, 120, 2, 25),
    "luna-long": Price(40, 180, 4, 50),
}


def model_cost(price: Price, fresh_input: int, output: int, cache_read: int, cache_write: int) -> float:
    return (
        fresh_input * price.input
        + output * price.output
        + cache_read * price.cache_read
        + cache_write * price.cache_write
    ) / 1_000_000


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("token counts must be non-negative")
    return parsed


def probability(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("probability must be between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--astra-mode", choices=("default", "long"), default="default")
    parser.add_argument("--luna-mode", choices=("default", "long"), default="default")

    for prefix in ("direct", "luna"):
        parser.add_argument(f"--{prefix}-input", type=non_negative_int, default=0)
        parser.add_argument(f"--{prefix}-output", type=non_negative_int, default=0)
        parser.add_argument(f"--{prefix}-cache-read", type=non_negative_int, default=0)
        parser.add_argument(f"--{prefix}-cache-write", type=non_negative_int, default=0)

    parser.add_argument(
        "--astra-handoff-units",
        type=float,
        default=9.0,
        help="Estimated Astra dispatch + result-ingestion + integration cost units (default: 9).",
    )
    parser.add_argument(
        "--retry-probability",
        type=probability,
        default=0.0,
        help="Probability that the Luna work needs one retry.",
    )
    parser.add_argument(
        "--retry-units",
        type=float,
        default=None,
        help="Cost units for one Luna retry. Defaults to the first Luna attempt cost.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    astra_price = PRICES[f"astra-{args.astra_mode}"]
    luna_price = PRICES[f"luna-{args.luna_mode}"]

    direct = model_cost(
        astra_price,
        args.direct_input,
        args.direct_output,
        args.direct_cache_read,
        args.direct_cache_write,
    )
    luna = model_cost(
        luna_price,
        args.luna_input,
        args.luna_output,
        args.luna_cache_read,
        args.luna_cache_write,
    )

    retry_units = luna if args.retry_units is None else args.retry_units
    delegated = args.astra_handoff_units + luna + args.retry_probability * retry_units
    delta = direct - delegated

    print(f"Astra direct:      {direct:.4f} units")
    print(f"Luna delegated:   {delegated:.4f} units")
    print(f"Difference:       {delta:+.4f} units")
    print(f"Recommendation:   {'delegate to Luna' if delta > 0 else 'keep in Astra'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
