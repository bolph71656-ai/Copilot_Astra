import unittest

from scripts.gateway_policy import evaluate_gateway, load_policy


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
        self.assertIn("no-calibrated-evidence", result["reasons"])

    def test_high_and_critical_always_escalate(self):
        for risk in ("high", "critical"):
            result = evaluate_gateway(**{**self.base, "risk_class": risk})
            self.assertEqual(result["decision"], "ESCALATE")
            self.assertIn("high-or-critical-risk", result["reasons"])

    def test_semantic_hard_gate_overrides_bootstrap(self):
        result = evaluate_gateway(**{**self.base, "authority_trigger": True})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertIn("authority-trigger", result["reasons"])

    def test_standard_can_expand_only_after_conservative_calibration(self):
        calibration = {
            "schema_version": 1,
            "entries": [{
                "task_class": "mechanical",
                "risk_class": "standard",
                "oracle_strength": "deterministic",
                "samples": 250,
                "false_downroute_upper_bound": 0.015,
                "validated_correct_lower_bound": 0.97,
                "authority_rescue_upper_bound": 0.04,
                "mean_cost_ratio_vs_authority_direct": 0.60,
            }],
            "global": {"samples": 250, "false_downroute_rate": 0.0, "authority_rescue_rate": 0.0, "mean_cost_ratio_vs_authority_direct": 0.60, "high_or_critical_false_downroutes": 0},
        }
        result = evaluate_gateway(**{**self.base, "risk_class": "standard", "calibration": calibration})
        self.assertEqual(result["decision"], "ALLOW_DIRECT")
        self.assertEqual(result["mode"], "calibrated")

    def test_global_rollback_pauses_even_bootstrap_direct_work(self):
        calibration = {
            "schema_version": 1,
            "entries": [],
            "global": {"samples": 20, "false_downroute_rate": 0.05, "authority_rescue_rate": 0.0, "mean_cost_ratio_vs_authority_direct": 0.5, "high_or_critical_false_downroutes": 0},
        }
        result = evaluate_gateway(**{**self.base, "calibration": calibration})
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertEqual(result["mode"], "rollback")
        self.assertIn("false-downroute-rate", result["reasons"])


if __name__ == "__main__":
    unittest.main()
