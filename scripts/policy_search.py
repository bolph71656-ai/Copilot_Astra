#!/usr/bin/env python3
"""Offline policy regression for representative Astra routing fixtures."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.route_cost import Stage, route_options

DEFAULT_FIXTURES = ROOT / "config" / "routing-fixtures.json"


def evaluate_fixture(row: dict) -> dict:
    stages = [
        Stage(
            model=stage["model"],
            cost=float(stage["cost"]),
            p_correct=float(stage["p_correct"]),
            detection_rate=float(stage.get("detection_rate", 1.0)),
            latency_seconds=float(stage.get("latency_seconds", 0.0)),
            human_detection_rate=(
                float(stage["human_detection_rate"])
                if "human_detection_rate" in stage
                else None
            ),
        )
        for stage in row["stages"]
    ]
    options, best = route_options(
        stages,
        dispatch_units=float(row.get("dispatch_units", 0.0)),
        handoff_units=float(row.get("handoff_units", 0.0)),
        failure_penalty_units=float(row.get("failure_penalty_units", 0.0)),
        defect_penalty_units=float(row.get("defect_penalty_units", 0.0)),
        latency_weight=float(row.get("latency_weight", 0.0)),
        max_hidden_failure=float(row.get("max_hidden_failure", 1.0)),
        human_validation_required=bool(row.get("human_validation_required", False)),
        human_detection_rate=float(row.get("human_detection_rate", 0.0)),
        human_validation_units=float(row.get("human_validation_units", 0.0)),
        human_validation_seconds=float(row.get("human_validation_seconds", 0.0)),
    )
    path = best["path"] if best else None
    return {
        "name": row["name"],
        "expected_path": row["expected_path"],
        "actual_path": path,
        "pass": path == row["expected_path"],
        "options": options,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = json.loads(args.fixtures.read_text(encoding="utf-8"))
    results = [evaluate_fixture(row) for row in rows]
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for result in results:
            marker = "PASS" if result["pass"] else "FAIL"
            actual = " -> ".join(result["actual_path"]) if result["actual_path"] else "none"
            print(
                f"{marker} {result['name']}: "
                f"expected={' -> '.join(result['expected_path'])}; actual={actual}"
            )
    return 0 if all(result["pass"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
