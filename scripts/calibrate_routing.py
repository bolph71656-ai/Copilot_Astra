#!/usr/bin/env python3
"""Bayesian calibration for Astra routing priors from metadata-only JSONL."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def beta_mean(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    return (alpha + successes) / (alpha + beta + successes + failures)


def summarize(records: list[dict], *, alpha: float = 1.0, beta: float = 1.0) -> dict:
    groups = defaultdict(lambda: {"successes": 0, "failures": 0, "detected_failures": 0, "hidden_failures": 0, "samples": 0})
    scout = defaultdict(lambda: {"used": 0, "changed_tier": 0, "samples": 0})
    for row in records:
        task_class = str(row.get("task_class", "unknown"))
        key = (task_class, str(row.get("start_model", "unknown")), str(row.get("reached_after", "direct")), str(row.get("oracle_strength", "unknown")))
        hidden = bool(row.get("hidden_defect", False))
        correct = bool(row.get("validated_correct", False)) and not hidden
        group = groups[key]
        group["samples"] += 1
        if correct:
            group["successes"] += 1
        else:
            group["failures"] += 1
            if hidden:
                group["hidden_failures"] += 1
            elif bool(row.get("failure_detected", True)):
                group["detected_failures"] += 1
        s = scout[task_class]
        s["samples"] += 1
        if bool(row.get("scout_used", False)):
            s["used"] += 1
            if bool(row.get("scout_changed_tier", False)):
                s["changed_tier"] += 1
    posterior = []
    for (task_class, start_model, reached_after, oracle), stats in sorted(groups.items()):
        incorrect = stats["detected_failures"] + stats["hidden_failures"]
        posterior.append({
            "task_class": task_class, "start_model": start_model, "reached_after": reached_after, "oracle_strength": oracle, **stats,
            "p_correct_mean": beta_mean(stats["successes"], stats["failures"], alpha, beta),
            "detection_rate_mean": beta_mean(stats["detected_failures"], stats["hidden_failures"], alpha, beta) if incorrect else None,
        })
    scout_summary = []
    for task_class, stats in sorted(scout.items()):
        scout_summary.append({"task_class": task_class, **stats, "changed_tier_given_scout": stats["changed_tier"] / stats["used"] if stats["used"] else None})
    return {"prior": {"alpha": alpha, "beta": beta}, "posteriors": posterior, "scout_value_signal": scout_summary}


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
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    args = parser.parse_args()
    if args.alpha <= 0 or args.beta <= 0:
        parser.error("alpha and beta must be > 0")
    print(json.dumps(summarize(load_jsonl(args.observations), alpha=args.alpha, beta=args.beta), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
