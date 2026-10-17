import base64
import copy
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend import app as module, identity, repository as repo
from backend.domain import digest
from scripts.pilot import backup, restore
from tests.test_api import post, prepare, approve, payload


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'DB', tmp_path/'pilot.sqlite3')
    monkeypatch.setenv('SOURCE_STORAGE_PATH',str(tmp_path/'sources'))
    monkeypatch.setenv('DEPLOYMENT_PROFILE','pilot')
    monkeypatch.setenv('PILOT_SESSION_SECRET','test-secret-only-not-a-production-secret-2026')
    monkeypatch.delenv('PILOT_DATABASE_URL',raising=False)
    from backend.public_demo import RequestLimiter
    monkeypatch.setattr(module,'limiter',RequestLimiter())
    accounts = {}
    with repo.write(module.connect) as db:
        for name,org,site,roles in [
            ('reviewer','northstar','plant1',['reporter','quality_reviewer']),
            ('second-reviewer','northstar','plant1',['reporter','quality_reviewer']),
            ('releaser','northstar','plant1',['release_approver']),
            ('auditor','northstar','plant1',['auditor']),
            ('administrator','northstar','plant1',['administrator']),
            ('other-org','other','plant1',['reporter','quality_reviewer']),
            ('other-site','northstar','plant2',['reporter','quality_reviewer'])]:
            accounts[name] = identity.create_user(db,name,'synthetic-test-password-2026',org,site,roles)
    def login(name):
        client=TestClient(module.app)
        org='other' if name=='other-org' else 'northstar'
        site='plant2' if name=='other-site' else 'plant1'
        assert client.post('/api/auth/login',json={'username':name,'password':'synthetic-test-password-2026','org':org,'site':site}).status_code==200
        return client
    return login,accounts


def test_sqlite_migration_preserves_anonymous_receipts(tmp_path):
    path=tmp_path/'legacy.sqlite3'
    old={'anonymous':True,'digest':'preserve-exactly'}
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE cases(id TEXT PRIMARY KEY,owner TEXT NOT NULL,state TEXT NOT NULL)')
        db.execute('CREATE TABLE receipts(owner TEXT,key TEXT,request_digest TEXT,receipt TEXT,PRIMARY KEY(owner,key))')
        db.execute('INSERT INTO cases VALUES(?,?,?)',('old','anonymous-owner',json.dumps(old)))
        db.execute('INSERT INTO receipts VALUES(?,?,?,?)',('anonymous-owner','key','unchanged',json.dumps(old)))
        db.execute('PRAGMA user_version=1')
    with repo.connect(path,url='') as db:
        assert json.loads(db.execute('SELECT state FROM cases').fetchone()[0])==old
        assert db.execute('SELECT owner,request_digest FROM receipts').fetchone()==('anonymous-owner','unchanged')
        assert db.execute('SELECT count(*) FROM bf_members').fetchone()[0]==0
    assert path.with_name(path.name+'.pre-v2-backup').exists()


def test_named_workflow_object_source_export_audit_and_revocation(pilot):
    login,ids=pilot
    anonymous=TestClient(module.app)
    assert anonymous.get('/api/cases').status_code==401
    client=login('reviewer')
    state=approve(client,prepare(client))
    state=post(client,f"/api/cases/{state['id']}/apply",payload(state))
    assert state['plan']['approval']['reviewer']['user_id']==ids['reviewer']
    assert state['plan']['result']['hold_units']==500
    raw=b'A source record with original bytes.\r\n'
    state=post(client,f"/api/cases/{state['id']}/documents",{'filename':'original.txt','content_base64':base64.b64encode(raw).decode()})
    sha=hashlib.sha256(raw).hexdigest()
    assert client.get('/api/sources/'+sha).content==raw
    for who in ['other-org','other-site']:
        other=login(who)
        assert other.get(f"/api/cases/{state['id']}").status_code==404
        assert other.get(f"/api/cases/{state['id']}/export").status_code==404
        assert other.get('/api/sources/'+sha).status_code==404
        assert other.get('/api/audit').json()['events']
        assert all(e['event']['actor'].get('org')!='northstar' or who=='other-site' for e in other.get('/api/audit').json()['events'])
    audit=client.get('/api/audit').json()['events']
    for i,entry in enumerate(audit):
        assert entry['event_hash']==digest({'previous_hash':entry['previous_hash'],'event':entry['event']})
        if i: assert entry['previous_hash']==audit[i-1]['event_hash']
    admin=login('administrator')
    assert admin.post('/api/cases/demo',json={}).status_code==403
    post(admin,'/api/auth/membership',{'user_id':ids['reviewer'],'roles':['auditor'],'active':True})
    assert client.get(f"/api/cases/{state['id']}/export").status_code==401
    assert client.get('/api/sources/'+sha).status_code==401
    auditor=login('reviewer')
    assert auditor.get(f"/api/cases/{state['id']}").status_code==200
    assert auditor.post(f"/api/cases/{state['id']}/approve",json={}).status_code==403


def test_selector_is_not_authority_and_logout(pilot):
    login,_=pilot
    client=TestClient(module.app)
    assert client.post('/api/auth/login',json={'username':'reviewer','password':'synthetic-test-password-2026','org':'other','site':'plant1'}).status_code==401
    client=login('reviewer')
    stolen_selector=client.get('/api/cases',headers={'X-Organization':'other'})
    assert stolen_selector.status_code==200
    post(client,'/api/auth/logout')
    assert client.get('/api/cases').status_code==401


def test_audit_append_only_and_transaction_rollback(pilot):
    login,_=pilot; c=login('reviewer'); s=prepare(c)
    with module.connect() as db:
        count=db.execute('SELECT count(*) FROM bf_audit').fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM bf_audit')
    before=c.get('/api/cases/'+s['id']).json()
    assert c.post('/api/cases/'+s['id']+'/approve',json={'plan_id':'wrong','digest':'wrong'}).status_code==409
    assert c.get('/api/cases/'+s['id']).json()==before
    with module.connect() as db: assert db.execute('SELECT count(*) FROM bf_audit').fetchone()[0]==count


def test_backup_restore_sources_records_receipts_and_corruption(pilot,tmp_path,monkeypatch):
    login,_=pilot; c=login('reviewer'); s=approve(c,prepare(c))
    s=post(c,f"/api/cases/{s['id']}/apply",payload(s))
    raw=b'Preserved source for a restore drill.'
    post(c,f"/api/cases/{s['id']}/documents",{'filename':'proof.txt','content_base64':base64.b64encode(raw).decode()})
    archive=tmp_path/'backup.zip'
    with module.connect() as db: report=backup(db,archive)
    target=tmp_path/'isolated.sqlite3'
    with repo.connect(target,url='') as db:
        result=restore(db,archive,tmp_path/'restored-sources')
        assert result['all_record_values_match'] and result['source_hashes_verified']>=1
        assert db.execute('SELECT count(*) FROM bf_sessions').fetchone()[0]==0
        with pytest.raises(ValueError): restore(db,archive,tmp_path/'another-location')
    monkeypatch.setattr(module,'DB',target)
    monkeypatch.setenv('SOURCE_STORAGE_PATH',str(tmp_path/'restored-sources'))
    fresh=login('reviewer')
    saved=fresh.get('/api/cases/'+s['id']).json()
    assert saved['receipts']==s['receipts']
    assert fresh.get('/api/sources/'+hashlib.sha256(raw).hexdigest()).content==raw
    assert fresh.post('/api/cases/'+s['id']+'/approve',json={'plan_id':s['plan']['id'],'digest':s['plan']['digest']}).status_code==409
    assert report['counts']['receipts']==1


def test_revoked_approver_cannot_supply_authority_to_another_reviewer(pilot):
    login,ids=pilot; c=login('reviewer'); s=approve(c,prepare(c))
    admin=login('administrator')
    post(admin,'/api/auth/membership',{'user_id':ids['reviewer'],'roles':['auditor'],'active':True})
    second=login('second-reviewer')
    result=second.post('/api/cases/'+s['id']+'/apply',json=payload(s))
    assert result.status_code==409 and result.json()['detail']['code']=='REVOKED_APPROVAL'
    assert second.get('/api/cases/'+s['id']).json()['receipts']==[]


def test_cancelled_model_job_and_expired_worker_never_grant_review(pilot,monkeypatch):
    login,_=pilot; c=login('reviewer'); state=post(c,'/api/cases/demo')
    import threading
    entered=threading.Event(); release=threading.Event()
    original=module.extract
    def wait_model(docs,mode):
        entered.set(); assert release.wait(8)
        return original(docs,mode)
    monkeypatch.setattr(module,'extract',wait_model)
    doc=next(d for d in state['documents'] if 'supplier_notice' in d['filename'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(c.post,'/api/cases/'+state['id']+'/analyze',json={'document_id':doc['id'],'mode':'fixture'})
        assert entered.wait(5)
        job=c.get('/api/jobs').json()[-1]
        other=login('other-org')
        assert other.get('/api/jobs').json()==[]
        assert other.post('/api/jobs/'+job['id']+'/cancel',json={}).status_code==422
        cancelled=post(c,'/api/jobs/'+job['id']+'/cancel')
        assert cancelled['status']=='cancelled'
        release.set(); result=future.result().json()
    assert result['runs'][-1]['status']=='cancelled' and result['plan'] is None
    from backend import jobs
    with repo.write(module.connect) as db:
        owner='pilot:northstar:plant1'
        job=jobs.start(db,owner,'interrupted-worker','OCR',{},'fixture')
        job['lease_until']=0
        repo.put_record(db,owner,'job',job['id'],job)
    persisted=c.get('/api/jobs').json()
    assert next(j for j in persisted if j['id']=='interrupted-worker')['status']=='interrupted'
    with repo.write(module.connect) as db:
        assert not jobs.finish(db,owner,'interrupted-worker','succeeded','result')


def test_unsafe_backup_and_mismatched_content_rejected(tmp_path):
    import zipfile
    from scripts.pilot import read_backup
    bad=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(bad,'w') as z: z.writestr('../escaped','bad')
    with pytest.raises(ValueError,match='Unsafe'): read_backup(bad)
    bad=tmp_path/'changed.zip'
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr('manifest.json','{}'); z.writestr('manifest.sha256','wrong')
    with pytest.raises(ValueError,match='changed'): read_backup(bad)
