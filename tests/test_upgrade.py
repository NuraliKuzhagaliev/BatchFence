"""Upgrade acceptance expectations, frozen before implementation; synthetic only."""
import copy
import pytest
from backend.fixtures import load_demo
from backend.domain import make_plan, digest
from backend.review_safety import REVIEW_POLICY_VERSION
from .test_api import client, prepare, approve, payload, post, review
from backend.fixtures import ROOT
import base64


def reviewed(lots=None):
    s = load_demo()
    s['scope'].update(lot_ids=lots or ['SUP-A'], incident_scope_status='resolved',
                      review_policy_version=REVIEW_POLICY_VERSION)
    s['plan'] = make_plan(s)
    return s


def test_shared_boundary_cause_not_six_missing_receipts():
    s = reviewed()
    s['scope']['incident_scope_status'] = 'unresolved'
    r = make_plan(s)['result']
    assert r['hold_units'] == 1200
    causes = r['requests']
    assert len([c for c in causes if c['kind'] == 'boundary_review']) == 1
    assert all(c['pool_ids'] == ['FG-C'] for c in causes if c['kind'] in ('possible_ancestry', 'incomplete_ancestry'))
    assert r['request_unique_units'] == 1200  # overlapping causes, once per pool


def test_unresolved_intermediate_node_uses_server_semantics():
    s = reviewed()
    s['scope']['uncertain_lot_ids'] = ['SUP-C']
    e = next(e for e in s['edges'] if e['target'] == 'FG-D')
    e['target'] = 'EV-C'
    s['edges'].append({'source':'EV-C', 'target':'FG-D', 'kind':'confirmed'})
    r = make_plan(s)['result']
    assert r['node_states']['EV-C'] == 'uncertain'
    assert r['hold_units'] == 800


@pytest.mark.parametrize('lots,before,after', [(['SUP-A'],500,400),(['SUP-A','SUP-C'],800,700)])
def test_readonly_complete_identity_impact(lots,before,after):
    from backend.scenarios import simulate
    s = reviewed(lots)
    s['plan']['status'] = 'approved'
    for stock in s['stocks']:
        if stock['id'] in {a['pool_id'] for a in s['plan']['actions']}:
            stock['status'] = 'held'
    original = digest(s)
    r = simulate(s,[{'kind':'identity','pool_id':'FG-C','supplier_lot_id':'SUP-B','complete':True}])
    assert (r['before']['hold_units'],r['after']['hold_units']) == (before,after)
    assert r['applied_hold_units'] == before
    assert r['label'] == 'Simulation' and 'plan_id' not in r
    assert digest(s) == original


def test_partial_answer_alternative_and_inconclusive_stay_held():
    from backend.scenarios import simulate
    s = reviewed()
    for h in [{'kind':'identity','pool_id':'FG-C','supplier_lot_id':'SUP-B','complete':False},
              {'kind':'identity','pool_id':'FG-C','supplier_lot_id':'SUP-A','complete':True},
              {'kind':'inconclusive'}]:
        assert simulate(s,[h])['after']['hold_units'] == 500


def test_scenario_overlaps_recompute_not_add():
    from backend.scenarios import simulate
    s = reviewed()
    h = {'kind':'identity','pool_id':'FG-C','supplier_lot_id':'SUP-B','complete':True}
    assert simulate(s,[h,h])['changed_units'] == 100
    with pytest.raises(ValueError):
        simulate(s,[h]*7)
    with pytest.raises(ValueError):
        simulate(s,[h,{**h,'supplier_lot_id':'SUP-A'}])


def test_executable_challenges_do_not_change_visitor_case(client):
    s=prepare(client)
    result=post(client,'/api/challenges')
    assert len(result['checks'])==6 and all(c['passed'] for c in result['checks'])
    assert client.get(f"/api/cases/{s['id']}").json()==s


def reply_case(c, filename='receiving-complete.txt', applied=False):
    s = approve(c,prepare(c))
    old = payload(s,'original-approval')
    if applied:
        s = post(c,f"/api/cases/{s['id']}/apply",old)
    question = next(q for q in s['plan']['result']['requests'] if q['kind']=='possible_ancestry')
    text = (ROOT/'fixtures/resolution'/filename).read_text()
    route = f"/api/cases/{s['id']}"
    s = post(c,route+'/documents',{'filename':filename,'synthetic':True,'request_id':question['id'],
                                  'content_base64':base64.b64encode(text.encode()).decode()})
    assert c.post(route+'/apply',json={**old,'idempotency_key':'new-stale-attempt'}).status_code==409
    doc = s['documents'][-1]
    s = post(c,route+'/analyze',{'document_id':doc['id'],'mode':'fixture'})
    return s,route,{'revision':s['revision'],'document_id':doc['id'],'pool_id':'FG-C',
        'supplier_lot_id':'SUP-B','outcome':'resolved','complete':True,'quote':doc['blocks'][1]['text'],
        'reviewed':True,'replacement_reviewed':True,'note':'Agent-operated synthetic review of explicit complete replacement and all superseded row IDs.'}


def test_reconcile_requires_review_preserves_holds_and_rejects_old_authority(client):
    s,route,body=reply_case(client,applied=True)
    before=copy.deepcopy(s)
    preview=post(client,route+'/reply-preview',body)
    assert preview['impact']['after']['hold_units']==400
    assert client.get(route).json()==before
    assert client.post(route+'/reply-review',json={**body,'replacement_reviewed':False}).status_code==422
    s=post(client,route+'/reply-review',body)
    assert s['plan']['result']['hold_units']==400
    assert sum(p['units'] for p in s['stocks'] if p['status']=='held')==500
    assert len(s['receipts'])==1 and s['plan']['status']=='proposed'
    assert client.post(route+'/approve',json={'plan_id':preview.get('plan_id','simulation'),'digest':preview['impact']['source_digest']}).status_code==409
    assert client.post(route+'/reply-review',json=body).status_code==422


@pytest.mark.parametrize('filename,outcome',[('receiving-inconclusive.txt','inconclusive'),('receiving-conflicting.txt','conflicting')])
def test_weak_reply_cannot_narrow(client,filename,outcome):
    s,route,body=reply_case(client,filename)
    assert client.post(route+'/reply-review',json=body).status_code==422
    s=post(client,route+'/reply-review',{**body,'outcome':outcome})
    assert s['plan']['result']['hold_units']==500
    assert any(c['kind']=='possible_ancestry' for c in s['plan']['result']['requests'])
    if outcome=='conflicting':
        assert any(c['kind']=='conflicting_evidence' for c in s['plan']['result']['requests'])


def test_causal_revision_path_300_and_order104(client):
    s=approve(client,prepare(client))
    s=post(client,f"/api/cases/{s['id']}/revision")
    s=review(client,s,True)
    diff=client.get(f"/api/cases/{s['id']}/comparison").json()
    assert (diff['before_units'],diff['after_units'])==(500,800)
    changes=[p for p in diff['pools'] if p['group']=='newly_included']
    assert len(changes)==1
    assert (changes[0]['pool_id'],changes[0]['units'],changes[0]['path'],changes[0]['order_ids'])==('FG-D',300,['SUP-C','FG-D'],['O-104'])
    assert diff['new_order_reviews']==['O-104'] and len(diff['prior_order_reviews'])==3


def test_scenario_api_session_and_immutable_authority(client):
    from fastapi.testclient import TestClient
    from backend.app import app
    s=approve(client,prepare(client))
    route=f"/api/cases/{s['id']}"
    args={'revision':s['revision'],'hypotheses':[{'kind':'inconclusive'}]}
    assert TestClient(app).post(route+'/simulate',json=args).status_code==404
    post(client,route+'/simulate',args)
    assert client.get(route).json()==s


def test_observed_live_receiving_omission_stays_uncertain():
    """Replay the exact 0.2.0 raw omission; no provider request or human validation."""
    import json
    from types import SimpleNamespace
    from backend.reconciliation import preview_reply, commit_reply
    s=json.loads((ROOT/'docs/release-0.2.0/live/reply-before-review.json').read_text(encoding='utf-8'))['case']
    doc=s['documents'][-1]
    assert [f['lot_id'] for f in s['runs'][-1]['output']['facts']]==['FG-C']
    data=SimpleNamespace(document_id=doc['id'],revision=s['revision'],pool_id='FG-C',
        supplier_lot_id='SUP-B',quote=doc['blocks'][1]['text'],outcome='resolved',
        complete=True,reviewed=True,replacement_reviewed=True,note='Replay of observed missing supplier candidate; preserve existing holds.')
    before=copy.deepcopy(s)
    with pytest.raises(ValueError,match='source-backed supplier candidate'):
        preview_reply(s,data)
    assert s==before
    data.outcome='inconclusive';data.complete=False
    commit_reply(s,data,'historical regression replay')
    assert s['plan']['result']['hold_units']==800
    assert sum(p['units'] for p in s['stocks'] if p['status']=='held')==800
    assert any(q['kind']=='possible_ancestry' for q in s['plan']['result']['requests'])
