import json
import uuid
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import repository as repo,identity,signals
from .domain import DomainError,digest
from .fixtures import load_demo,now

router=APIRouter()
class Baseline(BaseModel):
    model_config=ConfigDict(extra='forbid')
    observation_ids:list[str]=Field(min_length=2,max_length=500)
    inspection_revision:int
    stable_reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class Investigation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    baseline_id:str=Field(max_length=80)
    observation_id:str=Field(max_length=80)
    chart_digest:str=Field(max_length=64)
    source_case_id:str=Field(max_length=80)


@router.post('/api/signals/baseline-review')
def baseline(data:Baseline,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer')
        rev,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        if rev!=data.inspection_revision or not data.stable_reviewed: raise DomainError('Current observations and explicit baseline stability review required')
        base=signals.freeze(observations['rows'],data.observation_ids)
        base.update(id='BASE-'+uuid.uuid4().hex,review={'actor':identity.current_actor(),'at':now(),'note':data.note},inspection_revision=rev)
        repo.put_record(db,request.state.owner,'baseline',base['id'],base,0)
        repo.audit(db,request.state.owner,identity.current_actor(),'signals.baseline_reviewed',{},base)
    return base


@router.get('/api/signals')
def get_signals(request:Request):
    from .app import connect
    with connect() as db:
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        bases=[json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='baseline' ORDER BY id",(request.state.owner,))]
    results=[]
    for base in bases:
        result=signals.chart(base,observations['rows'])
        results.append({'baseline':base,'chart':result,'chart_digest':digest(result)})
    return {'results':results,'default_policy':signals.DEFAULT_POLICY,'minimum_policy_is_universal_guarantee':False}


@router.post('/api/signals/investigation')
def investigation(data:Investigation,request:Request):
    from .app import connect,insert
    with repo.write(connect) as db:
        identity.recheck(db,'reporter')
        _,base=repo.get_record(db,request.state.owner,'baseline',data.baseline_id)
        _,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[]})
        if not base:raise DomainError('Baseline unavailable')
        result=signals.chart(base,observations['rows'])
        if digest(result)!=data.chart_digest or result['status']!='ready':raise DomainError('Signal changed; inspect the current result')
        point=next((p for p in result['points'] if p['observation_id']==data.observation_id and p['status']=='signal'),None)
        if not point: raise DomainError('Select a current statistical signal')
        _,prior=repo.get_record(db,request.state.owner,'signal-case',data.baseline_id+':'+data.observation_id)
        if prior:return prior
        row=db.execute('SELECT state FROM cases WHERE id=? AND owner=?',(data.source_case_id,request.state.owner)).fetchone()
        if not row:raise DomainError('Choose an accessible incident record universe for the investigation')
        state=json.loads(row[0])
        state.update(id=uuid.uuid4().hex,revision=1,plan=None,plans=[],runs=[],reviews=[],receipts=[],history=[],pending_revision=False,pending_data=None,
                     scope={'lot_ids':[],'revision':0,'qualifiers':[]},bounded=False)
        state['incident']='Inspection variation · investigation required'
        known={s['id'] for s in state['stocks']}|{e['source'] for e in state['edges']}
        state['origin_signal']={'baseline_id':base['id'],'baseline_hash':base['row_hash'],'chart_digest':data.chart_digest,'observation':point,
                                'known_affected':[],'potential_identifiers':[p for p in point.get('pool_ids',[]) if p in known],
                                'unmapped_identifiers':[p for p in point.get('pool_ids',[]) if p not in known],'supplier_cause':'not established'}
        # Save the case in this transaction, preserving signal linkage exactly once.
        db.execute('INSERT INTO cases VALUES(?,?,?)',(state['id'],request.state.owner,json.dumps(state)))
        repo.put_record(db,request.state.owner,'signal-case',data.baseline_id+':'+data.observation_id,{'case_id':state['id']},0)
        repo.audit(db,request.state.owner,identity.current_actor(),'signals.investigation_created',{},state['origin_signal'])
    return {'case_id':state['id']}
