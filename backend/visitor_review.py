"""Public, source-only review. No owner-token bypass on existing live routes.

The shared free endpoint enforces its own quota. Historical engineering ledgers
are never read or modified here. Every dispatch checks actual catalog/usage.
"""
import json,os,re,threading,time,uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Request,HTTPException
from pydantic import Field
import httpx
from . import repository as repo,evolus_adapter as external,jobs
from .assist_contracts import Strict,ReviewDraft,validate_draft,source_context,fingerprint
from .domain import DomainError,digest
from .fixtures import now
from .public_demo import live_slot,RequestLimiter

router=APIRouter()
BASE='https://developer.amd.com.cn/radeon/api/v1'
MODEL='Gemma-4-31B-IT'
REFERENCE='https://notebooks.amd.com/tokenfactory (User Manual, checked 2026-10-18)'
visitor_limit=RequestLimiter()
status_cache={}
status_lock=threading.Lock()


def enabled():
    from .identity import pilot
    return os.getenv('PUBLIC_REVIEW_ENABLED')=='true' and not pilot()


def entitlement(transport=None):
    """No inference, paid fallback, coupon redemption or credential changes."""
    if not enabled():raise HTTPException(503,{'code':'PROVIDER_UNAVAILABLE','message':'Visitor AI analysis is not enabled.'})
    if os.getenv('GEMMA_API_BASE_URL','').rstrip('/')!=BASE or os.getenv('GEMMA_MODEL_ID')!=MODEL or os.getenv('GEMMA_HOSTING_KIND')!='managed-amd-shared' or not os.getenv('GEMMA_API_KEY'):
        raise HTTPException(503,{'code':'PROVIDER_UNAVAILABLE','message':'The verified free shared Gemma route is unavailable.'})
    try:
        with httpx.Client(timeout=12,follow_redirects=False,trust_env=False,transport=transport) as c:
            headers={'Authorization':'Bearer '+os.environ['GEMMA_API_KEY']}
            u=c.get(BASE+'/usage',params={'include_recent':'false'},headers=headers)
            m=c.get(BASE+'/models',headers=headers)
            if u.status_code==429 or m.status_code==429:raise HTTPException(429,{'code':'ALLOWANCE_EXHAUSTED','message':'Shared provider allowance or rate limit reached. Try after the provider reset.'})
            if u.status_code!=200 or m.status_code!=200:raise ValueError()
            usage=json.loads(b''.join(external._bounded(u.iter_bytes(),100000)))
            models=json.loads(b''.join(external._bounded(m.iter_bytes(),100000)))['data']
        match=next((x for x in models if x.get('id')==MODEL),None)
        limit=float(usage['daily_cost_limit_usd']);remaining=float(usage['daily_cost_remaining_usd'])
        reset=datetime.fromisoformat(usage['daily_reset_at'].replace('Z','+00:00'))
        if not match or match.get('json_output') is not True or not 0<limit<=1 or reset<=datetime.now(timezone.utc):raise ValueError()
        if not 0.02<=remaining<=limit:raise HTTPException(429,{'code':'ALLOWANCE_EXHAUSTED','message':'Shared free allowance is exhausted or below its safety margin. Quota reset: '+usage['daily_reset_at']})
        return {'status':'available','provider':'AMD shared Gemma','requested_model_id':MODEL,'checked_at':now(),
            'remaining_nonmonetary_points':remaining,'daily_limit_nonmonetary_points':limit,'quota_reset_at':usage['daily_reset_at'],
            'access_expires_at':None,'availability':'Event access has no published end date; it can be withdrawn. Quota reset is not an access expiration.',
            'additional_cash':0,'basis':REFERENCE,'catalog_free_flag':match.get('free'),
            'cost_note':'The shared-event manual defines pricing as nonmonetary points, despite the generic catalog free flag. No dedicated or paid endpoint is used.'}
    except HTTPException:raise
    except (httpx.HTTPError,ValueError,KeyError,TypeError,DomainError):
        raise HTTPException(503,{'code':'PROVIDER_UNAVAILABLE','message':'Current free provider entitlement could not be verified. No inference was submitted.'}) from None


@router.get('/api/visitor/status')
def status():
    # Status display cache only; dispatch always performs a fresh entitlement read.
    with status_lock:
        if status_cache.get('until',0)>time.monotonic():return status_cache['value']
        try:value=entitlement()
        except HTTPException as e:value={'status':'allowance exhausted' if e.status_code==429 else 'provider unavailable','message':e.detail['message']}
        status_cache.update(until=time.monotonic()+60,value=value)
        return value


@router.post('/api/cases/visitor')
def create(request:Request):
    from .app import insert
    if not enabled():raise HTTPException(503,{'code':'VISITOR_UNAVAILABLE','message':'Visitor review is unavailable.'})
    state={'id':uuid.uuid4().hex,'name':'Your document review','incident':'Uploaded evidence · inventory context required','synthetic':False,'visitor_review':True,
        'revision':1,'inventory_version':1,'documents':[],'stocks':[],'edges':[],'allocations':[],'bounded':False,
        'policy':{'id':'SOURCE-REVIEW','revision':1,'rule':'Source-only review. No inventory calculation, approval, hold or release authority.'},
        'scope':{'lot_ids':[],'revision':0,'qualifiers':['Inventory quantities and lineage have not been supplied.']},
        'runs':[],'reviews':[],'plans':[],'plan':None,'history':[],'receipts':[],'pending_data':None,'pending_revision':True}
    return insert(state,request.state.owner)


class Analyze(Strict):
    document_id:str=Field(min_length=1,max_length=80)
    revision:int
    idempotency_key:str=Field(min_length=8,max_length=100)
    external_processing_consent:bool


def source_check(doc):
    text='\n'.join(b['text'] for b in doc['blocks'])
    if doc.get('ocr') and not doc['ocr'].get('critical_fields_confirmed'):
        raise HTTPException(422,{'code':'UNREADABLE_INPUT','message':'This scan needs original-image/OCR confirmation. Use a readable native-text PDF or UTF-8 TXT for visitor analysis.'})
    if not re.search(r'\b(lots?|batches|batch|supplier|receiving|recall)\b|партии|партия|поставщик|lott[oi]|fornitore',text,re.I) or not re.search(r'\b(lots?|batches|batch|defect|affected|excluded|receipt|quality|hold|inspection)\b|партии|партия|дефект|lott[oi]',text,re.I):
        raise HTTPException(422,{'code':'UNRELATED_INPUT','message':'Unsupported document purpose: provide a supplier/quality notice, batch record or receiving evidence with lot context. General documents are not analyzed.'})
    return text


def retain_unknown_ids(state,raw,doc):
    """Bounded source checklist, no invented identifiers, relationships or effects."""
    # Source-only review must not turn an interpretation into an inventory
    # assertion. Preserve the exact model proposals separately, then validate
    # grounding on unresolved identities. The protected action-level vocabulary
    # and every downstream approval check remain unchanged.
    proposed=ReviewDraft.model_validate(raw).model_dump()
    safe=json.loads(json.dumps(proposed))
    for candidate in safe['candidates']:
        if candidate['source']['document_id']!=doc['id']:raise DomainError('Visitor candidates must cite the selected original')
        if candidate['kind'] in ('supplier_lot','stock_pool','receipt_id','lineage_row'):
            candidate.update(disposition='unresolved',incident_status='uncertain')
    safe['incident_scope']='unknown'
    draft=validate_draft(state,safe,[doc['id']])
    for candidate,original in zip(draft['candidates'],proposed['candidates']):
        candidate['model_incident_status']=original['incident_status']
        candidate['model_disposition']=original['disposition']
    draft['model_incident_scope']=proposed['incident_scope']
    selected={c['value'] for c in draft['candidates']}
    for b in doc['blocks']:
        if not re.search(r'\b(lots?|batches|batch)\b|парт|lott[oi]',b['text'],re.I):continue
        for value in re.findall(r'(?<![\w./-])[A-Za-z0-9]+(?:[-./][A-Za-z0-9]+)+(?![\w./-])',b['text']):
            if value in selected:continue
            if len(draft['candidates'])>=40:raise DomainError('Source identity envelope exceeded; no partial identity set accepted')
            offset=max(0,b['text'].index(value)-800)
            draft['candidates'].append({'kind':'supplier_lot','value':value,'disposition':'unresolved','incident_status':'uncertain',
                'source':{'document_id':doc['id'],'block_id':b['id'],'quote':b['text'][offset:offset+2000]},'origin':'Exact local source checklist; model omitted this reference'})
            selected.add(value)
    # Preserve raw model interpretation separately from missing inventory context.
    for c in draft['candidates']:
        if c['kind'] in ('supplier_lot','stock_pool','receipt_id','lineage_row'):c['inventory_status']='unresolved / no inventory relationship supplied'
    draft['unresolved']=list(dict.fromkeys(draft['unresolved']+['Model incident effects remain unreviewed proposals. Source inspection does not resolve inventory or incident scope.','Supply reviewed inventory quantities, supplier-to-stock lineage and allocations before any containment calculation.']))
    return draft


@router.get('/api/cases/{case_id}/visitor-analysis')
def results(case_id:str,request:Request):
    from .app import read,connect
    state=read(case_id,request.state.owner)
    if not state.get('visitor_review'):raise HTTPException(404,'Visitor review unavailable')
    from .assisted import records
    with repo.write(connect) as db:
        jobs.recover_expired(db,request.state.owner)
        values=records(db,request.state.owner,'assist',case_id)
        for value in values:
            if value['status']=='running':
                _,job=repo.get_record(db,request.state.owner,'job',value['id'])
                if job and job['status']=='interrupted':
                    rev,_=repo.get_record(db,request.state.owner,'assist',value['id'])
                    value.update(status='provider unavailable',error='Processing was interrupted or exceeded its lease. The attempt is retained; no automatic retry.',finished_at=now())
                    repo.put_record(db,request.state.owner,'assist',value['id'],value,rev)
    for value in values:value['stale']=value.get('snapshot_hash')!=fingerprint(state)
    return values


@router.post('/api/cases/{case_id}/visitor-analysis')
def analyze(case_id:str,data:Analyze,request:Request):
    from .app import read,connect
    state=read(case_id,request.state.owner)
    if not state.get('visitor_review') or not enabled():raise HTTPException(403,{'code':'REVIEW_ONLY','message':'This route is only for isolated visitor source review.'})
    if data.revision!=state['revision']:raise HTTPException(409,{'code':'STALE_SOURCE','message':'The source changed. Inspect the current original before analysis.'})
    if not data.external_processing_consent:raise HTTPException(422,{'code':'CONSENT','message':'Confirm that this nonsensitive document may be processed by AMD.'})
    doc=next((d for d in state['documents'] if d['id']==data.document_id),None)
    if not doc:raise HTTPException(404,{'code':'DOCUMENT','message':'Select an uploaded original in this session.'})
    source_check(doc)
    context=source_context(state,[doc['id']]);context['task']='Extract exact supplier/batch identities and source-grounded incident proposals, including excluded, uncertain and merely mentioned lots. Retain every source identity. Cite supplied original document_id/block_id and exact quotes. Preserve negation, conflicting revisions and incomplete scope. Do not invent inventory, ancestry, quantities or sample IDs. If unrelated or unreadable, abstain with explicit unresolved reasons. Never grant approval or act.'
    key='VISITOR-'+digest([case_id,data.idempotency_key])[:32]
    signature=digest(data.model_dump())
    with connect() as db:
        _,old=repo.get_record(db,request.state.owner,'assist',key)
    if old:
        if old['request_hash']!=signature:raise HTTPException(409,{'code':'IDEMPOTENCY','message':'The request key belongs to different input.'})
        return old
    if not live_slot.acquire(blocking=False):raise HTTPException(429,{'code':'LIVE_BUSY','message':'Another AI analysis is processing. Try again after it finishes.'})
    try:
        proof=entitlement()
        # Session quota persists with workspace state, separate from phase ledgers.
        with repo.write(connect) as db:
            _,old=repo.get_record(db,request.state.owner,'assist',key)
            if old:return old
            rev,quota=repo.get_record(db,request.state.owner,'visitor-usage','current',{'attempts':0})
            if quota['attempts']>=4:raise HTTPException(429,{'code':'SESSION_LIMIT','message':'This session has used its four AI attempts. Retained results and originals remain available.'})
            host=request.client.host if request.client else 'unknown'
            if not visitor_limit.allow('visitor:'+host,global_limit=6,owner_limit=2):raise HTTPException(429,{'code':'RATE_LIMIT','message':'Visitor analysis is temporarily rate limited. Try in one minute.'})
            quota['attempts']+=1;repo.put_record(db,request.state.owner,'visitor-usage','current',quota,rev)
            record={'id':key,'case_id':case_id,'kind':'document','document_ids':[doc['id']],'mode':'live','status':'running','started_at':now(),
                'provider_path':'Direct AMD shared Gemma / visitor source review','request_hash':signature,'snapshot_hash':fingerprint(state),
                'entitlement':proof,'authority':'Unreviewed proposals only. No inventory relationships or action authority.'}
            repo.put_record(db,request.state.owner,'assist',key,record,0)
            # A distinct job class preserves old workspace evaluation ceilings.
            # Visitor quota is the persisted four-attempt record above plus
            # current provider-enforced entitlement, never a phase reservation.
            jobs.start(db,request.state.owner,key,'visitor-document',{'case_id':case_id,'document_id':doc['id'],'revision':state['revision']},'visitor-live',lease_seconds=120)
        try:
            response=external.gemma(context,ReviewDraft.model_json_schema(),timeout_seconds=90);raw=response.pop('result')
            record.update(raw_output=raw,provenance=response,finished_at=now())
            current=read(case_id,request.state.owner)
            if fingerprint(current)!=record['snapshot_hash']:raise DomainError('Evidence changed during processing; response retained as stale, not a current proposal')
            record['draft']=retain_unknown_ids(current,raw,doc)
            record['status']='completed / review required'
        except (DomainError,ValueError) as exc:
            record.update(status='failed validation',error=str(exc)[:600],finished_at=now())
            if isinstance(exc,external.ProviderFailure):record.update(status='allowance exhausted' if exc.evidence['http_status']==429 else 'provider unavailable',failure_evidence=exc.evidence)
        except (httpx.HTTPError,KeyError,TypeError):
            record.update(status='provider unavailable',error='Provider response was unavailable or malformed. No retry or fixture substitution.',finished_at=now())
        with repo.write(connect) as db:
            if not jobs.finish(db,request.state.owner,key,'succeeded' if record['status']=='completed / review required' else 'failed',digest(record.get('raw_output',{}))):
                record.update(status='provider unavailable',error='Processing lease ended. Raw response retained without current proposal authority.');record.pop('draft',None)
            rev,_=repo.get_record(db,request.state.owner,'assist',key);repo.put_record(db,request.state.owner,'assist',key,record,rev)
        return record
    finally:live_slot.release()


class Review(Strict):
    proposal_id:str=Field(min_length=1,max_length=80)
    revision:int
    reviewed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/visitor-review')
def review(case_id:str,data:Review,request:Request):
    from .app import read,connect
    with repo.write(connect) as db:
        state=read(case_id,request.state.owner)
        rev,record=repo.get_record(db,request.state.owner,'assist',data.proposal_id)
        if not state.get('visitor_review') or not record or record['case_id']!=case_id or record['status']!='completed / review required' or not data.reviewed or data.revision!=state['revision'] or record['snapshot_hash']!=fingerprint(state):
            raise HTTPException(409,{'code':'STALE_REVIEW','message':'Inspect the current original and completed proposal before recording review.'})
        record['review']={'at':now(),'actor':'Anonymous session reviewer','note':data.note,'authority':'Original-source inspection only; inventory context and scope approval remain absent.'}
        repo.put_record(db,request.state.owner,'assist',record['id'],record,rev)
    return record
