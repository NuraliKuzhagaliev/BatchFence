"""Whole-pool removal of one incident restriction, never automatic stock release."""
import copy
import json
import uuid
from datetime import datetime,timezone,timedelta
from . import repository as repo,identity,workspace
from .domain import DomainError,digest,make_plan
from .fixtures import now
from .knowledge_routes import catalog


def require_role(db,role):
    if identity.pilot():identity.recheck(db,role)
    else:
        p=identity.principal.get()
        if not p or role not in p['roles'] or p['identity_mode']!='simulated demonstration role':
            raise DomainError('Choose the explicitly simulated demonstration role for this action')


def actor_authority():
    return identity.approval_identity() if identity.pilot() else identity.current_actor()


def authority_current(db,actor,role):
    if identity.pilot():return identity.approval_still_authorized(db,actor,role)
    return actor.get('identity_mode')=='simulated demonstration role' and role in actor.get('roles',[])


def case(db,owner,key):
    row=db.execute('SELECT state FROM cases WHERE id=? AND owner=?',(key,owner)).fetchone()
    if not row:raise DomainError('Incident unavailable')
    state=json.loads(row[0]);workspace.hydrate(db,owner,state)
    if not workspace.enabled(state):raise DomainError('Link the incident to the shared inventory first')
    return state


def source_basis(state,doc_id,quote):
    from .review_safety import resolution_evidence,require_language_review
    from .ocr import require_visual_review
    doc=next((d for d in state['documents'] if d['id']==doc_id),None)
    if not doc:raise DomainError('Source document unavailable')
    require_visual_review(doc)
    require_language_review(doc)
    ref=resolution_evidence(doc,quote)
    if not ref:raise DomainError('An exact original-source passage is required')
    return {'citation':ref,'original_hash':doc['original_hash'],'document_revision':doc['revision']}


def evidence(db,owner,state,data):
    require_role(db,'quality_reviewer')
    if data.revision!=state['revision']:raise DomainError('Evidence review is stale')
    pool=next((s for s in state['stocks'] if s['id']==data.pool_id),None)
    if not pool or data.inspected_units!=pool['units'] or data.nonconforming_units!=0 or not data.inspection_passed:
        raise DomainError('This whole-pool policy requires a passed 100% inspection with zero nonconforming units')
    if not data.authenticity_verified or len(data.verification_reference.strip())<8:raise DomainError('Source authenticity remains unknown; record explicit verification')
    receiving=source_basis(state,data.receiving_document_id,data.receiving_quote)
    inspected=source_basis(state,data.inspection_document_id,data.inspection_quote)
    from .review_safety import mentions
    if not mentions(data.pool_id,data.receiving_quote) or not mentions(data.pool_id,data.inspection_quote):raise DomainError('Both source passages must identify this exact pool')
    # Source occurrence is necessary, not a certificate of semantic truth; named review is recorded.
    for ref in (receiving,inspected):
        if not db.execute('SELECT 1 FROM bf_sources WHERE owner=? AND hash=?',(owner,ref['original_hash'])).fetchone():
            raise DomainError('Original source bytes must be available in the authorized store')
    try:observed=datetime.fromisoformat(data.inspected_at.replace('Z','+00:00'))
    except ValueError:raise DomainError('Use a valid timezone-aware inspection timestamp')
    if not observed.tzinfo or observed>datetime.now(timezone.utc) or observed<datetime.now(timezone.utc)-timedelta(days=30):
        raise DomainError('Inspection must be timezone-aware, not future-dated, and within the 30-day policy')
    result={'id':'REC-EVID-'+uuid.uuid4().hex,'case_id':state['id'],'pool_id':pool['id'],'receiving':receiving,'inspection':inspected,
            'inspected_units':data.inspected_units,'nonconforming_units':0,'inspected_at':data.inspected_at,'method':'visual-v1',
            'authenticity':'reviewer verified','verification_reference':data.verification_reference,'note':data.note,
            'actor':actor_authority(),'at':now(),'case_revision':state['revision']}
    repo.put_record(db,owner,'recovery-evidence',result['id'],result,0)
    repo.audit(db,owner,identity.current_actor(),'recovery.evidence_reviewed',{},result,[receiving['original_hash'],inspected['original_hash']])
    return result


def snapshot(db,owner,state,hold_ids,evidence_ids):
    from .assisted import blocking_reviews
    if blocking_reviews(db,owner,state['id']):raise DomainError('Effective source/procedure change requires explicit current re-review before recovery')
    _,inventory=repo.get_record(db,owner,'inventory','shared')
    policy_revision,policy=repo.get_record(db,owner,'recovery-policy','current')
    if not policy:raise DomainError('The recovery policy must be explicitly reviewed first')
    if state.get('pending_revision') or not state.get('plan') or state['scope'].get('incident_scope_status')!='resolved':
        raise DomainError('Current resolved incident scope and reviewed records are required')
    fresh=make_plan(state)
    if fresh['digest']!=state['plan']['digest']:raise DomainError('Containment proposal changed; review the current scope first')
    docs=catalog(db,owner)
    if policy['catalog_digest']!=digest(docs):raise DomainError('Approved procedures changed; review the recovery prerequisites again')
    selected=[d for d in docs if d['id']+'@'+str(d['version']) in policy['procedure_refs']]
    products={s['product_family'] for s in state['stocks']}
    for doc in selected:
        if doc['status']!='approved' or not products<=set(doc['products']) or 'coating' not in doc['processes'] or (doc['synthetic'] and not state['synthetic']):
            raise DomainError('Recovery prerequisite procedure is inapplicable to this incident')
        current=datetime.now(timezone.utc)
        if datetime.fromisoformat(doc['valid_from'].replace('Z','+00:00'))>current or (doc['valid_to'] and datetime.fromisoformat(doc['valid_to'].replace('Z','+00:00'))<=current):
            raise DomainError('Recovery procedure is not currently effective')
        if sum(d['id']==doc['id'] and d['status']=='approved' for d in docs)>1:raise DomainError('Conflicting approved procedure revisions block recovery')
    outside={r['id'] for r in fresh['result']['rows'] if r['classification']=='outside'}
    holds=[h for h in inventory['holds'] if h['id'] in hold_ids and h['status']=='active' and h['incident_id']==state['id']]
    if not holds or len(holds)!=len(set(hold_ids)):raise DomainError('Select exact active whole-pool holds from this incident')
    if any(h['pool_id'] not in outside for h in holds):raise DomainError('Unresolved or in-scope stock cannot be recovered')
    proofs=[]
    for key in evidence_ids:
        _,proof=repo.get_record(db,owner,'recovery-evidence',key)
        if not proof or proof['case_id']!=state['id'] or proof['case_revision']!=state['revision']:raise DomainError('Recovery evidence is unavailable or stale')
        if not authority_current(db,proof['actor'],'quality_reviewer'):raise DomainError('Recovery evidence reviewer authority was revoked')
        for kind in ('receiving','inspection'):
            ref=proof[kind];doc=next((d for d in state['documents'] if d['id']==ref['citation']['document_id']),None)
            if not doc or doc['original_hash']!=ref['original_hash']:raise DomainError('Recovery evidence source changed')
            from .review_safety import require_language_review
            require_language_review(doc)
        if datetime.fromisoformat(proof['inspected_at'].replace('Z','+00:00'))<datetime.now(timezone.utc)-timedelta(days=30):raise DomainError('Required inspection is stale')
        proofs.append(proof)
    if {p['pool_id'] for p in proofs}!={h['pool_id'] for h in holds}:raise DomainError('Every requested pool needs its own reviewed authenticity and passed inspection evidence')
    actions=[{'hold_id':h['id'],'hold_version':h['version'],'pool_id':h['pool_id'],'units':h['units'],'disposition':'remove_incident_restriction'} for h in sorted(holds,key=lambda h:h['id'])]
    return {'case_id':state['id'],'case_revision':state['revision'],'inventory_revision':inventory['revision'],'plan_digest':fresh['digest'],
            'policy_revision':policy_revision,'policy':policy,'catalog_digest':digest(docs),'evidence':proofs,'actions':actions,
            'other_active_restrictions':[h for h in inventory['holds'] if h['status']=='active' and h['id'] not in hold_ids and h['pool_id'] in {x['pool_id'] for x in holds}]}


def prepare(db,owner,state,hold_ids,evidence_ids,note):
    require_role(db,'quality_reviewer')
    basis=snapshot(db,owner,state,hold_ids,evidence_ids)
    proposal={'id':'RECOVERY-'+uuid.uuid4().hex,'case_id':state['id'],'status':'prepared','snapshot':basis,'digest':digest(basis),
              'pool_ids':sorted({a['pool_id'] for a in basis['actions']}),'hold_ids':hold_ids,'evidence_ids':evidence_ids,
              'preparer':actor_authority(),'prepared_at':now(),'note':note,'approval':None,'execution':'sandbox only'}
    repo.put_record(db,owner,'recovery',proposal['id'],proposal,0)
    repo.audit(db,owner,identity.current_actor(),'recovery.prepared',{},proposal)
    return proposal


def check_current(db,owner,proposal):
    state=case(db,owner,proposal['case_id'])
    if snapshot(db,owner,state,proposal['hold_ids'],proposal['evidence_ids'])!=proposal['snapshot']:
        raise DomainError('Recovery is stale: inventory, holds, sources, policy or procedure changed')
    if not authority_current(db,proposal['preparer'],'quality_reviewer'):raise DomainError('Preparer authority was revoked')
    return state


def approve(db,owner,key,expected):
    require_role(db,'release_approver')
    rev,proposal=repo.get_record(db,owner,'recovery',key)
    if not proposal or proposal['status']!='prepared' or proposal['digest']!=expected:raise DomainError('Current prepared exact recovery required')
    if proposal['preparer']['user_id']==identity.current_actor().get('user_id'):raise DomainError('Self-approval is prohibited, including administrators')
    check_current(db,owner,proposal)
    before=copy.deepcopy(proposal)
    proposal.update(status='approved',approval={'actor':actor_authority(),'at':now(),'digest':expected})
    repo.put_record(db,owner,'recovery',key,proposal,rev)
    repo.audit(db,owner,identity.current_actor(),'recovery.approved',before,proposal)
    return proposal


def execute(db,owner,key,expected,idempotency_key):
    require_role(db,'release_approver')
    rev,proposal=repo.get_record(db,owner,'recovery',key)
    fingerprint=digest({'recovery_id':key,'digest':expected})
    _,prior=repo.get_record(db,owner,'recovery-operation',idempotency_key)
    if prior:
        if prior['fingerprint']!=fingerprint:raise DomainError('Idempotency key belongs to another recovery')
        return prior['receipt']
    if not proposal or proposal['status']!='approved' or proposal['digest']!=expected:raise DomainError('Unconsumed approved exact recovery required')
    state=check_current(db,owner,proposal)
    if not authority_current(db,proposal['approval']['actor'],'release_approver'):raise DomainError('Release approver authority was revoked')
    return commit_removal(db,owner,rev,proposal,state,idempotency_key,fingerprint)


def commit_removal(db,owner,rev,proposal,state,idempotency_key,fingerprint,ack=None):
    inventory_version,inventory=repo.get_record(db,owner,'inventory','shared')
    before=copy.deepcopy(inventory)
    for hold in inventory['holds']:
        if hold['id'] in proposal['hold_ids']:
            if hold['status']!='active':raise DomainError('Restriction changed before execution')
            hold.update(status='removed',version=hold['version']+1,removed_at=now(),recovery_id=proposal['id'])
    remaining=workspace.active_pools(inventory)
    changes=[{'pool_id':a['pool_id'],'units':a['units'],'removed_hold_id':a['hold_id'],'became_available':a['pool_id'] not in remaining} for a in proposal['snapshot']['actions']]
    inventory['revision']+=1
    receipt={'transaction_id':'REC-TX-'+uuid.uuid4().hex,'recovery_id':proposal['id'],'at':now(),'execution':'SANDBOX LEDGER' if not ack else 'LOCAL REFERENCE CONNECTOR SANDBOX',
             'changes':changes,'prior_inventory_version':before['revision'],'current_inventory_version':inventory['revision'],
             'digest':proposal['digest'],'preparer':proposal['preparer'],'approver':proposal['approval']['actor'],
             'policy':proposal['snapshot']['policy'],'source_evidence':proposal['snapshot']['evidence'],'connector_acknowledgement':ack,
             'boundary':'Removes only the selected incident restriction; every other hold remains effective. No physical enterprise action.'}
    inventory['recovery_receipts'].append(receipt)
    repo.put_record(db,owner,'inventory','shared',inventory,inventory_version)
    proposal.update(status='executed',receipt=receipt)
    repo.put_record(db,owner,'recovery',proposal['id'],proposal,rev)
    repo.put_record(db,owner,'recovery-operation',idempotency_key,{'fingerprint':fingerprint,'receipt':receipt},0)
    repo.audit(db,owner,identity.current_actor(),'recovery.executed',before,inventory,operation_id=idempotency_key)
    workspace.hydrate(db,owner,state)
    db.execute('UPDATE cases SET state=? WHERE id=? AND owner=?',(json.dumps(state),state['id'],owner))
    return receipt
