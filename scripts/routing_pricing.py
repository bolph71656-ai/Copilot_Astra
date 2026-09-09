from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT=Path(__file__).resolve().parents[1]
PRICING_PATH=ROOT/'config'/'pricing.json'

@dataclass(frozen=True)
class Rates:
    fresh_input:float; cached_input:float; cache_write:float; output:float
@dataclass(frozen=True)
class ModelPricing:
    default:Rates; long:Rates; long_threshold:int
@dataclass(frozen=True)
class CallShape:
    fresh_input:int=0; cached_input:int=0; cache_write:int=0; output:int=0; context_tokens:int|None=None

def _load(path:Path=PRICING_PATH):
    raw=json.loads(path.read_text(encoding='utf-8'))
    return {m:ModelPricing(Rates(**s['default']),Rates(**s['long']),int(s['long_threshold'])) for m,s in raw['models'].items()}
PRICING=_load()

def non_negative_int(v:str)->int:
    import argparse
    x=int(v)
    if x<0: raise argparse.ArgumentTypeError('value must be non-negative')
    return x

def non_negative_float(v:str)->float:
    import argparse
    x=float(v)
    if x<0: raise argparse.ArgumentTypeError('value must be non-negative')
    return x

def probability(v:str|float)->float:
    import argparse
    x=float(v)
    if not 0<=x<=1: raise argparse.ArgumentTypeError('probability must be between 0 and 1')
    return x

def tier_for(model:str,requested:str,context_tokens:int)->str:
    if requested in {'default','long'}: return requested
    return 'long' if context_tokens>PRICING[model].long_threshold else 'default'

def model_cost(model:str,fresh_input:int,cached_input:int,cache_write:int,output:int,*,tier:str='auto',context_tokens:int|None=None):
    if model not in PRICING: raise ValueError(f'unknown model: {model}')
    context=fresh_input+cached_input+cache_write if context_tokens is None else context_tokens
    selected=tier_for(model,tier,context); r=getattr(PRICING[model],selected)
    units=(fresh_input*r.fresh_input+cached_input*r.cached_input+cache_write*r.cache_write+output*r.output)/1_000_000
    return units,selected

def calls_cost(model:str,calls:Sequence[CallShape],*,tier:str='auto'):
    total=0.0; tiers=[]
    for c in calls:
        cost,t=model_cost(model,c.fresh_input,c.cached_input,c.cache_write,c.output,tier=tier,context_tokens=c.context_tokens)
        total+=cost; tiers.append(t)
    return total,tiers
