"""Finite original frozen-set evaluation, sequential, no automatic retries.

One item (KNW-01) already ran in the integrated workflow. Evaluate the other
23 exactly once; deterministic retrieval abstentions are not inference calls.
Also perform one isolated signal-context retest. All records are synthetic.
"""
import base64,hashlib,json,os,secrets,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/enterprise/live/frozen';OUT.mkdir(exist_ok=True)
PRIVATE=ROOT/'work/enterprise-live-frozen';PRIVATE.mkdir(exist_ok=True)
load_dotenv(ROOT/'.env')
gate=json.loads((ROOT/'docs/enterprise/live/access-recheck.json').read_text())
assert gate['followup_authorized'] and gate['cost_gate']=='verified zero additional charge for shared event endpoint'
assert os.environ['AMD_API_BASE_URL'].rstrip('/')==gate['base_url'] and os.environ['AMD_MODEL_ID']==gate['requested_model_id']
frozen=(ROOT/'evals/enterprise/frozen-v1.json').read_bytes()
assert hashlib.sha256(frozen).hexdigest()==json.loads((ROOT/'evals/enterprise/manifest.json').read_text())['sha256']
config=PRIVATE/'private.json'
if not config.exists():config.write_text(json.dumps({'session_secret':secrets.token_urlsafe(48),'password':secrets.token_urlsafe(32),'started_ids':[]}),encoding='utf-8')
private=json.loads(config.read_text())
os.environ.update(DATABASE_PATH=str(PRIVATE/'state.sqlite3'),SOURCE_STORAGE_PATH=str(PRIVATE/'sources'),DEPLOYMENT_PROFILE='pilot',
    PILOT_DATABASE_URL='',PILOT_SESSION_SECRET=private['session_secret'],PILOT_AMD_DATA_APPROVED='true',PUBLIC_DEMO='false',LIVE_DEMO_TOKEN='',
    MAX_ORG_LIVE_JOBS='24',MAX_USER_LIVE_JOBS='24',MAX_TOTAL_LIVE_RUNS='24',MAX_RUNS_PER_SESSION='12',MAX_REQUESTS_PER_MINUTE='1000',MAX_SESSION_REQUESTS_PER_MINUTE='1000')
from backend import app as module,repository as repo,identity
from fastapi.testclient import TestClient
from tests.test_api import post

def save(name,data):
    text=json.dumps(data,indent=2,ensure_ascii=False)
    assert os.environ['AMD_API_KEY'] not in text and private['password'] not in text
    (OUT/(name+'.json')).write_text(text,encoding='utf-8')

def allowance(group):
    r=httpx.get(gate['base_url']+'/usage?include_recent=false',headers={'Authorization':'Bearer '+os.environ['AMD_API_KEY']},timeout=30,follow_redirects=False,trust_env=False)
    assert r.status_code==200,'Cannot verify remaining event quota; no further model request'
    d=r.json();save('quota-'+str(group),{'at':datetime.now(timezone.utc).isoformat(),'remaining_points':d['daily_cost_remaining_usd'],'used_points':d['daily_cost_used_usd'],'today_requests':d['today']['requests'],'monetary_charge_usd':0,'unit_basis':'Authenticated event manual: points are not charges'})
    assert d['daily_cost_remaining_usd']>.2,'Preserve shared allowance headroom'

if 'case_id' not in private:
    with repo.write(module.connect) as db:identity.create_user(db,'frozen-reviewer',private['password'],'frozen','synthetic',['reporter','quality_reviewer'])
c=TestClient(module.app)
post(c,'/api/auth/login',{'username':'frozen-reviewer','password':private['password'],'org':'frozen','site':'synthetic'})
if 'case_id' not in private:
    s=post(c,'/api/cases/demo');s=post(c,'/api/enterprise/example',{'case_id':s['id'],'acknowledged_synthetic':True})
    private['case_id']=s['id'];config.write_text(json.dumps(private),encoding='utf-8')
route='/api/cases/'+private['case_id']
known=json.loads((ROOT/'docs/enterprise/live/fresh/knowledge-raw.json').read_text())
save('KNW-01',{'item':next(i for i in json.loads(frozen)['items'] if i['id']=='KNW-01'),'run':known,'provenance':'Original fresh integrated request reused for evaluation; no second request or independent holdout claim.'})
items=[i for i in json.loads(frozen)['items'] if i['id']!='KNW-01']
allowance('before')
for item in items:
    key=item['id']
    if (OUT/(key+'.json')).exists():continue
    assert key not in private['started_ids'],'Prior dispatch lacks a result; inspect manually, never automatically retry'
    assert len(private['started_ids'])<24
    if len(private['started_ids']) and len(private['started_ids'])%5==0:allowance(len(private['started_ids']))
    private['started_ids'].append(key);config.write_text(json.dumps(private),encoding='utf-8')
    if item['task']=='extraction':
        s=post(c,route+'/documents',{'filename':key+'-unseen-notice.txt','content_base64':base64.b64encode(item['text'].encode()).decode(),'synthetic':True})
        s=post(c,route+'/analyze',{'document_id':s['documents'][-1]['id'],'mode':'live'});run=s['runs'][-1]
    else:
        run=post(c,'/api/knowledge/answer',{'case_id':private['case_id'],'question':item['question'],
            'product':{'decorative-housings':'Decorative housing'}.get(item['product'],item['product']),'process':item['process'],'mode':'live'})
    save(key,{'item':item,'run':run,'provenance':'Unchanged frozen agent-authored synthetic label; actual application route. No human correction, approval or inventory action in this benchmark.'})
    print(json.dumps({'id':key,'status':run['status'],'mode':run['mode'],'elapsed_ms':run.get('elapsed_ms'),'request_id':run.get('request_id')}),flush=True)
    time.sleep(3.2)  # Shared key <=20 RPM; no retry or concurrency.
if not (OUT/'signal-v2.json').exists():
    assert 'SIGNAL-V2' not in private['started_ids'],'No automatic retry of signal dispatch'
    assert len(private['started_ids'])<24
    allowance('signal')
    obs=c.get('/api/inspections').json()
    baseline=post(c,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in obs['rows'] if r['observation_id'].startswith('BASE-')],
        'inspection_revision':obs['revision'],'stable_reviewed':True,'note':'Agent-operated synthetic baseline review for one bounded context-fix verification.'})
    chart=c.get('/api/signals').json()['results'][0]
    save('signal-v2-input',chart)
    private['started_ids'].append('SIGNAL-V2');config.write_text(json.dumps(private),encoding='utf-8')
    run=post(c,'/api/signals/explain',{'baseline_id':baseline['id'],'chart_digest':chart['chart_digest'],'mode':'live'})
    save('signal-v2',run);print(json.dumps({'id':'SIGNAL-V2','status':run['status'],'elapsed_ms':run.get('elapsed_ms')}),flush=True)
allowance('after')
save('packet',c.get(route+'/export').json())
print('Frozen set dispatched once; inspect every raw result before scoring or promotion.',flush=True)
