"""Compare immutable pre-execution plans; no restoration or execution endpoint."""
def compare_plans(before, after):
    b, a = before['result'], after['result']
    bi, ai = before['inputs'], after['inputs']
    old = {r['id']:r for r in b['rows']}
    changes = []
    for r in a['rows']:
        previous = old.get(r['id'])
        included = r['classification']!='outside'
        was = previous is not None and previous['classification']!='outside'
        group = 'newly_included' if included and not was else 'still_included' if included else 'outside_proposal'
        ancestors, todo = set(), [r['id']]
        while todo:
            n = todo.pop()
            if n in ancestors:
                continue
            ancestors.add(n)
            todo.extend(e['source'] for e in ai['lineage'] if e['target']==n)
        changes.append({'pool_id':r['id'],'group':group,'before':previous['classification'] if previous else 'absent',
            'after':r['classification'],'units':r['units'],'value_cents':r['units']*r['unit_cents'],
            'path':r['path'],'evidence':r['evidence'],
            'lineage_edges':[e for e in ai['lineage'] if e['source'] in ancestors and e['target'] in ancestors],
            'order_ids':sorted({x['order_id'] for x in ai['allocations'] if x['pool_id']==r['id'] and x['status']=='open'})})
    bo, ao = {o['order_id'] for o in b['orders']},{o['order_id'] for o in a['orders']}
    bd, ad = {d[0]:d for d in bi['documents']},{d[0]:d for d in ai['documents']}
    keys = ('lot_ids','uncertain_lot_ids','excluded_lot_ids','incident_scope_status','resolution_evidence')
    return {'before_id':before['id'],'after_id':after['id'],'before_units':b['hold_units'],'after_units':a['hold_units'],
        'source_changes':{'added':[ad[k] for k in ad.keys()-bd.keys()],'removed':[bd[k] for k in bd.keys()-ad.keys()],
                          'changed':[{'before':bd[k],'after':ad[k]} for k in ad.keys()&bd.keys() if ad[k]!=bd[k]]},
        'claims_before':before.get('source_claims',[]),'claims_after':after.get('source_claims',[]),
        'scope_changes':[{ 'field':k,'before':bi['reviewed_scope'].get(k),'after':ai['reviewed_scope'].get(k)} for k in keys if bi['reviewed_scope'].get(k)!=ai['reviewed_scope'].get(k)],
        'pools':changes,'new_order_reviews':sorted(ao-bo),'prior_order_reviews':sorted(bo),
        'records_changed':bi['lineage']!=ai['lineage'] or bi['stocks']!=ai['stocks'],
        'notice':'Comparison of immutable reviewed snapshots. Multiple edits may contribute. Earlier approval remains historical and cannot be restored.'}
