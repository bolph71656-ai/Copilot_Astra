import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.gateway_policy import evaluate_gateway, load_policy

ROOT = Path(__file__).resolve().parents[1]


class GatewayPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.base = dict(
            task_class="mechanical",
            risk_class="exploratory",
            oracle_strength="deterministic",
            explicit_acceptance=True,
            local_bounded_surface=True,
            policy=self.policy,
            calibration=None,
        )

    def test_bootstrap_allows_only_narrow_exploratory_deterministic_work(self):
        result = evaluate_gateway(**self.base)
        self.assertEqual(result["decision"], "ALLOW_DIRECT")
        self.assertEqual(result["mode"], "bootstrap")

    def test_standard_escalates_without_calibrated_evidence(self):
        result = evaluate_gateway(**{**self.base, "risk_class": "standard"})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("no-exact-calibrated-evidence", result["reasons"])

    def test_high_and_critical_always_escalate(self):
        for risk in ("high", "critical"):
            result = evaluate_gateway(**{**self.base, "risk_class": risk})
            self.assertEqual(result["decision"], "ESCALATE")
            self.assertIn("high-or-critical-risk", result["reasons"])

    def test_semantic_hard_gate_overrides_bootstrap(self):
        result = evaluate_gateway(**{**self.base, "authority_trigger": True})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("authority-trigger", result["reasons"])

    def _good_standard_calibration(self):
        return {
            "schema_version": 1,
            "confidence_z": 1.96,
            "entries": [{
                "task_class": "mechanical",
                "risk_class": "standard",
                "oracle_strength": "deterministic",
                "samples": 250,
                "cost_ratio_samples": 250,
                "false_downroute_upper_bound": 0.015,
                "validated_correct_lower_bound": 0.97,
                "authority_rescue_upper_bound": 0.04,
                "mean_cost_ratio_vs_authority_direct": 0.60,
            }],
            "global": {"samples": 250, "false_downroute_rate": 0.0, "authority_rescue_rate": 0.0, "mean_cost_ratio_vs_authority_direct": 0.60, "high_or_critical_false_downroutes": 0},
        }

    def test_standard_can_expand_only_after_conservative_calibration(self):
        calibration = self._good_standard_calibration()
        result = evaluate_gateway(**{**self.base, "risk_class": "standard", "calibration": calibration})
        self.assertEqual(result["decision"], "ALLOW_DIRECT")
        self.assertEqual(result["mode"], "calibrated")

    def test_wildcard_calibration_cannot_unlock_standard(self):
        calibration = self._good_standard_calibration()
        calibration["entries"][0]["task_class"] = "*"
        result = evaluate_gateway(**{**self.base, "risk_class": "standard", "calibration": calibration})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("no-exact-calibrated-evidence", result["reasons"])

    def test_lower_confidence_calibration_cannot_unlock_standard(self):
        calibration = self._good_standard_calibration()
        calibration["confidence_z"] = 1.0
        result = evaluate_gateway(**{**self.base, "risk_class": "standard", "calibration": calibration})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("insufficient-confidence-level", result["reasons"])

    def test_sparse_cost_evidence_cannot_unlock_standard(self):
        calibration = self._good_standard_calibration()
        calibration["entries"][0]["cost_ratio_samples"] = 5
        result = evaluate_gateway(**{**self.base, "risk_class": "standard", "calibration": calibration})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("insufficient-cost-samples", result["reasons"])

    def test_global_rollback_pauses_even_bootstrap_direct_work(self):
        calibration = {
            "schema_version": 1,
            "confidence_z": 1.96,
            "entries": [],
            "global": {"samples": 20, "false_downroute_rate": 0.05, "authority_rescue_rate": 0.0, "mean_cost_ratio_vs_authority_direct": 0.5, "high_or_critical_false_downroutes": 0},
        }
        result = evaluate_gateway(**{**self.base, "calibration": calibration})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertEqual(result["mode"], "rollback")
        self.assertIn("false-downroute-rate", result["reasons"])

    def test_cli_normal_escalation_returns_zero_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_calibration = Path(tmp) / "missing.json"
            done = subprocess.run(
                [
                    sys.executable,
                    "scripts/gateway_policy.py",
                    "--task-class", "mechanical",
                    "--risk-class", "standard",
                    "--oracle-strength", "deterministic",
                    "--explicit-acceptance",
                    "--local-bounded-surface",
                    "--calibration", str(missing_calibration),
                    "--json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('"decision": "ESCALATE"', done.stdout)


if __name__ == "__main__":
    unittest.main()
