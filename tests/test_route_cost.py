import argparse
import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_registry import active_model_ids, authority_model_id, load_model_registry
from scripts.route_cost import (
    CallShape,
    DEFAULT_PRIORS_PATH,
    Stage,
    calls_cost,
    candidate_routes,
    default_prior_paths,
    evaluate,
    expected_route_metrics,
    load_prior_bundle,
    parse_ladder,
    resolve_model_prior,
    route_options,
)
from scripts.routing_pricing import _load as load_pricing, model_cost

REGISTRY = load_model_registry()


def synthetic_pricing():
    raw = {
        "schema_version": 2,
        "models": {
            "cheap": {
                "tiers": [
                    {"name":"base","min_context_tokens":0,"rates":{"fresh_input":1,"cached_input":1,"cache_write":1,"output":1}},
                    {"name":"large","min_context_tokens":101,"rates":{"fresh_input":2,"cached_input":2,"cache_write":2,"output":2}},
                ]
            },
            "expensive": {
                "tiers": [
                    {"name":"base","min_context_tokens":0,"rates":{"fresh_input":10,"cached_input":10,"cache_write":10,"output":10}}
                ]
            }
        }
    }
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / "pricing.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return tmp, load_pricing(path)


class RouteCostTests(unittest.TestCase):
    def test_pricing_ratio_uses_supplied_data_not_repository_rates(self):
        tmp, pricing = synthetic_pricing()
        self.addCleanup(tmp.cleanup)
        shape = dict(fresh_input=10, cached_input=20, cache_write=0, output=5)
        cheap, _ = model_cost("cheap", **shape, tier="base", pricing=pricing)
        expensive, _ = model_cost("expensive", **shape, tier="base", pricing=pricing)
        self.assertAlmostEqual(expensive / cheap, 10)

    def test_auto_tier_selection_and_cache_write_context(self):
        tmp, pricing = synthetic_pricing()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(model_cost("cheap", 50, 0, 51, 0, pricing=pricing)[1], "large")
        self.assertEqual(model_cost("cheap", 50, 0, 51, 0, context_tokens=90, pricing=pricing)[1], "base")

    def test_call_level_pricing_does_not_aggregate_context(self):
        tmp, pricing = synthetic_pricing()
        self.addCleanup(tmp.cleanup)
        total, tiers = calls_cost(
            "cheap",
            [CallShape(fresh_input=60), CallShape(fresh_input=60)],
            pricing=pricing,
        )
        self.assertEqual(tiers, ["base", "base"])
        one, _ = model_cost("cheap", 60, 0, 0, 0, pricing=pricing)
        self.assertAlmostEqual(total, one * 2)

    def test_candidate_routes_support_arbitrary_stage_count_and_names(self):
        paths = [
            [stage.model for stage in route]
            for route in candidate_routes(
                [
                    Stage("economy", 1, .8, 1),
                    Stage("reasoner", 10, .95, 1),
                    Stage("authority", 50, .995, .995),
                ]
            )
        ]
        self.assertIn(["economy", "authority"], paths)
        self.assertIn(["reasoner", "authority"], paths)
        self.assertIn(["authority"], paths)

    def test_direct_authority_route_has_no_dispatch_cost_without_name_assumption(self):
        metrics = expected_route_metrics([Stage("future-authority", 10, .99, 1)], dispatch_units=999)
        self.assertAlmostEqual(metrics["expected_units"], 10)

    def test_seed_authority_is_not_infallible(self):
        bundle = load_prior_bundle([DEFAULT_PRIORS_PATH])
        authority = authority_model_id(REGISTRY)
        direct = resolve_model_prior(
            bundle["entries"],
            task_class="default",
            oracle_strength="mixed",
            model=authority,
            reached_after="direct",
        )
        after = resolve_model_prior(
            bundle["entries"],
            task_class="default",
            oracle_strength="mixed",
            model=authority,
            reached_after=active_model_ids(REGISTRY)[0],
        )
        self.assertLess(direct["p_correct"], 1)
        self.assertLessEqual(after["p_correct"], direct["p_correct"])

    def test_transition_prior_differs_from_direct(self):
        entries = [
            {"task_class":"*","oracle_strength":"*","model":"reasoner","reached_after":"direct","p_correct":.99,"detection_rate":1,"_source_order":0},
            {"task_class":"*","oracle_strength":"*","model":"reasoner","reached_after":"after:any","p_correct":.3,"detection_rate":1,"_source_order":0},
        ]
        self.assertEqual(resolve_model_prior(entries,task_class="x",oracle_strength="mixed",model="reasoner",reached_after="direct")["p_correct"],.99)
        self.assertEqual(resolve_model_prior(entries,task_class="x",oracle_strength="mixed",model="reasoner",reached_after="economy")["p_correct"],.3)

    def test_exact_transition_beats_after_any(self):
        entries = [
            {"task_class":"*","oracle_strength":"*","model":"authority","reached_after":"after:any","p_correct":.8,"detection_rate":.9,"_source_order":0},
            {"task_class":"*","oracle_strength":"*","model":"authority","reached_after":"economy>reasoner","p_correct":.95,"detection_rate":.99,"_source_order":0},
        ]
        prior = resolve_model_prior(entries,task_class="x",oracle_strength="mixed",model="authority",reached_after="economy>reasoner")
        self.assertEqual(prior["p_correct"],.95)
        self.assertEqual(prior["detection_rate"],.99)

    def test_overlay_can_supply_partial_more_specific_prior(self):
        entries = [
            {"task_class":"*","oracle_strength":"*","model":"worker","reached_after":"direct","p_correct":.8,"detection_rate":.9,"_source_order":0},
            {"task_class":"mechanical","oracle_strength":"deterministic","model":"worker","reached_after":"direct","p_correct":.95,"_source_order":1},
        ]
        prior = resolve_model_prior(entries,task_class="mechanical",oracle_strength="deterministic",model="worker",reached_after="direct")
        self.assertEqual(prior["p_correct"],.95)
        self.assertEqual(prior["detection_rate"],.9)

    def test_terminal_failure_constraint_rejects_route(self):
        options, best = route_options([Stage("authority",1,p_correct=.9,detection_rate=1)], max_terminal_failure=.05)
        self.assertFalse(options[0]["viable"])
        self.assertIn("terminal-failure", options[0]["rejection_reasons"])
        self.assertIsNone(best)

    def test_min_validated_correct_constraint_rejects_route(self):
        options, best = route_options([Stage("authority",1,p_correct=.9,detection_rate=0)], min_validated_correct=.95)
        self.assertFalse(options[0]["viable"])
        self.assertIn("validated-correct", options[0]["rejection_reasons"])
        self.assertIsNone(best)

    def test_human_oracle_reduces_hidden_failure(self):
        metrics = expected_route_metrics([Stage("worker",1,.8,.5)], human_validation_required=True, human_detection_rate=.9)
        self.assertAlmostEqual(metrics["hidden_failure_probability"],.01)
        self.assertAlmostEqual(metrics["expected_human_detected_defect_events"],.09)
        self.assertAlmostEqual(metrics["expected_human_validation_count"],.9)

    def test_event_metrics_are_named_as_expected_counts(self):
        metrics = expected_route_metrics(
            [Stage("worker",1,.5,0),Stage("authority",1,.5,0)],
            human_validation_required=True,
            human_detection_rate=1,
        )
        self.assertIn("expected_human_detected_defect_events", metrics)
        self.assertIn("expected_human_validation_count", metrics)
        self.assertNotIn("human_detected_failure_probability", metrics)

    def test_parse_ladder_rejects_duplicate_current_model(self):
        first = active_model_ids(REGISTRY)[0]
        authority = authority_model_id(REGISTRY)
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_ladder(f"{first}:.8,{first}:.9,{authority}:.99")

    def test_evaluate_uses_registry_route_when_models_omitted(self):
        args = argparse.Namespace(
            fresh_input=1000,cached_input=0,cache_write=0,output=100,context_tokens=None,tier="auto",
            ladder=None,models=None,task_class="default",oracle_strength="mixed",priors=[],risk_class="standard",
            max_hidden_failure=None,max_terminal_failure=None,min_validated_correct=None,dispatch_units=0,handoff_units=0,
            failure_penalty=0,defect_penalty=0,latency_weight=0,latency={},human_validation_required=False,
            human_validation_kind="default",human_detection_rate=None,human_validation_units=0,human_validation_seconds=None,
        )
        result = evaluate(args)
        self.assertEqual(result["model_registry"]["evaluated_route"], active_model_ids(REGISTRY))
        self.assertEqual(result["model_registry"]["authority_model"], authority_model_id(REGISTRY))
        self.assertTrue(result["start_options"])

    def test_route_cost_cli_runs_as_script(self):
        import subprocess, sys
        root = Path(__file__).resolve().parents[1]
        done = subprocess.run(
            [sys.executable, "scripts/route_cost.py", "--models", ",".join(active_model_ids(REGISTRY)), "--fresh-input", "1", "--output", "1", "--risk-class", "exploratory", "--json"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("recommended_route", done.stdout)

    def test_default_prior_paths_include_seed(self):
        self.assertEqual(default_prior_paths()[0], DEFAULT_PRIORS_PATH)


if __name__ == "__main__":
    unittest.main()
