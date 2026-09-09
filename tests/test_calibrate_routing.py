import json
import unittest

from scripts.calibrate_routing import beta_mean, routing_prior_document, summarize, validate_observation

class CalibrationTests(unittest.TestCase):
    def test_beta_mean(self):
        self.assertAlmostEqual(beta_mean(3,1,1,1),4/6)

    def test_direct_and_escalated_priors_are_separate(self):
        result=summarize([
            {'task_class':'mechanical','start_model':'sol','reached_after':'direct','oracle_strength':'deterministic','validated_correct':True},
            {'task_class':'mechanical','start_model':'sol','reached_after':'luna>terra','oracle_strength':'deterministic','validated_correct':False,'failure_detected':True,'failure_attribution':'implementation'},
        ])
        self.assertEqual(len(result['posteriors']),2)

    def test_pending_human_validation_is_not_failure(self):
        row=summarize([{'task_class':'device-ui','start_model':'luna','oracle_strength':'human-device','human_validation_required':True,'human_validation_performed':False,'validation_state':'needs_human_validation'}])['posteriors'][0]
        self.assertEqual(row['pending_human'],1);self.assertEqual(row['resolved_samples'],0);self.assertIsNone(row['p_correct_mean'])

    def test_environment_failure_does_not_penalize_model(self):
        row=summarize([{'task_class':'bluetooth','start_model':'terra','oracle_strength':'human-device','human_validation_required':True,'human_validation_performed':True,'validation_state':'failed','failure_attribution':'device'}])['posteriors'][0]
        self.assertEqual(row['non_model_failures'],1);self.assertEqual(row['resolved_samples'],0)

    def test_unattributed_failure_does_not_penalize_model(self):
        row=summarize([{'task_class':'network','start_model':'luna','oracle_strength':'mixed','validation_state':'failed'}])['posteriors'][0]
        self.assertEqual(row['unattributed_failures'],1);self.assertEqual(row['resolved_samples'],0);self.assertIsNone(row['p_correct_mean'])

    def test_implementation_failure_updates_model_prior(self):
        row=summarize([{'task_class':'network','start_model':'luna','oracle_strength':'mixed','validation_state':'failed','failure_attribution':'implementation','failure_detected':True}])['posteriors'][0]
        self.assertEqual(row['resolved_samples'],1);self.assertEqual(row['failures'],1);self.assertIsNotNone(row['p_correct_mean'])

    def test_human_validated_requires_performed(self):
        with self.assertRaises(ValueError):validate_observation({'validation_state':'human_validated','human_validation_required':True,'human_validation_performed':False})

    def test_validated_correct_cannot_bypass_required_human_check(self):
        with self.assertRaises(ValueError):validate_observation({'human_validation_required':True,'human_validation_performed':False,'validated_correct':True})

    def test_human_detection_requires_human_performed(self):
        with self.assertRaises(ValueError):validate_observation({'validation_state':'failed','human_validation_required':True,'human_validation_performed':False,'human_detected_defect':True})

    def test_human_oracle_is_calibrated_separately(self):
        result=summarize([
            {'task_class':'device-ui','start_model':'luna','oracle_strength':'human-device','human_validation_required':True,'human_validation_performed':True,'human_validation_kind':'ios-device','validation_state':'failed','failure_attribution':'implementation','human_detected_defect':True,'human_validation_seconds':30},
            {'task_class':'device-ui','start_model':'luna','oracle_strength':'human-device','human_validation_required':True,'human_validation_performed':True,'human_validation_kind':'ios-device','validation_state':'human_validated','hidden_defect':True,'failure_attribution':'implementation','human_validation_seconds':10},
        ])
        human=result['human_oracle_posteriors'][0];self.assertAlmostEqual(human['human_detection_rate_mean'],0.5);self.assertAlmostEqual(human['mean_human_validation_seconds'],20)

    def test_routing_prior_document_is_machine_readable(self):
        result=summarize([
            {'task_class':'mechanical','start_model':'luna','reached_after':'direct','oracle_strength':'deterministic','validated_correct':True},
            {'task_class':'mechanical','start_model':'luna','reached_after':'direct','oracle_strength':'deterministic','validation_state':'failed','failure_attribution':'implementation','failure_detected':True},
        ])
        doc=routing_prior_document(result);self.assertEqual(doc['schema_version'],1);self.assertEqual(doc['entries'][0]['model'],'luna');self.assertEqual(doc['entries'][0]['reached_after'],'direct');json.dumps(doc)

if __name__=='__main__':unittest.main()
