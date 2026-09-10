import copy
import unittest
from pathlib import Path

from scripts.model_registry import active_model_ids, authority_model_id, load_model_registry, validate_registry
from scripts.sync_model_config import GATEWAY_FILENAME, desired_agent_files, gateway_model_id

ROOT = Path(__file__).resolve().parents[1]


class GatewayGenerationTests(unittest.TestCase):
    def test_current_topology_generates_fail_closed_gateway_on_lowest_worker(self):
        registry = load_model_registry(ROOT / "config" / "model-registry.json")
        gateway_id = gateway_model_id(registry)
        self.assertIsNotNone(gateway_id)
        self.assertEqual(gateway_id, active_model_ids(registry)[0])
        self.assertNotEqual(gateway_id, authority_model_id(registry))

        files = desired_agent_files(registry, template_dir=ROOT / ".github" / "agent-templates")
        self.assertIn(GATEWAY_FILENAME, files)
        gateway = files[GATEWAY_FILENAME]

        self.assertIn("name: Astra Gateway", gateway)
        self.assertIn(f"model: {registry['models'][gateway_id]['copilot_model']}", gateway)
        self.assertIn(f'agents: ["{registry.get("parent_agent_name", "Astra Orchestrator")}"]', gateway)
        self.assertIn("user-invocable: true", gateway)
        self.assertIn("disable-model-invocation: true", gateway)
        self.assertIn("fail-closed", gateway.lower())
        self.assertIn("False down-routing", gateway)
        self.assertIn("decisive automatic oracle", gateway)

    def test_authority_only_topology_omits_gateway(self):
        registry = load_model_registry(ROOT / "config" / "model-registry.json")
        authority = authority_model_id(registry)
        reduced = copy.deepcopy(registry)
        reduced["route_order"] = [authority]
        reduced["role_policies"] = {
            role: {"slots": ["all"], "min_worker_count": 1}
            for role in ("scout", "research", "execute", "debug", "verify")
        }
        reduced = validate_registry(reduced)

        self.assertIsNone(gateway_model_id(reduced))
        files = desired_agent_files(reduced, template_dir=ROOT / ".github" / "agent-templates")
        self.assertNotIn(GATEWAY_FILENAME, files)


if __name__ == "__main__":
    unittest.main()
