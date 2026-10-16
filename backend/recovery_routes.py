import json
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import recovery,repository as repo,identity
from .domain import DomainError,digest
from .fixtures import now
from .knowledge_routes import catalog

router=APIRouter()
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Policy(Strict):
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
    expected_revision:int
    procedure_refs:list[str]=Field(min_length=1,max_length=10)
class Evidence(Strict):
    revision:int
    pool_id:str=Field(max_length=160)
    receiving_document_id:str=Field(max_length=80)
    receiving_quote:str=Field(min_length=8,max_length=2000)
    authenticity_verified:bool
    verification_reference:str=Field(max_length=500)
    inspection_document_id:str=Field(max_length=80)
    inspection_quote:str=Field(min_length=8,max_length=2000)
    inspected_units:int=Field(ge=1,le=1_000_000)
    nonconforming_units:int=Field(ge=0,le=1_000_000)
    inspection_passed:bool
    inspected_at:str=Field(max_length=80)
    note:str=Field(min_length=20,max_length=2000)
class Prepare(Strict):
    hold_ids:list[str]=Field(min_length=1,max_length=80)
    evidence_ids:list[str]=Field(min_length=1,max_length=80)
    note:str=Field(min_length=20,max_length=2000)
class Approve(Strict):
    recovery_id:str=Field(max_length=80)
    digest:str=Field(min_length=64,max_length=64)
class Execute(Approve):
    idempotency_key:str=Field(min_length=8,max_length=100)


@router.get('/api/cases/{case_id}/recovery')
def read(case_id:str,request:Request):
    from .app import connect
    with connect() as db:
        state=recovery.case(db,request.state.owner,case_id)
        rev,policy=repo.get_record(db,request.state.owner,'recovery-policy','current')
        proposals=[json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='recovery'",(request.state.owner,))]
        proofs=[json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='recovery-evidence'",(request.state.owner,))]
        outbox=[json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='outbox'",(request.state.owner,))]
    return {'policy':policy,'policy_revision':rev,'proposals':[p for p in proposals if p['case_id']==case_id],
            'evidence':[p for p in proofs if p['case_id']==case_id],'holds':state.get('hold_ledger',[]),'quantities':state.get('quantities',{}),
            'outbox':[o for o in outbox if o['recovery_id'] in {p['id'] for p in proposals if p['case_id']==case_id}],
            'scope':'Whole pools only; partial release unsupported','identity':identity.current_actor()}


@router.post('/api/recovery/policy-review')
def policy(data:Policy,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        recovery.require_role(db,'quality_reviewer')
        rev,previous=repo.get_record(db,request.state.owner,'recovery-policy','current')
        docs=catalog(db,request.state.owner)
        if not data.reviewed or not any(d['status']=='approved' for d in docs):raise DomainError('Approved procedure context and explicit policy review required')
        if set(data.procedure_refs)-{d['id']+'@'+str(d['version']) for d in docs if d['status']=='approved'}:raise DomainError('Select current approved procedure references')
        policy={'id':'RECOVER-WHOLE-1','revision':rev+1,'whole_pool_only':True,'require_verified_authenticity':True,
                'inspection':'100% visual-v1; zero nonconforming units; at most 30 days old','distinct_release_approver':True,
                'catalog_digest':digest(docs),'procedure_refs':data.procedure_refs,'approved_by':recovery.actor_authority(),'at':now(),'note':data.note,
                'execution_boundary':'Sandbox only; no use-as-is waiver, destruction or real enterprise execution'}
        repo.put_record(db,request.state.owner,'recovery-policy','current',policy,data.expected_revision)
        repo.audit(db,request.state.owner,identity.current_actor(),'recovery.policy_reviewed',previous or {},policy)
    return policy


@router.post('/api/cases/{case_id}/recovery-evidence')
def evidence(case_id:str,data:Evidence,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        state=recovery.case(db,request.state.owner,case_id)
        return recovery.evidence(db,request.state.owner,state,data)


@router.post('/api/cases/{case_id}/recovery-prepare')
def prepare(case_id:str,data:Prepare,request:Request):
    from .app import connect
    with repo.write(connect) as db:
        state=recovery.case(db,request.state.owner,case_id)
        return recovery.prepare(db,request.state.owner,state,data.hold_ids,data.evidence_ids,data.note)


@router.post('/api/recovery/release-approve')
def approve(data:Approve,request:Request):
    from .app import connect
    with repo.write(connect) as db:return recovery.approve(db,request.state.owner,data.recovery_id,data.digest)


@router.post('/api/recovery/recovery-execute')
def execute(data:Execute,request:Request):
    from .app import connect
    with repo.write(connect) as db:return recovery.execute(db,request.state.owner,data.recovery_id,data.digest,data.idempotency_key)


class Dispatch(Strict):
    operation_id:str=Field(pattern='^[a-f0-9]{64}$')


@router.post('/api/recovery/connector-enqueue')
def connector_enqueue(data:Execute,request:Request):
    from .app import connect
    from .outbox import enqueue
    with repo.write(connect) as db:return enqueue(db,request.state.owner,data.recovery_id,data.digest,data.idempotency_key)


@router.post('/api/recovery/connector-dispatch')
def connector_dispatch(data:Dispatch,request:Request):
    from .app import connect
    from .outbox import dispatch
    return dispatch(connect,request.state.owner,data.operation_id)
