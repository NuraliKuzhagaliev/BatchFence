import base64
import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend import app as module
from backend.domain import digest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'DB', tmp_path / 'test.sqlite3')
    return TestClient(module.app)


def post(c, route, payload=None):
    r = c.post(route, json=payload or {})
    assert r.status_code == 200, r.text
    return r.json()


def prepare(c):
    s = post(c, '/api/cases/demo')
    return review(c, s)


def review(c, s, revision=False):
    doc = s['documents'][-1] if revision else next(d for d in s['documents'] if 'supplier_notice' in d['filename'])
    s = post(c, f"/api/cases/{s['id']}/analyze", {'document_id': doc['id'], 'mode': 'fixture'})
    run = s['runs'][-1]
    assert run['status'] == 'succeeded', run
    return post(c, f"/api/cases/{s['id']}/reviews", {'run_id': run['id'], 'revision': s['revision'],
        'lot_ids': [f['lot_id'] for f in run['output']['facts']], 'accept_scope': True,
        'bounded_scope_reviewed': True, 'incident_scope_status': 'resolved',
        'resolution_quote': next(b['text'] for b in doc['blocks'] if b['text'].startswith('Affected lots:')),
        'note': 'Test operator reviewed the synthetic notice as the complete incident boundary.'})


def approve(c, s):
    return post(c, f"/api/cases/{s['id']}/approve", {'plan_id': s['plan']['id'], 'digest': s['plan']['digest']})


def payload(s, key='request-key-1'):
    return {'plan_id': s['plan']['id'], 'digest': s['plan']['digest'],
            'actions': s['plan']['actions'], 'idempotency_key': key}


def test_full_revised_workflow_and_persistence(client):
    c = client
    s = approve(c, prepare(c))
    old = payload(s)
    s = post(c, f"/api/cases/{s['id']}/revision")
    assert c.post(f"/api/cases/{s['id']}/apply", json=old).status_code == 409
    assert s['plan']['status'] == 'stale'
    s = approve(c, review(c, s, True))
    assert s['plan']['result']['hold_units'] == 800
    assert len(s['plan']['result']['orders']) == 4
    request = payload(s)
    applied = post(c, f"/api/cases/{s['id']}/apply", request)
    assert len(applied['receipts']) == 1 and sum(x['units'] for x in applied['receipts'][0]['changes']) == 800
    again = post(c, f"/api/cases/{s['id']}/apply", request)
    assert again['receipts'] == applied['receipts']
    fresh = TestClient(module.app)
    fresh.cookies.update(c.cookies)
    saved = fresh.get(f"/api/cases/{s['id']}").json()
    assert saved['receipts'] == applied['receipts']
    packet = c.get(f"/api/cases/{s['id']}/export").json()
    assert packet['integrity_hash'] == digest(packet['case'])
    assert 'bf_session' not in json.dumps(packet) and 'AMD_API_KEY' not in json.dumps(packet)
    draft = post(c, '/api/cases/import', packet)
    assert draft['plan'] is None and not draft['receipts'] and not draft['scope']['lot_ids']


def test_exact_actions_policy_and_cross_session(client):
    c = client; s = approve(c, prepare(c)); route = f"/api/cases/{s['id']}/apply"
    bad = payload(s); bad['actions'] = [a for a in bad['actions'] if a['pool_id'] != 'FG-C']
    r = c.post(route, json=bad)
    assert r.status_code == 409 and r.json()['detail']['code'] == 'POLICY_VIOLATION'
    unsupported = payload(s); unsupported['actions'] = [{'type': 'release', 'pool_id': 'FG-C'}]
    assert c.post(route, json=unsupported).status_code == 422
    other = TestClient(module.app)
    assert other.get(f"/api/cases/{s['id']}").status_code == 404
    assert other.post(route, json=payload(s)).status_code == 404
    post(c, route, payload(s))
    bad = payload(s); bad['actions'] = []
    assert c.post(route, json=bad).json()['detail']['code'] == 'IDEMPOTENCY_CONFLICT'


def test_changed_inventory_rejected_atomically(client):
    s = approve(client, prepare(client))
    with module.transaction(s['id'], __import__('hashlib').sha256(client.cookies.get('bf_session').encode()).hexdigest()) as (_, current):
        current['inventory_version'] += 1
    r = client.post(f"/api/cases/{s['id']}/apply", json=payload(s))
    assert r.status_code == 409 and r.json()['detail']['code'] == 'STALE_INVENTORY'


def test_race_evidence_and_apply_serialized(client):
    s = approve(client, prepare(client))
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(client.post, f"/api/cases/{s['id']}/apply", json=payload(s))
        b = pool.submit(client.post, f"/api/cases/{s['id']}/revision", json={})
        ar, br = a.result(), b.result()
    assert br.status_code == 200
    assert ar.status_code in (200, 409)
    current = client.get(f"/api/cases/{s['id']}").json()
    assert current['pending_revision']
    assert len(current['receipts']) == (1 if ar.status_code == 200 else 0)


def test_concurrent_duplicate_apply_one_receipt(client):
    s = approve(client, prepare(client))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(f"/api/cases/{s['id']}/apply", json=payload(s)), range(2)))
    assert [r.status_code for r in results] == [200, 200]
    assert len(results[0].json()['receipts']) == len(results[1].json()['receipts']) == 1


def test_provider_failure_never_falls_back(client, monkeypatch):
    monkeypatch.delenv('AMD_API_KEY', raising=False)
    s = post(client, '/api/cases/demo')
    doc = next(d for d in s['documents'] if 'supplier' in d['filename'])
    s = post(client, f"/api/cases/{s['id']}/analyze", {'document_id': doc['id'], 'mode': 'live'})
    assert s['runs'][-1]['mode'] == 'live' and s['runs'][-1]['status'] == 'failed'
    assert s['plan'] is None


def test_upload_validation_and_csrf(client):
    s = prepare(client); route = f"/api/cases/{s['id']}/documents"
    assert client.post(route, json={'filename': '../bad.txt', 'content_base64': 'QQ=='}).status_code == 422
    data = {'filename': 'changed.txt', 'content_base64': base64.b64encode(b'Affected lots: SUP-E').decode(), 'synthetic': True}
    s = post(client, route, data)
    assert s['pending_revision'] and s['plan']['status'] == 'stale'
    assert client.post('/api/cases/demo', json={}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/cases/demo', content='{}', headers={'Content-Type': 'text/plain'}).status_code == 415
