#!/usr/bin/env python3
"""Bayesian calibration for Astra routing priors from metadata-only JSONL."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


PENDING_STATES = {"needs_human_validation", "blocked"}
PASS_STATES = {"auto_validated", "human_validated"}
NON_MODEL_ATTRIBUTIONS = {"environment", "device", "infrastructure", "validation-procedure", "operator"}


def beta_mean(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    return (alpha + successes) / (alpha + beta + successes + failures)


def _validation_state(row: dict) -> str:
    explicit = row.get("validation_state")
    if explicit:
        return str(explicit)
    human_required = bool(row.get("human_validation_required", False))
    human_performed = bool(row.get("human_validation_performed", False))
    if human_required and not human_performed and not row.get("validated_correct", False):
        return "needs_human_validation"
    if bool(row.get("validated_correct", False)):
        return "human_validated" if human_required else "auto_validated"
    return "failed"


def summarize(records: list[dict], *, alpha: float = 1.0, beta: float = 1.0) -> dict:
    groups = defaultdict(
        lambda: {
            "observations": 0,
            "resolved_samples": 0,
            "successes": 0,
            "failures": 0,
            "detected_failures": 0,
            "hidden_failures": 0,
            "human_detected_failures": 0,
            "pending_human": 0,
            "blocked": 0,
            "non_model_failures": 0,
        }
    )
    scout = defaultdict(lambda: {"used": 0, "changed_tier": 0, "samples": 0})
    human_oracles = defaultdict(
        lambda: {
            "samples": 0,
            "detected_defects": 0,
            "missed_defects": 0,
            "passes": 0,
            "total_seconds": 0.0,
        }
    )

    for row in records:
        task_class = str(row.get("task_class", "unknown"))
        start_model = str(row.get("start_model", "unknown"))
        reached_after = str(row.get("reached_after", "direct"))
        oracle = str(row.get("oracle_strength", "unknown"))
        key = (task_class, start_model, reached_after, oracle)
        group = groups[key]
        group["observations"] += 1

        state = _validation_state(row)
        human_required = bool(row.get("human_validation_required", False))
        human_performed = bool(row.get("human_validation_performed", False)) or state == "human_validated"
        validation_kind = str(row.get("human_validation_kind", "device" if human_required else "none"))

        if human_required and not human_performed:
            if state == "blocked":
                group["blocked"] += 1
            else:
                group["pending_human"] += 1
        else:
            attribution = str(
                row.get(
                    "failure_attribution",
                    "implementation" if not human_required else "unknown",
                )
            )
            hidden = bool(row.get("hidden_defect", False))
            correct = state in PASS_STATES and not hidden

            if correct:
                group["resolved_samples"] += 1
                group["successes"] += 1
            elif state == "failed" or hidden:
                if attribution in NON_MODEL_ATTRIBUTIONS:
                    group["non_model_failures"] += 1
                elif attribution == "unknown" and human_required:
                    group["non_model_failures"] += 1
                else:
                    group["resolved_samples"] += 1
                    group["failures"] += 1
                    if hidden:
                        group["hidden_failures"] += 1
                    elif bool(row.get("failure_detected", True)):
                        group["detected_failures"] += 1
                    if bool(row.get("human_detected_defect", False)):
                        group["human_detected_failures"] += 1

        if human_performed:
            human_key = (task_class, validation_kind)
            human = human_oracles[human_key]
            human["samples"] += 1
            human["total_seconds"] += float(row.get("human_validation_seconds", 0.0) or 0.0)
            if bool(row.get("human_detected_defect", False)):
                human["detected_defects"] += 1
            elif bool(row.get("hidden_defect", False)):
                human["missed_defects"] += 1
            elif state == "human_validated":
                human["passes"] += 1

        s = scout[task_class]
        s["samples"] += 1
        if bool(row.get("scout_used", False)):
            s["used"] += 1
            if bool(row.get("scout_changed_tier", False)):
                s["changed_tier"] += 1

    posterior = []
    for (task_class, start_model, reached_after, oracle), stats in sorted(groups.items()):
        incorrect = stats["detected_failures"] + stats["hidden_failures"]
        resolved = stats["resolved_samples"]
        posterior.append(
            {
                "task_class": task_class,
                "start_model": start_model,
                "reached_after": reached_after,
                "oracle_strength": oracle,
                **stats,
                "p_correct_mean": (
                    beta_mean(stats["successes"], stats["failures"], alpha, beta)
                    if resolved
                    else None
                ),
                "detection_rate_mean": (
                    beta_mean(
                        stats["detected_failures"],
                        stats["hidden_failures"],
                        alpha,
                        beta,
                    )
                    if incorrect
                    else None
                ),
            }
        )

    human_summary = []
    for (task_class, kind), stats in sorted(human_oracles.items()):
        informative = stats["detected_defects"] + stats["missed_defects"]
        human_summary.append(
            {
                "task_class": task_class,
                "human_validation_kind": kind,
                **stats,
                "human_detection_rate_mean": (
                    beta_mean(
                        stats["detected_defects"],
                        stats["missed_defects"],
                        alpha,
                        beta,
                    )
                    if informative
                    else None
                ),
                "mean_human_validation_seconds": (
                    stats["total_seconds"] / stats["samples"] if stats["samples"] else None
                ),
            }
        )

    scout_summary = []
    for task_class, stats in sorted(scout.items()):
        scout_summary.append(
            {
                "task_class": task_class,
                **stats,
                "changed_tier_given_scout": (
                    stats["changed_tier"] / stats["used"] if stats["used"] else None
                ),
            }
        )

    return {
        "prior": {"alpha": alpha, "beta": beta},
        "posteriors": posterior,
        "human_oracle_posteriors": human_summary,
        "scout_value_signal": scout_summary,
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
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    args = parser.parse_args()
    if args.alpha <= 0 or args.beta <= 0:
        parser.error("alpha and beta must be > 0")
    print(
        json.dumps(
            summarize(load_jsonl(args.observations), alpha=args.alpha, beta=args.beta),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
