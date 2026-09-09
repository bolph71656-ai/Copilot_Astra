from __future__ import annotations
import itertools
from dataclasses import dataclass
from typing import Iterable, Sequence
from scripts.routing_pricing import probability
from scripts.routing_priors import resolve_model_prior

@dataclass(frozen=True)
class Stage:
    model:str; cost:float; p_correct:float|None=None; detection_rate:float|None=None; latency_seconds:float=0.0; human_detection_rate:float|None=None

def _stage_probs(stage:Stage,entries,task_class,oracle,reached):
    if entries is not None: return resolve_model_prior(entries,task_class=task_class,oracle_strength=oracle,model=stage.model,reached_after=reached)
    if stage.p_correct is None or stage.detection_rate is None: raise ValueError(f'{stage.model}: explicit probabilities required')
    return {'p_correct':probability(stage.p_correct),'detection_rate':probability(stage.detection_rate),'provenance':[{'source_kind':'explicit-stage'}]}

def expected_route_metrics(stages:Iterable[Stage],*,prior_entries=None,task_class='default',oracle_strength='mixed',handoff_units=0.0,failure_penalty_units=0.0,dispatch_units=0.0,defect_penalty_units=0.0,latency_weight=0.0,human_validation_required=False,human_detection_rate=0.0,human_validation_units=0.0,human_validation_seconds=0.0):
    seq=list(stages)
    if not seq: raise ValueError('route must contain at least one stage')
    reach=1.0; cost=dispatch_units if seq[0].model!='astra' else 0.0; latency=correct=hidden=terminal=0.0
    auto_escape_events=human_detect_events=human_checks=0.0; assumptions=[]
    for i,stage in enumerate(seq):
        reached='direct' if i==0 else '>'.join(s.model for s in seq[:i])
        prior=_stage_probs(stage,prior_entries,task_class,oracle_strength,reached)
        p=prior['p_correct']; d=prior['detection_rate']; assumptions.append({'model':stage.model,'reached_after':reached,'p_correct':p,'detection_rate':d,'provenance':prior['provenance']})
        cost+=reach*stage.cost; latency+=reach*stage.latency_seconds
        ok=reach*p; bad=reach*(1-p); auto_detect=bad*d; escaped=bad*(1-d); auto_escape_events+=escaped
        human_detect=0.0
        if human_validation_required:
            hd=human_detection_rate if stage.human_detection_rate is None else stage.human_detection_rate
            checks=ok+escaped; human_checks+=checks; cost+=checks*human_validation_units; latency+=checks*human_validation_seconds
            human_detect=escaped*hd; escaped*=1-hd; human_detect_events+=human_detect
        correct+=ok; hidden+=escaped; detected=auto_detect+human_detect
        if i<len(seq)-1:
            cost+=detected*(failure_penalty_units+handoff_units); reach=detected
        else: terminal=detected
    adjusted=cost+defect_penalty_units*hidden+latency_weight*latency
    return {'expected_units':cost,'expected_latency_seconds':latency,'validated_correct_probability':correct,'hidden_failure_probability':hidden,'terminal_detected_failure_probability':terminal,'expected_auto_escaped_defect_events':auto_escape_events,'expected_human_detected_defect_events':human_detect_events,'expected_human_validation_count':human_checks,'risk_adjusted_units':adjusted,'risk_adjusted_units_per_correct':adjusted/correct if correct>0 else None,'stage_assumptions':assumptions}

def candidate_routes(stages:Sequence[Stage]):
    if not stages:return []
    if len(stages)==1:return [list(stages)]
    final=stages[-1]; prefix=list(stages[:-1]); routes=[]
    for size in range(len(prefix)+1):
        for combo in itertools.combinations(prefix,size): routes.append(list(combo)+[final])
    rank={s.model:i for i,s in enumerate(stages)}
    return sorted(routes,key=lambda r:(rank[r[0].model],len(r),[rank[s.model] for s in r]))

def route_options(stages:Sequence[Stage],*,prior_entries=None,task_class='default',oracle_strength='mixed',dispatch_units=0.0,handoff_units=0.0,failure_penalty_units=0.0,defect_penalty_units=0.0,latency_weight=0.0,max_hidden_failure=1.0,max_terminal_failure=1.0,min_validated_correct=0.0,human_validation_required=False,human_detection_rate=0.0,human_validation_units=0.0,human_validation_seconds=0.0):
    options=[]
    for route in candidate_routes(stages):
        m=expected_route_metrics(route,prior_entries=prior_entries,task_class=task_class,oracle_strength=oracle_strength,dispatch_units=dispatch_units,handoff_units=handoff_units,failure_penalty_units=failure_penalty_units,defect_penalty_units=defect_penalty_units,latency_weight=latency_weight,human_validation_required=human_validation_required,human_detection_rate=human_detection_rate,human_validation_units=human_validation_units,human_validation_seconds=human_validation_seconds)
        reasons=[]
        if m['hidden_failure_probability']>max_hidden_failure: reasons.append('hidden-failure')
        if m['terminal_detected_failure_probability']>max_terminal_failure: reasons.append('terminal-failure')
        if m['validated_correct_probability']<min_validated_correct: reasons.append('validated-correct')
        options.append({'start_model':route[0].model,'path':[s.model for s in route],'viable':not reasons,'rejection_reasons':reasons,**m})
    viable=[o for o in options if o['viable'] and o['risk_adjusted_units_per_correct'] is not None]
    return options,min(viable,key=lambda o:o['risk_adjusted_units_per_correct']) if viable else None
