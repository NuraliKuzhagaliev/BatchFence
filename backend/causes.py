"""Source-linked questions, independent of model confidence and monetary guesses."""
import hashlib
import json
from .review_safety import scope_concerns


def evidence_queue(state, result):
    stocks, edges, scope = state['stocks'], state['edges'], state['scope']
    rows = {r['id']: r for r in result['rows']}
    docs = state.get('documents', [])
    source = next((d for d in docs if d['id'] == scope.get('source_document_id')), None)
    if source is None:
        source = next((d for d in reversed(docs) if 'supplier' in d['filename']), None)
    causes = []

    def descendants(node):
        seen, todo = set(), [node]
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            todo.extend(e['target'] for e in edges if e['source'] == n)
        return sorted(seen & rows.keys())

    def add(kind, key, pools, title, reason, evidence, role, review_first=False, global_gap=False, choices=None):
        pools = sorted(set(pools))
        if not pools:
            return
        refs = [e for e in evidence if e]
        identity = json.dumps([kind, key, refs], sort_keys=True)
        cid = 'CAUSE-' + hashlib.sha256(identity.encode()).hexdigest()[:14]
        units = sum(rows[p]['units'] for p in pools)
        urgency = min((a['due_date'] for a in state['allocations'] if a['pool_id'] in pools and a['status'] == 'open'), default='9999-12-31')
        causes.append({'id':cid, 'kind':kind, 'pool_ids':pools, 'units':units,
            'value_cents':sum(rows[p]['units']*rows[p]['unit_cents'] for p in pools),
            'missing':title, 'reason':reason, 'evidence':refs,
            'suggested_role':role, 'review_existing_first':review_first, 'global':global_gap,
            'earliest_order_due':urgency if urgency != '9999-12-31' else None,
            'hypotheses':choices or [],
            'impact_note': 'Impact cannot yet be bounded without an explicit complete incident scope.' if global_gap else 'Conditional scenarios; overlapping question impacts are not additive.',
            'draft':f"Please clarify {title.lower()} for {', '.join(pools)} ({units} unique units). {reason} Provide original record IDs, exact lot identities and document revision; state whether the record is complete or inconclusive. This request does not authorize release."})

    concerns = scope_concerns(source) if source else []
    if not result['narrowing_available']:
        evidence = concerns or ([{'document_id':source['id'], 'block_id':b['id'], 'quote':b['text']} for b in source['blocks'][:3]] if source else [])
        add('boundary_source' if concerns else 'boundary_review', source['id'] if source else 'scope', list(rows),
            'Complete incident boundary',
            'The source explicitly leaves incident scope unresolved; request a clarifying notice.' if concerns else 'Review the existing notice and completeness manifest before narrowing. Complete receiving records are not missing merely because incident scope is unconfirmed.',
            evidence, 'Supplier quality contact' if concerns else 'Quality reviewer', not concerns, True)
    for lot in scope.get('uncertain_lot_ids', []):
        refs = [{'document_id':d['id'], 'block_id':b['id'], 'quote':b['text']} for d in docs if d['id']==scope.get('source_document_id') for b in d['blocks'] if lot in b['text']]
        add('lot_involvement',lot,descendants(lot),f'Incident involvement of {lot}',
            'This supplier lot has an unresolved reviewed disposition. Obtain an explicit source-backed involvement decision.',refs,'Supplier quality contact')
    targets = sorted({e['target'] for e in edges if e['kind']=='possible'})
    for target in targets:
        incoming = [e for e in edges if e['target']==target]
        suppliers = sorted({e['source'] for e in incoming})
        choices = ([{'kind':'identity','pool_id':target,'supplier_lot_id':lot,'complete':True} for lot in suppliers] if target in rows else [])
        add('possible_ancestry',target,descendants(target),f'Receiving identity for {target}',
            'Alternative possible ancestry remains. A preferred supplier mention alone cannot remove other possible links; a complete replacement needs explicit evidence and review.',
            [e.get('evidence') for e in incoming],'Receiving records owner',choices=choices+[{'kind':'inconclusive'}])
    for s in stocks:
        if not s.get('complete') or not any(e['target']==s['id'] for e in edges):
            add('incomplete_ancestry',s['row_id'],[s['id']],f'Complete ancestry manifest for {s["id"]}',
                'The inventory completeness flag or terminal ancestry record is missing. Confirm all parents, not only one preferred path.',
                [{'document_id':d['id'],'block_id':b['id'],'quote':b['text']} for d in docs for b in d['blocks'] if s['row_id'] in b['text']],
                'Receiving records owner')
    for conflict in state.get('reconciliations', []):
        if conflict.get('outcome') == 'conflicting':
            add('conflicting_evidence',conflict['document_id'],conflict['pool_ids'],'Conflicting supplier reply',
                'The reviewed reply conflicts with existing records; uncertainty remains until an explicit superseding complete record is reviewed.',
                [conflict['evidence']],'Supplier quality contact')
    # One complete receiving record can answer identity and completeness. Keep
    # both cause identities while presenting one question for the same record.
    for c in causes:
        c['causes']=[{'id':c['id'],'kind':c['kind']}]
    for c in list(causes):
        if c['kind']=='incomplete_ancestry':
            shared=next((q for q in causes if q['kind']=='possible_ancestry' and q['pool_ids']==c['pool_ids']),None)
            if shared:
                shared['causes']+=c['causes']
                shared['reason']+=' The completeness manifest also needs confirmation.'
                causes.remove(c)
    # Bound automatic ranking work; the explicit scenario API remains capped at
    # six hypotheses. Do not invent precise impacts for unenumerated boundaries.
    from .domain import calculate
    from .scenarios import apply_hypotheses
    remaining=12
    for c in causes:
        changes=[]
        for h in c['hypotheses']:
            if remaining<=0:
                break
            remaining-=1
            candidate=apply_hypotheses(state,[h])
            r=calculate(candidate['stocks'],candidate['edges'],candidate['scope']['lot_ids'],candidate['allocations'],result['narrowing_available'],candidate['scope'].get('uncertain_lot_ids',[]))
            changes.append(abs(result['hold_units']-r['hold_units']))
        c['decision_change_units']=max(changes) if changes else None
    # Group by actual gap; global blockers precede potentially decision-changing
    # identity questions, then earliest affected open order. Value is secondary.
    causes.sort(key=lambda c:(not c['global'],not bool(c['decision_change_units']),c['earliest_order_due'] or '9999',-c['value_cents'],c['id']))
    for c in causes:
        c['sort_reason'] = ('Global scope blocker first' if c['global'] else f"Conditional change up to {c['decision_change_units']} proposed units" if c['decision_change_units'] is not None else 'Impact not computed within bounded ranking') + '; decision-changing questions first, then earliest affected order, then inventory carrying value.'
    unique = {p for c in causes for p in c['pool_ids']}
    return causes, sum(rows[p]['units'] for p in unique), sum(rows[p]['units']*rows[p]['unit_cents'] for p in unique)
