"""Fresh public AMD ambiguity checks; extraction and agent review are separate steps."""
from pathlib import Path
from datetime import datetime, timezone
import base64,hashlib,json,os,sys,httpx
from dotenv import dotenv_values
from backend.domain import digest
ROOT=Path(__file__).resolve().parents[1]; suffix=os.getenv('BATCHFENCE_AMBIGUITY_RUN',''); assert not suffix or suffix.replace('-','').isalnum()
DEST=ROOT/('docs/cloud/ambiguity'+('-'+suffix if suffix else ''));DEST.mkdir(exist_ok=True)
BASE='https://batchfence.onrender.com';REPORT=DEST/'results.json';PRIVATE=ROOT/('work/cloud-ambiguity'+('-'+suffix if suffix else '')+'-session.json')
inputs=[
 {'name':'uncertain-involvement','text':'SYNTHETIC VERIFICATION DATA. QL-6304-P may have a coating defect.\nOur investigation has not determined whether UT-5529 is involved.\nThis supplier incident list is incomplete; the scope remains unresolved.',
  'affected':[],'uncertain':['QL-6304-P','UT-5529'],'excluded':[],'documented_units':0,'uncertain_units':1200},
 {'name':'confirmed-plus-pending','text':'SYNTHETIC VERIFICATION DATA. Coating failure is confirmed in QL-6304-P.\nUT-5529 is awaiting test results and has not been cleared.\nThe incident batch list is not final. CZ-8031 is expressly excluded from this incident.',
  'affected':['QL-6304-P'],'uncertain':['UT-5529'],'excluded':['CZ-8031'],'documented_units':400,'uncertain_units':800}]
if os.getenv('BATCHFENCE_AMBIGUITY_CASE'): inputs=[i for i in inputs if i['name']==os.environ['BATCHFENCE_AMBIGUITY_CASE']]
def now():return datetime.now(timezone.utc).isoformat()
def save(r):REPORT.write_text(json.dumps(r,indent=2),encoding='utf-8')
with httpx.Client(base_url=BASE,timeout=65) as c:
 def post(route,data):
  q=c.post(route,json=data);q.raise_for_status();return q.json()
 if sys.argv[1]=='extract':
  assert not REPORT.exists(), 'Preserve existing live results; no automatic retries'
  report={'at':now(),'url':BASE,'synthetic_inputs':True,'live_calls':0,'fallback_used':False,'independent_human_validation':False,'cases':[]}
  report['inputs']=[{**i,'sha256':hashlib.sha256(i['text'].encode()).hexdigest()} for i in inputs];save(report)
  c.headers['X-BF-Demo-Token']=dotenv_values(ROOT/'work/cloud-demo.env')['LIVE_DEMO_TOKEN']
  seed=json.loads((ROOT/'docs/cloud/live/input-packet.json').read_text(encoding='utf-8'))
  for i in inputs:
   s=post('/api/cases/import',seed);route='/api/cases/'+s['id']
   s=post(route+'/documents',{'filename':'supplier-message.txt','content_base64':base64.b64encode(i['text'].encode()).decode(),'synthetic':True});doc=s['documents'][-1]
   s=post(route+'/analyze',{'mode':'live','document_id':doc['id']});report['live_calls']+=1;run=s['runs'][-1]
   item={'name':i['name'],'case_id':s['id'],'source':doc,'raw_run':run,'before_review':{'scope':s['scope'],'plan':s['plan'],'receipts':s['receipts']},'review_status':'awaiting_agent_review'}
   proposed=sorted(f['lot_id'] for f in run.get('output',{}).get('facts',[]) if f['affected'])
   item['raw_quality']={'expected_confirmed':i['affected'],'proposed_true':proposed,'extra_confirmed':sorted(set(proposed)-set(i['affected'])),'missing_confirmed':sorted(set(i['affected'])-set(proposed)),'schema_limitation':'Boolean proposals cannot represent unresolved involvement; reviewed dispositions are separate.'}
   report['cases'].append(item);save(report);PRIVATE.write_text(json.dumps(dict(c.cookies)),encoding='utf-8');print(json.dumps(item,indent=2),flush=True)
 else:
  report=json.loads(REPORT.read_text(encoding='utf-8'));c.cookies.update(json.loads(PRIVATE.read_text(encoding='utf-8')))
  choices=json.loads((ROOT/('work/cloud-ambiguity'+('-'+suffix if suffix else '')+'-review.json')).read_text(encoding='utf-8'))
  for item,choice,truth in zip(report['cases'],choices,report['inputs'],strict=True):
   if item['review_status']=='agent_reviewed': continue
   assert choice['run_id']==item['raw_run']['id'] and choice['source_hash']==item['source']['original_hash']
   route='/api/cases/'+item['case_id'];s=c.get(route).json()
   body={'run_id':choice['run_id'],'revision':s['revision'],'lot_ids':choice['affected'],'uncertain_lot_ids':choice['uncertain'],'excluded_lot_ids':choice['excluded'],
    'incident_scope_status':'unresolved','accept_scope':True,'bounded_scope_reviewed':False,'note':choice['note']}
   if item['raw_run']['status']!='succeeded':
    blocked=c.post(route+'/reviews',json=body);assert blocked.status_code==422;assert s['plan'] is None and not s['receipts']
    item.update(review_status='blocked_failed_extraction',review_attempt={'status':blocked.status_code,'detail':blocked.json()['detail']});save(report);continue
   blocked=c.post(route+'/reviews',json={**body,'bounded_scope_reviewed':True});assert blocked.status_code==422 and blocked.json()['detail']['code']=='UNRESOLVED_SCOPE'
   item['unsupported_narrowing']={'status':blocked.status_code,'detail':blocked.json()['detail']}
   s=post(route+'/reviews',body);result=s['plan']['result'];assert (result['hold_units'],result['outside_units'],result['documented_units'],result['uncertain_units'])==(1200,0,truth['documented_units'],truth['uncertain_units'])
   p=s['plan'];post(route+'/approve',{'plan_id':p['id'],'digest':p['digest']})
   s=post(route+'/apply',{'plan_id':p['id'],'digest':p['digest'],'actions':p['actions'],'idempotency_key':'cloud-ambiguity-'+item['name']});assert sum(v['units'] for v in s['receipts'][-1]['changes'])==1200
   item.update(review_status='agent_reviewed',review=choice,result_after_review=result,receipt=s['receipts'][-1])
   packet=c.get(route+'/export').json();assert digest(packet['case'])==packet['integrity_hash'];(DEST/(item['name']+'-packet.json')).write_text(json.dumps(packet,indent=2),encoding='utf-8');save(report)
  report['completed_at']=now();report['review_method']='Codex inspected actual raw responses and exact sources before supplying dispositions. Not independent human validation.';save(report)
  print(json.dumps({'review_statuses':[x['review_status'] for x in report['cases']],'review_command_live_calls':0}))
