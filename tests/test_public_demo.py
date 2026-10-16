"""Public deployment controls. Provider calls here are mocked, never called live."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading
import pytest
from fastapi.testclient import TestClient
from backend import app as module
from backend import public_demo as guard
from tests.test_api import post


@pytest.fixture
def public_client(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'DB', tmp_path / 'public.sqlite3')
    monkeypatch.setattr(module, 'ORIGIN', 'https://demo.example')
    monkeypatch.setenv('PUBLIC_DEMO', 'true')
    monkeypatch.setenv('LIVE_DEMO_TOKEN', 'test-only-access-' * 3)
    monkeypatch.setenv('MAX_TOTAL_LIVE_RUNS', '20')
    monkeypatch.setenv('MAX_RUNS_PER_SESSION', '8')
    monkeypatch.setattr(module, 'limiter', guard.RequestLimiter())
    return TestClient(module.app, base_url='https://demo.example')


def call_live(c, state, token=True):
    return c.post('/api/cases/'+state['id']+'/analyze', json={
        'mode':'live', 'document_id':next(d['id'] for d in state['documents'] if 'supplier_notice' in d['filename'])},
        headers={'X-BF-Demo-Token': 'test-only-access-'*3} if token else {})


def test_live_access_fails_closed_and_never_consumes_provider(public_client, monkeypatch):
    def forbidden(*args): raise AssertionError('Provider must not be called')
    monkeypatch.setattr(module, 'extract', forbidden)
    s=post(public_client, '/api/cases/demo')
    assert call_live(public_client,s,False).status_code==403
    monkeypatch.delenv('LIVE_DEMO_TOKEN')
    r=call_live(public_client,s)
    assert r.status_code==503 and r.json()['detail']['code']=='LIVE_UNAVAILABLE'
    assert public_client.get('/api/cases/'+s['id']).json()['runs']==[]
    cookie=public_client.get('/api/health').headers['set-cookie'].lower()
    assert all(x in cookie for x in ['secure','httponly','samesite=strict'])


def test_live_concurrency_and_failed_attempt_budget_survive_new_client(public_client, monkeypatch):
    entered=threading.Event(); release=threading.Event()
    def blocked(docs,mode):
        entered.set(); assert release.wait(5)
        return {'id':'mock-live-failure','mode':'live','status':'failed','error':'Mock network failure; no fallback'}
    monkeypatch.setattr(module,'extract',blocked)
    monkeypatch.setenv('MAX_TOTAL_LIVE_RUNS','1')
    s=post(public_client,'/api/cases/demo')
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(call_live,public_client,s)
        assert entered.wait(3)
        try:
            second=call_live(public_client,s)
            assert second.status_code==429 and second.json()['detail']['code']=='LIVE_BUSY'
        finally: release.set()
        assert first.result().json()['runs'][-1]['status']=='failed'
    fresh=TestClient(module.app,base_url='https://demo.example')
    other=post(fresh,'/api/cases/demo')
    r=call_live(fresh,other)
    assert r.status_code==429 and r.json()['detail']['code']=='OWNER_BUDGET'
    assert public_client.get('/api/cases/'+s['id']).json()['plan'] is None


def test_global_rate_limit_cannot_be_bypassed_with_new_sessions(public_client,monkeypatch):
    monkeypatch.setenv('MAX_REQUESTS_PER_MINUTE','2')
    assert public_client.get('/api/cases').status_code==200
    fresh=TestClient(module.app,base_url='https://demo.example')
    assert fresh.get('/api/cases').status_code==200
    r=TestClient(module.app,base_url='https://demo.example').get('/api/cases')
    assert r.status_code==429 and r.headers['retry-after']=='60'
    assert public_client.get('/api/health').status_code==200


def test_storage_capacity_and_origin_isolation(public_client,monkeypatch):
    monkeypatch.setenv('MAX_STORED_CASES','1')
    a=post(public_client,'/api/cases/demo')
    fresh=TestClient(module.app,base_url='https://demo.example')
    assert fresh.get('/api/cases/'+a['id']).status_code==404
    assert fresh.get('/api/cases/'+a['id']+'/export').status_code==404
    assert fresh.post('/api/cases/demo',json={}).json()['detail']['code']=='DEMO_CAPACITY'
    assert public_client.post('/api/cases/demo',json={},headers={'Origin':'http://localhost:5173'}).status_code==403


def test_body_size_header_and_chunked(public_client):
    assert public_client.post('/api/cases/demo',content=b'{}',headers={
        'content-type':'application/json','content-length':'8000001'}).status_code==413
    chunks=(b' ' * 1_000_000 for _ in range(9))
    assert public_client.post('/api/cases/demo',content=chunks,headers={'content-type':'application/json'}).status_code==413
    assert public_client.get('/api/cases').json()==[]


def test_health_detects_unavailable_database_without_exposing_path(public_client,monkeypatch,tmp_path):
    assert public_client.get('/api/health').json()['database']=='ready'
    monkeypatch.setattr(module,'DB',tmp_path/'missing'/'private-name.sqlite3')
    r=public_client.get('/api/health')
    assert r.status_code==503 and 'private-name' not in r.text


def test_schema_version_not_silently_overwritten(public_client):
    public_client.get('/api/health')
    with sqlite3.connect(module.DB) as db: db.execute('PRAGMA user_version=99')
    assert public_client.get('/api/health').status_code==503
    with sqlite3.connect(module.DB) as db: assert db.execute('PRAGMA user_version').fetchone()[0]==99


def test_public_replay_is_historical_and_navigation_keeps_api_404(public_client):
    replay=public_client.get('/api/replay').json()
    assert replay['case']['runs'][-1]['mode']=='live'
    assert replay['case']['receipts']
    assert public_client.get('/api/cases').json()==[]
    assert public_client.get('/api/not-a-route',headers={'Accept':'text/html'}).status_code==404
    assert public_client.get('/assets/missing.js').status_code==404
    html=public_client.get('/workspace/review',headers={'Accept':'text/html'})
    assert html.status_code==200 and 'src="/assets/' in html.text and 'href="/assets/' in html.text
    assert 'test-only-access' not in json.dumps(replay)


def test_health_identifies_ephemeral_storage(public_client, monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "ephemeral")
    health = public_client.get("/api/health").json()
    assert health["storage_mode"] == "ephemeral"
    assert health["public_demo"] is True
