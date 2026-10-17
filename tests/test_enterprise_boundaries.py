import copy
import hashlib
import pytest
from fastapi.testclient import TestClient
from backend import app as module,repository as repo,identity,onboarding,signals
from backend.domain import DomainError,digest
from tests.test_api import client,post,prepare,approve,payload
from tests.test_foundations import pilot
from tests.test_signals_knowledge import training


def test_source_rollback_removes_only_new_uncommitted_bytes(tmp_path,monkeypatch):
    monkeypatch.setenv('SOURCE_STORAGE_PATH',str(tmp_path/'sources'))
    factory=lambda:repo.connect(tmp_path/'data.sqlite3',url='')
    with repo.write(factory) as db:
        repo.save_source(db,'owner',b'preserved committed source')
    old=hashlib.sha256(b'preserved committed source').hexdigest()
    new=hashlib.sha256(b'aborted source').hexdigest()
    with pytest.raises(RuntimeError):
        with repo.write(factory) as db:
            repo.save_source(db,'owner',b'preserved committed source')
            repo.save_source(db,'owner',b'aborted source')
            raise RuntimeError('Force transaction rollback')
    assert repo.source_path('owner',old).read_bytes()==b'preserved committed source'
    assert not repo.source_path('owner',new).exists()
    with factory() as db:assert db.execute('SELECT count(*) FROM bf_sources').fetchone()[0]==1


@pytest.mark.parametrize('value',['2026-11-01T01:30:00','2026-03-08T02:30:00'])
def test_dst_ambiguity_and_missing_hour_require_offset(value):
    with pytest.raises(ValueError,match='explicit UTC offset'):onboarding.timestamp(value,'America/New_York')
    assert onboarding.timestamp('2026-11-01T01:30:00-05:00','America/New_York')=='2026-11-01T06:30:00+00:00'


def test_pilot_external_provider_requires_owner_consent(pilot,monkeypatch):
    login,_=pilot;c=login('reviewer');s=post(c,'/api/cases/demo')
    monkeypatch.delenv('PILOT_AMD_DATA_APPROVED',raising=False)
    def forbidden(*args,**kwargs):raise AssertionError('Provider must not be contacted without consent')
    monkeypatch.setattr(module,'extract',forbidden)
    result=c.post('/api/cases/'+s['id']+'/analyze',json={'document_id':s['documents'][0]['id'],'mode':'live'})
    assert result.status_code==403 and 'PILOT_AMD_DATA_APPROVED' in result.text
    assert c.get('/api/jobs').json()==[]


def test_module_snapshot_owner_isolation_and_packet_no_transfer(pilot):
    login,_=pilot;c=login('reviewer');state=training(c)
    route='/api/cases/'+state['id']
    data=c.get(route+'/modules').json()
    assert len(data['procedure'])==3 and len(data['inspections'][0]['rows'])==45
    for other in ('other-site','other-org'):
        assert login(other).get(route+'/modules').status_code==404
        assert login(other).get('/api/knowledge').json()['documents']==[]
    packet=c.get(route+'/export').json()
    assert packet['integrity_hash']==digest(packet['case'])
    # Even an edited, self-consistently hashed packet cannot import authority.
    packet['case'].update(procedure_checks=[{'status':'reviewed complete'}],recovery_receipts=[{'transaction_id':'invented'}],
                         quantities={'confirmed_recovery_units':100},origin_signal={'known_affected':['SUP-B']})
    packet['integrity_hash']=digest(packet['case'])
    promoted=post(c,'/api/cases/import',packet)
    assert not promoted.get('procedure_checks') and not promoted.get('origin_signal')
    assert not promoted.get('recovery_receipts')
    assert promoted['plan'] is None and promoted['scope']['lot_ids']==[]


def test_chart_explanation_fixture_is_labelled_and_has_no_inventory_authority(client):
    c=client;s=training(c);obs=c.get('/api/inspections').json()
    base=post(c,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in obs['rows'] if r['observation_id'].startswith('BASE-')],
        'inspection_revision':obs['revision'],'stable_reviewed':True,'note':'Agent reviewed disclosed synthetic baseline for an isolated engineering check.'})
    chart=c.get('/api/signals').json()['results'][0]
    result=post(c,'/api/signals/explain',{'baseline_id':base['id'],'chart_digest':chart['chart_digest'],'mode':'fixture'})
    assert result['mode']=='fixture' and result['model_id']=='synthetic-task-fixture'
    unchanged=c.get('/api/cases/'+s['id']).json()
    assert unchanged['plan'] is None and unchanged['receipts']==[]
    assert c.post('/api/signals/explain',json={'baseline_id':base['id'],'chart_digest':'0'*64,'mode':'fixture'}).status_code==422


def test_malformed_procedure_rejected_without_500(client):
    c=client
    for value in ({'id':'PROC'}, {'id':'PROC','version':'bad','status':'approved'}):
        response=c.post('/api/knowledge/procedure-review',json={'document':value,'reviewed':True,'note':'Testing malformed source metadata should be rejected.'})
        assert response.status_code==422


def test_public_simulation_is_explicit_and_logout_safe(client):
    assert client.post('/api/auth/simulate',json={'role':'preparer','acknowledge_simulation':False}).status_code==403
    result=post(client,'/api/auth/simulate',{'role':'preparer','acknowledge_simulation':True})
    assert result['identity_mode']=='simulated demonstration role'
    assert post(client,'/api/auth/logout')['signed_out']


def test_local_connector_rejects_unapproved_targets(monkeypatch):
    from backend.outbox import send
    monkeypatch.setenv('REFERENCE_CONNECTOR_TOKEN','synthetic-contract-token-'*3)
    for url in ('http://example.com','http://localhost:8799','http://127.0.0.1:8799/path','http://user:pass@127.0.0.1:8799','https://127.0.0.1:8799','http://169.254.169.254'):
        monkeypatch.setenv('REFERENCE_CONNECTOR_URL',url)
        with pytest.raises(DomainError):send({'operation_id':'test'})
