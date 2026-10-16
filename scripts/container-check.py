"""CI container integration: dynamic port, exact workflow, real Docker restart."""
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, time, os
import httpx

base='http://127.0.0.1:8795'
report={'at':datetime.now(timezone.utc).isoformat(), 'mode':'fixture', 'live_inference':False, 'checks':[]}

def wait():
    for _ in range(45):
        try:
            r=httpx.get(base+'/api/health',timeout=2)
            if r.status_code==200: return
        except httpx.HTTPError: pass
        time.sleep(1)
    raise RuntimeError('Container health did not become ready')

try:
    wait()
    c=httpx.Client(base_url=base,timeout=20)
    def post(path,data=None):
        r=c.post(path,json=data or {}); r.raise_for_status(); return r.json()
    s=post('/api/cases/demo'); path='/api/cases/'+s['id']
    def review(s,doc):
        s=post(path+'/analyze',{'mode':'fixture','document_id':doc['id']})
        run=s['runs'][-1]; assert run['status']=='succeeded'
        return post(path+'/reviews',{'run_id':run['id'],'revision':s['revision'],
            'lot_ids':[f['lot_id'] for f in run['output']['facts']], 'accept_scope':True,
            'bounded_scope_reviewed':True,'incident_scope_status':'resolved',
            'resolution_quote':next(b['text'] for b in doc['blocks'] if b['text'].startswith('Affected lots:')),
            'note':'Automated synthetic CI review; not independent human validation.'})
    s=review(s,next(d for d in s['documents'] if 'supplier_notice' in d['filename']))
    assert s['plan']['result']['hold_units']==500
    p=s['plan']; s=post(path+'/approve',{'plan_id':p['id'],'digest':p['digest']})
    old={'plan_id':p['id'],'digest':p['digest'],'actions':p['actions'],'idempotency_key':'ci-stale-approval'}
    s=post(path+'/revision'); assert c.post(path+'/apply',json=old).status_code==409
    s=review(s,s['documents'][-1]); assert s['plan']['result']['hold_units']==800
    p=s['plan']; s=post(path+'/approve',{'plan_id':p['id'],'digest':p['digest']})
    s=post(path+'/apply',{'plan_id':p['id'],'digest':p['digest'],'actions':p['actions'],'idempotency_key':'ci-real-receipt'})
    receipts=s['receipts']; assert len(receipts)==1
    other=httpx.Client(base_url=base)
    assert other.get(path).status_code==404
    report['checks']+=['dynamic PORT=8795','500 to 800 synthetic workflow','stale approval rejected','sandbox receipt','two-session isolation']
    subprocess.run(['docker','restart','batchfence-ci'],check=True,capture_output=True)
    wait(); saved=c.get(path).json()
    assert saved['receipts']==receipts and saved['stocks']==s['stocks']
    report['checks'].append('same SQLite volume survives actual container restart')
    assert c.get('/workspace/review',headers={'Accept':'text/html'}).status_code==200
    assert c.get('/api/missing').status_code==404
    report['checks'].append('SPA refresh and missing API routing')
    report['passed']=True
except Exception as e:
    report['passed']=False; report['failure_type']=type(e).__name__
    raise
finally:
    out=Path(os.getenv('BATCHFENCE_CONTAINER_REPORT_DIR','docs/cloud'));out.mkdir(parents=True,exist_ok=True)
    (out/'container-results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
