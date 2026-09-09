import argparse
import unittest

from scripts.route_cost import (
    PRICING,
    cheap_first_success_threshold,
    evaluate,
    expected_ladder_cost,
    model_cost,
    parse_ladder,
    starting_route_options,
)


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
        cost, success = expected_ladder_cost(
            [
                ("luna", 1.0, 0.8),
                ("terra", 10.0, 0.95),
                ("astra", 30.0, 1.0),
            ],
            handoff_units=0.1,
            failure_penalty_units=0.2,
        )
        self.assertAlmostEqual(success, 1.0)
        self.assertGreater(cost, 1.0)
        self.assertLess(cost, 10.0)

    def test_start_router_can_skip_luna(self):
        options, best = starting_route_options(
            [
                ("luna", 1.0, 0.01),
                ("terra", 10.0, 0.95),
                ("sol", 20.0, 0.99),
                ("astra", 50.0, 1.0),
            ],
            dispatch_units=0.5,
            handoff_units=1.0,
            failure_penalty_units=2.0,
        )
        self.assertEqual([o["start_model"] for o in options], ["luna", "terra", "sol", "astra"])
        self.assertIsNotNone(best)
        self.assertEqual(best["start_model"], "terra")

    def test_start_router_keeps_luna_when_success_is_high(self):
        _, best = starting_route_options(
            [
                ("luna", 1.0, 0.90),
                ("terra", 10.0, 0.97),
                ("sol", 20.0, 0.995),
                ("astra", 50.0, 1.0),
            ],
            dispatch_units=0.25,
            handoff_units=0.5,
            failure_penalty_units=0.5,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["start_model"], "luna")

    def test_dispatch_overhead_can_favor_astra_direct(self):
        _, best = starting_route_options(
            [
                ("luna", 0.01, 0.99),
                ("terra", 0.1, 0.999),
                ("astra", 0.5, 1.0),
            ],
            dispatch_units=1.0,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["start_model"], "astra")

    def test_parse_ladder_rejects_duplicate_model(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_ladder("luna:0.8,luna:0.9,astra:1")

    def test_evaluate_contains_start_recommendation(self):
        args = argparse.Namespace(
            fresh_input=1000,
            cached_input=0,
            cache_write=0,
            output=100,
            context_tokens=None,
            tier="auto",
            ladder=parse_ladder("luna:0.8,terra:0.95,astra:1"),
            dispatch_units=0.0,
            handoff_units=0.0,
            failure_penalty=0.0,
        )
        result = evaluate(args)
        self.assertEqual(set(result["models"]), set(PRICING))
        self.assertEqual(result["ladder"]["success_probability"], 1.0)
        self.assertEqual(
            [o["start_model"] for o in result["start_options"]],
            ["luna", "terra", "astra"],
        )
        self.assertIn(result["recommended_start"]["start_model"], {"luna", "terra", "astra"})


if __name__ == "__main__":
    unittest.main()
