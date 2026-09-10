import argparse
import unittest

from scripts.route_cost import load_operational_costs, resolve_operational_costs


class OperationalCostTests(unittest.TestCase):
    def test_repository_defaults_are_nonzero_for_orchestration_and_rework(self):
        cfg = load_operational_costs()
        self.assertGreater(cfg["defaults"]["dispatch_units"], 0)
        self.assertGreater(cfg["defaults"]["handoff_units"], 0)
        self.assertGreater(cfg["defaults"]["failure_penalty_units"], 0)
        self.assertGreater(cfg["defect_penalty_units_by_risk"]["standard"], 0)

    def test_unspecified_cli_values_use_config_defaults(self):
        args = argparse.Namespace(
            dispatch_units=None,
            handoff_units=None,
            failure_penalty=None,
            defect_penalty=None,
            latency_weight=None,
        )
        resolved = resolve_operational_costs(args, risk_class="standard")
        self.assertEqual(resolved["sources"]["dispatch_units"], "config")
        self.assertEqual(resolved["sources"]["defect_penalty_units"], "config")
        self.assertGreater(resolved["dispatch_units"], 0)
        self.assertGreater(resolved["defect_penalty_units"], 0)

    def test_explicit_zero_remains_an_override_for_experiments(self):
        args = argparse.Namespace(
            dispatch_units=0.0,
            handoff_units=0.0,
            failure_penalty=0.0,
            defect_penalty=0.0,
            latency_weight=0.0,
        )
        resolved = resolve_operational_costs(args, risk_class="critical")
        self.assertEqual(resolved["dispatch_units"], 0.0)
        self.assertEqual(resolved["defect_penalty_units"], 0.0)
        self.assertEqual(resolved["sources"]["dispatch_units"], "cli")
        self.assertEqual(resolved["sources"]["defect_penalty_units"], "cli")


if __name__ == "__main__":
    unittest.main()
