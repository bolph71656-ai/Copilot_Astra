#!/usr/bin/env python3
"""Calibrate Astra Gateway safety/economics from metadata-only observations."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

VALID_ACTIONS = {"direct", "escalate"}
VALID_RISKS = {"exploratory", "standard", "high", "critical"}


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if trials <= 0:
        return None, None
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denom
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * trials)) / trials) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def validate_observation(row: dict, *, index: int | None = None) -> dict:
    prefix = f"observation[{index}]" if index is not None else "observation"
    action = str(row.get("gateway_action", ""))
    if action not in VALID_ACTIONS:
        raise ValueError(f"{prefix}: gateway_action must be direct or escalate")
    risk = str(row.get("risk_class", ""))
    if risk not in VALID_RISKS:
        raise ValueError(f"{prefix}: invalid risk_class={risk!r}")
    task_class = str(row.get("task_class", "default"))
    oracle = str(row.get("oracle_strength", "mixed"))
    false_downroute = bool(row.get("false_downroute", False))
    rescue = bool(row.get("authority_rescue_required", False))
    if action != "direct" and (false_downroute or rescue):
        raise ValueError(f"{prefix}: false_downroute/authority_rescue require gateway_action=direct")
    validated = row.get("final_validated_correct")
    if action == "direct" and not isinstance(validated, bool):
        raise ValueError(f"{prefix}: direct observations require boolean final_validated_correct")

    gateway_units = row.get("gateway_path_units")
    authority_units = row.get("authority_direct_estimated_units")
    if gateway_units is not None and float(gateway_units) < 0:
        raise ValueError(f"{prefix}: gateway_path_units must be non-negative")
    if authority_units is not None and float(authority_units) <= 0:
        raise ValueError(f"{prefix}: authority_direct_estimated_units must be > 0")
    if (gateway_units is None) != (authority_units is None):
        raise ValueError(f"{prefix}: cost comparison requires both gateway_path_units and authority_direct_estimated_units")

    return {
        **row,
        "gateway_action": action,
        "risk_class": risk,
        "task_class": task_class,
        "oracle_strength": oracle,
        "false_downroute": false_downroute,
        "authority_rescue_required": rescue,
    }


def _new_stats() -> dict:
    return {
        "samples": 0,
        "validated_correct": 0,
        "false_downroutes": 0,
        "authority_rescues": 0,
        "cost_ratio_samples": 0,
        "cost_ratio_total": 0.0,
        "high_or_critical_false_downroutes": 0,
    }


def _add(stats: dict, row: dict) -> None:
    if row["gateway_action"] != "direct":
        return
    stats["samples"] += 1
    if bool(row["final_validated_correct"]):
        stats["validated_correct"] += 1
    if row["false_downroute"]:
        stats["false_downroutes"] += 1
        if row["risk_class"] in {"high", "critical"}:
            stats["high_or_critical_false_downroutes"] += 1
    if row["authority_rescue_required"]:
        stats["authority_rescues"] += 1
    if row.get("gateway_path_units") is not None:
        ratio = float(row["gateway_path_units"]) / float(row["authority_direct_estimated_units"])
        stats["cost_ratio_samples"] += 1
        stats["cost_ratio_total"] += ratio


def _finalize(stats: dict, *, z: float) -> dict:
    samples = stats["samples"]
    false_lower, false_upper = wilson_interval(stats["false_downroutes"], samples, z)
    correct_lower, correct_upper = wilson_interval(stats["validated_correct"], samples, z)
    rescue_lower, rescue_upper = wilson_interval(stats["authority_rescues"], samples, z)
    return {
        "samples": samples,
        "validated_correct": stats["validated_correct"],
        "validated_correct_rate": stats["validated_correct"] / samples if samples else None,
        "validated_correct_lower_bound": correct_lower,
        "validated_correct_upper_bound": correct_upper,
        "false_downroutes": stats["false_downroutes"],
        "false_downroute_rate": stats["false_downroutes"] / samples if samples else None,
        "false_downroute_lower_bound": false_lower,
        "false_downroute_upper_bound": false_upper,
        "authority_rescues": stats["authority_rescues"],
        "authority_rescue_rate": stats["authority_rescues"] / samples if samples else None,
        "authority_rescue_lower_bound": rescue_lower,
        "authority_rescue_upper_bound": rescue_upper,
        "cost_ratio_samples": stats["cost_ratio_samples"],
        "mean_cost_ratio_vs_authority_direct": (
            stats["cost_ratio_total"] / stats["cost_ratio_samples"]
            if stats["cost_ratio_samples"]
            else None
        ),
        "high_or_critical_false_downroutes": stats["high_or_critical_false_downroutes"],
    }


def summarize(records: list[dict], *, z: float = 1.96) -> dict:
    groups = defaultdict(_new_stats)
    global_stats = _new_stats()
    escalations = 0
    for index, original in enumerate(records):
        row = validate_observation(original, index=index)
        if row["gateway_action"] == "escalate":
            escalations += 1
            continue
        key = (row["task_class"], row["risk_class"], row["oracle_strength"])
        _add(groups[key], row)
        _add(global_stats, row)

    entries = []
    for (task_class, risk_class, oracle), stats in sorted(groups.items()):
        entries.append({
            "task_class": task_class,
            "risk_class": risk_class,
            "oracle_strength": oracle,
            **_finalize(stats, z=z),
        })
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_kind": "gateway-calibration-output",
        "confidence_z": z,
        "entries": entries,
        "global": {**_finalize(global_stats, z=z), "escalations": escalations},
    }


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--confidence-z", type=float, default=1.96)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.confidence_z <= 0:
        parser.error("--confidence-z must be > 0")
    result = summarize(load_jsonl(args.observations), z=args.confidence_z)
    if args.out is not None:
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
