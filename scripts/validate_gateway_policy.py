#!/usr/bin/env python3
"""Static validation for Astra Gateway policy, calibration plumbing, and routing economics defaults."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gateway_policy import POLICY_PATH, load_policy
from scripts.route_cost import OPERATIONAL_COSTS_PATH, load_operational_costs

GATEWAY_AGENT = ROOT / ".github" / "agents" / "astra-gateway.agent.md"
GATEWAY_ADR = ROOT / "docs" / "adr" / "0006-calibrated-gateway-admission.md"
GITIGNORE = ROOT / ".gitignore"
LOCAL_GATEWAY_CALIBRATION = "config/gateway-calibration.local.json"


def validate() -> list[str]:
    errors: list[str] = []

    try:
        policy = load_policy(POLICY_PATH)
    except Exception as exc:
        return [f"gateway-policy: {exc}"]

    bootstrap = policy["bootstrap"]
    calibrated = policy["calibrated"]
    rollback = policy["rollback"]

    if set(bootstrap.get("direct_risk_classes", [])) - {"exploratory"}:
        errors.append("gateway bootstrap may directly allow exploratory risk only")
    if set(bootstrap.get("direct_oracle_strengths", [])) - {"deterministic"}:
        errors.append("gateway bootstrap may directly allow deterministic oracle only")
    for key in ("require_explicit_acceptance", "require_local_bounded_surface", "require_no_human_validation"):
        if bootstrap.get(key) is not True:
            errors.append(f"gateway bootstrap must keep {key}=true")
    if {"high", "critical"} & set(calibrated.get("direct_risk_classes", [])):
        errors.append("gateway calibrated policy must never directly allow high/critical risk")
    if set(calibrated.get("direct_oracle_strengths", [])) - {"deterministic"}:
        errors.append("gateway calibrated policy may directly allow deterministic oracle only")
    if int(calibrated.get("min_samples", 0)) < 1:
        errors.append("gateway calibrated min_samples must be positive")
    if int(calibrated.get("min_cost_samples", 0)) < 1:
        errors.append("gateway calibrated min_cost_samples must be positive")
    confidence_z = calibrated.get("confidence_z")
    if not isinstance(confidence_z, (int, float)) or float(confidence_z) < 1.96:
        errors.append("gateway calibrated confidence_z must be at least 1.96")
    for key in (
        "max_false_downroute_upper_bound",
        "min_validated_correct_lower_bound",
        "max_authority_rescue_upper_bound",
        "max_mean_cost_ratio_vs_authority_direct",
    ):
        value = calibrated.get(key)
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"gateway calibrated {key} must be non-negative")
    if float(calibrated.get("max_false_downroute_upper_bound", 1)) > 0.05:
        errors.append("gateway calibrated false-downroute upper bound is too permissive")
    if float(calibrated.get("min_validated_correct_lower_bound", 0)) < 0.94:
        errors.append("gateway calibrated validated-correct lower bound is too permissive")
    if int(rollback.get("min_samples", 0)) < 1:
        errors.append("gateway rollback min_samples must be positive")
    if int(rollback.get("min_cost_samples", 0)) < 1:
        errors.append("gateway rollback min_cost_samples must be positive")
    if not rollback.get("pause_on_any_high_or_critical_direct_attempt", False):
        errors.append("gateway rollback must pause on any high/critical direct attempt")
    if not rollback.get("pause_on_any_high_or_critical_false_downroute", False):
        errors.append("gateway rollback must pause on any high/critical false down-route")

    try:
        operational = load_operational_costs(OPERATIONAL_COSTS_PATH)
    except Exception as exc:
        errors.append(f"operational-costs: {exc}")
    else:
        defaults = operational["defaults"]
        for key in ("dispatch_units", "handoff_units", "failure_penalty_units"):
            if float(defaults.get(key, 0)) <= 0:
                errors.append(f"operational-costs {key} must be positive by default")
        for risk in ("exploratory", "standard", "high", "critical"):
            if float(operational["defect_penalty_units_by_risk"].get(risk, 0)) <= 0:
                errors.append(f"operational-costs missing positive defect penalty for {risk}")

    if not GATEWAY_AGENT.exists():
        errors.append("generated Astra Gateway agent missing")
    else:
        text = GATEWAY_AGENT.read_text(encoding="utf-8")
        for required in (
            "scripts/gateway_policy.py",
            "ALLOW_DIRECT",
            "exploratory + deterministic-oracle",
            "high/critical work never completes directly",
        ):
            if required not in text:
                errors.append(f"gateway agent missing policy contract text: {required}")

    if not GATEWAY_ADR.exists():
        errors.append("calibrated gateway ADR missing")

    ignore = GITIGNORE.read_text(encoding="utf-8") if GITIGNORE.exists() else ""
    if LOCAL_GATEWAY_CALIBRATION not in ignore:
        errors.append(f".gitignore must ignore {LOCAL_GATEWAY_CALIBRATION}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Gateway policy validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Gateway policy validation passed: fail-closed bootstrap, calibrated expansion, rollback guardrails, and nonzero economics defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
