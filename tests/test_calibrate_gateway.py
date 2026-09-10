import unittest

from scripts.calibrate_gateway import summarize, validate_observation, wilson_interval
from scripts.gateway_policy import evaluate_gateway, load_policy


class GatewayCalibrationTests(unittest.TestCase):
    def test_wilson_interval_is_conservative_for_zero_events(self):
        lower, upper = wilson_interval(0, 200, 1.96)
        self.assertEqual(lower, 0.0)
        self.assertLess(upper, 0.02)

    def test_escalated_record_cannot_claim_false_downroute(self):
        with self.assertRaises(ValueError):
            validate_observation({
                "gateway_action": "escalate",
                "risk_class": "standard",
                "false_downroute": True,
            })

    def test_direct_record_requires_final_validation_outcome(self):
        with self.assertRaises(ValueError):
            validate_observation({
                "gateway_action": "direct",
                "risk_class": "exploratory",
            })

    def test_clean_standard_evidence_can_clear_policy_bounds(self):
        records = [
            {
                "gateway_action": "direct",
                "task_class": "mechanical",
                "risk_class": "standard",
                "oracle_strength": "deterministic",
                "final_validated_correct": True,
                "false_downroute": False,
                "authority_rescue_required": False,
                "gateway_path_units": 5.0,
                "authority_direct_estimated_units": 10.0,
            }
            for _ in range(250)
        ]
        calibration = summarize(records)
        entry = calibration["entries"][0]
        self.assertLessEqual(entry["false_downroute_upper_bound"], 0.02)
        self.assertGreaterEqual(entry["validated_correct_lower_bound"], 0.94)
        self.assertLessEqual(entry["authority_rescue_upper_bound"], 0.05)
        self.assertEqual(entry["cost_ratio_samples"], 250)
        self.assertAlmostEqual(entry["mean_cost_ratio_vs_authority_direct"], 0.5)

        result = evaluate_gateway(
            task_class="mechanical",
            risk_class="standard",
            oracle_strength="deterministic",
            explicit_acceptance=True,
            local_bounded_surface=True,
            policy=load_policy(),
            calibration=calibration,
        )
        self.assertEqual(result["decision"], "ALLOW_DIRECT")

    def test_global_summary_reports_direct_and_escalation_rates(self):
        calibration = summarize([
            {
                "gateway_action": "direct",
                "task_class": "mechanical",
                "risk_class": "exploratory",
                "oracle_strength": "deterministic",
                "final_validated_correct": True,
            },
            {
                "gateway_action": "escalate",
                "task_class": "coupled",
                "risk_class": "standard",
                "oracle_strength": "mixed",
            },
        ])
        global_summary = calibration["global"]
        self.assertEqual(global_summary["total_requests"], 2)
        self.assertAlmostEqual(global_summary["direct_completion_rate"], 0.5)
        self.assertAlmostEqual(global_summary["escalation_rate"], 0.5)

    def test_high_risk_false_downroute_triggers_global_pause(self):
        calibration = summarize([
            {
                "gateway_action": "direct",
                "task_class": "security",
                "risk_class": "high",
                "oracle_strength": "deterministic",
                "final_validated_correct": False,
                "false_downroute": True,
                "authority_rescue_required": True,
            }
        ])
        result = evaluate_gateway(
            task_class="mechanical",
            risk_class="exploratory",
            oracle_strength="deterministic",
            explicit_acceptance=True,
            local_bounded_surface=True,
            policy=load_policy(),
            calibration=calibration,
        )
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertEqual(result["mode"], "rollback")
        self.assertIn("high-or-critical-false-downroute", result["reasons"])


if __name__ == "__main__":
    unittest.main()
