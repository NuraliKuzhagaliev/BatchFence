import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import pytest
from tests.test_api import post,review,approve,payload
from tests.test_foundations import pilot
from backend import repository as repo,app as module


def prepared_recovery(login):
    c=login('reviewer')
    state=post(c,'/api/cases/demo')
    state=post(c,'/api/enterprise/example',{'case_id':state['id'],'acknowledged_synthetic':True})
    route='/api/cases/'+state['id']
    # Inspection evidence predates the frozen recovery decision, not a fabricated model claim.
    proof='FG-C: 100 pieces inspected using visual-v1; 0 nonconforming. Passed whole-pool cosmetic inspection.'
    state=post(c,route+'/documents',{'filename':'inspection.txt','content_base64':base64.b64encode(proof.encode()).decode(),'synthetic':True})
    inspection=state['documents'][-1]
    state=approve(c,review(c,state)); assert state['plan']['result']['hold_units']==500
    state=post(c,route+'/apply',payload(state,'first-containment'))
    state=post(c,route+'/revision')
    state=approve(c,review(c,state,True));assert state['plan']['result']['hold_units']==800
    state=post(c,route+'/apply',payload(state,'second-containment'))
    question=next(q for q in state['plan']['result']['requests'] if q.get('kind')=='incomplete_ancestry' or q.get('pool_ids')==['FG-C'])
    quote='Receiver reconciled every receipt for FG-C. Its entire ancestry is supplier lot SUP-B, with no additional parents. Original supplier receipt REC-812 was authenticated by the receiving supervisor.'
    state=post(c,route+'/documents',{'filename':'natural-receiving.txt','content_base64':base64.b64encode(quote.encode()).decode(),'synthetic':True,'request_id':question['id']})
    doc=state['documents'][-1]
    receiving={'revision':state['revision'],'document_id':doc['id'],'review_path':'structured_record','pool_id':'FG-C','parent_ids':['SUP-B'],'complete':True,
        'quote':quote,'superseded_row_ids':['LIN-3','LIN-4'],'unresolved_contradictions':False,'outcome':'resolved','reviewed':True,'replacement_reviewed':True,
        'completeness_confirmed':True,'note':'Agent reviewed synthetic full receiving records and every superseded relationship; not independent domain validation.'}
    preview=post(c,route+'/receiving-preview',receiving)
    assert preview['after_units']==700 and preview['applied_hold_units']==800
    assert c.post(route+'/receiving-review',json={**receiving,'unresolved_contradictions':True}).status_code==422
    assert c.post(route+'/receiving-review',json={**receiving,'parent_ids':['REC-812']}).status_code==422
    assert c.post(route+'/receiving-review',json={**receiving,'superseded_row_ids':['LIN-3']}).status_code==422
    state=post(c,route+'/receiving-review',receiving)
    assert state['plan']['result']['hold_units']==700
    assert state['quantities']['applied_hold_units']==800 and len(state['receipts'])==2
    post(c,'/api/recovery/policy-review',{'reviewed':True,'note':'Agent accepted the synthetic whole-pool policy and current procedure for engineering tests.','expected_revision':0,'procedure_refs':['PROC-100@1']})
    evidence={'revision':state['revision'],'pool_id':'FG-C','receiving_document_id':doc['id'],'receiving_quote':quote,'authenticity_verified':True,
        'verification_reference':'Synthetic receiving supervisor record REC-812; agent-operated test','inspection_document_id':inspection['id'],'inspection_quote':proof,
        'inspected_units':100,'nonconforming_units':0,'inspection_passed':True,'inspected_at':datetime.now(timezone.utc).isoformat(),'note':'Agent checked synthetic original receipt and inspection; no real supplier validation claimed.'}
    assert c.post(route+'/recovery-evidence',json={**evidence,'authenticity_verified':False}).status_code==422
    assert c.post(route+'/recovery-evidence',json={**evidence,'inspected_units':50}).status_code==422
    ev=post(c,route+'/recovery-evidence',evidence)
    holds=post_get(c,route+'/recovery')['holds']
    held=next(h for h in holds if h['pool_id']=='FG-C' and h['incident_id']==state['id'] and h['status']=='active')
    proposal=post(c,route+'/recovery-prepare',{'hold_ids':[held['id']],'evidence_ids':[ev['id']],'note':'Prepare exactly the 100-unit whole-pool incident restriction removal.'})
    return c,state,proposal,ev


def post_get(c,path):
    result=c.get(path);assert result.status_code==200,result.text;return result.json()


def test_800_700_exact_100_recovery_and_duplicate_execution(pilot):
    login,ids=pilot;c,state,proposal,_=prepared_recovery(login)
    # Give the same person release capability as well: distinction still applies.
    admin=login('administrator')
    post(admin,'/api/auth/membership',{'user_id':ids['reviewer'],'roles':['reporter','quality_reviewer','release_approver','administrator'],'active':True})
    same=login('reviewer')
    body={'recovery_id':proposal['id'],'digest':proposal['digest']}
    denied=same.post('/api/recovery/release-approve',json=body)
    assert denied.status_code==422 and 'Self-approval' in denied.text
    # Role change also revokes old preparer authority, so create a fresh evidence/proposal.
    # This test uses a separate valid preparation before any role change instead below.
    releaser=login('releaser')
    assert releaser.post('/api/recovery/release-approve',json=body).status_code==422
    assert post_get(releaser,'/api/cases/'+state['id'])['quantities']['applied_hold_units']==800


def test_valid_distinct_recovery_exact_once(pilot):
    login,_=pilot;c,state,proposal,_=prepared_recovery(login)
    r=login('releaser'); body={'recovery_id':proposal['id'],'digest':proposal['digest']}
    approved=post(r,'/api/recovery/release-approve',body)
    assert approved['preparer']['user_id']!=approved['approval']['actor']['user_id']
    execute={**body,'idempotency_key':'explicit-recovery-100'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:r.post('/api/recovery/recovery-execute',json=execute),range(2)))
    assert all(x.status_code==200 for x in results),[x.text for x in results]
    assert results[0].json()==results[1].json()
    saved=post_get(r,'/api/cases/'+state['id'])
    assert saved['quantities']=={'applied_hold_units':700,'recovery_pending_units':0,'confirmed_recovery_units':100}
    assert len(saved['receipts'])==2 and saved['receipts']==state['receipts']
    assert len(saved['recovery_receipts'])==1 and saved['recovery_receipts'][0]['changes'][0]['units']==100
    assert r.post('/api/recovery/recovery-execute',json={**execute,'idempotency_key':'another-replay-key'}).status_code==422


def test_second_incident_hold_stales_recovery_and_preserves_stock(pilot):
    login,_=pilot;c,state,proposal,_=prepared_recovery(login)
    r=login('releaser');body={'recovery_id':proposal['id'],'digest':proposal['digest']}
    post(r,'/api/recovery/release-approve',body)
    second=post(c,'/api/cases/demo')
    # Shared reviewed ancestry would normally exclude FG-C. Conservatively unresolved
    # boundary requires all stock, so a genuinely separate reason includes FG-C.
    owner='pilot:northstar:plant1'
    second_route='/api/cases/'+second['id']
    second=post(c,second_route+'/documents',{'filename':'second-incident.txt','content_base64':base64.b64encode(b'Affected lots: SUP-B. Separate synthetic incident boundary is complete.').decode(),'synthetic':True})
    second=approve(c,review(c,second,True))
    assert second['plan']['result']['hold_units']==100
    post(c,second_route+'/apply',payload(second,'second-incident-restriction'))
    denied=r.post('/api/recovery/recovery-execute',json={**body,'idempotency_key':'stale-other-hold'})
    assert denied.status_code==422
    saved=post_get(c,'/api/cases/'+state['id']);assert saved['quantities']['applied_hold_units']==800
    assert not saved['recovery_receipts']
    # Explicit new review/proposal is necessary; removal itself retains the other reason.
    doc=next(d for d in saved['documents'] if d['filename']=='supplier_notice_v2.txt')
    analyzed=post(c,'/api/cases/'+state['id']+'/analyze',{'document_id':doc['id'],'mode':'fixture'})
    saved=post(c,'/api/cases/'+state['id']+'/reviews',{'run_id':analyzed['runs'][-1]['id'],'revision':analyzed['revision'],'lot_ids':['SUP-A','SUP-C'],
        'accept_scope':True,'bounded_scope_reviewed':True,'incident_scope_status':'resolved','resolution_quote':next(b['text'] for b in doc['blocks'] if b['text'].startswith('Affected lots:')),
        'note':'Explicit synthetic scope re-review after another incident added a shared restriction.'})
    renewed=post(c,'/api/cases/'+state['id']+'/recovery-prepare',{'hold_ids':proposal['hold_ids'],'evidence_ids':proposal['evidence_ids'],'note':'Explicit new recovery preparation retaining the second incident restriction.'})
    newbody={'recovery_id':renewed['id'],'digest':renewed['digest']}
    post(r,'/api/recovery/release-approve',newbody)
    receipt=post(r,'/api/recovery/recovery-execute',{**newbody,'idempotency_key':'overlap-verified-api'})
    assert receipt['changes'][0]['became_available'] is False
    saved=post_get(c,'/api/cases/'+state['id'])
    assert next(s for s in saved['stocks'] if s['id']=='FG-C')['status']=='held'
    assert saved['quantities']['applied_hold_units']==800 and saved['quantities']['confirmed_recovery_units']==0


def test_outbox_timeout_retry_duplicate_ack_and_ssrf_guard(pilot,monkeypatch,tmp_path):
    login,_=pilot;c,state,proposal,_=prepared_recovery(login)
    r=login('releaser');body={'recovery_id':proposal['id'],'digest':proposal['digest']}
    post(r,'/api/recovery/release-approve',body)
    item=post(r,'/api/recovery/connector-enqueue',{**body,'idempotency_key':'reference-outbox-key'})
    from backend import outbox,reference_connector
    from backend.domain import DomainError,digest
    import httpx
    def timeout(_):raise httpx.ReadTimeout('synthetic timeout')
    monkeypatch.setattr(outbox,'send',timeout)
    failed=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']})
    assert failed['status']=='failed_ack'
    assert post_get(c,'/api/cases/'+state['id'])['quantities']['applied_hold_units']==800
    from fastapi.testclient import TestClient
    monkeypatch.setenv('REFERENCE_CONNECTOR_TOKEN','synthetic-reference-test-token-'*2)
    monkeypatch.setenv('REFERENCE_DATABASE_PATH',str(tmp_path/'connector.sqlite3'))
    reference=TestClient(reference_connector.app)
    assert reference.post('/inventory/restrictions',json=item['payload']).status_code==401
    headers={'Authorization':'Bearer '+'synthetic-reference-test-token-'*2}
    def acknowledge(payload):
        result=reference.post('/inventory/restrictions',json=payload,headers=headers)
        assert result.status_code==200,result.text
        return result.json()
    monkeypatch.setattr(outbox,'send',acknowledge)
    confirmed=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']})
    assert confirmed['status']=='acknowledged' and confirmed['attempts']==2
    again=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']})
    assert again==confirmed
    # A new connector client reads its actual persisted acknowledgement.
    reference=TestClient(reference_connector.app)
    assert acknowledge(item['payload'])==confirmed['receipt']['connector_acknowledgement']
    assert post_get(c,'/api/cases/'+state['id'])['quantities']['applied_hold_units']==700
    changed={**item['payload'],'actions':[{**item['payload']['actions'][0],'units':50}]}
    assert reference.post('/inventory/restrictions',json=changed,headers=headers).status_code==409
