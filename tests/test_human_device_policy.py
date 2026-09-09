from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];AGENT_DIR=ROOT/'.github'/'agents'
WRITERS=['execute-luna.agent.md','execute-terra.agent.md','execute-sol.agent.md','debug-sol.agent.md'];READONLY=['scout-luna.agent.md','research-luna.agent.md','research-terra.agent.md'];VERIFIERS=['verify-luna.agent.md','verify-terra.agent.md','verify-sol.agent.md']

class AgentPolicyTests(unittest.TestCase):
    def test_all_agents_target_vscode(self):
        for path in AGENT_DIR.glob('*.agent.md'):self.assertIn('target: vscode',path.read_text(encoding='utf-8'),path.name)
    def test_subagents_are_protected_and_non_recursive(self):
        for path in AGENT_DIR.glob('*.agent.md'):
            if path.name=='astra-orchestrator.agent.md':continue
            text=path.read_text(encoding='utf-8');self.assertIn('agents: []',text,path.name);self.assertIn('disable-model-invocation: true',text,path.name);self.assertNotIn("'agent'",text.split('---',2)[1],path.name)
    def test_orchestrator_explicitly_allowlists_subagents(self):
        text=(AGENT_DIR/'astra-orchestrator.agent.md').read_text(encoding='utf-8')
        for name in ('Scout Luna','Research Luna','Research Terra','Execute Luna','Execute Terra','Execute Sol','Debug Sol','Verify Luna','Verify Terra','Verify Sol'):self.assertIn(name,text)
        self.assertIn('not an infallible fallback',text);self.assertIn('reached_after',text)
    def test_writer_human_state_contract(self):
        for name in WRITERS:
            text=(AGENT_DIR/name).read_text(encoding='utf-8');self.assertIn('NEEDS_HUMAN_VALIDATION',text,name);self.assertIn('ATTRIBUTION_HINTS',text,name);self.assertIn('unknown',text.lower(),name)
    def test_role_specific_status_contracts(self):
        for name in READONLY:self.assertIn('DONE | BLOCKED | NEEDS_PARENT',(AGENT_DIR/name).read_text(encoding='utf-8'),name)
        for name in VERIFIERS:self.assertIn('PASS | FAIL | BLOCKED | NEEDS_PARENT',(AGENT_DIR/name).read_text(encoding='utf-8'),name)
    def test_transition_design_records_exist(self):
        for rel in ('docs/astra-routing.md','docs/adr/0004-transition-aware-empirical-routing.md','docs/research/2026-09-10-routing-review.md'):self.assertTrue((ROOT/rel).exists(),rel)

if __name__=='__main__':unittest.main()
