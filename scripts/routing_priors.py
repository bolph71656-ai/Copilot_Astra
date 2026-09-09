from __future__ import annotations
import json
from pathlib import Path
from typing import Sequence
from scripts.routing_pricing import probability, non_negative_float

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_PRIORS_PATH=ROOT/'config'/'routing-priors.json'
LOCAL_PRIORS_PATH=ROOT/'config'/'routing-priors.local.json'

def load_prior_bundle(paths:Sequence[Path]):
    entries=[]; human=[]
    for order,path in enumerate(paths):
        raw=json.loads(path.read_text(encoding='utf-8'))
        if raw.get('schema_version')!=1: raise ValueError(f'{path}: unsupported routing-prior schema')
        for row in raw.get('entries',[]): entries.append({**row,'_source_order':order,'_source_path':str(path)})
        for row in raw.get('human_oracles',[]): human.append({**row,'_source_order':order,'_source_path':str(path)})
    return {'entries':entries,'human_oracles':human}

def default_prior_paths(extra_paths:Sequence[Path]=()):
    paths=[DEFAULT_PRIORS_PATH]
    if LOCAL_PRIORS_PATH.exists(): paths.append(LOCAL_PRIORS_PATH)
    return paths+list(extra_paths)

def _reached_score(pattern:str,reached:str):
    if pattern==reached: return 4
    if reached!='direct' and pattern=='after:any': return 2
    if pattern=='*': return 0
    return None

def resolve_model_prior(entries:Sequence[dict],*,task_class:str,oracle_strength:str,model:str,reached_after:str):
    matches=[]
    for row in entries:
        if row.get('model')!=model: continue
        task=str(row.get('task_class','*')); oracle=str(row.get('oracle_strength','*'))
        if task not in {'*',task_class} or oracle not in {'*',oracle_strength}: continue
        rs=_reached_score(str(row.get('reached_after','*')),reached_after)
        if rs is None: continue
        score=(4 if task==task_class else 0)+(2 if oracle==oracle_strength else 0)+rs
        matches.append(((score,int(row.get('_source_order',0))),row))
    if not matches: raise ValueError(f'no routing prior for model={model} reached_after={reached_after}')
    out={}; provenance=[]
    for _,row in sorted(matches,key=lambda x:x[0]):
        for key in ('p_correct','detection_rate'):
            if row.get(key) is not None: out[key]=probability(row[key])
        provenance.append({k:row.get(k) for k in ('task_class','oracle_strength','reached_after','source_kind','samples','_source_path')})
    if not {'p_correct','detection_rate'}<=out.keys(): raise ValueError(f'incomplete routing prior for {model=} {reached_after=}')
    return {**out,'provenance':provenance}

def resolve_human_oracle(rows:Sequence[dict],*,task_class:str,validation_kind:str):
    matches=[]
    for row in rows:
        task=str(row.get('task_class','*')); kind=str(row.get('human_validation_kind','*'))
        if task not in {'*',task_class} or kind not in {'*',validation_kind}: continue
        score=(2 if task==task_class else 0)+(1 if kind==validation_kind else 0)
        matches.append(((score,int(row.get('_source_order',0))),row))
    if not matches: raise ValueError(f'no human oracle prior for {task_class=} {validation_kind=}')
    out={}; provenance=[]
    for _,row in sorted(matches,key=lambda x:x[0]):
        if row.get('detection_rate') is not None: out['detection_rate']=probability(row['detection_rate'])
        if row.get('mean_validation_seconds') is not None: out['mean_validation_seconds']=non_negative_float(str(row['mean_validation_seconds']))
        provenance.append({k:row.get(k) for k in ('task_class','human_validation_kind','source_kind','samples','_source_path')})
    if 'detection_rate' not in out: raise ValueError('human oracle prior missing detection_rate')
    return {**out,'provenance':provenance}
