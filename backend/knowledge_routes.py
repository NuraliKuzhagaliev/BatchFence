import json
import uuid
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from . import repository as repo,identity,knowledge,jobs
from .domain import DomainError,digest,canonical
from .fixtures import now
from .provider_tasks import infer
from .public_demo import inference_access

router=APIRouter()
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Procedure(Strict):
    document:dict
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
class Question(Strict):
    case_id:str=Field(max_length=80)
    question:str=Field(min_length=8,max_length=1000)
    product:str=Field(max_length=160)
    process:str=Field(max_length=160)
    mode:str=Field(pattern='^(live|fixture)$')
class Check(Strict):
    answer_id:str=Field(max_length=80)
    claim_index:int=Field(ge=0,le=4)
    evidence_document_id:str=Field(max_length=80)
    evidence_quote:str=Field(min_length=8,max_length=2000)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


def catalog(db,owner):return [json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='procedure' ORDER BY id",(owner,)).fetchall()]


@router.get('/api/knowledge')
def list_documents(request:Request):
    from .app import connect
    with connect() as db:docs=catalog(db,request.state.owner)
    return {'documents':docs,'catalog_digest':digest(docs),'retrieval':'Local lexical retrieval after organization/site, approved revision and applicability filtering; no shared cache'}


@router.post('/api/knowledge/procedure-review')
def review_procedure(data:Procedure,request:Request):
    from .app import connect
    try:knowledge.validate_document(data.document)
    except (ValueError,TypeError,KeyError,AttributeError):raise DomainError('Malformed procedure metadata, passage or validity interval')
    if not data.reviewed:raise DomainError('Explicit applicability, source and revision approval required')
    with repo.write(connect) as db:
        identity.recheck(db,'quality_reviewer')
        key=data.document['id']+'@'+str(data.document['version'])
        revision,old=repo.get_record(db,request.state.owner,'procedure',key)
        if old and {k:v for k,v in old.items() if k!='status'}!={k:v for k,v in data.document.items() if k!='status'}:
            raise DomainError('Published procedure contents are immutable; create a new revision')
        if not old and len(catalog(db,request.state.owner))>=30:raise DomainError('Procedure catalog limit: 30 revisions')
        repo.save_source(db,request.state.owner,canonical(data.document['passages']).encode())
        repo.put_record(db,request.state.owner,'procedure',key,data.document,revision)
        repo.audit(db,request.state.owner,identity.current_actor(),'knowledge.procedure_reviewed',old or {},data.document,[data.document['source_hash']])
    return data.document


@router.post('/api/knowledge/answer')
def answer(data:Question,request:Request):
    from .app import connect,read
    state=read(data.case_id,request.state.owner)
    if data.mode=='fixture' and not state['synthetic']:raise DomainError('Synthetic answers require an explicitly synthetic incident')
    with inference_access(data.mode,request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'reporter')
            docs=catalog(db,request.state.owner)
            retrieval=knowledge.retrieve(docs,data.question,data.product,data.process,state['synthetic'])
            snapshot=digest(docs);key='ANSWER-'+uuid.uuid4().hex
            if retrieval['status']=='insufficient':
                result={'id':key,'status':'insufficient','mode':'deterministic retrieval abstention; no model request','retrieval':retrieval,
                        'output':{'claims':[],'insufficient_evidence':True,'missing_information':[retrieval['reason']]},'catalog_digest':snapshot,'case_id':state['id']}
                repo.put_record(db,request.state.owner,'answer',key,result,0)
                return result
            jobs.start(db,request.state.owner,key,'knowledge',{'case_id':state['id'],'catalog_digest':snapshot,'question':data.question},data.mode)
        synthetic={'claims':[{k:p[k] for k in ('document_id','version','passage_id','quote')} for p in retrieval['passages'][:2]],'insufficient_evidence':False,'missing_information':[]}
        run=infer('approved-knowledge',knowledge.SYSTEM,knowledge.Answer.model_json_schema(),{'question':data.question,'passages':retrieval['passages']},data.mode,synthetic)
        if run['status']=='succeeded':
            try:run['output']=knowledge.validate_answer(run['output'],retrieval)
            except Exception:
                run.update(status='failed',error='Unsupported procedural claim or invalid answer schema; no checklist authority')
        with repo.write(connect) as db:
            identity.recheck(db,'reporter')
            accepted=jobs.finish(db,request.state.owner,key,run['status'],digest(run))
            if not accepted or digest(catalog(db,request.state.owner))!=snapshot:
                run.update(status='stale',error='Job cancelled/interrupted or procedure revision changed; answer cannot create a check')
            result={'id':key,**run,'id':key,'catalog_digest':snapshot,'case_id':state['id'],'retrieval':retrieval,'question':data.question,
                    'boundary':'AMD-selected exact procedure passages are proposals. They do not authorize inventory actions.'}
            repo.put_record(db,request.state.owner,'answer',key,result,0)
    return result


@router.post('/api/cases/{case_id}/knowledge-check')
def record_check(case_id:str,data:Check,request:Request):
    from .app import transaction
    from .review_safety import resolution_evidence
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer')
        _,answer=repo.get_record(db,request.state.owner,'answer',data.answer_id)
        if not answer or answer['case_id']!=case_id or answer['status']!='succeeded' or answer['catalog_digest']!=digest(catalog(db,request.state.owner)):
            raise DomainError('Current applicable answer required; procedure changes invalidate pending checks')
        claims=answer.get('output',{}).get('claims',[])
        if data.claim_index>=len(claims) or not data.reviewed:raise DomainError('Select and explicitly review a supported procedure check')
        doc=next((d for d in state['documents'] if d['id']==data.evidence_document_id),None)
        evidence=resolution_evidence(doc,data.evidence_quote) if doc else None
        if not evidence:raise DomainError('Attach exact recorded evidence for this check')
        from .ocr import require_visual_review
        require_visual_review(doc)
        check={'id':'CHECK-'+uuid.uuid4().hex,'procedure':claims[data.claim_index],'evidence':evidence,'document_hash':doc['original_hash'],
               'catalog_digest':answer['catalog_digest'],'actor':identity.current_actor(),'at':now(),'note':data.note,'status':'reviewed complete'}
        state.setdefault('procedure_checks',[]).append(check)
        state['revision']+=1
        if state.get('plan') and state['plan']['status']!='applied':state['plan']['status']='stale'
        state['pending_revision']=True
        repo.audit(db,request.state.owner,identity.current_actor(),'knowledge.check_completed',{},check,[doc['original_hash']])
    return state
