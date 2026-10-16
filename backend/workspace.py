"""One physical inventory universe per scoped pilot/workspace, with overlapping reasons."""
import copy
import json
from . import repository as repo,identity
from .domain import DomainError,digest,validate_dataset
from .fixtures import now


def enabled(state):return identity.pilot() or state.get('workspace_attached',False)


def initialize(db,owner,state):
    version,inventory=repo.get_record(db,owner,'inventory','shared')
    if inventory:
        existing={s['id']:s for s in inventory['stocks']}
        for stock in state['stocks']:
            prior=existing.get(stock['id'])
            if not prior or any(prior.get(k)!=stock.get(k) for k in ('units','site','product_family')):
                raise DomainError('Case does not match the shared physical inventory; use reviewed onboarding before linking it')
        return inventory
    inventory={'stocks':copy.deepcopy(state['stocks']),'edges':copy.deepcopy(state['edges']),'allocations':copy.deepcopy(state['allocations']),
               'revision':1,'holds':[],'source_documents':[],'recovery_receipts':[]}
    for stock in inventory['stocks']:
        if stock['status']=='held':
            inventory['holds'].append({'id':'HOLD-'+digest([state['id'],stock['id']])[:20],'pool_id':stock['id'],'incident_id':state['id'],
                'units':stock['units'],'status':'active','origin':'migrated prior restriction','version':1,'created_at':now()})
            stock['status']='available'
    repo.put_record(db,owner,'inventory','shared',inventory,0)
    return inventory


def active_pools(inventory):return {h['pool_id'] for h in inventory['holds'] if h['status']=='active'}


def hydrate(db,owner,state):
    if not enabled(state):return state
    _,inventory=repo.get_record(db,owner,'inventory','shared')
    if not inventory:return state
    held=active_pools(inventory)
    state['stocks']=copy.deepcopy(inventory['stocks'])
    for stock in state['stocks']:
        if stock['id'] in held and stock['status']!='shipped':stock['status']='held'
    state['edges']=copy.deepcopy(inventory['edges'])
    state['allocations']=copy.deepcopy(inventory['allocations'])
    state['inventory_version']=inventory['revision']
    state['workspace_attached']=True
    ids={d['id'] for d in state['documents']}
    state['documents'] += [copy.deepcopy(d) for d in inventory['source_documents'] if d['id'] not in ids]
    state['hold_ledger']=copy.deepcopy(inventory['holds'])
    state['recovery_receipts']=copy.deepcopy(inventory['recovery_receipts'])
    pending=set()
    for row in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='recovery'",(owner,)).fetchall():
        recovery=json.loads(row[0])
        if recovery['status'] in ('prepared','approved','pending_ack','failed_ack'):
            pending.update(recovery['pool_ids'])
    confirmed={c['pool_id'] for receipt in inventory['recovery_receipts'] for c in receipt['changes'] if c['became_available']}
    units={s['id']:s['units'] for s in state['stocks']}
    state['quantities']={'applied_hold_units':sum(units[p] for p in held),
                         'recovery_pending_units':sum(units[p] for p in pending&held),
                         'confirmed_recovery_units':sum(units[p] for p in confirmed-held)}
    if state.get('plan') and state['plan']['inventory_version']!=inventory['revision'] and state['plan']['status']!='applied':
        state['plan']['status']='stale'
    return state


def synchronize(db,owner,before,state):
    if not enabled(state):return
    initialize(db,owner,state)
    version,inventory=repo.get_record(db,owner,'inventory','shared')
    previous=copy.deepcopy(inventory)
    held=active_pools(inventory)
    if any(before.get(k)!=state.get(k) for k in ('stocks','edges','allocations')):
        proposed=copy.deepcopy(state['stocks'])
        old={s['id']:s for s in inventory['stocks']}
        for pool in held:
            if not any(s['id']==pool and s['units']==old[pool]['units'] for s in proposed):
                raise DomainError('Shared held pools cannot be removed or resized')
        for s in proposed:
            if s['status']=='held':s['status']=old.get(s['id'],{}).get('status','available')
        inventory.update(stocks=proposed,edges=copy.deepcopy(state['edges']),allocations=copy.deepcopy(state['allocations']))
        validate_dataset(inventory['stocks'],inventory['edges'],inventory['allocations'])
        source_ids={e.get('evidence',{}).get('document_id') for e in state['edges']}
        inventory['source_documents']=[copy.deepcopy(d) for d in state['documents'] if d['id'] in source_ids]
    for receipt in state['receipts'][len(before.get('receipts',[])):]:
        for change in receipt['changes']:
            existing=next((h for h in inventory['holds'] if h['incident_id']==state['id'] and h['pool_id']==change['pool_id'] and h['status']=='active'),None)
            if not existing:
                inventory['holds'].append({'id':'HOLD-'+digest([receipt['transaction_id'],change['pool_id']])[:20],'pool_id':change['pool_id'],
                    'incident_id':state['id'],'units':change['units'],'status':'active','origin':'sandbox containment receipt '+receipt['transaction_id'],
                    'version':1,'created_at':now()})
    if inventory!=previous or len(state['receipts'])>len(before.get('receipts',[])):
        inventory['revision']=previous['revision']+1
        repo.put_record(db,owner,'inventory','shared',inventory,version)
        repo.audit(db,owner,identity.current_actor(),'inventory.updated',previous,inventory)
    hydrate(db,owner,state)
