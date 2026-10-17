import base64
import json
import uuid
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from . import repository as repo,identity,onboarding
from .domain import DomainError
from .fixtures import now

router=APIRouter()
class Strict(BaseModel): model_config=ConfigDict(extra='forbid')
class Preview(Strict):
    filename:str=Field(min_length=1,max_length=160)
    content_base64:str=Field(max_length=3_000_000)
    kind:str=Field(max_length=30)
    mapping:dict[str,str]=Field(max_length=24)
    metadata:dict=Field(max_length=10)
class Commit(Strict):
    proposal_id:str=Field(max_length=80)
    reviewed:bool
    note:str=Field(max_length=2000)
    freshness_ack:bool=False
    profile_name:str=Field(default='',max_length=80)


@router.get('/api/intake/profiles')
def profiles(request:Request):
    from .app import connect
    with connect() as db:
        rows=db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='mapping'",(request.state.owner,)).fetchall()
    return {'profiles':[json.loads(r[0]) for r in rows],'fields':onboarding.FIELDS,'limits':{'rows':500,'bytes':2_000_000,'units':['piece']}}


@router.post('/api/cases/{case_id}/intake-preview')
def preview(case_id:str,data:Preview,request:Request):
    from .app import connect,read
    if '/' in data.filename or '\\' in data.filename or not data.filename.lower().endswith('.csv'): raise DomainError('Select a plain CSV filename')
    try: raw=base64.b64decode(data.content_base64,validate=True)
    except ValueError: raise DomainError('Invalid base64 upload')
    if not raw or len(raw)>2_000_000: raise DomainError('File limit: 2 MB')
    state=read(case_id,request.state.owner)
    try: result=onboarding.preview(state,raw,data.filename,data.kind,data.mapping,data.metadata)
    except (UnicodeDecodeError,ValueError) as exc:
        if isinstance(exc,DomainError): raise
        raise DomainError('Malformed CSV or invalid values')
    result['id']='IMPORT-'+uuid.uuid4().hex
    with repo.write(connect) as db:
        identity.recheck(db)
        count=db.execute("SELECT count(*) FROM bf_records WHERE owner=? AND kind='import'",(request.state.owner,)).fetchone()[0]
        if count>=30: raise DomainError('Import preview limit reached')
        repo.save_source(db,request.state.owner,raw)
        repo.put_record(db,request.state.owner,'import',result['id'],result,0)
    return result


@router.post('/api/cases/{case_id}/intake-review')
def commit(case_id:str,data:Commit,request:Request):
    from .app import transaction,invalidate
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer')
        if len(state['documents'])>=24: raise DomainError('Case document limit reached')
        rev,proposal=repo.get_record(db,request.state.owner,'import',data.proposal_id)
        if not proposal or proposal.get('committed'): raise DomainError('Import proposal unavailable or already reviewed')
        onboarding.validate_commit(state,proposal,data.reviewed,data.note,data.freshness_ack)
        state['revision']+=1
        doc=proposal['document']; doc['revision']=state['revision'];state['documents'].append(doc)
        if proposal['kind']=='inspections':
            version,observations=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[],'history':[]})
            old={r['observation_id']:r for r in observations['rows']}
            changed=[]
            for row in proposal['rows']:
                if row['observation_id'] in old:
                    observations['history'].append({'prior':old[row['observation_id']],'replaced_at':now(),'source_revision':proposal['metadata']['source_revision']})
                    changed.append(row['observation_id'])
                old[row['observation_id']]=row
            if len(old)>500: raise DomainError('Inspection dataset exceeds the supported 500-row envelope')
            observations['rows']=list(old.values())
            observations['changed_ids']=changed
            observations['revision']=version+1
            repo.put_record(db,request.state.owner,'inspections','current',observations,version)
        else:
            target={'inventory':'stocks','lineage':'edges','allocations':'allocations'}[proposal['kind']]
            state['pending_data']={**(state.get('pending_data') or {}),target:proposal['rows']}
            invalidate(state,'Reviewed mapped import; current incident scope must be reviewed against the changed records.')
        proposal.update(committed=True,review={'actor':identity.current_actor(),'at':now(),'note':data.note})
        repo.put_record(db,request.state.owner,'import',proposal['id'],proposal,rev)
        if data.profile_name:
            repo.put_record(db,request.state.owner,'mapping',data.profile_name,{'name':data.profile_name,'kind':proposal['kind'],'mapping':proposal['mapping'],'metadata':proposal['metadata']})
        repo.audit(db,request.state.owner,identity.current_actor(),'import.reviewed',{},proposal,[doc['original_hash']])
    return state


@router.get('/api/inspections')
def inspections(request:Request):
    from .app import connect
    with connect() as db:
        rev,data=repo.get_record(db,request.state.owner,'inspections','current',{'rows':[],'history':[]})
    return {'revision':rev,**data}


class VisualReview(Strict):
    document_id:str=Field(max_length=80)
    revision:int
    page_numbers:list[int]=Field(max_length=8)
    identifiers_confirmed:bool
    quantities_confirmed:bool
    completeness_confirmed:bool
    note:str=Field(min_length=20,max_length=2000)


@router.post('/api/cases/{case_id}/ocr-review')
def ocr_review(case_id:str,data:VisualReview,request:Request):
    from .app import transaction,invalidate
    with transaction(case_id,request.state.owner) as (db,state):
        identity.recheck(db,'quality_reviewer')
        doc=next((d for d in state['documents'] if d['id']==data.document_id),None)
        if not doc or not doc.get('ocr') or state['revision']!=data.revision: raise DomainError('Current scanned document required')
        if not all([data.identifiers_confirmed,data.quantities_confirmed,data.completeness_confirmed]) or set(data.page_numbers)!={p['page'] for p in doc['ocr']['pages']}:
            raise DomainError('Confirm critical fields against every retained original page')
        doc['ocr'].update(critical_fields_confirmed=True,visual_review={'actor':identity.current_actor(),'at':now(),'note':data.note,'pages':data.page_numbers})
        invalidate(state,'Scanned source visually reviewed; explicit incident or receiving review is still required')
    return state


@router.get('/api/cases/{case_id}/documents/{doc_id}/pages/{number}')
def ocr_page(case_id:str,doc_id:str,number:int,request:Request):
    from .app import read,connect
    import hashlib
    state=read(case_id,request.state.owner)
    doc=next((d for d in state['documents'] if d['id']==doc_id),None)
    page=next((p for p in doc.get('ocr',{}).get('pages',[]) if p['page']==number),None) if doc else None
    if not page: raise HTTPException(404,'Page unavailable')
    with connect() as db:
        row=db.execute('SELECT size FROM bf_sources WHERE owner=? AND hash=?',(request.state.owner,page['image_hash'])).fetchone()
    if not row: raise HTTPException(404,'Page source unavailable')
    raw=repo.source_path(request.state.owner,page['image_hash']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=page['image_hash']: raise DomainError('Stored page integrity failure')
    return {'page':number,'hash':page['image_hash'],'data_url':'data:image/png;base64,'+base64.b64encode(raw).decode()}
