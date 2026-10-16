"""Prepare a synthetic receipt and later inspect storage after a real Render deploy.
Does not itself restart, delete, or infer. Cookies remain under ignored work/.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, sys, httpx
from backend.domain import digest
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/cloud'; PRIVATE=ROOT/'work/cloud-storage-session.json'
BASE='https://batchfence.onrender.com'
def now(): return datetime.now(timezone.utc).isoformat()
with httpx.Client(base_url=BASE,timeout=30) as c:
 def post(route,data):
  r=c.post(route,json=data); r.raise_for_status();return r.json()
 if sys.argv[1]=='before':
  assert not PRIVATE.exists(), 'Refusing to overwrite previous storage test'
  s=post('/api/cases/demo',{});route='/api/cases/'+s['id']
  d=next(d for d in s['documents'] if d['filename']=='supplier_notice_v1.txt')
  s=post(route+'/analyze',{'mode':'fixture','document_id':d['id']})
  s=post(route+'/reviews',{'run_id':s['runs'][-1]['id'],'revision':s['revision'],'lot_ids':['SUP-A'],
   'accept_scope':True,'bounded_scope_reviewed':True,'incident_scope_status':'resolved',
   'resolution_quote':'Affected lots: SUP-A','note':'Agent-operated synthetic storage check. The fixture provides a complete supplier boundary; no independent human validation.'})
  p=s['plan'];assert p['result']['hold_units']==500
  post(route+'/approve',{'plan_id':p['id'],'digest':p['digest']})
  s=post(route+'/apply',{'plan_id':p['id'],'digest':p['digest'],'actions':p['actions'],'idempotency_key':'free-storage-check'})
  packet=c.get(route+'/export').json();assert digest(packet['case'])==packet['integrity_hash']
  (DEST/'storage-test-packet.json').write_text(json.dumps(packet,indent=2),encoding='utf-8')
  PRIVATE.write_text(json.dumps({'case_id':s['id'],'cookies':dict(c.cookies)}),encoding='utf-8')
  report={'url':BASE,'before_at':now(),'provenance':'Synthetic fixture, agent-operated review; no live inference',
   'before_health':c.get('/api/health').json(),'case_id':s['id'],'receipt_ids':[r['transaction_id'] for r in s['receipts']],
   'held_units':sum(x['units'] for x in s['stocks'] if x['status']=='held'),'after_deploy_status':'pending'}
 else:
  private=json.loads(PRIVATE.read_text());c.cookies.update(private['cookies'])
  report=json.loads((DEST/'storage-results.json').read_text())
  r=c.get('/api/cases/'+private['case_id']); report.update(after_at=now(),after_health=c.get('/api/health').json(),after_case_status=r.status_code)
  packet=json.loads((DEST/'storage-test-packet.json').read_text());assert digest(packet['case'])==packet['integrity_hash']
  report['export_still_valid']=True
  report['after_deploy_status']='lost_as_documented' if r.status_code==404 else 'retained_in_this_observation_not_a_durability_guarantee'
  report['durable_cloud_persistence_verified']=False
 (DEST/'storage-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
