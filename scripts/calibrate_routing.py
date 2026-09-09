#!/usr/bin/env python3
"""Strict Bayesian calibration for Astra routing priors from metadata-only JSONL."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PASS_STATES = {"auto_validated", "human_validated"}
VALID_STATES = PASS_STATES | {"needs_human_validation", "failed", "blocked"}
NON_MODEL_ATTRIBUTIONS = {"environment", "device", "infrastructure", "validation-procedure", "operator"}
VALID_ATTRIBUTIONS = NON_MODEL_ATTRIBUTIONS | {"implementation", "unknown"}


def beta_mean(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    return (alpha + successes) / (alpha + beta + successes + failures)


def _validation_state(row: dict) -> str:
    explicit = row.get("validation_state")
    if explicit is not None:
        return str(explicit)
    human_required = bool(row.get("human_validation_required", False))
    human_performed = bool(row.get("human_validation_performed", False))
    validated_correct = bool(row.get("validated_correct", False))
    if human_required and not human_performed:
        if validated_correct:
            raise ValueError("validated_correct=true contradicts pending required human validation")
        return "needs_human_validation"
    if validated_correct:
        return "human_validated" if human_required else "auto_validated"
    return "failed"


def validate_observation(row: dict, *, index: int | None = None) -> dict:
    prefix = f"observation[{index}]" if index is not None else "observation"
    state = _validation_state(row)
    if state not in VALID_STATES:
        raise ValueError(f"{prefix}: invalid validation_state={state!r}")

    human_required = bool(row.get("human_validation_required", False))
    human_performed = bool(row.get("human_validation_performed", False))
    human_detected = bool(row.get("human_detected_defect", False))
    attribution = str(row.get("failure_attribution", "unknown"))
    if attribution not in VALID_ATTRIBUTIONS:
        raise ValueError(f"{prefix}: invalid failure_attribution={attribution!r}")

    if state == "human_validated":
        if not human_required:
            raise ValueError(f"{prefix}: human_validated requires human_validation_required=true")
        if not human_performed:
            raise ValueError(f"{prefix}: human_validated requires human_validation_performed=true")
    if state == "needs_human_validation":
        if not human_required:
            raise ValueError(f"{prefix}: needs_human_validation requires human_validation_required=true")
        if human_performed:
            raise ValueError(f"{prefix}: needs_human_validation contradicts human_validation_performed=true")
    if human_detected and not human_performed:
        raise ValueError(f"{prefix}: human_detected_defect requires human_validation_performed=true")
    if state == "blocked" and bool(row.get("validated_correct", False)):
        raise ValueError(f"{prefix}: blocked cannot also be validated_correct")

    normalized = dict(row)
    normalized["validation_state"] = state
    normalized["failure_attribution"] = attribution
    normalized["human_validation_required"] = human_required
    normalized["human_validation_performed"] = human_performed
    return normalized


def summarize(records: list[dict], *, alpha: float = 1.0, beta: float = 1.0) -> dict:
    groups = defaultdict(lambda: {
        "observations": 0, "resolved_samples": 0, "successes": 0, "failures": 0,
        "detected_failures": 0, "hidden_failures": 0, "human_detected_failures": 0,
        "pending_human": 0, "blocked": 0, "non_model_failures": 0, "unattributed_failures": 0,
    })
    scout = defaultdict(lambda: {"used": 0, "changed_tier": 0, "samples": 0})
    human_oracles = defaultdict(lambda: {
        "samples": 0, "detected_defects": 0, "missed_defects": 0, "passes": 0, "total_seconds": 0.0,
    })

    for index, original in enumerate(records):
        row = validate_observation(original, index=index)
        task_class = str(row.get("task_class", "default"))
        start_model = str(row.get("start_model", "unknown"))
        reached_after = str(row.get("reached_after", "direct"))
        oracle = str(row.get("oracle_strength", "mixed"))
        key = (task_class, start_model, reached_after, oracle)
        group = groups[key]
        group["observations"] += 1

        state = row["validation_state"]
        human_performed = row["human_validation_performed"]
        kind = str(row.get("human_validation_kind", "default"))

        if state == "needs_human_validation":
            group["pending_human"] += 1
        elif state == "blocked":
            group["blocked"] += 1
        else:
            attribution = row["failure_attribution"]
            hidden = bool(row.get("hidden_defect", False))
            correct = state in PASS_STATES and not hidden
            if correct:
                group["resolved_samples"] += 1
                group["successes"] += 1
            elif state == "failed" or hidden:
                if attribution in NON_MODEL_ATTRIBUTIONS:
                    group["non_model_failures"] += 1
                elif attribution == "unknown":
                    group["unattributed_failures"] += 1
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
            human = human_oracles[(task_class, kind)]
            human["samples"] += 1
            human["total_seconds"] += float(row.get("human_validation_seconds", 0.0) or 0.0)
            if bool(row.get("human_detected_defect", False)):
                human["detected_defects"] += 1
            elif bool(row.get("hidden_defect", False)):
                human["missed_defects"] += 1
            elif state == "human_validated":
                human["passes"] += 1

        scout_row = scout[task_class]
        scout_row["samples"] += 1
        if bool(row.get("scout_used", False)):
            scout_row["used"] += 1
            if bool(row.get("scout_changed_tier", False)):
                scout_row["changed_tier"] += 1

    posteriors = []
    for (task_class, model, reached_after, oracle), stats in sorted(groups.items()):
        incorrect = stats["detected_failures"] + stats["hidden_failures"]
        posteriors.append({
            "task_class": task_class, "start_model": model, "reached_after": reached_after,
            "oracle_strength": oracle, **stats,
            "p_correct_mean": beta_mean(stats["successes"], stats["failures"], alpha, beta) if stats["resolved_samples"] else None,
            "detection_rate_mean": beta_mean(stats["detected_failures"], stats["hidden_failures"], alpha, beta) if incorrect else None,
        })

    human_summary = []
    for (task_class, kind), stats in sorted(human_oracles.items()):
        informative = stats["detected_defects"] + stats["missed_defects"]
        human_summary.append({
            "task_class": task_class, "human_validation_kind": kind, **stats,
            "human_detection_rate_mean": beta_mean(stats["detected_defects"], stats["missed_defects"], alpha, beta) if informative else None,
            "mean_human_validation_seconds": stats["total_seconds"] / stats["samples"] if stats["samples"] else None,
        })

    scout_summary = []
    for task_class, stats in sorted(scout.items()):
        scout_summary.append({"task_class": task_class, **stats, "changed_tier_given_scout": stats["changed_tier"] / stats["used"] if stats["used"] else None})
    return {"prior": {"alpha": alpha, "beta": beta}, "posteriors": posteriors, "human_oracle_posteriors": human_summary, "scout_value_signal": scout_summary}


def routing_prior_document(summary: dict) -> dict:
    entries = []
    for row in summary["posteriors"]:
        entry = {"task_class": row["task_class"], "oracle_strength": row["oracle_strength"], "model": row["start_model"], "reached_after": row["reached_after"], "source_kind": "calibrated", "samples": row["resolved_samples"]}
        if row["p_correct_mean"] is not None: entry["p_correct"] = row["p_correct_mean"]
        if row["detection_rate_mean"] is not None: entry["detection_rate"] = row["detection_rate_mean"]
        if "p_correct" in entry or "detection_rate" in entry: entries.append(entry)

    human = []
    for row in summary["human_oracle_posteriors"]:
        if row["human_detection_rate_mean"] is None: continue
        human.append({"task_class": row["task_class"], "human_validation_kind": row["human_validation_kind"], "source_kind": "calibrated", "samples": row["samples"], "detection_rate": row["human_detection_rate_mean"], "mean_validation_seconds": row["mean_human_validation_seconds"]})
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "source_kind": "calibration-output", "entries": entries, "human_oracles": human}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        value = json.loads(line)
        if not isinstance(value, dict): raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--routing-priors-out", type=Path, default=None)
    args = parser.parse_args()
    if args.alpha <= 0 or args.beta <= 0: parser.error("alpha and beta must be > 0")
    result = summarize(load_jsonl(args.observations), alpha=args.alpha, beta=args.beta)
    if args.routing_priors_out is not None:
        args.routing_priors_out.write_text(json.dumps(routing_prior_document(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
