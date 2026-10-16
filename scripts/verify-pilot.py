"""Run actual PostgreSQL foundation checks in new isolated databases; print no secrets."""
import base64
import hashlib
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import psycopg
from psycopg import sql
from backend import repository as repo
from backend.identity import create_user
from scripts.pilot import backup,restore

ROOT=Path(__file__).resolve().parents[1]
private=json.loads((ROOT/'work/pilot-eval/private.json').read_text(encoding='utf-8'))
base=private['migration_url']; part=urlsplit(base)
suffix=uuid.uuid4().hex[:10]
database='bf_verify_'+suffix
restored_database='bf_restore_'+suffix
role='bf_app_'+suffix
password=secrets.token_urlsafe(32)
started=time.perf_counter()
with psycopg.connect(base,autocommit=True) as admin:
    admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
    for name in (database,restored_database): admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))

def migration_url(name): return urlunsplit((part.scheme,part.netloc,'/'+name,'',''))
def app_url(name): return f'postgresql://{role}:{password}@{part.hostname}:{part.port}/{name}'
for name in (database,restored_database):
    with repo.connect('',url=migration_url(name),migration=True) as db:
        db.raw.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
        for table in repo.TABLES:
            grants='SELECT' if table=='bf_schema' else 'SELECT,INSERT' if table=='bf_audit' else 'SELECT,INSERT,UPDATE,DELETE'
            db.raw.execute(sql.SQL('GRANT '+grants+' ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))

source_dir=ROOT/'work/pilot-eval'/('sources-'+suffix)
source_dir.mkdir()
os.environ.update(PILOT_DATABASE_URL=app_url(database),DEPLOYMENT_PROFILE='pilot',
                  PILOT_SESSION_SECRET=secrets.token_urlsafe(48),SOURCE_STORAGE_PATH=str(source_dir),
                  PUBLIC_DEMO='false',MAX_REQUESTS_PER_MINUTE='1000',MAX_SESSION_REQUESTS_PER_MINUTE='1000')
from backend import app as module
from fastapi.testclient import TestClient
from tests.test_api import post,prepare,approve,payload,review
user_password=secrets.token_urlsafe(24)
with repo.write(module.connect) as db:
    user=create_user(db,'pilot-reviewer',user_password,'northstar','plant1',['reporter','quality_reviewer'])

client=TestClient(module.app)
post(client,'/api/auth/login',{'username':'pilot-reviewer','password':user_password,'org':'northstar','site':'plant1'})
state=approve(client,prepare(client))
assert state['plan']['result']['hold_units']==500
state=post(client,f"/api/cases/{state['id']}/apply",payload(state))
old=payload(state)
state=post(client,f"/api/cases/{state['id']}/revision")
assert client.post(f"/api/cases/{state['id']}/apply",json={**old,'idempotency_key':'stale-key-postgres'}).status_code==409
state=approve(client,review(client,state,True))
assert state['plan']['result']['hold_units']==800
request=payload(state,'second-key-postgres')
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as pool:
    outcomes=list(pool.map(lambda _:client.post(f"/api/cases/{state['id']}/apply",json=request),range(2)))
assert all(r.status_code==200 for r in outcomes)
state=client.get('/api/cases/'+state['id']).json()
assert len(state['receipts'])==2
raw=b'Synthetic original source bytes for actual PostgreSQL restore verification.\r\n'
post(client,f"/api/cases/{state['id']}/documents",{'filename':'restore.txt','content_base64':base64.b64encode(raw).decode()})
packet=client.get('/api/cases/'+state['id']+'/export').json()
backup_path=ROOT/'work/pilot-eval'/('backup-'+suffix+'.zip')
with module.connect() as db:
    backup_report=backup(db,backup_path)
    try:
        db.execute('DELETE FROM bf_audit')
        raise AssertionError('Runtime role could delete audit')
    except psycopg.errors.InsufficientPrivilege: db.rollback()
    try:
        db.execute('CREATE TABLE forbidden_test(id INTEGER)')
        raise AssertionError('Runtime role could change schema')
    except psycopg.errors.InsufficientPrivilege: db.rollback()
restored_sources=ROOT/'work/pilot-eval'/('restored-sources-'+suffix)
with repo.connect('',url=app_url(restored_database)) as db:
    restore_report=restore(db,backup_path,restored_sources)
os.environ.update(PILOT_DATABASE_URL=app_url(restored_database),SOURCE_STORAGE_PATH=str(restored_sources))
fresh=TestClient(module.app)
assert fresh.get('/api/cases').status_code==401
post(fresh,'/api/auth/login',{'username':'pilot-reviewer','password':user_password,'org':'northstar','site':'plant1'})
assert fresh.get('/api/cases/'+state['id']+'/export').json()['case']==packet['case']
assert fresh.get('/api/sources/'+hashlib.sha256(raw).hexdigest()).content==raw
assert fresh.post('/api/cases/'+state['id']+'/apply',json={**request,'idempotency_key':'restored-stale-key'}).status_code==409
report={'timestamp':repo.now(),'profile':'real local PostgreSQL; synthetic records and agent-operated named identities',
        'server_version':None,'checks':['500 hold','800 revised hold','stale rejection','concurrent duplicate: two receipts total',
        'runtime cannot delete audit or create schema','database and source backup','isolated restored records byte-equivalent',
        'restored source hash','sessions excluded','restored stale execution rejected'],
        'backup':backup_report,'restore':restore_report,'duration_ms':round((time.perf_counter()-started)*1000),
        'rpo_rto':'Owner targets unset; same-device drill, not disaster recovery','independent_human_acceptance':False}
with psycopg.connect(base,autocommit=True) as db: report['server_version']=db.execute('SHOW server_version').fetchone()[0]
out=ROOT/'docs/enterprise/foundation-postgres.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
private.update(last_verification_database=database,last_restore_database=restored_database,last_runtime_role=role)
(ROOT/'work/pilot-eval/private.json').write_text(json.dumps(private),encoding='utf-8')
print(json.dumps(report,indent=2))
