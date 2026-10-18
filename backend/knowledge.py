"""Authorized revision selection precedes lexical retrieval and AMD context."""
import re,unicodedata
from datetime import datetime,timezone
from pydantic import BaseModel,ConfigDict,Field
from .domain import DomainError,digest


class PassageClaim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    document_id:str=Field(max_length=80)
    version:int
    passage_id:str=Field(max_length=80)
    quote:str=Field(min_length=1,max_length=2000)
class Answer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    claims:list[PassageClaim]=Field(max_length=5)
    insufficient_evidence:bool
    missing_information:list[str]=Field(max_length=5)

class PassageKey(BaseModel):
    model_config=ConfigDict(extra='forbid')
    document_id:str=Field(max_length=80)
    version:int
    passage_id:str=Field(max_length=80)

class PassageSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    selections:list[PassageKey]=Field(max_length=5)
    insufficient_evidence:bool
    missing_information:list[str]=Field(max_length=5)

def selected_answer(raw,retrieval):
    """Resolve model-selected keys to unchanged authorized full passages.

    The model does not author the displayed quotes. No fuzzy matching, repair,
    omitted caveat, cross-version lookup or outside-catalog key is accepted.
    """
    selected=PassageSelection.model_validate(raw).model_dump();by={(p['document_id'],p['version'],p['passage_id']):p for p in retrieval['passages']}
    claims=[];seen=set()
    for key in selected['selections']:
        identity=(key['document_id'],key['version'],key['passage_id'])
        if identity not in by or identity in seen:raise DomainError('Selection must name unique exact authorized passage keys')
        seen.add(identity);claims.append({**key,'quote':by[identity]['quote']})
    return validate_answer({'claims':claims,'insufficient_evidence':selected['insufficient_evidence'],'missing_information':selected['missing_information']},retrieval)


def validate_document(doc):
    required={'id','version','status','valid_from','valid_to','products','processes','owner','passages','source_hash','synthetic'}
    if set(doc)!=required or not doc['id'] or type(doc['version']) is not int or doc['version']<1:raise DomainError('Invalid versioned procedure metadata')
    if doc['status'] not in ('draft','approved','obsolete'):raise DomainError('Unsupported procedure lifecycle')
    if not doc['products'] or not doc['processes'] or not doc['owner']:raise DomainError('Procedure applicability and owner required')
    if not 1<=len(doc['passages'])<=40:raise DomainError('Procedure passage limit: 1–40')
    if len({p['id'] for p in doc['passages']})!=len(doc['passages']):raise DomainError('Duplicate passage identifier')
    if any(not p.get('text') or len(p['text'])>2000 or type(p.get('page')) is not int or p['page']<1 for p in doc['passages']):raise DomainError('Bounded text passages and positive integer page numbers required')
    if digest(doc['passages'])!=doc['source_hash']:raise DomainError('Procedure source passage hash mismatch')
    start=datetime.fromisoformat(doc['valid_from'].replace('Z','+00:00'));end=datetime.fromisoformat(doc['valid_to'].replace('Z','+00:00')) if doc['valid_to'] else None
    if not start.tzinfo or (end and (not end.tzinfo or end<=start)):raise DomainError('Procedure validity must use a valid timezone-aware interval')


def lexical_terms(text):
    # Search-only canonical normalization. Original text and identifier
    # comparisons remain byte/exact-string based; no confusable folding.
    return set(re.findall(r'[^\W_]+',unicodedata.normalize('NFC',text).casefold()))


def retrieve(documents,question,product,process,synthetic,at=None):
    if not isinstance(question,str) or not 1<=len(question)<=1000:raise DomainError('Knowledge question limit: 1–1000 characters')
    at=at or datetime.now(timezone.utc)
    applicable=[]
    for doc in documents:
        if doc['status']!='approved' or product not in doc['products'] or process not in doc['processes'] or (doc['synthetic'] and not synthetic):continue
        if datetime.fromisoformat(doc['valid_from'].replace('Z','+00:00'))>at:continue
        if doc['valid_to'] and at>=datetime.fromisoformat(doc['valid_to'].replace('Z','+00:00')):continue
        applicable.append(doc)
    by_id={}
    for doc in applicable:by_id.setdefault(doc['id'],[]).append(doc)
    conflicts=[key for key,versions in by_id.items() if len(versions)>1]
    if conflicts:return {'status':'insufficient','reason':'Overlapping approved revisions require owner resolution: '+', '.join(conflicts),'passages':[]}
    terms=lexical_terms(question)-{'the','a','is','are','to','of','in','and','what','how','for','which','can','i','it','this'}
    if len(terms)>128:raise DomainError('Knowledge question limit: 128 distinct search terms')
    scored=[]
    for doc in applicable:
        for p in doc['passages']:
            score=len(terms & lexical_terms(p['text']))
            if score:scored.append((score,{'document_id':doc['id'],'version':doc['version'],'passage_id':p['id'],'quote':p['text'],'page':p['page'],'source_hash':doc['source_hash']}))
    scored.sort(key=lambda x:(-x[0],x[1]['document_id'],x[1]['passage_id']))
    return {'status':'retrieved' if scored else 'insufficient','reason':'' if scored else 'No applicable approved passage supports this question; lexical matching does not translate across languages','passages':[p for _,p in scored[:8]],'method':'Unicode lexical matching of approved applicable originals; no translation or semantic-search claim'}


def validate_answer(raw,retrieval):
    answer=Answer.model_validate(raw).model_dump()
    by={(p['document_id'],p['version'],p['passage_id']):p for p in retrieval['passages']}
    for claim in answer['claims']:
        p=by.get((claim['document_id'],claim['version'],claim['passage_id']))
        if not p or claim['quote']!=p['quote']:raise DomainError('Answer must select exact retrieved source passages; unsupported procedural claims rejected')
    if not answer['claims'] and not answer['insufficient_evidence']:raise DomainError('An unsupported answer must abstain')
    if answer['insufficient_evidence']:answer['claims']=[]
    return answer


SYSTEM='Select only applicable source passages that answer the procedure question. Each substantive procedural answer must be an EXACT full passage quote with its document ID, revision and passage ID. Do not paraphrase, invent instructions, combine conflicting rules, infer causes, give machine settings or authorize release. Return insufficient_evidence=true when the supplied passages do not directly answer the question, the question asks to bypass controls, or any needed evidence is missing. Missing information is diagnostic text, never operational instructions.'
