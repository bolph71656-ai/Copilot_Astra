#!/usr/bin/env python3
"""Fail-closed admission policy for Astra Gateway."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "gateway-policy.json"
LOCAL_CALIBRATION_PATH = ROOT / "config" / "gateway-calibration.local.json"
VALID_RISK_CLASSES = {"exploratory", "standard", "high", "critical"}


def _load_json(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected JSON object")
    return raw


def load_policy(path: Path = POLICY_PATH) -> dict:
    raw = _load_json(path)
    if raw.get("schema_version") != 1:
        raise ValueError(f"{path}: unsupported gateway-policy schema")
    for section in ("bootstrap", "calibrated", "rollback"):
        if not isinstance(raw.get(section), dict):
            raise ValueError(f"{path}: missing {section} section")
    return raw


def load_calibration(path: Path = LOCAL_CALIBRATION_PATH) -> dict | None:
    if not path.exists():
        return None
    raw = _load_json(path)
    if raw.get("schema_version") != 1:
        raise ValueError(f"{path}: unsupported gateway calibration schema")
    if not isinstance(raw.get("entries", []), list):
        raise ValueError(f"{path}: entries must be a list")
    confidence_z = raw.get("confidence_z")
    if not isinstance(confidence_z, (int, float)) or float(confidence_z) <= 0:
        raise ValueError(f"{path}: positive confidence_z is required")
    return raw


def _entry_score(row: dict, *, task_class: str, risk_class: str, oracle_strength: str) -> tuple[int, int, int] | None:
    task = str(row.get("task_class", "*"))
    risk = str(row.get("risk_class", "*"))
    oracle = str(row.get("oracle_strength", "*"))
    if task not in {"*", task_class} or risk not in {"*", risk_class} or oracle not in {"*", oracle_strength}:
        return None
    return (
        1 if task == task_class else 0,
        1 if risk == risk_class else 0,
        1 if oracle == oracle_strength else 0,
    )


def resolve_calibration(calibration: dict | None, *, task_class: str, risk_class: str, oracle_strength: str) -> dict | None:
    if calibration is None:
        return None
    matches: list[tuple[tuple[int, int, int], dict]] = []
    for row in calibration.get("entries", []):
        score = _entry_score(row, task_class=task_class, risk_class=risk_class, oracle_strength=oracle_strength)
        if score is not None:
            matches.append((score, row))
    if not matches:
        return None
    row = max(matches, key=lambda item: item[0])[1]
    return {**row, "_confidence_z": calibration.get("confidence_z")}


def rollback_reasons(calibration: dict | None, policy: dict) -> list[str]:
    if calibration is None:
        return []
    summary = calibration.get("global") or {}
    rollback = policy["rollback"]
    samples = int(summary.get("samples", 0) or 0)
    reasons: list[str] = []
    if rollback.get("pause_on_any_high_or_critical_false_downroute", True):
        if int(summary.get("high_or_critical_false_downroutes", 0) or 0) > 0:
            reasons.append("high-or-critical-false-downroute")
    if samples >= int(rollback.get("min_samples", 0)):
        false_rate = summary.get("false_downroute_rate")
        if false_rate is not None and float(false_rate) > float(rollback["max_false_downroute_rate"]):
            reasons.append("false-downroute-rate")
        rescue_rate = summary.get("authority_rescue_rate")
        if rescue_rate is not None and float(rescue_rate) > float(rollback["max_authority_rescue_rate"]):
            reasons.append("authority-rescue-rate")
        cost_ratio = summary.get("mean_cost_ratio_vs_authority_direct")
        if cost_ratio is not None and float(cost_ratio) > float(rollback["max_mean_cost_ratio_vs_authority_direct"]):
            reasons.append("gateway-cost-regression")
    return reasons


def calibrated_entry_reasons(entry: dict | None, policy: dict) -> list[str]:
    if entry is None:
        return ["no-calibrated-evidence"]
    cfg = policy["calibrated"]
    reasons: list[str] = []
    confidence_z = entry.get("_confidence_z")
    if confidence_z is None or float(confidence_z) < float(cfg["confidence_z"]):
        reasons.append("insufficient-confidence-level")
    if int(entry.get("samples", 0) or 0) < int(cfg["min_samples"]):
        reasons.append("insufficient-samples")
    false_upper = entry.get("false_downroute_upper_bound")
    if false_upper is None or float(false_upper) > float(cfg["max_false_downroute_upper_bound"]):
        reasons.append("false-downroute-bound")
    correct_lower = entry.get("validated_correct_lower_bound")
    if correct_lower is None or float(correct_lower) < float(cfg["min_validated_correct_lower_bound"]):
        reasons.append("validated-correct-bound")
    rescue_upper = entry.get("authority_rescue_upper_bound")
    if rescue_upper is None or float(rescue_upper) > float(cfg["max_authority_rescue_upper_bound"]):
        reasons.append("authority-rescue-bound")
    cost_ratio = entry.get("mean_cost_ratio_vs_authority_direct")
    if cost_ratio is None or float(cost_ratio) > float(cfg["max_mean_cost_ratio_vs_authority_direct"]):
        reasons.append("cost-break-even")
    return reasons


def evaluate_gateway(
    *,
    task_class: str,
    risk_class: str,
    oracle_strength: str,
    explicit_acceptance: bool,
    local_bounded_surface: bool,
    authority_trigger: bool = False,
    unresolved_design: bool = False,
    human_validation_required: bool = False,
    substantive_failure: bool = False,
    policy: dict | None = None,
    calibration: dict | None = None,
) -> dict:
    policy = policy or load_policy()
    if risk_class not in VALID_RISK_CLASSES:
        return {"decision": "ESCALATE", "mode": "hard-gate", "reasons": ["unknown-risk-class"]}

    hard_reasons: list[str] = []
    if risk_class in {"high", "critical"}:
        hard_reasons.append("high-or-critical-risk")
    if authority_trigger:
        hard_reasons.append("authority-trigger")
    if unresolved_design:
        hard_reasons.append("unresolved-design")
    if human_validation_required:
        hard_reasons.append("human-validation-required")
    if substantive_failure:
        hard_reasons.append("substantive-failure")
    if not explicit_acceptance:
        hard_reasons.append("acceptance-not-explicit")
    if not local_bounded_surface:
        hard_reasons.append("surface-not-local-bounded")
    if hard_reasons:
        return {"decision": "ESCALATE", "mode": "hard-gate", "reasons": hard_reasons}

    rollback = rollback_reasons(calibration, policy)
    if rollback:
        return {"decision": "ESCALATE", "mode": "rollback", "reasons": rollback}

    bootstrap = policy["bootstrap"]
    if (
        risk_class in bootstrap.get("direct_risk_classes", [])
        and oracle_strength in bootstrap.get("direct_oracle_strengths", [])
    ):
        return {"decision": "ALLOW_DIRECT", "mode": "bootstrap", "reasons": []}

    calibrated = policy["calibrated"]
    if not calibrated.get("enabled", False):
        return {"decision": "ESCALATE", "mode": "calibrated", "reasons": ["calibrated-expansion-disabled"]}
    if risk_class not in calibrated.get("direct_risk_classes", []):
        return {"decision": "ESCALATE", "mode": "calibrated", "reasons": ["risk-class-not-eligible"]}
    if oracle_strength not in calibrated.get("direct_oracle_strengths", []):
        return {"decision": "ESCALATE", "mode": "calibrated", "reasons": ["oracle-not-eligible"]}

    entry = resolve_calibration(
        calibration,
        task_class=task_class,
        risk_class=risk_class,
        oracle_strength=oracle_strength,
    )
    reasons = calibrated_entry_reasons(entry, policy)
    return {
        "decision": "ALLOW_DIRECT" if not reasons else "ESCALATE",
        "mode": "calibrated",
        "reasons": reasons,
        "calibration": entry,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--risk-class", required=True)
    parser.add_argument("--oracle-strength", required=True)
    parser.add_argument("--explicit-acceptance", action="store_true")
    parser.add_argument("--local-bounded-surface", action="store_true")
    parser.add_argument("--authority-trigger", action="store_true")
    parser.add_argument("--unresolved-design", action="store_true")
    parser.add_argument("--human-validation-required", action="store_true")
    parser.add_argument("--substantive-failure", action="store_true")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--calibration", type=Path, default=LOCAL_CALIBRATION_PATH)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        policy = load_policy(args.policy)
        calibration = load_calibration(args.calibration)
        result = evaluate_gateway(
            task_class=args.task_class,
            risk_class=args.risk_class,
            oracle_strength=args.oracle_strength,
            explicit_acceptance=args.explicit_acceptance,
            local_bounded_surface=args.local_bounded_surface,
            authority_trigger=args.authority_trigger,
            unresolved_design=args.unresolved_design,
            human_validation_required=args.human_validation_required,
            substantive_failure=args.substantive_failure,
            policy=policy,
            calibration=calibration,
        )
    except Exception as exc:
        result = {"decision": "ESCALATE", "mode": "policy-error", "reasons": [str(exc)]}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["decision"])
        if result.get("reasons"):
            print("reasons=" + ",".join(result["reasons"]))
    return 0 if result["decision"] == "ALLOW_DIRECT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
