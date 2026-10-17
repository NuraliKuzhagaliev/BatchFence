"""One context-fix verification within the owner's 24 additional / 30 total cap.

This is a new bounded context, not an automatic retry. Preserve the original
semantic error and the v2 timeout. All sources and operated identities are synthetic.
"""
import json,os
from datetime import datetime,timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/enterprise/live/frozen'
load_dotenv(ROOT/'.env')
gate=json.loads((ROOT/'docs/enterprise/live/access-recheck.json').read_text())
assert gate['cost_gate']=='verified zero additional charge for shared event endpoint'
assert os.environ['AMD_API_BASE_URL'].rstrip('/')==gate['base_url'] and os.environ['AMD_MODEL_ID']==gate['requested_model_id']
paths=[ROOT/'docs/enterprise/live/fresh'/n for n in ('partial-raw.json','complete-raw.json','knowledge-raw.json','signal-raw.json')]
paths += [ROOT/'docs/enterprise/live/fresh/receiving-v2'/n for n in ('partial-raw.json','complete-raw.json')]
runs=[json.loads(p.read_text()) for p in paths]
runs += [json.loads(p.read_text())['run'] for p in OUT.glob('EXT-*.json')]
runs += [json.loads(p.read_text())['run'] for p in OUT.glob('KNW-*.json')]
runs += [json.loads((OUT/'signal-v2.json').read_text())]
unique={r.get('request_id') or r['id']:r for r in runs if r['mode']=='live'}
assert len(unique)==26 and len(unique)-6<24
reservation=OUT/'signal-v3-reservation.json'
assert not reservation.exists(),'Already reserved; no automatic retry'
private=json.loads((ROOT/'work/enterprise-live-frozen/private.json').read_text())
os.environ.update(DATABASE_PATH=str(ROOT/'work/enterprise-live-frozen/state.sqlite3'),SOURCE_STORAGE_PATH=str(ROOT/'work/enterprise-live-frozen/sources'),
    DEPLOYMENT_PROFILE='pilot',PILOT_DATABASE_URL='',PILOT_SESSION_SECRET=private['session_secret'],PILOT_AMD_DATA_APPROVED='true',PUBLIC_DEMO='false',LIVE_DEMO_TOKEN='',
    MAX_ORG_LIVE_JOBS='24',MAX_USER_LIVE_JOBS='24',MAX_REQUESTS_PER_MINUTE='1000',MAX_SESSION_REQUESTS_PER_MINUTE='1000')
def save(name,value):
    text=json.dumps(value,indent=2,ensure_ascii=False)
    assert os.environ['AMD_API_KEY'] not in text and private['password'] not in text
    (OUT/(name+'.json')).write_text(text,encoding='utf-8')
def quota(name):
    r=httpx.get(gate['base_url']+'/usage?include_recent=false',headers={'Authorization':'Bearer '+os.environ['AMD_API_KEY']},timeout=30,follow_redirects=False,trust_env=False)
    assert r.status_code==200
    d=r.json();assert d['daily_cost_remaining_usd']>.2
    save(name,{'at':datetime.now(timezone.utc).isoformat(),'remaining_points':d['daily_cost_remaining_usd'],'used_points':d['daily_cost_used_usd'],
        'today_requests':d['today']['requests'],'monetary_charge_usd':0,'unit_basis':'Authenticated event manual: points are not charges'})
quota('quota-before-v3')
from backend import app as module,signals
from fastapi.testclient import TestClient
from tests.test_api import post
c=TestClient(module.app)
post(c,'/api/auth/login',{'username':'frozen-reviewer','password':private['password'],'org':'frozen','site':'synthetic'})
old=json.loads((OUT/'signal-v2.json').read_text())
chart=next(r for r in c.get('/api/signals').json()['results'] if r['baseline']['id']==old['baseline_id'])
save('signal-v3-input',signals.explanation_context(chart['baseline'],chart['chart']))
save('signal-v3-reservation',{'at':datetime.now(timezone.utc).isoformat(),'owner_authorization':'Approve up to 24 additional free calls',
    'maximum_total':30,'maximum_additional':24,'prior_actual_dispatches':26,'this_dispatch_number':27,
    'reason':'Verify smaller exact-signal context after v2 timeout, retaining both prior outcomes; no automatic retries or further call in this script.'})
run=post(c,'/api/signals/explain',{'baseline_id':old['baseline_id'],'chart_digest':chart['chart_digest'],'mode':'live'})
save('signal-v3',run)
save('packet-after-signal-v3',c.get('/api/cases/'+private['case_id']+'/export').json())
quota('quota-after-v3')
print(json.dumps({k:run.get(k) for k in ('status','request_id','model_id','elapsed_ms','error_kind')}))
