#!/usr/bin/env python3
"""Static guardrails for physical agents, priors, risk policy, and local validation."""
from __future__ import annotations
import ast,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT_DIR=ROOT/'.github'/'agents';ORCHESTRATOR='Astra Orchestrator';MODELS={'luna','terra','sol','astra'}
EXPECTED={
'astra-orchestrator.agent.md':('Astra Orchestrator','GPT-6 Astra (copilot)',True,True),
'scout-luna.agent.md':('Scout Luna','GPT-5.6 Luna (copilot)',False,False),
'research-luna.agent.md':('Research Luna','GPT-5.6 Luna (copilot)',False,False),
'research-terra.agent.md':('Research Terra','GPT-5.6 Terra (copilot)',False,False),
'execute-luna.agent.md':('Execute Luna','GPT-5.6 Luna (copilot)',False,True),
'execute-terra.agent.md':('Execute Terra','GPT-5.6 Terra (copilot)',False,True),
'execute-sol.agent.md':('Execute Sol','GPT-5.6 Sol (copilot)',False,True),
'debug-sol.agent.md':('Debug Sol','GPT-5.6 Sol (copilot)',False,True),
'verify-luna.agent.md':('Verify Luna','GPT-5.6 Luna (copilot)',False,False),
'verify-terra.agent.md':('Verify Terra','GPT-5.6 Terra (copilot)',False,False),
'verify-sol.agent.md':('Verify Sol','GPT-5.6 Sol (copilot)',False,False)}
SUBAGENT_NAMES=[v[0] for v in EXPECTED.values() if v[0]!=ORCHESTRATOR];LEGACY={'scout.agent.md','researcher.agent.md','executor.agent.md','debugger.agent.md','verifier.agent.md'}

def frontmatter(text):
    if not text.startswith('---\n'):raise ValueError('missing YAML frontmatter start')
    end=text.find('\n---\n',4)
    if end<0:raise ValueError('missing YAML frontmatter end')
    return text[4:end]
def scalar(fm,key):
    m=re.search(rf'(?m)^{re.escape(key)}:\s*(.+?)\s*$',fm);return m.group(1).strip().strip("'\"") if m else None
def list_value(fm,key):
    raw=scalar(fm,key)
    if raw is None:return None
    try:value=ast.literal_eval(raw)
    except (ValueError,SyntaxError):return None
    return value if isinstance(value,list) and all(isinstance(x,str) for x in value) else None

def validate_agent(path):
    errors=[];spec=EXPECTED.get(path.name)
    if spec is None:return [f'{path}: unexpected profile'],None,None
    expected_name,expected_model,is_parent,can_edit=spec;text=path.read_text(encoding='utf-8');fm=frontmatter(text)
    name,desc,model=scalar(fm,'name'),scalar(fm,'description'),scalar(fm,'model');tools,agents=list_value(fm,'tools'),list_value(fm,'agents')
    if name!=expected_name:errors.append(f'{path}: wrong name')
    if model!=expected_model:errors.append(f'{path}: wrong fixed model')
    if scalar(fm,'target')!='vscode':errors.append(f'{path}: target must be vscode')
    if not desc:errors.append(f'{path}: missing description')
    if tools is None:errors.append(f'{path}: tools must be explicit list');tools=[]
    if is_parent:
        if scalar(fm,'user-invocable')!='true':errors.append(f'{path}: parent user-invocable must be true')
        if scalar(fm,'disable-model-invocation')!='true':errors.append(f'{path}: parent must require explicit user selection')
        if 'agent' not in tools:errors.append(f'{path}: parent missing agent tool')
        if agents!=SUBAGENT_NAMES:errors.append(f'{path}: parent allowlist mismatch')
        for token in ('not an infallible fallback','reached_after','routing-priors.local.json','max_terminal'):
            if token not in text:errors.append(f'{path}: missing routing contract token {token!r}')
    else:
        if scalar(fm,'user-invocable')!='false':errors.append(f'{path}: subagent user-invocable must be false')
        if scalar(fm,'disable-model-invocation')!='true':errors.append(f'{path}: subagent must be protected from general model invocation')
        if agents!=[]:errors.append(f'{path}: subagent agents must be []')
        if 'agent' in tools:errors.append(f'{path}: subagent must not have agent tool')
        if can_edit and 'edit' not in tools:errors.append(f'{path}: writer missing edit')
        if not can_edit and 'edit' in tools:errors.append(f'{path}: read-only profile has edit')
    return errors,name,desc

def validate_pricing():
    path=ROOT/'config'/'pricing.json';errors=[];data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1:errors.append(f'{path}: schema_version must be 1')
    for key in ('as_of','source_url','source_checked_at','source_policy'):
        if not data.get(key):errors.append(f'{path}: missing {key}')
    models=data.get('models')
    if not isinstance(models,dict) or set(models)!=MODELS:return errors+[f'{path}: models mismatch']
    for model,spec in models.items():
        if not isinstance(spec.get('long_threshold'),int) or spec['long_threshold']<=0:errors.append(f'{path}: invalid {model} long_threshold')
        for tier in ('default','long'):
            rates=spec.get(tier)
            if not isinstance(rates,dict):errors.append(f'{path}: missing {model}.{tier}');continue
            for key in ('fresh_input','cached_input','cache_write','output'):
                if not isinstance(rates.get(key),(int,float)) or rates[key]<0:errors.append(f'{path}: invalid {model}.{tier}.{key}')
    return errors

def validate_priors():
    path=ROOT/'config'/'routing-priors.json';errors=[];data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1:errors.append(f'{path}: schema_version must be 1')
    entries=data.get('entries')
    if not isinstance(entries,list) or not entries:return errors+[f'{path}: entries must be non-empty list']
    direct=after=False
    for row in entries:
        if row.get('model') not in MODELS:errors.append(f'{path}: unknown model in prior')
        reached=str(row.get('reached_after',''))
        if not reached:errors.append(f'{path}: prior missing reached_after')
        for key in ('p_correct','detection_rate'):
            if key in row and (not isinstance(row[key],(int,float)) or not 0<=row[key]<=1):errors.append(f'{path}: invalid {key}')
        if row.get('model')=='astra' and reached=='direct':direct=True;errors += [f'{path}: Astra direct prior must not be infallible'] if row.get('p_correct')==1 else []
        if row.get('model')=='astra' and reached=='after:any':after=True;errors += [f'{path}: Astra fallback prior must not be infallible'] if row.get('p_correct')==1 else []
    if not (direct and after):errors.append(f'{path}: Astra direct/after:any priors required')
    if not data.get('human_oracles'):errors.append(f'{path}: human oracle fallback required')
    return errors

def validate_risk_policy():
    path=ROOT/'config'/'risk-policy.json';errors=[];data=json.loads(path.read_text(encoding='utf-8'));classes=data.get('classes',{})
    if data.get('schema_version')!=1:errors.append(f'{path}: schema_version must be 1')
    if data.get('default_class') not in classes:errors.append(f'{path}: default_class missing from classes')
    for name,row in classes.items():
        for key in ('max_hidden_failure','max_terminal_failure','min_validated_correct'):
            v=row.get(key)
            if not isinstance(v,(int,float)) or not 0<=v<=1:errors.append(f'{path}: {name}.{key} invalid')
    return errors

def validate_fixtures():
    path=ROOT/'config'/'routing-fixtures.json';errors=[];rows=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows,list) or not rows:return [f'{path}: expected non-empty list']
    names=[];has_human=has_transition=False
    for row in rows:
        names.append(row.get('name'));stages=row.get('stages');expected=row.get('expected_path')
        if not isinstance(stages,list) or not stages:errors.append(f'{path}: fixture missing stages');continue
        models=[s.get('model') for s in stages]
        if any(m not in MODELS for m in models):errors.append(f'{path}: unknown model')
        if len(models)!=len(set(models)):errors.append(f'{path}: duplicate stage model')
        if models[-1]!='astra':errors.append(f'{path}: final stage must be astra')
        if not isinstance(expected,list) or not expected or expected[-1]!='astra':errors.append(f'{path}: expected_path must end astra')
        if row.get('human_validation_required'):has_human=True
        if row.get('prior_entries'):has_transition=True
        for stage in stages:
            if stage.get('model')=='astra' and stage.get('p_correct')==1.0:errors.append(f'{path}: static Astra fixture must not use p_correct=1')
    if len(names)!=len(set(names)):errors.append(f'{path}: fixture names must be unique')
    if not has_human:errors.append(f'{path}: human validation fixture required')
    if not has_transition:errors.append(f'{path}: transition-aware fixture required')
    return errors

def validate_docs_and_ignore():
    errors=[];required=[ROOT/'docs'/'research'/'2026-09-09-deep-routing-research.md',ROOT/'docs'/'research'/'2026-09-10-routing-review.md',ROOT/'docs'/'adr'/'0001-risk-aware-routing.md',ROOT/'docs'/'adr'/'0002-local-validation-no-github-actions.md',ROOT/'docs'/'adr'/'0003-human-validation-as-oracle.md',ROOT/'docs'/'adr'/'0004-transition-aware-empirical-routing.md',ROOT/'docs'/'human-device-validation.md']
    for path in required:
        if not path.exists():errors.append(f'{path}: missing')
    ignore=(ROOT/'.gitignore').read_text(encoding='utf-8') if (ROOT/'.gitignore').exists() else ''
    if 'config/routing-priors.local.json' not in ignore:errors.append('.gitignore must ignore config/routing-priors.local.json')
    return errors

def main():
    errors=[];paths=sorted(AGENT_DIR.glob('*.agent.md'));filenames={p.name for p in paths}
    if set(EXPECTED)-filenames:errors.append(f'missing physical profiles: {sorted(set(EXPECTED)-filenames)}')
    if filenames-set(EXPECTED):errors.append(f'unexpected profiles: {sorted(filenames-set(EXPECTED))}')
    if LEGACY&filenames:errors.append(f'legacy profiles present: {sorted(LEGACY&filenames)}')
    names=[];descs=[]
    for path in paths:
        e,n,d=validate_agent(path);errors.extend(e)
        if n:names.append(n)
        if d:descs.append(d)
    if len(names)!=len(set(names)):errors.append('agent names must be unique')
    if len(descs)!=len(set(descs)):errors.append('agent descriptions must be unique')
    skill=ROOT/'.github'/'skills'/'calibrate-routing'/'SKILL.md'
    if not skill.exists() or scalar(frontmatter(skill.read_text(encoding='utf-8')),'name')!=skill.parent.name:errors.append('routing skill invalid')
    instructions=ROOT/'.github'/'copilot-instructions.md'
    if not instructions.exists() or len(instructions.read_text(encoding='utf-8'))>2500:errors.append('always-on instructions missing/too large')
    errors+=validate_pricing()+validate_priors()+validate_risk_policy()+validate_fixtures()+validate_docs_and_ignore()
    if errors:
        print('Configuration validation failed:')
        for error in errors:print(f'- {error}')
        return 1
    print(f'Configuration validation passed: {len(paths)} VS Code fixed-model profiles + transition-aware priors + risk policy');return 0
if __name__=='__main__':raise SystemExit(main())
