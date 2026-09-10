import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_registry import (
    active_model_ids,
    authority_model_id,
    select_role_model_ids,
    validate_registry,
    validate_route_subset,
)
from scripts.routing_pricing import _load as load_pricing, model_cost
from scripts.sync_model_config import desired_agent_files, desired_agent_specs, seed_prior_document

ROOT = Path(__file__).resolve().parents[1]


def synthetic_registry(route_order):
    data = {
        "schema_version": 1,
        "as_of": "2099-01-01",
        "parent_agent_name": "Astra Orchestrator",
        "authority_model": route_order[-1],
        "route_order": list(route_order),
        "models": {},
        "role_policies": {
            "scout": {"slots": ["lowest"], "min_worker_count": 1},
            "research": {"slots": ["lowest", "middle"], "min_worker_count": 1},
            "execute": {"slots": ["all"], "min_worker_count": 1},
            "debug": {"slots": ["highest"], "min_worker_count": 2},
            "verify": {"slots": ["all"], "min_worker_count": 1},
        },
        "human_oracle_seed": {"detection_rate": 0.5, "mean_validation_seconds": 0},
    }
    ranks = {"economy": 10, "general": 20, "reasoner": 30, "authority": 40, "future-x": 50}
    for model_id in set(route_order):
        rank = ranks[model_id]
        data["models"][model_id] = {
            "display_name": model_id.replace("-", " ").title(),
            "copilot_model": f"Future {model_id} (copilot)",
            "capability_rank": rank,
            "tier_guidance": f"guidance for {model_id}",
            "seed_prior": {
                "direct": {"p_correct": min(0.75 + rank / 200, 0.995), "detection_rate": 0.95},
                "after_any": {"p_correct": min(0.70 + rank / 220, 0.98), "detection_rate": 0.95},
            },
        }
    return validate_registry(data)


class ModelRegistryTests(unittest.TestCase):
    def test_three_model_topology_selects_adaptive_profiles(self):
        registry = synthetic_registry(["economy", "reasoner", "authority"])
        self.assertEqual(select_role_model_ids(registry, "scout"), ["economy"])
        self.assertEqual(select_role_model_ids(registry, "research"), ["economy", "reasoner"])
        self.assertEqual(select_role_model_ids(registry, "execute"), ["economy", "reasoner"])
        self.assertEqual(select_role_model_ids(registry, "debug"), ["reasoner"])
        self.assertEqual(select_role_model_ids(registry, "verify"), ["economy", "reasoner"])
        self.assertEqual(len(desired_agent_specs(registry)), 8)

    def test_two_model_topology_omits_underpowered_debug_profile(self):
        registry = synthetic_registry(["economy", "authority"])
        self.assertEqual(select_role_model_ids(registry, "scout"), ["economy"])
        self.assertEqual(select_role_model_ids(registry, "research"), ["economy"])
        self.assertEqual(select_role_model_ids(registry, "execute"), ["economy"])
        self.assertEqual(select_role_model_ids(registry, "debug"), [])
        self.assertEqual(select_role_model_ids(registry, "verify"), ["economy"])
        self.assertEqual(len(desired_agent_specs(registry)), 4)
        files = desired_agent_files(registry, template_dir=ROOT / ".github" / "agent-templates")
        parent = files["astra-orchestrator.agent.md"]
        self.assertIn('agents: ["Scout Economy", "Research Economy", "Execute Economy", "Verify Economy"]', parent)
        self.assertNotIn("Debug Economy", parent)

    def test_future_model_id_and_authority_are_not_hardcoded(self):
        registry = synthetic_registry(["reasoner", "future-x"])
        self.assertEqual(authority_model_id(registry), "future-x")
        self.assertEqual(active_model_ids(registry), ["reasoner", "future-x"])
        validate_route_subset(registry, ["reasoner", "future-x"])
        with self.assertRaises(ValueError):
            validate_route_subset(registry, ["future-x", "reasoner"])

    def test_seed_priors_follow_active_route_only(self):
        registry = synthetic_registry(["economy", "reasoner", "authority"])
        doc = seed_prior_document(registry)
        direct = [row["model"] for row in doc["entries"] if row["reached_after"] == "direct"]
        after = [row["model"] for row in doc["entries"] if row["reached_after"] == "after:any"]
        self.assertEqual(direct, ["economy", "reasoner", "authority"])
        self.assertEqual(after, ["reasoner", "authority"])

    def test_pricing_schema_supports_arbitrary_models_and_tier_counts(self):
        pricing_doc = {
            "schema_version": 2,
            "models": {
                "future-model": {
                    "tiers": [
                        {"name": "base", "min_context_tokens": 0, "rates": {"fresh_input": 1, "cached_input": 1, "cache_write": 1, "output": 1}},
                        {"name": "large", "min_context_tokens": 100, "rates": {"fresh_input": 2, "cached_input": 2, "cache_write": 2, "output": 2}},
                        {"name": "huge", "min_context_tokens": 1000, "rates": {"fresh_input": 3, "cached_input": 3, "cache_write": 3, "output": 3}},
                    ]
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pricing.json"
            path.write_text(json.dumps(pricing_doc), encoding="utf-8")
            pricing = load_pricing(path)
            self.assertEqual(model_cost("future-model", 1001, 0, 0, 0, pricing=pricing)[1], "huge")
            self.assertEqual(model_cost("future-model", 50, 0, 0, 0, pricing=pricing)[1], "base")


if __name__ == "__main__":
    unittest.main()
