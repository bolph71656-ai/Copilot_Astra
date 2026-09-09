import argparse
import unittest
from scripts.route_cost import CallShape,DEFAULT_PRIORS_PATH,PRICING,Stage,calls_cost,candidate_routes,default_prior_paths,evaluate,expected_route_metrics,load_prior_bundle,model_cost,parse_ladder,resolve_model_prior,route_options

class RouteCostTests(unittest.TestCase):
    def test_luna_terra_default_ratio_for_same_mix(self):
        shape=dict(fresh_input=10_000,cached_input=50_000,cache_write=0,output=3_000);luna,_=model_cost('luna',**shape,tier='default');terra,_=model_cost('terra',**shape,tier='default');self.assertAlmostEqual(terra/luna,10)
    def test_auto_long_threshold_is_model_specific(self):
        _,l=model_cost('luna',200_001,0,0,0);_,t=model_cost('terra',200_001,0,0,0);self.assertEqual(l,'long');self.assertEqual(t,'default')
    def test_context_fallback_counts_cache_write(self):self.assertEqual(model_cost('luna',150_000,0,60_001,0)[1],'long')
    def test_explicit_context_tokens_override_inference(self):self.assertEqual(model_cost('luna',150_000,0,60_001,0,context_tokens=190_000)[1],'default')
    def test_call_level_pricing_does_not_aggregate_context(self):
        total,tiers=calls_cost('luna',[CallShape(fresh_input=150_000),CallShape(fresh_input=150_000)]);self.assertEqual(tiers,['default','default']);one,_=model_cost('luna',150_000,0,0,0);self.assertAlmostEqual(total,one*2)
    def test_candidate_routes_can_skip_terra(self):
        paths=[[s.model for s in route] for route in candidate_routes([Stage('luna',1,.8,1),Stage('terra',10,.95,1),Stage('sol',20,.99,1),Stage('astra',50,.995,.995)])];self.assertIn(['luna','sol','astra'],paths);self.assertIn(['astra'],paths)
    def test_seed_astra_is_not_infallible(self):
        b=load_prior_bundle([DEFAULT_PRIORS_PATH]);direct=resolve_model_prior(b['entries'],task_class='default',oracle_strength='mixed',model='astra',reached_after='direct');after=resolve_model_prior(b['entries'],task_class='default',oracle_strength='mixed',model='astra',reached_after='luna');self.assertLess(direct['p_correct'],1);self.assertLess(after['p_correct'],direct['p_correct'])
    def test_transition_prior_differs_from_direct(self):
        e=[{'task_class':'*','oracle_strength':'*','model':'sol','reached_after':'direct','p_correct':.99,'detection_rate':1,'_source_order':0},{'task_class':'*','oracle_strength':'*','model':'sol','reached_after':'after:any','p_correct':.3,'detection_rate':1,'_source_order':0}];self.assertEqual(resolve_model_prior(e,task_class='x',oracle_strength='mixed',model='sol',reached_after='direct')['p_correct'],.99);self.assertEqual(resolve_model_prior(e,task_class='x',oracle_strength='mixed',model='sol',reached_after='luna')['p_correct'],.3)
    def test_exact_transition_beats_after_any(self):
        e=[{'task_class':'*','oracle_strength':'*','model':'astra','reached_after':'after:any','p_correct':.8,'detection_rate':.9,'_source_order':0},{'task_class':'*','oracle_strength':'*','model':'astra','reached_after':'luna>sol','p_correct':.95,'detection_rate':.99,'_source_order':0}];p=resolve_model_prior(e,task_class='x',oracle_strength='mixed',model='astra',reached_after='luna>sol');self.assertEqual(p['p_correct'],.95);self.assertEqual(p['detection_rate'],.99)
    def test_overlay_can_supply_partial_more_specific_prior(self):
        e=[{'task_class':'*','oracle_strength':'*','model':'terra','reached_after':'direct','p_correct':.8,'detection_rate':.9,'_source_order':0},{'task_class':'mechanical','oracle_strength':'deterministic','model':'terra','reached_after':'direct','p_correct':.95,'_source_order':1}];p=resolve_model_prior(e,task_class='mechanical',oracle_strength='deterministic',model='terra',reached_after='direct');self.assertEqual(p['p_correct'],.95);self.assertEqual(p['detection_rate'],.9)
    def test_terminal_failure_constraint_rejects_route(self):
        o,b=route_options([Stage('astra',1,p_correct=.9,detection_rate=1)],max_terminal_failure=.05);self.assertFalse(o[0]['viable']);self.assertIn('terminal-failure',o[0]['rejection_reasons']);self.assertIsNone(b)
    def test_min_validated_correct_constraint_rejects_route(self):
        o,b=route_options([Stage('astra',1,p_correct=.9,detection_rate=0)],min_validated_correct=.95);self.assertFalse(o[0]['viable']);self.assertIn('validated-correct',o[0]['rejection_reasons']);self.assertIsNone(b)
    def test_human_oracle_reduces_hidden_failure(self):
        m=expected_route_metrics([Stage('luna',1,.8,.5)],human_validation_required=True,human_detection_rate=.9);self.assertAlmostEqual(m['hidden_failure_probability'],.01);self.assertAlmostEqual(m['expected_human_detected_defect_events'],.09);self.assertAlmostEqual(m['expected_human_validation_count'],.9)
    def test_event_metrics_are_named_as_expected_counts(self):
        m=expected_route_metrics([Stage('luna',1,.5,0),Stage('astra',1,.5,0)],human_validation_required=True,human_detection_rate=1);self.assertIn('expected_human_detected_defect_events',m);self.assertIn('expected_human_validation_count',m);self.assertNotIn('human_detected_failure_probability',m)
    def test_parse_ladder_rejects_duplicate(self):
        with self.assertRaises(argparse.ArgumentTypeError):parse_ladder('luna:.8,luna:.9,astra:.99')
    def test_evaluate_uses_priors_when_ladder_omitted(self):
        args=argparse.Namespace(fresh_input=1000,cached_input=0,cache_write=0,output=100,context_tokens=None,tier='auto',ladder=None,models='luna,terra,sol,astra',task_class='default',oracle_strength='mixed',priors=[],risk_class='standard',max_hidden_failure=None,max_terminal_failure=None,min_validated_correct=None,dispatch_units=0,handoff_units=0,failure_penalty=0,defect_penalty=0,latency_weight=0,latency={},human_validation_required=False,human_validation_kind='default',human_detection_rate=None,human_validation_units=0,human_validation_seconds=None);r=evaluate(args);self.assertIsNotNone(r['recommended_route']);self.assertTrue(r['recommended_route']['stage_assumptions']);self.assertLess(r['start_options'][-1]['stage_assumptions'][0]['p_correct'],1)
    def test_default_prior_paths_include_seed(self):self.assertEqual(default_prior_paths()[0],DEFAULT_PRIORS_PATH)

if __name__=='__main__':unittest.main()
