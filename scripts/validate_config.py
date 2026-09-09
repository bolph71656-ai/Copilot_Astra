#!/usr/bin/env python3
"""Static guardrails for physical agents and routing configuration."""
from __future__ import annotations
import ast, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT_DIR=ROOT/'.github'/'agents'; ORCHESTRATOR='Astra Orchestrator'; MODELS={'luna','terra','sol','astra'}
EXPECTED={
'astra-orchestrator.agent.md':('Astra Orchestrator','GPT-6 Astra (copilot)',True,True),'scout-luna.agent.md':('Scout Luna','GPT-5.6 Luna (copilot)',False,False),'research-luna.agent.md':('Research Luna','GPT-5.6 Luna (copilot)',False,False),'research-terra.agent.md':('Research Terra','GPT-5.6 Terra (copilot)',False,False),'execute-luna.agent.md':('Execute Luna','GPT-5.6 Luna (copilot)',False,True),'execute-terra.agent.md':('Execute Terra','GPT-5.6 Terra (copilot)',False,True),'execute-sol.agent.md':('Execute Sol','GPT-5.6 Sol (copilot)',False,True),'debug-sol.agent.md':('Debug Sol','GPT-5.6 Sol (copilot)',False,True),'verify-luna.agent.md':('Verify Luna','GPT-5.6 Luna (copilot)',False,False),'verify-terra.agent.md':('Verify Terra','GPT-5.6 Terra (copilot)',False,False),'verify-sol.agent.md':('Verify Sol','GPT-5.6 Sol (copilot)',False,False)}
LEGACY={'scout.agent.md','researcher.agent.md','executor.agent.md','debugger.agent.md','verifier.agent.md'}; SUBAGENT_NAMES=[v[0] for v in EXPECTED.values() if v[0]!=ORCHESTRATOR]

def frontmatter(text):
    if not text.startswith('---\n'): raise ValueError('missing YAML frontmatter start')
    end=text.find('\n---\n',4)
    if end<0: raise ValueError('missing YAML frontmatter end')
    return text[4:end]
def scalar(fm,key):
    m=re.search(rf'(?m)^{re.escape(key)}:\s*(.+?)\s*$',fm); return m.group(1).strip().strip("'\"") if m else None
def list_value(fm,key):
    raw=scalar(fm,key)
    if raw is None:return None
    try:v=ast.literal_eval(raw)
    except (ValueError,SyntaxError):return None
    return v if isinstance(v,list) and all(isinstance(x,str) for x in v) else None

def validate_agent(path):
    errors=[]; spec=EXPECTED.get(path.name)
    if spec is None:return [f'{path}: unexpected physical profile'],None,None
    expected_name,expected_model,is_parent,can_edit=spec
    try: fm=frontmatter(path.read_text(encoding='utf-8'))
    except Exception as exc:return [f'{path}: {exc}'],None,None
    name=scalar(fm,'name'); desc=scalar(fm,'description'); model=scalar(fm,'model'); tools=list_value(fm,'tools'); agents=list_value(fm,'agents')
    if name!=expected_name:errors.append(f'{path}: wrong name')
    if model!=expected_model:errors.append(f'{path}: wrong fixed model')
    if not desc:errors.append(f'{path}: missing description')
    if tools is None:errors.append(f'{path}: tools must be explicit list');tools=[]
    if is_parent:
        if scalar(fm,'user-invocable')!='true':errors.append(f'{path}: parent must be user-invocable')
        if scalar(fm,'disable-model-invocation')!='true':errors.append(f'{path}: parent must require explicit selection')
        if 'agent' not in tools:errors.append(f'{path}: parent missing agent tool')
        if agents!=SUBAGENT_NAMES:errors.append(f'{path}: agent allowlist mismatch')
    else:
        if scalar(fm,'user-invocable')!='false':errors.append(f'{path}: subagent user-invocable must be false')
        if scalar(fm,'disable-model-invocation')!='false':errors.append(f'{path}: subagent must remain dispatchable')
        if agents!=[]:errors.append(f'{path}: subagent agents must be []')
        if 'agent' in tools:errors.append(f'{path}: subagent must not have agent tool')
        if can_edit and 'edit' not in tools:errors.append(f'{path}: writer missing edit')
        if not can_edit and 'edit' in tools:errors.append(f'{path}: read-only agent has edit')
    return errors,name,desc

def validate_pricing():
    path=ROOT/'config'/'pricing.json';errors=[]
    try:data=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:return [f'{path}: {exc}']
    if data.get('schema_version')!=1:errors.append(f'{path}: schema_version must be 1')
    models=data.get('models')
    if not isinstance(models,dict) or set(models)!=MODELS:return errors+[f'{path}: models mismatch']
    for model,spec in models.items():
        if not isinstance(spec.get('long_threshold'),int) or spec['long_threshold']<=0:errors.append(f'{path}: invalid {model} threshold')
        for tier in ('default','long'):
            rates=spec.get(tier)
            if not isinstance(rates,dict):errors.append(f'{path}: missing {model}.{tier}');continue
            for key in ('fresh_input','cached_input','cache_write','output'):
                v=rates.get(key)
                if not isinstance(v,(int,float)) or v<0:errors.append(f'{path}: invalid {model}.{tier}.{key}')
    return errors

def validate_fixtures():
    path=ROOT/'config'/'routing-fixtures.json';errors=[]
    try:rows=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:return [f'{path}: {exc}']
    if not isinstance(rows,list) or not rows:return [f'{path}: expected non-empty list']
    names=[]
    for row in rows:
        names.append(row.get('name')); stages=row.get('stages'); expected=row.get('expected_path')
        if not isinstance(stages,list) or not stages:errors.append(f'{path}: missing stages');continue
        models=[s.get('model') for s in stages if isinstance(s,dict)]
        if len(models)!=len(stages) or len(models)!=len(set(models)):errors.append(f'{path}: stage models must be unique')
        if any(m not in MODELS for m in models):errors.append(f'{path}: unknown model')
        if models[-1]!='astra':errors.append(f'{path}: final stage must be astra')
        if not isinstance(expected,list) or not expected or expected[-1]!='astra':errors.append(f'{path}: expected_path must end astra')
    if len(names)!=len(set(names)):errors.append(f'{path}: fixture names must be unique')
    return errors

def main():
    errors=[];paths=sorted(AGENT_DIR.glob('*.agent.md'));filenames={p.name for p in paths}
    if set(EXPECTED)-filenames:errors.append('missing physical profiles')
    if filenames-set(EXPECTED):errors.append('unexpected profiles')
    if LEGACY&filenames:errors.append('legacy generic profiles must be removed')
    names=[];descs=[]
    for path in paths:
        e,n,d=validate_agent(path);errors.extend(e);names += [n] if n else [];descs += [d] if d else []
    if len(names)!=len(set(names)):errors.append('agent names must be unique')
    if len(descs)!=len(set(descs)):errors.append('agent descriptions must be unique')
    skill=ROOT/'.github'/'skills'/'calibrate-routing'/'SKILL.md'
    if not skill.exists() or scalar(frontmatter(skill.read_text(encoding='utf-8')),'name')!=skill.parent.name:errors.append('routing skill invalid')
    instructions=ROOT/'.github'/'copilot-instructions.md'
    if not instructions.exists() or len(instructions.read_text(encoding='utf-8'))>2500:errors.append('always-on instructions missing/too large')
    errors.extend(validate_pricing());errors.extend(validate_fixtures())
    for path in [ROOT/'docs'/'research'/'2026-09-09-deep-routing-research.md',ROOT/'docs'/'adr'/'0001-risk-aware-routing.md']:
        if not path.exists():errors.append(f'{path}: missing')
    if errors:
        print('Configuration validation failed:');[print(f'- {e}') for e in errors];return 1
    print(f'Configuration validation passed: {len(paths)} fixed-model profiles + risk-aware routing policy');return 0
if __name__=='__main__':raise SystemExit(main())
