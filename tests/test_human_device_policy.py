from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRITERS = [
    ROOT / '.github' / 'agents' / 'execute-luna.agent.md',
    ROOT / '.github' / 'agents' / 'execute-terra.agent.md',
    ROOT / '.github' / 'agents' / 'execute-sol.agent.md',
    ROOT / '.github' / 'agents' / 'debug-sol.agent.md',
]


class HumanDevicePolicyTests(unittest.TestCase):
    def test_orchestrator_has_explicit_human_validation_state_machine(self):
        text = (ROOT / '.github' / 'agents' / 'astra-orchestrator.agent.md').read_text(encoding='utf-8')
        for token in ('NEEDS_HUMAN_VALIDATION', 'BLOCKED', 'failure_attribution', 'd_human'):
            self.assertIn(token, text)

    def test_writers_never_claim_done_before_required_human_validation(self):
        for path in WRITERS:
            text = path.read_text(encoding='utf-8')
            self.assertIn('STATUS=NEEDS_HUMAN_VALIDATION', text, path.name)
            self.assertIn('HUMAN_VALIDATION', text, path.name)
            self.assertIn('Do not mark pending or unavailable human validation as `FAILED`', text, path.name)

    def test_protocol_separates_pending_validation_from_failure(self):
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('NEEDS_HUMAN_VALIDATION', text)
        self.assertIn('must not update model success priors', text)
        self.assertIn('failure', text.lower())

    def test_human_validation_design_record_exists(self):
        for rel in ('docs/human-device-validation.md', 'docs/adr/0003-human-validation-as-oracle.md'):
            path = ROOT / rel
            self.assertTrue(path.exists(), rel)
            text = path.read_text(encoding='utf-8')
            self.assertIn('human', text.lower())
            self.assertIn('validation', text.lower())


if __name__ == '__main__':
    unittest.main()
