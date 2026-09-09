#!/usr/bin/env python3
"""Risk-aware cost estimator for Copilot Astra routing."""
from __future__ import annotations
import argparse,itertools,json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable,Sequence
ROOT=Path(__file__).resolve().parents[1];PRICING_PATH=ROOT/'config'/'pricing.json'
@dataclass(frozen=True)
class Rates:fresh_input:float;cached_input:float;cache_write:float;output:float
@dataclass(frozen=True)
class ModelPricing:default:Rates;long:Rates;long_threshold:int
@dataclass(frozen=True)
class CallShape:fresh_input:int=0;cached_input:int=0;cache_write:int=0;output:int=0;context_tokens:int|None=None
@dataclass(frozen=True)
class Stage:model:str;cost:float;p_correct:float;detection_rate:float=1.0;latency_seconds:float=0.0
def _load_pricing():
 raw=json.loads(PRICING_PATH.read_text(encoding='utf-8'));return {m:ModelPricing(Rates(**s['default']),Rates(**s['long']),int(s['long_threshold'])) for m,s in raw['models'].items()}
PRICING=_load_pricing()
def non_negative_int(v):
 p=int(v)
 if p<0:raise argparse.ArgumentTypeError('value must be non-negative')
 return p
def non_negative_float(v):
 p=float(v)
 if p<0:raise argparse.ArgumentTypeError('value must be non-negative')
 return p
def probability(v):
 p=float(v)
 if not 0<=p<=1:raise argparse.ArgumentTypeError('probability must be between 0 and 1')
 return p
def tier_for(model,requested,context_tokens):return requested if requested in {'default','long'} else ('long' if context_tokens>PRICING[model].long_threshold else 'default')
def model_cost(model,fresh_input,cached_input,cache_write,output,*,tier='auto',context_tokens=None):
 if model not in PRICING:raise ValueError(f'unknown model: {model}')
 selected=tier_for(model,tier,fresh_input+cached_input if context_tokens is None else context_tokens);r=getattr(PRICING[model],selected)
 return (fresh_input*r.fresh_input+cached_input*r.cached_input+cache_write*r.cache_write+output*r.output)/1_000_000,selected
def calls_cost(model,calls:Sequence[CallShape],*,tier='auto'):
 total=0.0;tiers=[]
 for c in calls:
  cost,t=model_cost(model,c.fresh_input,c.cached_input,c.cache_write,c.output,tier=tier,context_tokens=c.context_tokens);total+=cost;tiers.append(t)
 return total,tiers
def parse_ladder(value):
 stages=[];seen=set()
 for raw in value.split(','):
  if not raw.strip():continue
  parts=[p.strip() for p in raw.split(':')]
  if len(parts) not in {2,3}:raise argparse.ArgumentTypeError('ladder entries must be model:p_correct[:detection_rate]')
  model=parts[0].lower()
  if model not in PRICING:raise argparse.ArgumentTypeError(f'unknown model in ladder: {model}')
  if model in seen:raise argparse.ArgumentTypeError(f'duplicate model in ladder: {model}')
  seen.add(model);stages.append((model,probability(parts[1]),probability(parts[2]) if len(parts)==3 else 1.0))
 if not stages:raise argparse.ArgumentTypeError('ladder must contain at least one stage')
 return stages
def expected_route_metrics(stages:Iterable[Stage],*,handoff_units=0.0,failure_penalty_units=0.0,dispatch_units=0.0,defect_penalty_units=0.0,latency_weight=0.0):
 s=list(stages)
 if not s:raise ValueError('route must contain at least one stage')
 reach=1.0;cost=dispatch_units if s[0].model!='astra' else 0.0;lat=correct=hidden=terminal=0.0
 for i,stage in enumerate(s):
  cost+=reach*stage.cost;lat+=reach*stage.latency_seconds;ok=reach*stage.p_correct;bad=reach*(1-stage.p_correct);escape=bad*(1-stage.detection_rate);detected=bad*stage.detection_rate;correct+=ok;hidden+=escape
  if i<len(s)-1:cost+=detected*(failure_penalty_units+handoff_units);reach=detected
  else:terminal=detected;reach=0.0
 adjusted=cost+defect_penalty_units*hidden+latency_weight*lat
 return {'expected_units':cost,'expected_latency_seconds':lat,'validated_correct_probability':correct,'hidden_failure_probability':hidden,'terminal_detected_failure_probability':terminal,'risk_adjusted_units':adjusted,'risk_adjusted_units_per_correct':adjusted/correct if correct>0 else None}
def candidate_routes(stages:Sequence[Stage]):
 if not stages:return []
 if len(stages)==1:return [list(stages)]
 final=stages[-1];prefix=list(stages[:-1]);routes=[]
 for size in range(len(prefix)+1):
  for combo in itertools.combinations(prefix,size):routes.append(list(combo)+[final])
 rank={s.model:i for i,s in enumerate(stages)};routes.sort(key=lambda r:(rank[r[0].model],len(r),[rank[s.model] for s in r]));return routes
def route_options(stages:Sequence[Stage],*,dispatch_units=0.0,handoff_units=0.0,failure_penalty_units=0.0,defect_penalty_units=0.0,latency_weight=0.0,max_hidden_failure=1.0):
 options=[]
 for route in candidate_routes(stages):
  m=expected_route_metrics(route,dispatch_units=dispatch_units,handoff_units=handoff_units,failure_penalty_units=failure_penalty_units,defect_penalty_units=defect_penalty_units,latency_weight=latency_weight);viable=m['hidden_failure_probability']<=max_hidden_failure;options.append({'start_model':route[0].model,'path':[s.model for s in route],'viable':viable,**m})
 viable=[o for o in options if o['viable'] and o['risk_adjusted_units_per_correct'] is not None];return options,(min(viable,key=lambda o:o['risk_adjusted_units_per_correct']) if viable else None)
def cheap_first_success_threshold(cheap_cost,expensive_cost):return None if expensive_cost<=0 else cheap_cost/expensive_cost
def parse_latency(value):
 out={}
 if not value:return out
 for raw in value.split(','):
  model,seconds=raw.split(':',1);model=model.strip().lower()
  if model not in PRICING:raise argparse.ArgumentTypeError(f'unknown latency model: {model}')
  out[model]=non_negative_float(seconds)
 return out
def build_parser():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fresh-input',type=non_negative_int,default=0);p.add_argument('--cached-input',type=non_negative_int,default=0);p.add_argument('--cache-write',type=non_negative_int,default=0);p.add_argument('--output',type=non_negative_int,default=0);p.add_argument('--context-tokens',type=non_negative_int,default=None);p.add_argument('--tier',choices=('auto','default','long'),default='auto');p.add_argument('--ladder',type=parse_ladder,default=parse_ladder('luna:0.80:0.99,terra:0.95:0.99,sol:0.99:0.995,astra:1:1'));p.add_argument('--dispatch-units',type=non_negative_float,default=0.0);p.add_argument('--handoff-units',type=non_negative_float,default=0.0);p.add_argument('--failure-penalty',type=non_negative_float,default=0.0);p.add_argument('--defect-penalty',type=non_negative_float,default=0.0);p.add_argument('--max-hidden-failure',type=probability,default=1.0);p.add_argument('--latency-weight',type=non_negative_float,default=0.0);p.add_argument('--latency',type=parse_latency,default={});p.add_argument('--json',action='store_true');return p
def evaluate(args):
 costs={}
 for model in PRICING:
  units,t=model_cost(model,args.fresh_input,args.cached_input,args.cache_write,args.output,tier=args.tier,context_tokens=args.context_tokens);costs[model]={'units':units,'usd':units/100,'tier':t}
 stages=[Stage(model,costs[model]['units'],pc,d,args.latency.get(model,0.0)) for model,pc,d in args.ladder];options,best=route_options(stages,dispatch_units=args.dispatch_units,handoff_units=args.handoff_units,failure_penalty_units=args.failure_penalty,defect_penalty_units=args.defect_penalty,latency_weight=args.latency_weight,max_hidden_failure=args.max_hidden_failure)
 return {'models':costs,'start_options':options,'recommended_route':best}
def main():
 args=build_parser().parse_args();result=evaluate(args)
 if args.json:print(json.dumps(result,indent=2,sort_keys=True));return 0
 print('Candidate routes')
 for o in result['start_options']:print(' -> '.join(o['path']),f"risk={o['hidden_failure_probability']:.4%}",f"score={o['risk_adjusted_units_per_correct']}",'' if o['viable'] else '[risk-rejected]')
 best=result['recommended_route'];print('recommended route:', ' -> '.join(best['path']) if best else 'none');return 0
if __name__=='__main__':raise SystemExit(main())
