import unittest

from scripts.calibrate_routing import beta_mean, summarize


class CalibrationTests(unittest.TestCase):
    def test_beta_mean(self):
        self.assertAlmostEqual(beta_mean(3, 1, 1, 1), 4 / 6)

    def test_direct_and_escalated_priors_are_separate(self):
        result = summarize([
            {"task_class":"mechanical","start_model":"luna","reached_after":"direct","oracle_strength":"deterministic","validated_correct":True},
            {"task_class":"mechanical","start_model":"luna","reached_after":"terra-failure","oracle_strength":"deterministic","validated_correct":False,"failure_detected":True},
        ])
        self.assertEqual(len(result["posteriors"]), 2)

    def test_hidden_defect_reduces_detection_posterior(self):
        result = summarize([
            {"task_class":"semantic","start_model":"luna","oracle_strength":"weak","validated_correct":False,"hidden_defect":True},
            {"task_class":"semantic","start_model":"luna","oracle_strength":"weak","validated_correct":False,"failure_detected":True},
        ])
        self.assertAlmostEqual(result["posteriors"][0]["detection_rate_mean"], 0.5)

    def test_scout_change_rate(self):
        result = summarize([
            {"task_class":"coupled","start_model":"terra","validated_correct":True,"scout_used":True,"scout_changed_tier":True},
            {"task_class":"coupled","start_model":"terra","validated_correct":True,"scout_used":True,"scout_changed_tier":False},
        ])
        self.assertAlmostEqual(result["scout_value_signal"][0]["changed_tier_given_scout"], 0.5)


if __name__ == "__main__":
    unittest.main()
