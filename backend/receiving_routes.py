import uuid
from typing import Literal
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import identity,receiving,jobs
from .domain import DomainError,digest
from .fixtures import now
from .provider_tasks import infer
from .public_demo import inference_access

router=APIRouter()
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Parse(Strict):
    document_id:str=Field(max_length=80)
    mode:Literal['live','fixture']
class Review(Strict):
    revision:int
    document_id:str=Field(max_length=80)
    review_path:Literal['structured_record','narrative_draft']
    run_id:str=Field(default='',max_length=80)
    pool_id:str=Field(max_length=160)
    parent_ids:list[str]=Field(max_length=20)
    complete:bool
    quote:str=Field(min_length=8,max_length=2000)
    superseded_row_ids:list[str]=Field(max_length=80)
    unresolved_contradictions:bool=True
    outcome:Literal['resolved','inconclusive']
    reviewed:bool=False
    replacement_reviewed:bool=False
    completeness_confirmed:bool=False
    note:str=Field(default='',max_length=2000)


@router.post('/api/cases/{case_id}/receiving-draft')
def draft(case_id:str,data:Parse,request:Request):
    from .app import transaction
    with inference_access(data.mode,request.headers.get('x-bf-demo-token','')):
        with transaction(case_id,request.state.owner) as (db,state):
            doc=next((d for d in state['documents'] if d['id']==data.document_id and d.get('request_id')),None)
            if not doc:raise DomainError('Attach a receiving source to the current evidence question')
            if data.mode=='fixture' and not doc['synthetic']:raise DomainError('Synthetic mode requires synthetic source records')
            revision=state['revision'];key='RECEIVING-'+uuid.uuid4().hex
            jobs.start(db,request.state.owner,key,'receiving',{'case_id':case_id,'document_id':doc['id'],'revision':revision},data.mode)
        # Fixture deliberately abstains; it cannot impersonate a useful live extraction.
        fixture={'entities':[],'pool_id':'','parent_ids':[],'completeness':'unknown','completeness_quote':'','contradictions':['Synthetic abstention; use structured source review or Live AMD.']}
        run=infer('typed-receiving',receiving.SYSTEM,receiving.Draft.model_json_schema(),{'document_id':doc['id'],'blocks':doc['blocks']},data.mode,fixture)
        if run['status']=='succeeded':
            try:run['output']=receiving.validate_draft(run['output'],doc)
            except Exception:run.update(status='failed',error='Invalid typed proposal or unsupported source reference; no record replacement')
        run.update(document_id=doc['id'],revision=revision)
        with transaction(case_id,request.state.owner) as (db,state):
            accepted=jobs.finish(db,request.state.owner,key,run['status'],digest(run))
            if not accepted or state['revision']!=revision:run.update(status='stale',error='Source/job changed; no review authority')
            state.setdefault('receiving_runs',[]).append(run)
    return state


@router.post('/api/cases/{case_id}/receiving-preview')
def preview(case_id:str,data:Review,request:Request):
    from .app import read
    return receiving.preview(read(case_id,request.state.owner),data)[0]


@router.post('/api/cases/{case_id}/receiving-review')
def review(case_id:str,data:Review,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer')
        receiving.commit(state,data,identity.current_actor(),now())
    return state
