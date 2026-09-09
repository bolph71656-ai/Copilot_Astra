import argparse
import unittest

from scripts.route_cost import PRICING, cheap_first_success_threshold, evaluate, expected_ladder_cost, model_cost, parse_ladder


class RouteCostTests(unittest.TestCase):
    def test_luna_terra_default_ratio_for_same_mix(self):
        shape = dict(fresh_input=10_000, cached_input=50_000, cache_write=0, output=3_000)
        luna, _ = model_cost("luna", **shape, tier="default")
        terra, _ = model_cost("terra", **shape, tier="default")
        self.assertAlmostEqual(terra / luna, 10.0)

    def test_auto_long_threshold_is_model_specific(self):
        _, luna_tier = model_cost("luna", 200_001, 0, 0, 0, tier="auto")
        _, terra_tier = model_cost("terra", 200_001, 0, 0, 0, tier="auto")
        self.assertEqual(luna_tier, "long")
        self.assertEqual(terra_tier, "default")

    def test_cheap_first_threshold(self):
        self.assertAlmostEqual(cheap_first_success_threshold(1.0, 10.0), 0.1)

    def test_ladder_expected_cost_and_success(self):
        cost, success = expected_ladder_cost([("luna", 1.0, 0.8), ("terra", 10.0, 0.95), ("astra", 30.0, 1.0)], handoff_units=0.1, failure_penalty_units=0.2)
        self.assertAlmostEqual(success, 1.0)
        self.assertGreater(cost, 1.0)
        self.assertLess(cost, 10.0)

    def test_evaluate_contains_all_models(self):
        args = argparse.Namespace(fresh_input=1000, cached_input=0, cache_write=0, output=100, context_tokens=None, tier="auto", ladder=parse_ladder("luna:0.8,terra:0.95,astra:1"), handoff_units=0.0, failure_penalty=0.0)
        result = evaluate(args)
        self.assertEqual(set(result["models"]), set(PRICING))
        self.assertEqual(result["ladder"]["success_probability"], 1.0)


if __name__ == "__main__":
    unittest.main()
