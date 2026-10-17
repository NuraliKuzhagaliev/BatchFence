import copy
import json
import uuid
from typing import Literal
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import repository as repo,identity,effectiveness,signals,onboarding
from .domain import DomainError,digest
from .fixtures import ROOT,now
from .recovery import source_basis

router=APIRouter()
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Create(Strict):
    case_id:str=Field(max_length=80)
    title:str=Field(min_length=8,max_length=160)
    owner:str=Field(min_length=3,max_length=120)
    due_date:str=Field(max_length=30)
    supplier_id:str=Field(max_length=160)
    product:str=Field(max_length=160)
    process:str=Field(max_length=160)
    defect:str=Field(max_length=160)
class Investigate(Strict):
    revision:int
    cause:str=Field(min_length=8,max_length=2000)
    cause_accepted:bool=False
    document_id:str=Field(max_length=80)
    quote:str=Field(min_length=8,max_length=2000)
    refuting_evidence:str=Field(max_length=2000)
    note:str=Field(min_length=20,max_length=2000)
class Plan(Strict):
    revision:int
    baseline_ids:list[str]=Field(min_length=2,max_length=500)
    group:dict[str,str]=Field(max_length=7)
    start:str=Field(max_length=80)
    end:str=Field(max_length=80)
    min_inspected:int
    expected_samples:int
    max_rate:float=Field(ge=0,le=1)
    synthetic_historical_replay:bool=False
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class Implement(Strict):
    revision:int
    document_id:str=Field(max_length=80)
    quote:str=Field(min_length=8,max_length=2000)
    note:str=Field(min_length=20,max_length=2000)
class Outcome(Strict):
    revision:int
    input_hash:str=Field(max_length=64)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class Start(Strict):
    revision:int
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class Recurrence(Strict):
    revision:int
    baseline_id:str=Field(max_length=80)
    observation_id:str=Field(max_length=80)
class Reopen(Strict):
    revision:int
    recurrence_id:str=Field(max_length=80)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class ExampleFollowup(Strict):
    phase:Literal['followup','recurrence']
    acknowledge_synthetic_replay:bool


def load(db,owner,key,revision=None):
    rev,action=repo.get_record(db,owner,'action',key)
    if not action or (revision is not None and rev!=revision):raise DomainError('Action unavailable or changed; refresh and review')
    return rev,action


def incident(db,owner,key):
    row=db.execute('SELECT state FROM cases WHERE id=? AND owner=?',(key,owner)).fetchone()
    if not row:raise DomainError('Incident unavailable')
    return json.loads(row[0])


def save(db,owner,action,rev,before,operation):
    action['revision']=rev+1
    repo.put_record(db,owner,'action',action['id'],action,rev)
    repo.audit(db,owner,identity.current_actor(),operation,before,action)
    return action


@router.get('/api/actions')
def actions(request:Request):
    from .app import connect
    with connect() as db:
        rows=db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='action' ORDER BY id",(request.state.owner,)).fetchall()
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
    results=[]
    for row in rows:
        action=json.loads(row[0])
        if action['outcomes'] and action['plan']:
            current=effectiveness.evaluate(action,observations['rows'])
            previous=action['outcomes'][-1]['result']
            action['historical_outcome_still_matches_current_evidence']=previous['input_hash']==current['input_hash'] and previous['plan_hash']==current['plan_hash']
        results.append(action)
    return results


@router.post('/api/actions/create')
def create(data:Create,request:Request):
    from .app import connect
    from datetime import date
    try:date.fromisoformat(data.due_date)
    except ValueError:raise DomainError('Valid due date required')
    with repo.write(connect) as db:
        identity.recheck(db,'reporter')
        state=incident(db,request.state.owner,data.case_id)
        if data.supplier_id not in {e['source'] for e in state['edges']}:raise DomainError('Supplier must belong to the incident lot universe')
        if identity.pilot():
            p=identity.principal.get()
            member=db.execute('SELECT u.id FROM bf_users u JOIN bf_members m ON u.id=m.user_id WHERE u.username=? AND m.org=? AND m.site=? AND m.active=1 AND u.active=1',(data.owner.lower(),p['org'],p['site'])).fetchone()
            if not member:raise DomainError('Action owner needs active membership in this organization/site')
        action={**data.model_dump(),'id':'ACTION-'+uuid.uuid4().hex,'status':'draft','revision':1,'created_at':now(),'creator':identity.current_actor(),
                'cause':None,'plan':None,'plan_history':[],'implementation':None,'outcomes':[],'recurrences':[],'synthetic':state['synthetic']}
        repo.put_record(db,request.state.owner,'action',action['id'],action,0)
        repo.audit(db,request.state.owner,identity.current_actor(),'action.created',{},action)
    return action


@router.post('/api/actions/{key}/investigation-review')
def investigate(key:str,data:Investigate,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if action['status'] not in ('draft','investigation'):raise DomainError('Reopen investigation explicitly before changing the cause')
        state=incident(db,request.state.owner,action['case_id']);proof=source_basis(state,data.document_id,data.quote);before=copy.deepcopy(action)
        action.update(status='investigation',cause={'statement':data.cause,'status':'reviewer accepted supporting evidence' if data.cause_accepted else 'hypothesis',
            'supporting':proof,'refuting':data.refuting_evidence,'note':data.note,'actor':identity.current_actor(),'at':now()})
        return save(db,request.state.owner,action,rev,before,'action.investigation_reviewed')


@router.post('/api/actions/{key}/plan-review')
def plan(key:str,data:Plan,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if not data.reviewed or not action['cause']:raise DomainError('Investigation and explicit prospective effectiveness-plan review required')
        if data.synthetic_historical_replay and not action['synthetic']:raise DomainError('Historical synthetic replay is unavailable for real records')
        if set(data.group)!=set(signals.GROUP):raise DomainError('Specify the complete comparison population')
        if any(data.group[k]!=action[k] for k in ('product','process','defect')):raise DomainError('Comparison population must match this corrective action')
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        frozen=effectiveness.freeze_plan(observations['rows'],data.baseline_ids,data.group,data.start,data.end,data.min_inspected,data.expected_samples,data.max_rate,data.synthetic_historical_replay)
        from .knowledge_routes import catalog
        frozen['procedure_revisions']=[{'id':d['id'],'version':d['version'],'source_hash':d['source_hash']} for d in catalog(db,request.state.owner) if d['status']=='approved']
        before=copy.deepcopy(action)
        if action['plan']:action['plan_history'].append({'plan':action['plan'],'superseded_at':now(),'outcomes_retained':True})
        action.update(status='approved_action_plan',plan={**frozen,'approved_at':now(),'actor':identity.current_actor(),'note':data.note},implementation=None)
        return save(db,request.state.owner,action,rev,before,'action.plan_frozen')


@router.post('/api/actions/{key}/implementation-review')
def implement(key:str,data:Implement,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if action['status']!='approved_action_plan':raise DomainError('An approved frozen action plan is required before implementation')
        from datetime import datetime,timezone
        if not action['plan']['synthetic_historical_replay'] and datetime.fromisoformat(action['plan']['start'].replace('Z','+00:00'))<datetime.now(timezone.utc):
            raise DomainError('Follow-up window began before recorded implementation; approve a new prospective plan')
        state=incident(db,request.state.owner,action['case_id']);proof=source_basis(state,data.document_id,data.quote);before=copy.deepcopy(action)
        action.update(status='implemented',implementation={'evidence':proof,'actor':identity.current_actor(),'at':now(),'note':data.note,
            'synthetic_historical_replay':action['plan']['synthetic_historical_replay']})
        return save(db,request.state.owner,action,rev,before,'action.implementation_reviewed')


@router.post('/api/actions/{key}/monitoring-start')
def start_monitoring(key:str,data:Start,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if action['status']!='implemented' or not data.reviewed:raise DomainError('Review recorded implementation before monitoring starts')
        before=copy.deepcopy(action);action['status']='effectiveness_monitoring'
        action['monitoring_started']={'at':now(),'actor':identity.current_actor(),'note':data.note}
        return save(db,request.state.owner,action,rev,before,'action.monitoring_started')


@router.get('/api/actions/{key}/effectiveness')
def evaluate(key:str,request:Request):
    from .app import connect
    with connect() as db:
        _,action=load(db,request.state.owner,key)
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        if not action['plan']:raise DomainError('Freeze an effectiveness plan first')
    return effectiveness.evaluate(action,observations['rows'])


@router.post('/api/actions/{key}/outcome-review')
def outcome(key:str,data:Outcome,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if action['status']!='effectiveness_monitoring' or not data.reviewed:raise DomainError('Explicit effectiveness review is required')
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        result=effectiveness.evaluate(action,observations['rows'])
        if result['input_hash']!=data.input_hash or result['status']=='inconclusive':raise DomainError('Stale, incomplete or confounded evidence cannot close the action')
        before=copy.deepcopy(action)
        action['outcomes'].append({'result':result,'actor':identity.current_actor(),'at':now(),'note':data.note})
        action['status']='reviewed_outcome'
        return save(db,request.state.owner,action,rev,before,'action.outcome_reviewed')


@router.post('/api/actions/{key}/recurrence-review')
def recurrence(key:str,data:Recurrence,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        if action['status']!='reviewed_outcome':raise DomainError('A completed historical outcome is required for recurrence review')
        _,base=repo.get_record(db,request.state.owner,'baseline',data.baseline_id)
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        if not base:raise DomainError('Baseline unavailable')
        chart=signals.chart(base,observations['rows'])
        point=next((p for p in chart.get('points',[]) if p['observation_id']==data.observation_id and p['status']=='signal'),None)
        if not point or any(point[k]!=action[k] for k in ('product','process','defect')):raise DomainError('No matching current statistical signal')
        if point['event_time']<=action['plan']['end']:raise DomainError('Recurrence must occur after the historical follow-up window')
        state=incident(db,request.state.owner,action['case_id'])
        reachable={action['supplier_id']}
        for _ in range(len(state['edges'])+1):
            expanded=reachable|{e['target'] for e in state['edges'] if e['source'] in reachable}
            if expanded==reachable:break
            reachable=expanded
        if not reachable & set(point.get('pool_ids',[])):raise DomainError('Supplier genealogy does not match the signal identifiers')
        existing=next((r for r in action['recurrences'] if r['observation_id']==data.observation_id),None)
        if existing and existing['chart_digest']==digest(chart):return action
        before=copy.deepcopy(action)
        if existing:existing['status']='superseded by current signal evidence'
        action['recurrences'].append({'id':'RECUR-'+uuid.uuid4().hex,'observation_id':data.observation_id,'baseline_id':base['id'],
            'chart_digest':digest(chart),'status':'reopen proposed','matched_on':{'supplier':action['supplier_id'],'product':point['product'],'process':point['process'],'defect':point['defect'],'pool_ids':point['pool_ids']},
            'source':point['source'],'at':now(),'boundary':'Potential recurrence; matching does not establish supplier causation or authorize stock actions'})
        return save(db,request.state.owner,action,rev,before,'action.recurrence_proposed')


@router.post('/api/actions/{key}/reopen-review')
def reopen(key:str,data:Reopen,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer');rev,action=load(db,request.state.owner,key,data.revision)
        recurrence=next((r for r in action['recurrences'] if r['id']==data.recurrence_id and r['status']=='reopen proposed'),None)
        if not recurrence or not data.reviewed:raise DomainError('Explicit current recurrence review required')
        _,base=repo.get_record(db,request.state.owner,'baseline',recurrence['baseline_id'])
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        if not base or digest(signals.chart(base,observations['rows']))!=recurrence['chart_digest']:raise DomainError('Recurrence evidence changed; review the current signal again')
        before=copy.deepcopy(action);recurrence.update(status='reopened',reviewer=identity.current_actor(),note=data.note)
        action['status']='investigation'
        return save(db,request.state.owner,action,rev,before,'action.reopened')


@router.post('/api/actions/{key}/synthetic-followup')
def synthetic_followup(key:str,data:ExampleFollowup,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'reporter');_,action=load(db,request.state.owner,key)
        if not action['synthetic'] or not action['plan'] or not action['plan']['synthetic_historical_replay'] or not data.acknowledge_synthetic_replay:
            raise DomainError('Explicit historical synthetic replay with a frozen plan required')
        if not action['implementation'] or action['status'] not in ('effectiveness_monitoring','reviewed_outcome'):raise DomainError('Record implementation and start monitoring before loading follow-up')
        state=incident(db,request.state.owner,action['case_id'])
        raw=(ROOT/'fixtures/enterprise/inspections.csv').read_bytes()
        proposal=onboarding.preview(state,raw,'inspections-followup.csv','inspections',{f:f for f in onboarding.FIELDS['inspections']},
            {'unit':'piece','timezone':'UTC','observed_at':'2026-10-16T00:00:00+00:00','source_revision':'synthetic-followup-v1','synthetic':True})
        prefix='FOLLOW-' if data.phase=='followup' else 'RECUR-'
        selected=[r for r in proposal['rows'] if r['observation_id'].startswith(prefix)]
        rev,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[],'history':[]})
        if any(r['observation_id'] in {p['observation_id'] for p in observations['rows']} for r in selected):raise DomainError('Synthetic phase already present')
        observations['rows']+=selected;observations['revision']=rev+1
        repo.save_source(db,request.state.owner,raw)
        repo.put_record(db,request.state.owner,'inspections','current',observations,rev)
        state['documents'].append(proposal['document'])
        db.execute('UPDATE cases SET state=? WHERE id=? AND owner=?',(json.dumps(state),state['id'],request.state.owner))
        repo.audit(db,request.state.owner,identity.current_actor(),'synthetic.followup_loaded',{}, {'phase':data.phase,'rows':len(selected),'historical_synthetic_replay':True})
    return {'loaded':len(selected),'provenance':'Historical synthetic replay, not real intervention effectiveness'}
