from pathlib import Path
import unittest

from scripts.model_registry import load_model_registry
from scripts.sync_model_config import GATEWAY_FILENAME, PARENT_FILENAME, desired_agent_specs

ROOT=Path(__file__).resolve().parents[1]
AGENT_DIR=ROOT/".github"/"agents"


class AgentPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=load_model_registry(ROOT/"config"/"model-registry.json")
        cls.specs=desired_agent_specs(cls.registry)

    def test_all_agents_target_vscode(self):
        for path in AGENT_DIR.glob("*.agent.md"):
            self.assertIn("target: vscode", path.read_text(encoding="utf-8"), path.name)

    def test_subagents_are_protected_and_non_recursive(self):
        for path in AGENT_DIR.glob("*.agent.md"):
            if path.name in {PARENT_FILENAME, GATEWAY_FILENAME}:
                continue
            text=path.read_text(encoding="utf-8")
            self.assertIn("agents: []",text,path.name)
            self.assertIn("disable-model-invocation: true",text,path.name)
            self.assertNotIn("'agent'",text.split("---",2)[1],path.name)

    def test_gateway_is_entry_layer_not_worker_subagent(self):
        path=AGENT_DIR/GATEWAY_FILENAME
        if path.exists():
            text=path.read_text(encoding="utf-8")
            self.assertIn('agents: ["Astra Orchestrator"]',text)
            self.assertIn("user-invocable: true",text)
            self.assertIn("disable-model-invocation: true",text)

    def test_orchestrator_explicitly_allowlists_current_generated_subagents(self):
        text=(AGENT_DIR/PARENT_FILENAME).read_text(encoding="utf-8")
        for spec in self.specs:
            self.assertIn(spec.name,text)
        self.assertIn("not an infallible fallback",text)
        self.assertIn("reached_after",text)

    def test_writer_human_state_contract(self):
        for spec in self.specs:
            if not spec.writable:
                continue
            text=(AGENT_DIR/spec.filename).read_text(encoding="utf-8")
            self.assertIn("NEEDS_HUMAN_VALIDATION",text,spec.filename)
            self.assertIn("ATTRIBUTION_HINTS",text,spec.filename)
            self.assertIn("unknown",text.lower(),spec.filename)

    def test_role_specific_status_contracts(self):
        for spec in self.specs:
            text=(AGENT_DIR/spec.filename).read_text(encoding="utf-8")
            if spec.role in {"scout","research"}:
                self.assertIn("DONE | BLOCKED | NEEDS_PARENT",text,spec.filename)
            elif spec.role=="verify":
                self.assertIn("PASS | FAIL | BLOCKED | NEEDS_PARENT",text,spec.filename)

    def test_transition_design_records_exist(self):
        for rel in (
            "docs/astra-routing.md",
            "docs/adr/0004-transition-aware-empirical-routing.md",
            "docs/adr/0005-registry-driven-model-topology.md",
            "docs/research/2026-09-10-routing-review.md",
        ):
            self.assertTrue((ROOT/rel).exists(),rel)


if __name__=="__main__":
    unittest.main()
