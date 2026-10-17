"""Connected synthetic training records; never a hidden substitute for live inference."""
import json
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import repository as repo,identity,onboarding
from .domain import DomainError,canonical
from .fixtures import ROOT,now

router=APIRouter()

def snapshot(db,owner,case_id):
    from . import signals,effectiveness
    from .domain import digest
    records={}
    for kind,raw in db.execute('SELECT kind,data FROM bf_records WHERE owner=? ORDER BY kind,id',(owner,)):
        if kind not in ('inspections','baseline','procedure','answer','action','recovery','recovery-evidence','recovery-policy','outbox','signal-explanation'):continue
        value=json.loads(raw)
        if value.get('case_id') and value['case_id']!=case_id:continue
        records.setdefault(kind,[]).append(value)
    rows=records.get('inspections',[{'rows':[]}])[0]
    records['signals']=[]
    for base in records.get('baseline',[]):
        chart=signals.chart(base,rows['rows'])
        records['signals'].append({'baseline':base,'chart':chart,'chart_digest':digest(chart)})
    for action in records.get('action',[]):
        if action.get('plan'):action['evaluation']=effectiveness.evaluate(action,rows['rows'])
    ids={p['id'] for p in records.get('recovery',[])}
    records['outbox']=[o for o in records.get('outbox',[]) if o['recovery_id'] in ids]
    rev,_=repo.get_record(db,owner,'recovery-policy','current')
    records['policy_revision']=rev
    records['actor']=identity.current_actor()
    records['snapshot_at']=now()
    records['boundary']='Historical snapshots confer no action authority. Synthetic records and simulated identities are not independent human validation.'
    return records

@router.get('/api/cases/{case_id}/modules')
def modules(case_id:str,request:Request):
    from .app import connect,read
    read(case_id,request.state.owner)
    with connect() as db:return snapshot(db,request.state.owner,case_id)
class Example(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id:str=Field(max_length=80)
    acknowledged_synthetic:bool


@router.post('/api/enterprise/example')
def example(data:Example,request:Request):
    from .app import transaction
    with transaction(data.case_id,request.state.owner) as (db,state):
        identity.recheck(db,'reporter')
        if not data.acknowledged_synthetic or not state['synthetic']:raise DomainError('Explicit synthetic training incident required')
        if repo.get_record(db,request.state.owner,'inspections','current')[0]:raise DomainError('Existing inspection records are preserved; use reviewed imports to change them')
        raw=(ROOT/'fixtures/enterprise/inspections.csv').read_bytes()
        metadata={'unit':'piece','timezone':'UTC','observed_at':'2026-10-16T00:00:00+00:00','source_revision':'synthetic-v1','synthetic':True}
        proposed=onboarding.preview(state,raw,'inspections.csv','inspections',{f:f for f in onboarding.FIELDS['inspections']},metadata)
        if proposed['errors']:raise DomainError('Synthetic fixture failed its data contract')
        # Follow-up and recurrence remain withheld until a frozen effectiveness plan.
        initial=[r for r in proposed['rows'] if not r['observation_id'].startswith(('FOLLOW-','RECUR-'))]
        repo.save_source(db,request.state.owner,raw)
        repo.put_record(db,request.state.owner,'inspections','current',{'rows':initial,'history':[],'revision':1,'provenance':'Disclosed synthetic inspection series; no human review claimed'},0)
        state['documents'].append(proposed['document'])
        state['enterprise_example']=True
        state['workspace_attached']=True
        for doc in json.loads((ROOT/'fixtures/enterprise/procedures.json').read_text(encoding='utf-8')):
            key=doc['id']+'@'+str(doc['version'])
            if not repo.get_record(db,request.state.owner,'procedure',key)[0]:
                repo.save_source(db,request.state.owner,canonical(doc['passages']).encode())
                repo.put_record(db,request.state.owner,'procedure',key,doc,0)
        repo.audit(db,request.state.owner,identity.current_actor(),'synthetic.training_records_loaded',{}, {'inspection_rows':len(initial),'fictional_procedures':3})
    return state
