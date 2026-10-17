import base64,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
from pydantic import Field
from .assist_contracts import Strict
from . import repository as repo,identity
from .domain import DomainError,digest
from .fixtures import now,ROOT


class LabelReading(Strict):
    candidates:list[str]=Field(max_length=8)
    unresolved_characters:list[str]=Field(max_length=12)
    unreadable:bool


def decode(raw,crop):
    if not 1<=len(raw)<=2_000_000:raise DomainError('Image limit is 2 MB')
    task_root=repo.source_root().parent/'image-tmp';task_root.mkdir(parents=True,exist_ok=True)
    from .documents import clean_environment
    with tempfile.TemporaryDirectory(dir=task_root) as tmp:
        source=Path(tmp)/'original';derived=Path(tmp)/'derived.png';source.write_bytes(raw)
        try:
            result=subprocess.run([sys.executable,'-m','backend.image_worker',str(source),str(derived),json.dumps(crop)],
                cwd=ROOT,env=clean_environment(),capture_output=True,text=True,timeout=7,check=True)
            info=json.loads(result.stdout);image=derived.read_bytes()
            if len(image)>4_000_000:raise ValueError()
            return info,image
        except (subprocess.SubprocessError,ValueError,OSError):raise DomainError('Image unreadable, unsupported, oversized or processing time exceeded; no partial import')


def commit_image(db,owner,state,filename,raw,crop,info,derived):
    original_hash=hashlib.sha256(raw).hexdigest();key='LABEL-'+digest([state['id'],original_hash,crop])[:24]
    _,prior=repo.get_record(db,owner,'label',key)
    if prior:return prior
    repo.save_source(db,owner,raw);derived_hash=repo.save_source(db,owner,derived)
    record={'id':key,'case_id':state['id'],'filename':filename,'original_hash':original_hash,'derived_hash':derived_hash,
            'image_version':1,'transform':info,'at':now(),'status':'image imported / identity unverified','reading':None,'review':None,
            'purpose':'Label identity only. No defect or product-quality inference. Barcode decoding unavailable in this build.'}
    repo.put_record(db,owner,'label',key,record,0);repo.audit(db,owner,identity.current_actor(),'label.imported',{},record,[original_hash,derived_hash])
    return record


def validate_reading(raw):
    reading=LabelReading.model_validate(raw).model_dump()
    if any(not s or len(s)>160 or '\n' in s for s in reading['candidates']) or len(set(reading['candidates']))!=len(reading['candidates']):raise DomainError('Preserve bounded distinct identifier candidates without normalization')
    if reading['unreadable'] and reading['candidates']:raise DomainError('Unreadable image must abstain')
    return reading


def review_label(db,owner,state,key,document_id,quote,selected_id,identity_confirmed,relationship_verified,unresolved,note):
    identity.recheck(db,'quality_reviewer');rev,label=repo.get_record(db,owner,'label',key)
    if not label or label['case_id']!=state['id']:raise DomainError('Label unavailable in this case')
    reading=label.get('reading')
    if not reading or reading['unreadable'] or reading['unresolved_characters'] or len(reading['candidates'])!=1 or unresolved:
        raise DomainError('Unreadable, ambiguous or multiple labels require another explicit crop/reading before association')
    if selected_id!=reading['candidates'][0]:raise DomainError('Preserve exact candidate spelling; O/0, leading zeros and hyphens are not normalized')
    doc=next((d for d in state['documents'] if d['id']==document_id),None)
    block=next((b for b in doc['blocks'] if quote and quote in b['text'] and selected_id in quote),None) if doc else None
    if not block or not identity_confirmed or not relationship_verified:raise DomainError('Exact document identifier, operator visual confirmation and verified source relationship required; a mismatch cannot be associated')
    label['review']={'actor':identity.current_actor(),'at':now(),'case_revision':state['revision'],'document_id':doc['id'],'source_hash':doc['original_hash'],
        'quote':quote,'block_id':block['id'],'selected_id':selected_id,'identity_confirmed':True,'relationship_verified':True,'note':note}
    label['status']='identity and source relationship reviewed / no inventory authority'
    repo.put_record(db,owner,'label',key,label,rev);repo.audit(db,owner,identity.current_actor(),'label.reviewed',{},label)
    return label
