#!/usr/bin/env python3
"""Offline policy regression for representative Astra routing fixtures."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.route_cost import Stage,route_options
DEFAULT_FIXTURES=ROOT/'config'/'routing-fixtures.json'

def evaluate_fixture(row:dict)->dict:
    use_priors=bool(row.get('prior_entries'))
    stages=[Stage(model=s['model'],cost=float(s['cost']),p_correct=None if use_priors else float(s['p_correct']),detection_rate=None if use_priors else float(s.get('detection_rate',1)),latency_seconds=float(s.get('latency_seconds',0)),human_detection_rate=float(s['human_detection_rate']) if 'human_detection_rate' in s else None) for s in row['stages']]
    entries=[{**item,'_source_order':0,'_source_path':'<fixture>'} for item in row.get('prior_entries',[])] or None
    options,best=route_options(stages,prior_entries=entries,task_class=str(row.get('task_class','default')),oracle_strength=str(row.get('oracle_strength','mixed')),dispatch_units=float(row.get('dispatch_units',0)),handoff_units=float(row.get('handoff_units',0)),failure_penalty_units=float(row.get('failure_penalty_units',0)),defect_penalty_units=float(row.get('defect_penalty_units',0)),latency_weight=float(row.get('latency_weight',0)),max_hidden_failure=float(row.get('max_hidden_failure',1)),max_terminal_failure=float(row.get('max_terminal_failure',1)),min_validated_correct=float(row.get('min_validated_correct',0)),human_validation_required=bool(row.get('human_validation_required',False)),human_detection_rate=float(row.get('human_detection_rate',0)),human_validation_units=float(row.get('human_validation_units',0)),human_validation_seconds=float(row.get('human_validation_seconds',0)))
    path=best['path'] if best else None
    return {'name':row['name'],'expected_path':row['expected_path'],'actual_path':path,'pass':path==row['expected_path'],'options':options}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,default=DEFAULT_FIXTURES);p.add_argument('--json',action='store_true');args=p.parse_args()
    results=[evaluate_fixture(row) for row in json.loads(args.fixtures.read_text(encoding='utf-8'))]
    if args.json:print(json.dumps(results,indent=2,sort_keys=True))
    else:
        for r in results:
            actual=' -> '.join(r['actual_path']) if r['actual_path'] else 'none';print(f"{'PASS' if r['pass'] else 'FAIL'} {r['name']}: expected={' -> '.join(r['expected_path'])}; actual={actual}")
    return 0 if all(r['pass'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
