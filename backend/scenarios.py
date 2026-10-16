"""Bounded counterfactual copies. Returned results carry no approval authority."""
import copy
from .domain import DomainError, make_plan, digest
from .review_safety import REVIEW_POLICY_VERSION


def apply_hypotheses(state, hypotheses):
    if not hypotheses or len(hypotheses) > 6:
        raise DomainError('Provide 1–6 explicit hypotheses')
    s = copy.deepcopy(state)
    replacements={}
    for h in hypotheses:
        if h['kind']=='identity' and h.get('complete'):
            prior=replacements.get(h.get('pool_id'))
            if prior and prior != h.get('supplier_lot_id'):
                raise DomainError('Joint scenario supplies conflicting complete identities for one pool')
            replacements[h.get('pool_id')]=h.get('supplier_lot_id')
        if h['kind'] == 'inconclusive':
            continue
        if h['kind'] == 'boundary':
            lots, uncertain = h.get('lot_ids', []), h.get('uncertain_lot_ids', [])
            known = {e['source'] for e in s['edges']}
            if not lots and not uncertain or not set(lots+uncertain) <= known or set(lots)&set(uncertain):
                raise DomainError('Impact cannot be bounded: supply explicit known, disjoint incident lots')
            s['scope'].update(lot_ids=sorted(set(lots)),uncertain_lot_ids=sorted(set(uncertain)),
                              incident_scope_status='resolved',review_policy_version=REVIEW_POLICY_VERSION)
            s['bounded'] = True
        elif h['kind'] == 'identity':
            target, lot = h.get('pool_id'), h.get('supplier_lot_id')
            stock = next((p for p in s['stocks'] if p['id']==target),None)
            if not stock or lot not in {e['source'] for e in state['edges'] if e['target']==target}:
                raise DomainError('Identity scenarios require a terminal pool and an existing candidate parent')
            if h.get('complete') is True:
                s['edges'] = [e for e in s['edges'] if e['target']!=target]
                stock['complete'] = True
            else:
                # Confirm one link only; all alternative possible links remain.
                s['edges'] = [e for e in s['edges'] if not(e['target']==target and e['source']==lot)]
            s['edges'].append({'source':lot,'target':target,'kind':'confirmed','evidence':h.get('evidence')})
        else:
            raise DomainError('Unsupported hypothesis')
    return s


def simulate(state, hypotheses):
    candidate = apply_hypotheses(state,hypotheses)
    before, after = make_plan(state)['result'], make_plan(candidate)['result']
    changed = [r for r in before['rows'] if r['classification'] != next(p['classification'] for p in after['rows'] if p['id']==r['id'])]
    for result in (before,after):
        result.pop('actions',None)
    prior_orders, next_orders = ({o['order_id'] for o in r['orders']} for r in (before,after))
    return {'label':'Simulation','source_digest':digest(state),'hypotheses':hypotheses,
            'before':before,'after':after,'changed_pool_ids':[r['id'] for r in changed],
            'changed_units':sum(r['units'] for r in changed),
            'changed_value_cents':sum(r['units']*r['unit_cents'] for r in changed),
            'new_order_reviews':sorted(next_orders-prior_orders),'removed_order_reviews':sorted(prior_orders-next_orders),
            'remaining_blockers':after['requests'],
            'applied_hold_units':sum(p['units'] for p in state['stocks'] if p['status']=='held'),
            'applied_hold_pool_ids':[p['id'] for p in state['stocks'] if p['status']=='held'],
            'warning':'Conditional proposal only. Existing applied holds remain; no automatic release. Standalone impacts are not additive.'}
