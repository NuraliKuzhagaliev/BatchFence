"""Typed receiving drafts and explicit reviewed replacement; old syntax remains supported."""
import copy
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from .domain import DomainError,make_plan
from .review_safety import resolution_evidence,mentions
from .ocr import require_visual_review


class Entity(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(max_length=160)
    kind:Literal['supplier_lot','stock_pool','receipt_id','document_id','lineage_row','unknown']
    quote:str=Field(min_length=1,max_length=2000)
class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    entities:list[Entity]=Field(max_length=80)
    pool_id:str=Field(max_length=160)
    parent_ids:list[str]=Field(max_length=20)
    completeness:Literal['complete','partial','unknown']
    completeness_quote:str=Field(max_length=2000)
    contradictions:list[str]=Field(max_length=10)
SYSTEM='Propose typed receiving relationships from the supplied source only. Separate supplier lots, terminal stock pools, receipt/document identifiers and lineage row identifiers. A preferred or missing parent is not complete ancestry. Preserve every uncertainty or contradiction. Completeness is complete only when the source explicitly asserts all parents; otherwise partial or unknown. Each entity requires an exact source quote containing its ID. This is a draft for explicit replacement review, never an authoritative record.'
PROMPT_VERSION='typed-receiving-2'


def source_context(doc):
    # This schema cites exact text, not block IDs. Internal transport identifiers
    # are not source evidence and must not enter the entity-extraction context.
    # Keep the original document/blocks unchanged for review and source storage.
    return {'source_passages':[block['text'] for block in doc['blocks']]}


def validate_draft(raw,doc):
    draft=Draft.model_validate(raw).model_dump()
    for entity in draft['entities']:
        if entity['id'] not in entity['quote'] or not resolution_evidence(doc,entity['quote']):raise DomainError('Typed entity lacks an exact source occurrence')
    if draft['completeness']=='complete' and not resolution_evidence(doc,draft['completeness_quote']):raise DomainError('Unsupported completeness proposal')
    return draft


def preview(state,data):
    doc=next((d for d in state['documents'] if d['id']==data.document_id),None)
    if not doc or data.revision!=state['revision'] or doc['revision']!=state['revision'] or not doc.get('request_id'):
        raise DomainError('Use the current source attached to an evidence question')
    if not state.get('plan') or state.get('pending_data') or doc.get('prior_pending') or doc.get('prior_plan_digest')!=state['plan']['digest']:
        raise DomainError('Resolve preceding record/scope changes before receiving replacement')
    if data.pool_id not in doc['request_snapshot']['pool_ids']:raise DomainError('Pool is outside the linked evidence question')
    basis=resolution_evidence(doc,data.quote)
    if not basis:raise DomainError('Select the exact receiving-source passage')
    old=[e for e in state['edges'] if e['target']==data.pool_id]
    proposed=copy.deepcopy(state)
    suppliers={e['source'] for e in state['edges']}-{e['target'] for e in state['edges']}
    parents=sorted(set(data.parent_ids))
    if data.outcome=='resolved':
        require_visual_review(doc)
        from .review_safety import require_language_review
        require_language_review(doc)
        if not parents or not set(parents)<=suppliers:raise DomainError('Unknown entities or non-supplier identifiers remain unresolved')
        if not all(mentions(value,data.quote) for value in [data.pool_id,*parents]):raise DomainError('Source passage must identify the pool and each reviewed parent')
        if data.unresolved_contradictions:raise DomainError('Unresolved contradictions cannot replace receiving records')
        if data.complete and set(data.superseded_row_ids)!={e['row_id'] for e in old}:raise DomainError('Review every superseded lineage row for complete replacement')
        if data.review_path=='narrative_draft':
            runs=[r for r in state.get('receiving_runs',[]) if r['id']==data.run_id and r['document_id']==doc['id'] and r['revision']==state['revision'] and r['status']=='succeeded']
            if not runs:raise DomainError('A current typed narrative draft is required; raw proposals remain preserved')
        if data.complete:
            proposed['edges']=[e for e in proposed['edges'] if e['target']!=data.pool_id]
            next(s for s in proposed['stocks'] if s['id']==data.pool_id)['complete']=True
        for i,parent in enumerate(parents):
            matches=[e for e in proposed['edges'] if e['source']==parent and e['target']==data.pool_id]
            if matches:
                for e in matches:e.update(kind='confirmed',evidence=basis)
            else:proposed['edges'].append({'row_id':f'RECV-{doc["id"]}-{i}','source':parent,'target':data.pool_id,'kind':'confirmed','evidence':basis})
    plan=make_plan(proposed)
    return {'old_relationships':old,'proposed_relationships':[e for e in proposed['edges'] if e['target']==data.pool_id],
            'before_units':make_plan(state)['result']['hold_units'],'after_units':plan['result']['hold_units'],
            'applied_hold_units':sum(s['units'] for s in state['stocks'] if s['status']=='held'),
            'outcome':data.outcome,'complete':data.complete,'review_path':data.review_path,'evidence':basis,
            'unknown_entities':sorted(set(parents)-suppliers),'authority':'Proposal only; no existing hold is removed'},proposed


def commit(state,data,actor,at):
    result,candidate=preview(state,data)
    if not data.reviewed or not data.replacement_reviewed or len(data.note.strip())<20:
        raise DomainError('Explicit source, entity typing, completeness and replacement review required')
    if data.complete and data.outcome=='resolved' and not data.completeness_confirmed:
        raise DomainError('An explicit source-backed completeness decision is required; model confidence cannot supply it')
    old=copy.deepcopy(state['plan']);old['status']='stale';state['plans'].append(old)
    if data.outcome=='resolved':
        state['stocks'],state['edges']=candidate['stocks'],candidate['edges'];state['inventory_version']+=1
    state.setdefault('reconciliations',[]).append({**result,'actor':actor,'at':at,'note':data.note,'raw_run_id':data.run_id,
        'reviewed_parent_ids':data.parent_ids,'superseded_row_ids':data.superseded_row_ids,'completeness_confirmed':data.completeness_confirmed})
    state['pending_revision']=False;state['scope']['revision']=state['revision'];state['plan']=make_plan(state)
    state['history'].append({'at':at,'type':'reconciled','revision':state['revision'],'message':'Typed receiving replacement explicitly reviewed. Applied restrictions retained.',
                             'old_units':old['result']['hold_units'],'new_units':state['plan']['result']['hold_units']})
    return state
