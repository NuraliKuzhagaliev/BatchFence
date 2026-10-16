"""Actual local PostgreSQL, loopback connector restart, restore and legacy migration."""
import base64,hashlib,json,os,secrets,socket,sqlite3,subprocess,sys,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from concurrent.futures import ThreadPoolExecutor
import httpx,psycopg
from psycopg import sql
from backend import repository as repo
from backend.identity import create_user
from scripts.pilot import backup,restore
ROOT=Path(__file__).resolve().parents[1];private=json.loads((ROOT/'work/pilot-eval/private.json').read_text());base=private['migration_url'];part=urlsplit(base);suffix=uuid.uuid4().hex[:10]
names=['bf_modules_'+suffix,'bf_modules_restore_'+suffix,'bf_legacy_'+suffix];role='bf_modules_'+suffix;password=secrets.token_urlsafe(32)
def admin_url(name):return urlunsplit((part.scheme,part.netloc,'/'+name,'',''))
def app_url(name):return f'postgresql://{role}:{password}@{part.hostname}:{part.port}/{name}'
with psycopg.connect(base,autocommit=True) as admin:
    admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
    for name in names:admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
for name in names:
    with repo.connect('',url=admin_url(name),migration=True) as db:
        db.raw.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
        for table in repo.TABLES:
            grants='SELECT' if table=='bf_schema' else 'SELECT,INSERT' if table=='bf_audit' else 'SELECT,INSERT,UPDATE,DELETE'
            db.raw.execute(sql.SQL('GRANT '+grants+' ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
folder=ROOT/'work/pilot-eval'/('modules-'+suffix);folder.mkdir()
os.environ.update(PILOT_DATABASE_URL=app_url(names[0]),DEPLOYMENT_PROFILE='pilot',PILOT_SESSION_SECRET=secrets.token_urlsafe(48),
    SOURCE_STORAGE_PATH=str(folder/'sources'),PUBLIC_DEMO='false',MAX_REQUESTS_PER_MINUTE='2000',MAX_SESSION_REQUESTS_PER_MINUTE='1000')
from backend import app as module
from fastapi.testclient import TestClient
from tests.test_recovery import prepared_recovery
from tests.test_api import post
user_password=secrets.token_urlsafe(24)
with repo.write(module.connect) as db:
    for name,roles in [('reviewer',['reporter','quality_reviewer']),('releaser',['release_approver'])]:create_user(db,name,user_password,'northstar','plant1',roles)
def login(name):
    c=TestClient(module.app);post(c,'/api/auth/login',{'username':name,'password':user_password,'org':'northstar','site':'plant1'});return c
c,state,proposal,proof=prepared_recovery(login);r=login('releaser');body={'recovery_id':proposal['id'],'digest':proposal['digest']};post(r,'/api/recovery/release-approve',body)
item=post(r,'/api/recovery/connector-enqueue',{**body,'idempotency_key':'actual-loopback-recovery'})
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
token=secrets.token_urlsafe(40);os.environ.update(REFERENCE_CONNECTOR_URL=f'http://127.0.0.1:{port}',REFERENCE_CONNECTOR_TOKEN=token,REFERENCE_DATABASE_PATH=str(folder/'connector.sqlite3'))
failed=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']});assert failed['status']=='failed_ack'
assert c.get('/api/cases/'+state['id']).json()['quantities']['applied_hold_units']==800
log=(folder/'connector.log').open('wb')
def launch():
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','backend.reference_connector:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(40):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):return proc
        except OSError:time.sleep(.1)
    proc.terminate();proc.wait(timeout=10);raise RuntimeError('Reference connector failed to start')
process=launch();first_pid=process.pid
try:confirmed=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']});assert confirmed['status']=='acknowledged'
finally:process.terminate();process.wait(timeout=10)
process=launch();second_pid=process.pid
try:
    ack=httpx.post(os.environ['REFERENCE_CONNECTOR_URL']+'/inventory/restrictions',json=item['payload'],headers={'Authorization':'Bearer '+token},timeout=8).json()
    assert ack==confirmed['receipt']['connector_acknowledgement']
    duplicate=post(r,'/api/recovery/connector-dispatch',{'operation_id':item['id']});assert duplicate==confirmed
finally:process.terminate();process.wait(timeout=10);log.close()
route='/api/cases/'+state['id'];current=c.get(route).json();assert current['quantities']=={'applied_hold_units':700,'recovery_pending_units':0,'confirmed_recovery_units':100}
assert current['receipts']==state['receipts'] and len(current['recovery_receipts'])==1
packet=c.get(route+'/export').json();archive=folder/'backup.zip'
with module.connect() as db:backup_report=backup(db,archive)
with repo.connect('',url=app_url(names[1])) as db:restore_report=restore(db,archive,folder/'restored-sources')
os.environ.update(PILOT_DATABASE_URL=app_url(names[1]),SOURCE_STORAGE_PATH=str(folder/'restored-sources'))
assert TestClient(module.app).get(route).status_code==401
restored=login('reviewer');saved=restored.get(route+'/export').json()
for value in (packet,saved):value['case']['enterprise_packet'].pop('snapshot_at')
assert packet['case']==saved['case']
assert restored.get(route).json()['recovery_receipts']==current['recovery_receipts']
assert login('releaser').post('/api/recovery/recovery-execute',json={**body,'idempotency_key':'post-restore-repeat'}).status_code==422
# Real legacy SQLite-to-PostgreSQL CLI migration with no owner/identity conversion.
legacy=json.loads((ROOT/'docs/verified-decision-packet.json').read_text(encoding='utf-8'))['case'];legacy_path=folder/'legacy.sqlite3'
with sqlite3.connect(legacy_path) as db:
    db.execute('CREATE TABLE cases(id TEXT PRIMARY KEY,owner TEXT NOT NULL,state TEXT NOT NULL)');db.execute('CREATE TABLE receipts(owner TEXT,key TEXT,request_digest TEXT,receipt TEXT,PRIMARY KEY(owner,key))');db.execute('PRAGMA user_version=1')
    db.execute('INSERT INTO cases VALUES(?,?,?)',(legacy['id'],'historical-anonymous-owner',json.dumps(legacy)))
    for rec in legacy['receipts']:db.execute('INSERT INTO receipts VALUES(?,?,?,?)',('historical-anonymous-owner',rec['transaction_id'],'historical-preserved',json.dumps(rec)))
env=os.environ.copy();env['PILOT_DATABASE_URL']=app_url(names[2]);command=[sys.executable,'-m','scripts.pilot','migrate-sqlite','--sqlite-source',str(legacy_path)]
migration=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=30,check=True)
with repo.connect('',url=app_url(names[2])) as db:
    row=db.execute('SELECT owner,state FROM cases').fetchone();assert row[0]=='historical-anonymous-owner' and json.loads(row[1])==legacy
    assert db.execute('SELECT count(*) FROM bf_members').fetchone()[0]==0
report={'at':repo.now(),'provenance':'Actual local PostgreSQL and separate loopback HTTP connector processes; synthetic records and agent-operated named test accounts',
    'checks':['500 then 800 containment','natural typed review: 700 proposed with 800 applied','distinct named release approval','actual connection-refused acknowledgement retains 800','explicit retry over loopback HTTP confirms exact 100','connector process restart returns same persisted acknowledgement','duplicate dispatch returns same receipt','original containment receipts unchanged','isolated database+source restore retains exact module snapshots and recovery receipts','sessions excluded from restore','post-restore repeated recovery rejected','actual legacy SQLite-to-Postgres CLI migration preserves anonymous owner and receipt JSON'],
    'connector':{'port':port,'first_pid':first_pid,'restarted_pid':second_pid,'attempts':confirmed['attempts'],'execution':'LOCAL SANDBOX REFERENCE'},'backup':backup_report,'restore':restore_report,'legacy_migration':json.loads(migration.stdout),'limits':'Same-device restore, not disaster recovery. Owner RPO/RTO unset. No real enterprise connector or physical stock action.'}
(ROOT/'docs/enterprise/modules-postgres.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
