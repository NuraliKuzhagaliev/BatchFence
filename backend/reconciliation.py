"""Reviewed receiving replies. Narrative candidates never replace records directly."""
import copy
import re
from .domain import DomainError, make_plan
from .review_safety import resolution_evidence, mentions
from .scenarios import simulate, apply_hypotheses


def preview_reply(state, data):
    doc = next((d for d in state['documents'] if d['id']==data.document_id),None)
    if not doc or not doc.get('request_id') or doc['revision'] != state['revision'] or data.revision != state['revision']:
        raise DomainError('Select the current reply linked to an evidence question')
    if state.get('pending_data') or not state.get('plan') or doc.get('prior_plan_digest') != state['plan']['digest']:
        raise DomainError('Other record changes require the ordinary scope review first')
    if doc.get('prior_pending'):
        raise DomainError('Resolve preceding evidence changes before reconciling this reply')
    basis = resolution_evidence(doc,data.quote)
    if not basis:
        raise DomainError('Use an exact supporting passage from the linked reply')
    if data.pool_id not in doc['request_snapshot']['pool_ids']:
        raise DomainError('Reply pool must belong to the linked question')
    old = [e for e in state['edges'] if e['target']==data.pool_id]
    hypothesis = {'kind':'inconclusive'}
    unresolved = re.search(r'\b(may|might|possibly|pending|inconclusive|conflicting|cannot|unknown)\b', ' '.join(b['text'] for b in doc['blocks']), re.I)
    if data.outcome == 'resolved':
        if unresolved:
            raise DomainError('Reply remains inconclusive or conflicting; records cannot be narrowed')
        if not mentions(data.pool_id,data.quote) or not mentions(data.supplier_lot_id,data.quote):
            raise DomainError('Quote must explicitly identify both the pool and supplier lot')
        if data.complete:
            # Bounded accepted receiving-record syntax. A narrative preferred-lot
            # mention cannot silently discard other parents. All replaced row IDs
            # must be explicitly superseded in the cited source.
            phrase = '^'+re.escape(data.pool_id)+r'\s+complete ancestry:\s*'+re.escape(data.supplier_lot_id)+r'\s+only\.\s+Supersedes\s+([A-Za-z0-9_, -]+)\.'
            match=re.search(phrase,data.quote,re.I)
            full_block=next(b['text'] for b in doc['blocks'] if b['id']==basis['block_id'])
            replaced={x.strip() for x in match.group(1).split(',')} if match else set()
            if not match or data.quote!=full_block or replaced != {e.get('row_id') for e in old}:
                raise DomainError('Complete replacement requires "POOL complete ancestry: LOT only." and an explicit Supersedes list of every replaced row ID')
        elif not re.search(re.escape(data.pool_id)+r'\s+confirmed parent:\s*'+re.escape(data.supplier_lot_id)+r'\.',data.quote,re.I):
            raise DomainError('Partial confirmation requires "POOL confirmed parent: LOT."; alternative paths remain')
        runs = [r for r in state['runs'] if r['status']=='succeeded' and r.get('document_id')==doc['id'] and r['revision']==state['revision']]
        if not runs or not any(f['lot_id']==data.supplier_lot_id for f in runs[-1]['output']['facts']):
            raise DomainError('Interpret this reply first; review the source-backed supplier candidate')
        hypothesis = {'kind':'identity','pool_id':data.pool_id,'supplier_lot_id':data.supplier_lot_id,
                      'complete':data.complete,'evidence':basis}
    effect = simulate(state,[hypothesis])
    return {'document_id':doc['id'],'document_revision':doc['revision'],'request_id':doc['request_id'],
            'outcome':data.outcome,'pool_ids':[data.pool_id], 'evidence':basis, 'hypothesis':hypothesis,
            'old_relationships':old,'old_complete':next(p['complete'] for p in state['stocks'] if p['id']==data.pool_id),
            'proposed_relationships': [e for e in apply_hypotheses(state,[hypothesis])['edges'] if e['target']==data.pool_id],
            'conflicts': ['Existing parent records are explicitly superseded; inspect every old row.'] if data.outcome=='resolved' and data.complete else ['Uncertainty retained; no records replaced.'] if data.outcome!='resolved' else ['Other possible parents are retained.'],
            'impact':effect}


def commit_reply(state, data, at):
    proposal = preview_reply(state,data)
    if not data.reviewed or len(data.note.strip()) < 20 or (data.complete and data.outcome=='resolved' and not data.replacement_reviewed):
        raise DomainError('Explicit source and replacement review plus an explanation are required')
    old = copy.deepcopy(state['plan'])
    old['status'] = 'stale'
    state['plans'].append(old)
    candidate = apply_hypotheses(state,[proposal['hypothesis']])
    state['stocks'],state['edges'] = candidate['stocks'],candidate['edges']
    if data.outcome=='resolved':
        state['inventory_version'] += 1
        # Retain a stable record ID for subsequent source-linked changes.
        for e in state['edges']:
            if e['target']==data.pool_id and not e.get('row_id'):
                e['row_id'] = 'RECON-'+proposal['document_id']
    state.setdefault('reconciliations',[]).append({k:v for k,v in proposal.items() if k!='impact'} | {'at':at,'note':data.note,'reviewer':'Session reviewer; identity not independently verified'})
    state['scope']['revision'] = state['revision']
    state['plan'] = make_plan(state)
    state['pending_revision'] = False
    state['history'].append({'at':at,'type':'reconciled','revision':state['revision'],
        'message':f"Reviewed reply: {data.outcome}. Existing applied holds preserved.",
        'old_units':old['result']['hold_units'],'new_units':state['plan']['result']['hold_units']})
    return state
