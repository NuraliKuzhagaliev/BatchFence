"""Scoped continuation APIs. Every external call is outside DB transactions."""
import base64,hashlib,json,os,uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,Request,HTTPException
from pydantic import Field
from . import assisted as a,repository as repo,identity,jobs,evolus_adapter as external,label_images,evolus_api
from .assist_contracts import Strict,ReviewDraft,Citation,validate_draft,fingerprint,source_context
from .domain import DomainError,digest
from .fixtures import now
from .knowledge_routes import catalog
from .public_demo import inference_access

router=APIRouter()
class Run(Strict):
    document_ids:list[str]=Field(min_length=1,max_length=2)
    revision:int
    idempotency_key:str=Field(min_length=8,max_length=100)
    mode:Literal['live','fixture']
class Poll(Strict):job_id:str=Field(min_length=1,max_length=80)


@router.get('/api/assist/status')
def status():return external.status()


def result_for_job(db,owner,state,key,execution):
    rev,record=repo.get_record(db,owner,'assist',key)
    if not record or record['case_id']!=state['id']:raise DomainError('Execution unavailable in this case')
    if execution.get('execution_id')!=record.get('external_execution_id'):raise DomainError('Unexpected external execution; callback/result cannot choose a case')
    record['executions'].append(execution)
    if execution['status']=='running':
        repo.put_record(db,owner,'assist',key,record,rev);return record
    if execution['status']!='completed':
        record['status']='failed';record['error']='Provider refused, exhausted credits or failed; no automatic retry'
        jobs.finish(db,owner,key,'failed',digest(execution))
    else:
        # Both configured Evolus building blocks must appear in actual execution
        # evidence. A settings screenshot or requested model name is insufficient.
        if record['mode']=='live':
            steps=execution.get('steps',[])
            if not any(s.get('kind')=='extractor' and s.get('id')==os.getenv('EVOLUS_EXTRACTOR_ID') for s in steps) or not any(s.get('kind')=='agent' and s.get('id')==os.getenv('EVOLUS_AGENT_ID') and s.get('configured_model_key')==os.getenv('EVOLUS_GEMMA_MODEL_KEY') for s in steps):
                raise DomainError('Actual extractor/agent/model step evidence missing; integration remains unverified')
            record['runtime_model_identity']=execution.get('runtime_model_identity','Not returned / independent inference verification pending')
        record['raw_draft']=execution.get('draft')
        try:record['draft']=validate_draft(state,execution['draft'])
        except Exception as exc:
            record.update(status='failed validation',error='Raw interpretation failed source/schema validation; no fact or scope update')
            record['validation_issues']=exc.errors(include_input=False,include_url=False,include_context=False) if hasattr(exc,'errors') else [{'message':str(exc)[:300]}]
            jobs.finish(db,owner,key,'failed',digest(execution))
        else:
            current=fingerprint(state,catalog(db,owner))==record['snapshot_hash'] and not state.get('cancelled')
            accepted=jobs.finish(db,owner,key,'succeeded' if current else 'obsolete',digest(record['draft']))
            record['status']='unreviewed proposal' if current and accepted else 'obsolete / cancelled or changed evidence'
    record['finished_at']=now();repo.put_record(db,owner,'assist',key,record,rev)
    repo.audit(db,owner,identity.current_actor(),'assisted.result_recorded',{},record)
    return record


@router.post('/api/cases/{case_id}/assist-run')
def run(case_id:str,data:Run,request:Request):
    from .app import connect,read
    state=read(case_id,request.state.owner)
    if state['revision']!=data.revision or state.get('cancelled'):raise DomainError('Current active incident revision required')
    context=source_context(state,data.document_ids);key='ASSIST-'+digest([case_id,data.idempotency_key])[:24]
    with inference_access(data.mode,request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'reporter');_,prior=repo.get_record(db,request.state.owner,'assist',key)
            signature=digest([data.document_ids,data.revision,data.mode])
            if prior:
                if prior['request_hash']!=signature:raise DomainError('Idempotency key belongs to another interpretation')
                return prior
            if data.mode=='fixture' and not state['synthetic']:raise DomainError('Fixtures require an explicitly synthetic incident')
            if data.mode=='live':
                external.contract();reservation=external.reserve(db,'evolus')
                # Two configured own-model steps. Shared AMD quota is separate
                # from Evolus credits and every upstream step is reserved.
                external.reserve(db,'gemma');external.reserve(db,'gemma')
                if not all(os.getenv(k) for k in ('EVOLUS_WORKFLOW_ID','EVOLUS_EXTRACTOR_ID','EVOLUS_AGENT_ID','GEMMA_MODEL_ID')):raise DomainError('Configured workflow,extractor,agent and actual Gemma model identifiers required')
            else:reservation=None
            jobs.start(db,request.state.owner,key,'evolus-document',{'case_id':case_id,'revision':state['revision'],'sources':[d['original_hash'] for d in state['documents'] if d['id'] in data.document_ids]},data.mode)
            record={'id':key,'case_id':case_id,'mode':data.mode,'status':'running','actor':identity.current_actor(),'snapshot_hash':fingerprint(state,catalog(db,request.state.owner)),
                'request_hash':signature,'context_hash':digest(context),'started_at':now(),'reservation':reservation,'executions':[],
                'external_execution_id':None,'authority':'Unreviewed proposal only; no inventory, genealogy or approval writes'}
            repo.put_record(db,request.state.owner,'assist',key,record,0)
        try:
            if data.mode=='fixture':
                execution={'execution_id':'synthetic-'+key,'status':'completed','draft':{'candidates':[],'changes':[],'contradictions':[],'unresolved':['Synthetic contract abstention. No Evolus, extractor or Gemma request occurred. Use explicit source review.'],'request_drafts':[]},'steps':[],'provider':'Synthetic local contract / no external call'}
            else:
                docs=[d for d in state['documents'] if d['id'] in data.document_ids]
                files=[]
                for d in docs:
                    raw=repo.source_path(request.state.owner,d['original_hash']).read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=d['original_hash']:raise DomainError('Original source integrity failure before transmission')
                    files.append({'filename':d['filename'],'raw':raw,'media_type':d['media_type']})
                def before_configuration_read():
                    with repo.write(connect) as db:identity.recheck(db,'reporter');external.reserve(db,'evolus')
                reply=external.operation('workflow_start',{'workflow_id':os.environ['EVOLUS_WORKFLOW_ID'],'text':json.dumps(context,ensure_ascii=False),'context':context,'schema':ReviewDraft.model_json_schema(),'file_items':files},before_call=before_configuration_read)
                execution=reply['result'];execution['transport_provenance']={k:v for k,v in reply.items() if k!='result'}
            if execution.get('status') not in ('running','completed','failed') or not isinstance(execution.get('execution_id'),str) or len(execution['execution_id'])>160:raise DomainError('Unexpected documented workflow result contract')
            with repo.write(connect) as db:
                identity.recheck(db,'reporter');rev,record=repo.get_record(db,request.state.owner,'assist',key)
                record['external_execution_id']=execution['execution_id'];repo.put_record(db,request.state.owner,'assist',key,record,rev)
                return result_for_job(db,request.state.owner,read(case_id,request.state.owner),key,execution)
        except Exception as exc:
            with repo.write(connect) as db:
                rev,record=repo.get_record(db,request.state.owner,'assist',key)
                record.update(status='failed',error=str(exc) if isinstance(exc,DomainError) else 'Provider transport/timeout/schema failure; raw exception omitted',finished_at=now())
                jobs.finish(db,request.state.owner,key,'failed',digest({'error':record['error']}));repo.put_record(db,request.state.owner,'assist',key,record,rev)
            return record


@router.post('/api/cases/{case_id}/assist-poll')
def poll(case_id:str,data:Poll,request:Request):
    from .app import connect,read
    state=read(case_id,request.state.owner)
    with inference_access('live',request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'reporter');jobs.recover_expired(db,request.state.owner)
            rev,record=repo.get_record(db,request.state.owner,'assist',data.job_id);_,job=repo.get_record(db,request.state.owner,'job',data.job_id)
            if not record or record['case_id']!=case_id or not job:raise DomainError('Expected execution unavailable')
            if job['status']!='running' or record['status']!='running':return {**record,'job_state':job['status']}
            external.reserve(db,'evolus');execution_id=record['external_execution_id']
        reply=external.operation('workflow_status',{'workflow_id':os.environ['EVOLUS_WORKFLOW_ID'],'execution_id':execution_id});execution=reply['result']
        execution['transport_provenance']={k:v for k,v in reply.items() if k!='result'}
        with repo.write(connect) as db:
            identity.recheck(db,'reporter');return result_for_job(db,request.state.owner,read(case_id,request.state.owner),data.job_id,execution)


@router.post('/api/assist/callback')
def callback():raise HTTPException(403,'Callbacks cannot update cases. Use authenticated scoped status polling.')


@router.get('/api/cases/{case_id}/assisted')
def view(case_id:str,request:Request):
    from .app import connect,read
    state=read(case_id,request.state.owner)
    with connect() as db:
        result={k:a.records(db,request.state.owner,k,case_id) for k in a.KINDS}
        current_snapshot=fingerprint(state,catalog(db,request.state.owner))
        for proposal in result['assist']:proposal['stale']=proposal.get('snapshot_hash')!=current_snapshot
        result['source-link']=a.references(state,{k:a.records(db,request.state.owner,k,case_id) for k in ('assist','evidence-task','translation','label-review','recovery','action','answer','handover')})
        for task in result['evidence-task']:task['stale']=task['snapshot_hash']!=fingerprint(state)
        for brief in result['handover']:brief['stale']=not a.brief_current(db,request.state.owner,state,brief)
        result['next_evidence']=a.evidence_requests(db,request.state.owner,state)
        result['release_conditions']=a.conditions(db,request.state.owner,state) if state.get('workspace_attached') else {'stage':'Link reviewed workspace inventory before recovery','conditions':[]}
    result['provider']=external.status();return result


class Task(Strict):
    cause_id:str=Field(max_length=80)
    role:str=Field(default='',max_length=160)
    due_date:str=Field(default='',max_length=10)
    request_draft:str=Field(default='',max_length=3000)
    idempotency_key:str=Field(min_length=8,max_length=100)
    revision:int


class Ranking(Strict):
    policy_first:bool=True
    deadline_first:bool=True


@router.post('/api/cases/{case_id}/evidence-ranking')
def ranking(case_id:str,data:Ranking,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer')
        return a.save(db,request.state.owner,'evidence-ranking',case_id,{'case_id':case_id,'rules':data.model_dump(),'at':now(),'actor':identity.current_actor(),'authority':'Display ranking only; no quantities, probability or action authority'})
class ResponseReview(Strict):
    task_id:str=Field(max_length=80)
    document_id:str=Field(max_length=80)
    outcome:Literal['resolved','inconclusive','conflicting']
    quote:str=Field(min_length=8,max_length=2000)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/evidence-task')
def task(case_id:str,data:Task,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        if state['revision']!=data.revision:raise DomainError('Request revision stale')
        return a.create_task(db,request.state.owner,state,data.cause_id,data.role,data.due_date,data.request_draft,data.idempotency_key)


@router.post('/api/cases/{case_id}/response-review')
def response_review(case_id:str,data:ResponseReview,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):return a.task_response(db,request.state.owner,state,**data.model_dump())


@router.get('/api/cases/{case_id}/release-conditions')
def conditions(case_id:str,request:Request):
    from .app import connect,read
    state=read(case_id,request.state.owner)
    with connect() as db:return a.conditions(db,request.state.owner,state)


class SourceChange(Strict):
    source_kind:Literal['document','procedure']
    source_id:str=Field(max_length=160)
    old_version:str=Field(max_length=80)
    new_version:str=Field(max_length=80)
    classification:Literal['wording_only','factual','withdrawal','uncertain','applicability']
    effective_at:str=Field(max_length=80)
    old_quote:str=Field(min_length=1,max_length=2000)
    new_quote:str=Field(min_length=1,max_length=2000)
    note:str=Field(min_length=20,max_length=2000)
    event_key:str=Field(min_length=8,max_length=100)


@router.post('/api/assist/source-change')
def source_change(data:SourceChange,request:Request):
    from .app import connect
    try:
        with repo.write(connect) as db:return a.register_change(db,request.state.owner,**data.model_dump())
    except ValueError:raise DomainError('Valid timezone-aware effective date required')


class Segment(Strict):source:Citation;translation:str=Field(min_length=1,max_length=2500)
class Translation(Strict):
    document_id:str=Field(max_length=80)
    language:Literal['en','ru','it']
    segments:list[Segment]=Field(min_length=1,max_length=80)
    idempotency_key:str=Field(min_length=8,max_length=100)
    provenance_reference:str=Field(min_length=8,max_length=1000)
class TranslationReview(Strict):
    translation_id:str=Field(max_length=80)
    can_verify_original:bool
    qualified_reference:str=Field(max_length=500)
    critical_fields_confirmed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/translation')
def translation(case_id:str,data:Translation,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        return a.make_translation(db,request.state.owner,state,data.document_id,data.language,[s.model_dump() for s in data.segments],
            {'provider':'Explicit manually supplied derived translation','reference':data.provenance_reference,'live_evolus_or_gemma':False},data.idempotency_key)


@router.post('/api/cases/{case_id}/translation-review')
def translation_review(case_id:str,data:TranslationReview,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        return a.review_translation(db,request.state.owner,state,data.translation_id,data.can_verify_original,data.qualified_reference,data.critical_fields_confirmed,data.note)


class Image(Strict):
    filename:str=Field(min_length=1,max_length=160)
    content_base64:str=Field(max_length=2_700_000)
    crop_xywh:list[int]=Field(default_factory=list,max_length=4)
class Reading(Strict):
    label_id:str=Field(max_length=80)
    reading:label_images.LabelReading
    reference:str=Field(min_length=8,max_length=1000)
class LabelReview(Strict):
    label_id:str=Field(max_length=80)
    document_id:str=Field(max_length=80)
    quote:str=Field(min_length=1,max_length=2000)
    selected_id:str=Field(min_length=1,max_length=160)
    identity_confirmed:bool
    relationship_verified:bool
    unresolved:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/label-image')
def image(case_id:str,data:Image,request:Request):
    from .app import read,transaction
    state=read(case_id,request.state.owner)
    if Path(data.filename).name!=data.filename or '/' in data.filename or '\\' in data.filename or Path(data.filename).suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise DomainError('Plain PNG/JPEG/WebP filename required')
    if len(data.crop_xywh) not in (0,4):raise DomainError('Crop requires x,y,width,height in the EXIF-oriented original')
    try:raw=base64.b64decode(data.content_base64,validate=True)
    except ValueError:raise DomainError('Invalid image encoding')
    # Authorize before expensive decode; network, image decode and source parser
    # work stay outside serialized writer transactions.
    info,derived=label_images.decode(raw,data.crop_xywh)
    with transaction(case_id,request.state.owner) as (db,current):
        if current['revision']!=state['revision']:raise DomainError('Incident changed during image processing; retry explicit import')
        return label_images.commit_image(db,request.state.owner,current,data.filename,raw,data.crop_xywh,info,derived)


@router.get('/api/cases/{case_id}/label-images/{label_id}')
def get_image(case_id:str,label_id:str,request:Request):
    from .app import read,connect
    read(case_id,request.state.owner)
    with connect() as db:
        _,label=repo.get_record(db,request.state.owner,'label',label_id)
        if not label or label['case_id']!=case_id:raise HTTPException(404,'Label unavailable')
        raw=repo.source_path(request.state.owner,label['derived_hash']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=label['derived_hash']:raise DomainError('Image source integrity failure')
    return {'label':label,'data_url':'data:image/png;base64,'+base64.b64encode(raw).decode()}


@router.post('/api/cases/{case_id}/label-reading')
def reading(case_id:str,data:Reading,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer');rev,label=repo.get_record(db,request.state.owner,'label',data.label_id)
        if not label or label['case_id']!=case_id:raise DomainError('Label unavailable')
        if label.get('review'):raise DomainError('Reviewed image reading is immutable; import a new crop/version for correction')
        if label.get('reading'):raise DomainError('Reading is immutable; create a new image/crop version')
        label['reading']=label_images.validate_reading(data.reading.model_dump());label['reading_provenance']={'provider':'Manual operator transcription / not Gemma vision','reference':data.reference,'actor':identity.current_actor(),'at':now()}
        return a.save(db,request.state.owner,'label',label['id'],label,rev)


@router.post('/api/cases/{case_id}/label-review')
def label_review(case_id:str,data:LabelReview,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):return label_images.review_label(db,request.state.owner,state,data.label_id,data.document_id,data.quote,data.selected_id,data.identity_confirmed,data.relationship_verified,data.unresolved,data.note)


class Handover(Strict):
    idempotency_key:str=Field(min_length=8,max_length=100)
    previous_id:str|None=Field(default=None,max_length=80)
class BriefReview(Strict):
    handover_id:str=Field(max_length=80)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/handover')
def handover(case_id:str,data:Handover,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):return a.create_handover(db,request.state.owner,state,data.idempotency_key,data.previous_id)


@router.post('/api/cases/{case_id}/handover-review')
def handover_review(case_id:str,data:BriefReview,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        rev,brief=repo.get_record(db,request.state.owner,'handover',data.handover_id)
        if not brief or brief['case_id']!=case_id or not data.reviewed or not a.brief_current(db,request.state.owner,state,brief):raise DomainError('Current handover and explicit review required; acknowledgements never approve recovery')
        brief['review']={'actor':identity.current_actor(),'at':now(),'note':data.note}
        return a.save(db,request.state.owner,'handover',brief['id'],brief,rev)


class Reassessment(Strict):
    task_id:str=Field(max_length=80)
    revision:int
    old_quote:str=Field(min_length=1,max_length=2000)
    new_quote:str=Field(min_length=1,max_length=2000)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/rereview-review')
def reassess(case_id:str,data:Reassessment,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer');rev,task=repo.get_record(db,request.state.owner,'rereview',data.task_id)
        if not task or task['case_id']!=case_id or not data.reviewed or state['revision']!=data.revision or state.get('pending_revision'):
            raise DomainError('Current explicitly reassessed incident scope required before closing source-change review')
        if data.old_quote!=task['old_quote'] or data.new_quote!=task['new_quote']:raise DomainError('Review both exact version passages')
        task.update(status='reassessed / historical receipts unchanged',review={'actor':identity.current_actor(),'at':now(),'revision':state['revision'],'note':data.note})
        return a.save(db,request.state.owner,'rereview',task['id'],task,rev)


class Generate(Strict):
    kind:Literal['document','request','translation','label','handover','knowledge']
    idempotency_key:str=Field(min_length=8,max_length=100)
    revision:int
    document_ids:list[str]=Field(default_factory=list,max_length=2)
    language:Literal['en','ru','it']='en'
    label_id:str=Field(default='',max_length=80)
    cause_id:str=Field(default='',max_length=80)
    previous_id:str|None=Field(default=None,max_length=80)
    question:str=Field(default='',max_length=1000)
    product:str=Field(default='',max_length=160)
    process:str=Field(default='coating',max_length=160)
class TranslatedDraft(Strict):segments:list[Segment]=Field(min_length=1,max_length=40)
class RequestDraft(Strict):cause_id:str;draft:str=Field(min_length=20,max_length=2500)
class HandoverStatement(Strict):fact_id:str=Field(max_length=100);text:str=Field(max_length=2000)
class HandoverDraft(Strict):statements:list[HandoverStatement]=Field(max_length=24)


@router.post('/api/cases/{case_id}/assist-generate')
def generate(case_id:str,data:Generate,request:Request):
    from .app import connect,read
    from . import knowledge
    state=read(case_id,request.state.owner)
    if data.revision!=state['revision']:raise DomainError('Current incident revision required')
    key='GENERATE-'+digest([case_id,data.idempotency_key])[:24];signature=digest(data.model_dump())
    image_url=None;label=None;binding=None;retrieval=None
    with inference_access('live',request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'reporter');_,prior=repo.get_record(db,request.state.owner,'assist',key)
            if prior:
                if prior['request_hash']!=signature:raise DomainError('Idempotency key belongs to another generation')
                return prior
            if data.kind in ('document','translation'):
                context=source_context(state,data.document_ids)
                from .scope_proposals import INSTRUCTIONS
                context['task']=(INSTRUCTIONS+' Use the supplied ReviewDraft shape: value is the identifier, disposition describes the identity assertion, incident_status separately describes incident involvement. asserted identity never means affected. Cite source. Include semantic paired changes and contradictions when comparing sources.') if data.kind=='document' else 'Translate into English. Preserve exact IDs,numbers,units,negation,modality and ambiguous dates. Cite originals; do not invent missing information.'
                if data.kind=='translation' and len(data.document_ids)!=1:raise DomainError('Translate one original document at a time')
                schema=ReviewDraft.model_json_schema() if data.kind=='document' else TranslatedDraft.model_json_schema()
            elif data.kind=='request':
                q=next((q for q in a.evidence_requests(db,request.state.owner,state)['requests'] if q['id']==data.cause_id),None)
                if not q:raise DomainError('Current unresolved evidence request required')
                context={'task':'Draft one specific missing-evidence request. No invented probabilities,dates,response times or release promises. It is a saved draft only.','computed_gap':q};schema=RequestDraft.model_json_schema()
            elif data.kind=='label':
                _,label=repo.get_record(db,request.state.owner,'label',data.label_id)
                if not label or label['case_id']!=case_id or label.get('reading'):raise DomainError('Owned untranscribed label required; import a new crop for a revised reading')
                if os.getenv('GEMMA_VISION_VERIFIED')!='true':raise DomainError('UNAVAILABLE: deployed Gemma image acceptance not yet verified')
                image_bytes=repo.source_path(request.state.owner,label['derived_hash']).read_bytes()
                if hashlib.sha256(image_bytes).hexdigest()!=label['derived_hash']:raise DomainError('Derived image integrity failure')
                image_url='data:image/png;base64,'+base64.b64encode(image_bytes).decode()
                context={'task':'Read only visible lot identifiers. Preserve spelling and leading zeros; abstain if unreadable. List O/0,B/8,S/5 ambiguity. Multiple labels stay separate. No quality or authenticity judgment.','crop':label['transform']};schema=label_images.LabelReading.model_json_schema()
            elif data.kind=='handover':
                context=a.handover_snapshot(db,request.state.owner,state,data.previous_id)
                context['task']='Select a concise next-shift brief. Each statement must copy one exact fact text and its fact_id. Never invent numbers,statuses,owners,deadlines or authority.';schema=HandoverDraft.model_json_schema()
            else:
                retrieval=knowledge.retrieve(catalog(db,request.state.owner),data.question,data.product,data.process,state['synthetic'])
                if retrieval['status']!='retrieved':return {'status':'insufficient / local applicability abstention','provider_calls':0,'retrieval':retrieval}
                documents=evolus_api.applicable_documents(catalog(db,request.state.owner),data.product,data.process,state['synthetic'])
                scope=evolus_api.library_scope(request.state.owner,data.product,data.process,documents)
                _,binding=repo.get_record(db,request.state.owner,'knowledge-binding',scope)
                if not binding or binding['status']!='indexed verified scope' or binding['scope']!=scope:
                    raise DomainError('UNAVAILABLE: a dedicated verified library for this organization/site and exact approved catalog is required before any retrieval')
                external.contract()
                context={'task':'Select only exact authorized document_id/version/passage_id keys that directly answer the question. Do not copy or paraphrase passages: the server displays the full retained original. Return insufficient_evidence=true for unsupported questions, bypass requests or missing evidence. Never invent keys, revisions, instructions or authority.',
                    'question':data.question,'approved_passages':retrieval['passages']};schema=knowledge.PassageSelection.model_json_schema()
            external.allowance('gemma');reservation=external.reserve(db,'gemma')
            jobs.start(db,request.state.owner,key,'gemma-'+data.kind,{'case_id':case_id,'kind':data.kind,'revision':state['revision'],'context_hash':digest(context)},'live')
            record={'id':key,'case_id':case_id,'kind':data.kind,'mode':'live','provider_path':('Direct AMD vision / ' if data.kind=='label' else 'Direct Gemma / ')+os.getenv('GEMMA_HOSTING_KIND','unverified'),
                'status':'running','request_hash':signature,'snapshot_hash':fingerprint(state,catalog(db,request.state.owner)),
                'actor':identity.current_actor(),'started_at':now(),'reservation':reservation,'authority':'Unreviewed draft only; existing review/calculation/approval remain mandatory'}
            repo.put_record(db,request.state.owner,'assist',key,record,0)
        try:
            library_provenance=None
            if binding:
                def reserve_library_call():
                    with repo.write(connect) as db:
                        identity.recheck(db,'reporter');external.reserve(db,'evolus')
                        current_docs=evolus_api.applicable_documents(catalog(db,request.state.owner),data.product,data.process,state['synthetic'])
                        if evolus_api.library_scope(request.state.owner,data.product,data.process,current_docs)!=binding['scope']:raise DomainError('Approved applicability changed before retrieval')
                passages,library_provenance=evolus_api.library_passages(binding,retrieval['passages'],before_call=reserve_library_call)
                context['approved_passages']=passages
            response=external.gemma(context,schema,image=image_url)
            raw=response.pop('result')
            with repo.write(connect) as db:
                identity.recheck(db,'reporter');current=read(case_id,request.state.owner);rev,record=repo.get_record(db,request.state.owner,'assist',key)
                record.update(raw_output=raw,provenance=response,library_provenance=library_provenance,finished_at=now())
                _,job=repo.get_record(db,request.state.owner,'job',key)
                if fingerprint(current,catalog(db,request.state.owner))!=record['snapshot_hash'] or job['status']!='running' or job['lease_until']<__import__('time').time() or current.get('cancelled'):
                    record['status']='obsolete / changed or cancelled';jobs.finish(db,request.state.owner,key,'obsolete',digest(raw))
                else:
                    if data.kind=='document':record['draft']=validate_draft(current,raw)
                    elif data.kind=='translation':
                        parsed=TranslatedDraft.model_validate(raw).model_dump()
                        record['draft']=a.make_translation(db,request.state.owner,current,data.document_ids[0],data.language,parsed['segments'],response,key)
                        db.execute('UPDATE cases SET state=? WHERE owner=? AND id=?',(json.dumps(current),request.state.owner,case_id))
                        record['snapshot_hash']=fingerprint(current,catalog(db,request.state.owner))
                    elif data.kind=='label':
                        result=label_images.validate_reading(raw);lrev,current_label=repo.get_record(db,request.state.owner,'label',data.label_id)
                        if current_label.get('reading'):raise DomainError('Label reading changed during inference; result cannot overwrite it')
                        current_label.update(reading=result,reading_provenance=response,status='Gemma reading proposed / visual confirmation required');a.save(db,request.state.owner,'label',data.label_id,current_label,lrev);record['draft']=current_label
                    elif data.kind=='request':
                        result=RequestDraft.model_validate(raw).model_dump()
                        if result['cause_id']!=data.cause_id or __import__('re').search(r'\d\s*%|probability|guaranteed|will release',result['draft'],__import__('re').I):raise DomainError('Request invented probability or release authority')
                        record['draft']=result
                    elif data.kind=='handover':record['draft']=a.create_handover(db,request.state.owner,current,key,data.previous_id,raw,response)
                    else:
                        record['draft']=knowledge.selected_answer(raw,retrieval)
                        record['quote_origin']='Deterministically resolved full authorized original passages; the model selected keys and did not author the displayed quotes'
                        linked={'id':key,'case_id':case_id,'status':'succeeded','mode':'Live Gemma / isolated Evolus library','output':record['draft'],
                            'catalog_digest':digest(catalog(db,request.state.owner)),'retrieval':retrieval,'question':data.question,'provenance':response,
                            'library_provenance':library_provenance,'timestamp':now(),'boundary':'Exact applicable passage proposals; explicit original evidence review required for any check'}
                        repo.put_record(db,request.state.owner,'answer',key,linked,0);record['linked_answer']=linked
                    record['status']='unreviewed proposal';jobs.finish(db,request.state.owner,key,'succeeded',digest(record['draft']))
                repo.put_record(db,request.state.owner,'assist',key,record,rev);return record
        except Exception as exc:
            with repo.write(connect) as db:
                rev,record=repo.get_record(db,request.state.owner,'assist',key)
                record.update(status='failed validation' if 'raw' in locals() else 'failed provider request',error=str(exc) if isinstance(exc,DomainError) else 'Structured-output,timeout or transport failure; no fallback',finished_at=now())
                if isinstance(exc,external.ProviderFailure):record['failed_request_metadata']=exc.evidence
                if 'raw' in locals():record.update(raw_output=raw,provenance=response)
                if binding:record.update(library_provenance=library_provenance,retrieval=retrieval)
                if 'raw' in locals():record['validation_issues']=exc.errors(include_input=False,include_url=False,include_context=False) if hasattr(exc,'errors') else [{'message':str(exc)[:300]}]
                jobs.finish(db,request.state.owner,key,'failed',digest({'error':record['error']}));repo.put_record(db,request.state.owner,'assist',key,record,rev)
                return record


class ProposalReview(Strict):
    proposal_id:str=Field(max_length=80)
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)
    corrected_draft:ReviewDraft|None=None


class ReviewIntake(Strict):
    proposal_id:str=Field(max_length=80)
    document_id:str=Field(max_length=80)
    revision:int


@router.post('/api/cases/{case_id}/assist-intake')
def review_intake(case_id:str,data:ReviewIntake,request:Request):
    """Open the existing critical-fact review using actual validated proposals.

    This copies no reviewed facts or completeness flags. Every candidate starts
    unresolved in the existing UI and must pass the unchanged approval engine.
    """
    from .app import transaction
    from .review_safety import scope_concerns
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer');_,proposal=repo.get_record(db,request.state.owner,'assist',data.proposal_id)
        if not proposal or proposal['case_id']!=case_id or data.revision!=state['revision'] or proposal['snapshot_hash']!=fingerprint(state,catalog(db,request.state.owner)) or proposal['status'] not in ('unreviewed proposal','source proposals inspected / no fact or action authority'):
            raise DomainError('Current source-validated proposal required')
        doc=next((d for d in state['documents'] if d['id']==data.document_id),None)
        if not doc or doc.get('request_id'):raise DomainError('Use receiving review for a linked response; choose an incident notice here')
        draft=proposal['draft'];facts=[]
        for c in draft.get('candidates',[]):
            if c['kind']=='supplier_lot' and c['source']['document_id']==doc['id']:
                # An asserted LOT ID is not an asserted incident effect. The
                # typed draft may merely mention a lot in a receipt. Preserve
                # its proposal meaning and require the existing explicit review.
                facts.append({'lot_id':c['value'],'affected':False,'proposal_disposition':c['disposition'],'proposal_incident_status':c.get('incident_status'),'evidence':[c['source']]})
        if not facts:raise DomainError('No source-backed supplier-lot candidates in this notice; abstention cannot become a scope extraction')
        rid='assist-'+digest([data.proposal_id,doc['id']])[:24]
        if not any(r['id']==rid for r in state['runs']):
            provenance=proposal.get('provenance',{})
            state['runs'].append({'id':rid,'mode':proposal['mode'],'status':'succeeded','revision':state['revision'],'document_id':doc['id'],
                'timestamp':now(),'provider':proposal.get('provider_path','Evolus workflow / configured Gemma agent'),
                'model_id':provenance.get('model_id'),'elapsed_ms':provenance.get('elapsed_ms'),'proposal_id':data.proposal_id,
                'runtime_model_identity':proposal.get('runtime_model_identity'),'scope_concerns':scope_concerns(doc),
                'proposal_correction':proposal.get('correction'),
                'output':{'facts':facts,'qualifiers':draft.get('unresolved',[])+['Identity proposals only; presence or asserted identity does not establish affected incident scope. All candidates require explicit current source and scope review.']}})
        return state


@router.post('/api/cases/{case_id}/assist-review')
def proposal_review(case_id:str,data:ProposalReview,request:Request):
    from .app import transaction
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer');rev,record=repo.get_record(db,request.state.owner,'assist',data.proposal_id)
        permitted=('unreviewed proposal','failed validation') if data.corrected_draft is not None else ('unreviewed proposal',)
        if not record or record['case_id']!=case_id or record.get('kind') not in (None,'document') or record['status'] not in permitted or not data.reviewed or fingerprint(state,catalog(db,request.state.owner))!=record['snapshot_hash']:raise DomainError('Current document proposal and explicit original-source inspection required')
        if data.corrected_draft is not None:
            corrected=validate_draft(state,data.corrected_draft.model_dump())
            # Original raw output and failed job remain intact. This explicit
            # quality-review correction is not a new successful model response.
            record['raw_quality_status']=record['status'];record['draft']=corrected
            record['correction']={'actor':identity.current_actor(),'at':now(),'note':data.note,'corrected_hash':digest(corrected),
                'basis':'Explicit source-checked reviewer correction; model raw output remains unchanged; separate critical-fact/scope review still required'}
        record.update(status='source proposals inspected / no fact or action authority',review={'actor':identity.current_actor(),'at':now(),'note':data.note})
        return a.save(db,request.state.owner,'assist',record['id'],record,rev)


class KnowledgeIndex(Strict):
    library_id:str=Field(pattern='^[A-Za-z0-9_-]{1,160}$')
    product:str=Field(min_length=1,max_length=160)
    process:str=Field(min_length=1,max_length=160)
    synthetic:bool=False
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/assist/knowledge-index')
def knowledge_index(data:KnowledgeIndex,request:Request):
    from .app import connect
    with inference_access('live',request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'administrator')
            if not data.reviewed:raise DomainError('Explicit isolated-library review required')
            docs=catalog(db,request.state.owner)
            approved=evolus_api.applicable_documents(docs,data.product,data.process,data.synthetic)
            if not approved:raise DomainError('No approved document versions to index')
            if len(approved)>12:raise DomainError('Initial isolated-library indexing is bounded to twelve approved versions')
            scope=evolus_api.library_scope(request.state.owner,data.product,data.process,approved)
            for other,encoded in db.execute("SELECT owner,data FROM bf_records WHERE kind='knowledge-binding'"):
                prior=json.loads(encoded)
                if prior['library_id']==data.library_id:
                    if other==request.state.owner and prior['scope']==scope and prior['status']=='indexed verified scope':return prior
                    raise DomainError('Library already reserved: use a separate empty library for this exact organization/site/product/process/source set')
            external.contract();external.reserve(db,'evolus');snapshot=digest(docs)
            # Reserve before networking. Failed/partial imports keep this library
            # unavailable and cannot be rebound to another tenant/applicability.
            value={'library_id':data.library_id,'scope':scope,'product':data.product,'process':data.process,
                'status':'reserved / indexing incomplete','catalog_digest':snapshot,'documents':[],
                'at':now(),'actor':identity.current_actor(),'note':data.note,'provenance':[]}
            a.save(db,request.state.owner,'knowledge-binding',scope,value,0)
        inspection=evolus_api.inspect_library(data.library_id)
        if inspection['result']!=[]:raise DomainError('Dedicated empty library required; existing remote documents cannot be adopted implicitly')
        with repo.write(connect) as db:identity.recheck(db,'administrator');external.reserve(db,'evolus')
        memory=evolus_api.call('GET',f'/api/v1/memories/{evolus_api.identifier(data.library_id)}')['result']
        if memory.get('applicationId')!=os.environ['EVOLUS_APPLICATION_ID'] or memory.get('type')!=1 or memory.get('aiAccess')!=0:
            raise DomainError('Initial zero-cost path requires this application\'s dedicated read-only Blob library; embeddings/platform-AI indexing are disabled')
        value['library_type']='Blob'
        for document in approved:
            with repo.write(connect) as db:
                identity.recheck(db,'administrator');external.reserve(db,'evolus')
                if digest(catalog(db,request.state.owner))!=snapshot:raise DomainError('Catalog changed during indexing; library remains unavailable')
            content='\n\n'.join(p['text'] for p in document['passages']).encode('utf-8')
            reply=evolus_api.call('POST',f'/api/v1/memories/{evolus_api.identifier(data.library_id)}/documents',
                files=[{'filename':document['source_hash']+'.txt','raw':content,'media_type':'text/plain'}],
                query={'language':'en','backgroundIngestion':'false','augmentation':'false','rephrasings':0,'implicitQuestions':0})
            remote=reply['result']
            if remote.get('memoryId')!=data.library_id or not remote.get('id'):raise DomainError('Unexpected indexing destination; binding remains unavailable')
            value['documents'].append({'document_id':document['id'],'version':document['version'],'source_hash':document['source_hash'],
                'remote_document_id':remote['id'],'ingestion_status':remote.get('ingestionStatus'),'uploaded_content_hash':hashlib.sha256(content).hexdigest()})
            value['provenance'].append({k:v for k,v in reply.items() if k!='result'})
        with repo.write(connect) as db:
            identity.recheck(db,'administrator')
            if digest(catalog(db,request.state.owner))!=snapshot:raise DomainError('Approved versions changed while indexing; binding remains disabled')
            value.update(status='indexed verified scope',at=now())
            value['provenance'].insert(0,{k:v for k,v in inspection.items() if k!='result'})
            return a.save(db,request.state.owner,'knowledge-binding',scope,value)
