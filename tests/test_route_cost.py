import argparse, unittest
from scripts.route_cost import CallShape,PRICING,Stage,calls_cost,candidate_routes,cheap_first_success_threshold,evaluate,expected_route_metrics,model_cost,parse_ladder,route_options
class RouteCostTests(unittest.TestCase):
 def test_luna_terra_default_ratio_for_same_mix(self):
  shape=dict(fresh_input=10000,cached_input=50000,cache_write=0,output=3000);l,_=model_cost('luna',**shape,tier='default');t,_=model_cost('terra',**shape,tier='default');self.assertAlmostEqual(t/l,10)
 def test_auto_long_threshold_is_model_specific(self):
  _,l=model_cost('luna',200001,0,0,0);_,t=model_cost('terra',200001,0,0,0);self.assertEqual(l,'long');self.assertEqual(t,'default')
 def test_call_level_pricing_does_not_aggregate_context(self):
  total,tiers=calls_cost('luna',[CallShape(fresh_input=150000),CallShape(fresh_input=150000)]);self.assertEqual(tiers,['default','default']);x,_=model_cost('luna',150000,0,0,0);self.assertAlmostEqual(total,x*2)
 def test_cheap_first_threshold(self):self.assertAlmostEqual(cheap_first_success_threshold(1,10),.1)
 def test_hidden_failure_probability(self):
  m=expected_route_metrics([Stage('luna',1,.8,.5)]);self.assertAlmostEqual(m['validated_correct_probability'],.8);self.assertAlmostEqual(m['hidden_failure_probability'],.1)
 def test_detection_allows_escalation(self):
  m=expected_route_metrics([Stage('luna',1,.8,1),Stage('astra',50,1,1)],handoff_units=1,failure_penalty_units=2);self.assertAlmostEqual(m['validated_correct_probability'],1);self.assertAlmostEqual(m['hidden_failure_probability'],0)
 def test_candidate_routes_can_skip_terra(self):
  paths=[[s.model for s in r] for r in candidate_routes([Stage('luna',1,.8),Stage('terra',10,.95),Stage('sol',20,.99),Stage('astra',50,1)])];self.assertIn(['luna','sol','astra'],paths);self.assertIn(['astra'],paths)
 def test_risk_constraint_rejects_hidden_failure(self):
  opts,b=route_options([Stage('luna',1,.9,0),Stage('terra',10,.98,1),Stage('astra',50,1,1)],max_hidden_failure=.01);self.assertTrue(all(not o['viable'] for o in opts if o['start_model']=='luna'));self.assertNotEqual(b['start_model'],'luna')
 def test_router_can_skip_luna(self):
  _,b=route_options([Stage('luna',1,.01,1),Stage('terra',10,.95,1),Stage('sol',20,.99,1),Stage('astra',50,1,1)],dispatch_units=.5,handoff_units=1,failure_penalty_units=2);self.assertEqual(b['start_model'],'terra')
 def test_router_keeps_luna_when_success_high(self):
  _,b=route_options([Stage('luna',1,.95,1),Stage('terra',10,.98,1),Stage('sol',20,.995,1),Stage('astra',50,1,1)],dispatch_units=.25,handoff_units=.5,failure_penalty_units=.5);self.assertEqual(b['start_model'],'luna')
 def test_dispatch_can_favor_astra(self):
  _,b=route_options([Stage('luna',.01,.99,1),Stage('terra',.1,.999,1),Stage('astra',.5,1,1)],dispatch_units=1);self.assertEqual(b['start_model'],'astra')
 def test_defect_penalty_changes_route(self):
  s=[Stage('luna',1,.9,.5),Stage('astra',30,1,1)];_,a=route_options(s);_,b=route_options(s,defect_penalty_units=1000);self.assertEqual(a['start_model'],'luna');self.assertEqual(b['start_model'],'astra')
 def test_latency_weight_changes_route(self):
  s=[Stage('luna',1,.8,1,100),Stage('astra',10,1,1,5)];_,a=route_options(s);_,b=route_options(s,latency_weight=1);self.assertEqual(a['start_model'],'luna');self.assertEqual(b['start_model'],'astra')
 def test_parse_rejects_duplicate(self):
  with self.assertRaises(argparse.ArgumentTypeError):parse_ladder('luna:.8,luna:.9,astra:1')
 def test_parse_accepts_detection(self):self.assertEqual(parse_ladder('luna:.8:.95,astra:1:1'),[('luna',.8,.95),('astra',1,1)])
 def test_evaluate_recommendation(self):
  a=argparse.Namespace(fresh_input=1000,cached_input=0,cache_write=0,output=100,context_tokens=None,tier='auto',ladder=parse_ladder('luna:.8:1,terra:.95:1,astra:1:1'),dispatch_units=0,handoff_units=0,failure_penalty=0,defect_penalty=0,max_hidden_failure=1,latency_weight=0,latency={});r=evaluate(a);self.assertEqual(set(r['models']),set(PRICING));self.assertIsNotNone(r['recommended_route'])
if __name__=='__main__':unittest.main()
