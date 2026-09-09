#!/usr/bin/env python3
"""Transition-aware risk/cost estimator for Copilot Astra routing."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from scripts.routing_pricing import CallShape,PRICING,calls_cost,model_cost,non_negative_float,non_negative_int,probability
from scripts.routing_priors import DEFAULT_PRIORS_PATH,LOCAL_PRIORS_PATH,default_prior_paths,load_prior_bundle,resolve_human_oracle,resolve_model_prior
from scripts.routing_core import Stage,candidate_routes,expected_route_metrics,route_options

ROOT=Path(__file__).resolve().parents[1]
RISK_POLICY_PATH=ROOT/'config'/'risk-policy.json'

def parse_ladder(value:str):
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

def cheap_first_success_threshold(cheap_cost:float,expensive_cost:float):
    return None if expensive_cost<=0 else cheap_cost/expensive_cost

def parse_latency(value:str):
    out={}
    if not value:return out
    for raw in value.split(','):
        model,seconds=raw.split(':',1);model=model.strip().lower()
        if model not in PRICING:raise argparse.ArgumentTypeError(f'unknown latency model: {model}')
        out[model]=non_negative_float(seconds)
    return out

def load_risk_policy(path:Path=RISK_POLICY_PATH):
    raw=json.loads(path.read_text(encoding='utf-8'))
    if raw.get('schema_version')!=1:raise ValueError('unsupported risk-policy schema')
    return raw

def resolve_risk_constraints(args):
    policy=load_risk_policy();name=getattr(args,'risk_class',None) or policy.get('default_class','standard')
    if name not in policy['classes']:raise ValueError(f'unknown risk class: {name}')
    out=dict(policy['classes'][name])
    for key in ('max_hidden_failure','max_terminal_failure','min_validated_correct'):
        value=getattr(args,key,None)
        if value is not None:out[key]=value
    return {'risk_class':name,**out}

def build_parser():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('fresh-input','cached-input','cache-write','output'):p.add_argument('--'+flag,type=non_negative_int,default=0)
    p.add_argument('--context-tokens',type=non_negative_int,default=None);p.add_argument('--tier',choices=('auto','default','long'),default='auto')
    p.add_argument('--ladder',type=parse_ladder,default=None);p.add_argument('--models',default='luna,terra,sol,astra')
    p.add_argument('--task-class',default='default');p.add_argument('--oracle-strength',default='mixed');p.add_argument('--priors',type=Path,action='append',default=[])
    p.add_argument('--risk-class',default=None);p.add_argument('--max-hidden-failure',type=probability,default=None);p.add_argument('--max-terminal-failure',type=probability,default=None);p.add_argument('--min-validated-correct',type=probability,default=None)
    p.add_argument('--dispatch-units',type=non_negative_float,default=0);p.add_argument('--handoff-units',type=non_negative_float,default=0);p.add_argument('--failure-penalty',type=non_negative_float,default=0);p.add_argument('--defect-penalty',type=non_negative_float,default=0)
    p.add_argument('--latency-weight',type=non_negative_float,default=0);p.add_argument('--latency',type=parse_latency,default={})
    p.add_argument('--human-validation-required',action='store_true');p.add_argument('--human-validation-kind',default='default');p.add_argument('--human-detection-rate',type=probability,default=None);p.add_argument('--human-validation-units',type=non_negative_float,default=0);p.add_argument('--human-validation-seconds',type=non_negative_float,default=None);p.add_argument('--json',action='store_true')
    return p

def evaluate(args):
    costs={}
    for model in PRICING:
        units,tier=model_cost(model,args.fresh_input,args.cached_input,args.cache_write,args.output,tier=args.tier,context_tokens=args.context_tokens)
        costs[model]={'units':units,'usd':units/100,'tier':tier}
    bundle=entries=None
    if args.ladder is not None:
        stages=[Stage(m,costs[m]['units'],pc,d,args.latency.get(m,0)) for m,pc,d in args.ladder]
    else:
        models=[m.strip().lower() for m in args.models.split(',') if m.strip()]
        if not models or models[-1]!='astra' or len(models)!=len(set(models)) or any(m not in PRICING for m in models):raise ValueError('--models must be unique known models ending in astra')
        bundle=load_prior_bundle(default_prior_paths(args.priors));entries=bundle['entries'];stages=[Stage(m,costs[m]['units'],latency_seconds=args.latency.get(m,0)) for m in models]
    hd=0 if args.human_detection_rate is None else args.human_detection_rate;hs=0 if args.human_validation_seconds is None else args.human_validation_seconds;human_prior=None
    if args.human_validation_required and args.human_detection_rate is None:
        bundle=bundle or load_prior_bundle(default_prior_paths(args.priors));human_prior=resolve_human_oracle(bundle['human_oracles'],task_class=args.task_class,validation_kind=args.human_validation_kind);hd=human_prior['detection_rate']
        if args.human_validation_seconds is None:hs=human_prior.get('mean_validation_seconds',0)
    risk=resolve_risk_constraints(args)
    options,best=route_options(stages,prior_entries=entries,task_class=args.task_class,oracle_strength=args.oracle_strength,dispatch_units=args.dispatch_units,handoff_units=args.handoff_units,failure_penalty_units=args.failure_penalty,defect_penalty_units=args.defect_penalty,latency_weight=args.latency_weight,max_hidden_failure=risk['max_hidden_failure'],max_terminal_failure=risk['max_terminal_failure'],min_validated_correct=risk['min_validated_correct'],human_validation_required=args.human_validation_required,human_detection_rate=hd,human_validation_units=args.human_validation_units,human_validation_seconds=hs)
    return {'models':costs,'routing_context':{'task_class':args.task_class,'oracle_strength':args.oracle_strength,**risk},'human_validation':{'required':args.human_validation_required,'kind':args.human_validation_kind,'detection_rate':hd,'validation_units':args.human_validation_units,'validation_seconds':hs,'prior':human_prior},'start_options':options,'recommended_route':best}

def main():
    args=build_parser().parse_args();result=evaluate(args)
    if args.json:print(json.dumps(result,indent=2,sort_keys=True));return 0
    c=result['routing_context'];print(f"risk={c['risk_class']} task={c['task_class']} oracle={c['oracle_strength']}");print('Candidate routes')
    for o in result['start_options']:
        suffix='' if o['viable'] else ' [rejected: '+','.join(o['rejection_reasons'])+']'
        print(f"{' -> '.join(o['path']):<36} correct={o['validated_correct_probability']:.4%} hidden={o['hidden_failure_probability']:.4%} terminal={o['terminal_detected_failure_probability']:.4%} score={o['risk_adjusted_units_per_correct']}{suffix}")
    best=result['recommended_route'];print('recommended route:',' -> '.join(best['path']) if best else 'none');return 0

if __name__=='__main__':raise SystemExit(main())
