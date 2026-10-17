"""Linux/shared persistence checks. Synthetic sources, no external inference."""
import base64,hashlib,json,os,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('BATCHFENCE_CONTAINER_BASE_URL','http://127.0.0.1:8803')
NAME=os.getenv('BATCHFENCE_CONTAINER_NAME','batchfence-continuation040rc1')
OUT=ROOT/'docs/continuation/container';OUT.mkdir(parents=True,exist_ok=True)

def main():
 c=httpx.Client(base_url=BASE,timeout=25);checks=[]
 def post(p,b=None):
  r=c.post(p,json=b or {});r.raise_for_status();return r.json()
 s=post('/api/cases/demo');route='/api/cases/'+s['id']
 def contain(s,doc,key):
  s=post(route+'/analyze',{'mode':'fixture','document_id':doc['id']});run=s['runs'][-1]
  s=post(route+'/reviews',{'run_id':run['id'],'revision':s['revision'],'lot_ids':[f['lot_id'] for f in run['output']['facts']],
   'accept_scope':True,'bounded_scope_reviewed':True,'incident_scope_status':'resolved','resolution_quote':doc['blocks'][0]['text'],'note':'Agent-operated synthetic container review; no independent human acceptance.'})
  p=s['plan'];s=post(route+'/approve',{'plan_id':p['id'],'digest':p['digest']})
  body={'plan_id':p['id'],'digest':p['digest'],'actions':p['actions'],'idempotency_key':key}
  s=post(route+'/apply',body);assert post(route+'/apply',body)['receipts']==s['receipts'];return s,body
 s,old=contain(s,next(d for d in s['documents'] if d['filename']=='supplier_notice_v1.txt'),'linux040-first')
 assert sum(x['units'] for x in s['stocks'] if x['status']=='held')==500
 s=post(route+'/revision');assert c.post(route+'/apply',json={**old,'idempotency_key':'linux040-stale'}).status_code==409
 s,_=contain(s,s['documents'][-1],'linux040-revised');assert sum(x['units'] for x in s['stocks'] if x['status']=='held')==800 and len(s['receipts'])==2
 checks.append('500 then800 applied through explicit review, two original receipts, idempotence and stale409')
 text='Il lotto SUP-001 potrebbe essere interessato. La completezza è sconosciuta.'
 s=post(route+'/documents',{'filename':'italiano.txt','content_base64':base64.b64encode(text.encode()).decode(),'synthetic':True,'evidence_language':'it'});d=s['documents'][-1]
 source={'document_id':d['id'],'block_id':d['blocks'][0]['id'],'quote':text}
 tr=post(route+'/translation',{'document_id':d['id'],'language':'it','segments':[{'source':source,'translation':'Lot SUP-001 may be affected. Completeness is unknown.'}],'provenance_reference':'Synthetic manual bilingual engineering regression','idempotency_key':'linux040-translation'})
 img=(ROOT/'evals/continuation/images/IMG-01.png').read_bytes()
 label=post(route+'/label-image',{'filename':'synthetic-label.png','content_base64':base64.b64encode(img).decode(),'crop_xywh':[10,10,680,280]})
 brief=post(route+'/handover',{'idempotency_key':'linux040-handover','previous_id':None})
 assert brief['snapshot']['quantities']['proposed_hold_units'] is None and brief['snapshot']['quantities']['applied_hold_units']==800
 checks.append('Linux bounded Pillow crop and original-linked Italian translation; stale proposal stays unknown, applied800 retained')
 before=c.get(route+'/assisted').json();receipts=s['receipts']
 subprocess.run(['docker','restart',NAME],check=True,capture_output=True)
 for _ in range(30):
  try:
   if c.get('/api/health').status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(1)
 saved=c.get(route).json();after=c.get(route+'/assisted').json()
 assert saved['receipts']==receipts and saved['stocks']==s['stocks']
 assert any(t['id']==tr['id'] for t in after['translation']) and any(h['id']==brief['id'] for h in after['handover'])
 assert next(x for x in after['label'] if x['id']==label['id'])['derived_hash']==label['derived_hash']
 original=c.get('/api/sources/'+label['original_hash']);original.raise_for_status();assert hashlib.sha256(original.content).hexdigest()==label['original_hash']
 other=httpx.Client(base_url=BASE);assert other.get(route).status_code==404 and other.get('/api/sources/'+label['original_hash']).status_code==404
 checks.append('Actual container restart preserves receipts, stock, translation, cropped-image hashes/bytes and handover; other session denied')
 packet=c.get(route+'/export').json();assert packet['case']['enterprise_packet']['handover']
 (OUT/'continuation-packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'checks':checks,'passed':True,'provider_calls':0,'native_dialogs':False,
  'review':'Agent-operated synthetic engineering review; no independent human/domain/language validation','container':NAME,'health':c.get('/api/health').json()}
 (OUT/'continuation-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
