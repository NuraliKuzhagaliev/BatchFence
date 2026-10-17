"""Frozen local acceptance contracts. Zero network/model calls; all review is agent-operated."""
import base64,copy,hashlib,io,json,math,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from backend import app as module,repository as repo,signals,knowledge,assisted,identity,jobs,evolus_adapter as external,effectiveness,label_images
from backend.domain import DomainError,digest,calculate
from backend.fixtures import document,load_demo
from backend.scope_proposals import validate_proposals,parse_json
from backend.public_demo import RequestLimiter
from tests.test_api import post,review,approve,payload
from tests.test_continuation import upload,ref
from tests.test_hardening_regressions import row

ROOT=Path(__file__).resolve().parents[1];MANIFEST=ROOT/'evals/hardening-v1/manifest.json'
DATA=json.loads(MANIFEST.read_text(encoding='utf-8'))
NOTE='Agent-operated synthetic hardening acceptance; not independent human/domain/language validation.'

@pytest.fixture
def local(tmp_path,monkeypatch):
 monkeypatch.setattr(module,'DB',tmp_path/'case.sqlite');monkeypatch.setenv('SOURCE_STORAGE_PATH',str(tmp_path/'sources'))
 monkeypatch.setenv('DEPLOYMENT_PROFILE','local');monkeypatch.setenv('PUBLIC_DEMO','false');monkeypatch.setenv('LIVE_DEMO_TOKEN','')
 monkeypatch.setenv('MAX_REQUESTS_PER_MINUTE','5000');monkeypatch.setenv('MAX_SESSION_REQUESTS_PER_MINUTE','1000');monkeypatch.setattr(module,'limiter',RequestLimiter())
 for k in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY','PILOT_DATABASE_URL'):monkeypatch.delenv(k,raising=False)
 return TestClient(module.app),tmp_path,monkeypatch

def applied(c):
 s=approve(c,review(c,post(c,'/api/cases/demo')));return post(c,'/api/cases/'+s['id']+'/apply',payload(s,'retained-baseline-receipt'))

def procedure():
 d={'id':'ACME-Q24','version':2,'status':'approved','valid_from':'2026-01-01T00:00:00Z','valid_to':None,'products':['Blue bracket'],'processes':['paint'],'owner':'Synthetic quality owner','passages':[{'id':'P3','text':'Inspect all 73 pieces before requesting recovery. FOOTNOTE: this does not authorize release; a separate approver and acknowledgement are required.','page':2}],'synthetic':True}
 d['source_hash']=digest(d['passages']);return d

def image_body():
 b=io.BytesIO();Image.new('RGB',(160,90),'white').save(b,format='PNG');return {'filename':'local-synthetic.png','content_base64':base64.b64encode(b.getvalue()).decode(),'crop_xywh':[]}

def ingest(c,x,expected):
 s=applied(c);route='/api/cases/'+s['id'];raw=x['text'].encode('utf-8')
 r=c.post(route+'/documents',json={'filename':x['filename'],'content_base64':base64.b64encode(raw).decode(),'synthetic':True})
 if expected=='reject':assert r.status_code in (413,422);assert c.get(route).json()==s
 else:
  assert r.status_code==200,r.text;out=r.json();d=out['documents'][-1]
  assert d['original_hash']==hashlib.sha256(raw).hexdigest() and out['receipts']==s['receipts']
  assert c.get('/api/sources/'+d['original_hash']).content==raw
  if x['filename'].lower().endswith('.csv'):assert len(d['blocks'])==2
  # A completed action remains historically applied; pending_revision rejects
  # reuse. Marking a physical historical action undone would be incorrect.
  assert out['pending_revision'] and out['plan']['status']=='applied'
  assert c.post(route+'/apply',json={**payload(s,'old-plan-after-source'),'idempotency_key':'old-plan-after-source'}).status_code==409

def proposal(x,expected):
 d=document('source-new.txt',x['text'].encode());e={'document_id':d['id'],'block_id':d['blocks'][0]['id'],'quote':x['text']}
 p={'facts':[{'lot_id':x['lot'],'kind':x['kind'],'status':x['status'],'evidence':[e]}],'qualifiers':[],'scope_status':x['scope'],'scope_evidence':[e] if x['scope']=='complete' else []}
 if expected=='reject':
  with pytest.raises(ValueError):validate_proposals(p,[d])
 else:assert validate_proposals(p,[d])['facts'][0]['status']==x['status']

def knowledge_case(op,x,expected):
 d=procedure();mode=x.get('mode')
 if op=='knowledge_metadata':
  f=x['field']
  if f=='page':d['passages'][0]['page']=x['value'];d['source_hash']=digest(d['passages'])
  elif f=='duplicate_passage':d['passages']*=2;d['source_hash']=digest(d['passages'])
  else:d[f]=x['value']
  with pytest.raises(DomainError):knowledge.validate_document(d)
 elif op=='knowledge_retrieve':
  docs=[d]
  if mode in ('draft','obsolete'):d['status']=mode
  if mode=='wrong-product':d['products']=['Red housing']
  if mode=='wrong-process':d['processes']=['weld']
  if mode=='future':d['valid_from']='2035-01-01T00:00:00Z'
  if mode=='expired':d['valid_to']='2026-02-01T00:00:00Z'
  if mode=='overlap':docs.append({**copy.deepcopy(d),'version':3})
  out=knowledge.retrieve(docs,'Which pieces must we inspect before recovery?','Blue bracket','paint',True,datetime(2026,10,18,tzinfo=timezone.utc))
  assert out['status']==('retrieved' if expected=='retrieve' else 'insufficient')
  if expected=='retrieve':assert out['passages'][0]['quote']==d['passages'][0]['text']
 else:
  r=knowledge.retrieve([d],'inspect recovery','Blue bracket','paint',True);claim={k:r['passages'][0][k] for k in ('document_id','version','passage_id','quote')}
  if mode=='changed-quote':claim['quote']='Release all stock now.'
  if mode=='missing-footnote':claim['quote']=claim['quote'].split(' FOOTNOTE')[0]
  if mode=='wrong-version':claim['version']=1
  if mode=='wrong-document':claim['document_id']='OTHER-ORG'
  if mode=='wrong-passage':claim['passage_id']='P9'
  raw={'claims':[] if mode=='empty-success' else [claim],'insufficient_evidence':mode=='explicit-abstention','missing_information':[]}
  if expected=='reject':
   with pytest.raises(DomainError):knowledge.validate_answer(raw,r)
  else:assert bool(knowledge.validate_answer(raw,r)['claims'])==(expected=='answer')

def statistics(x,expected):
 mode=x['mode'];a=row('A','2026-01-01T00:00:00Z',1000,100);b=row('B','2026-01-02T00:00:00Z',3000,300);f=row('F','2026-01-03T00:00:00Z',400,40);policy={'min_observations':2,'min_inspected':1000,'min_expected':5,'sigma':3}
 if mode in ('missing-followup','no-implementation','changed-regime'):
  plan=effectiveness.freeze_plan([a,b],['A','B'],{k:a[k] for k in signals.GROUP},'2030-01-01T00:00:00Z','2030-03-01T00:00:00Z',1000,2,.05,True)
  rows=[a,b]
  if mode!='missing-followup':rows += [row('FOLLOW-1','2030-01-03T00:00:00Z',1000,0),row('FOLLOW-2','2030-01-04T00:00:00Z',1000,0)]
  if mode=='changed-regime':rows[-1]['regime']='changed'
  result=effectiveness.evaluate({'plan':plan,'implementation':None if mode=='no-implementation' else {'record':'synthetic proof'}},rows,datetime(2030,3,2,tzinfo=timezone.utc))
  assert result['status']=='inconclusive' and result['reasons'];return
 if mode=='weighted':b['nonconforming']=150
 if mode=='unequal-n-limits':f.update(inspected=900,nonconforming=90)
 if mode=='high':f['nonconforming']=80
 if mode=='low':f['nonconforming']=0
 if mode=='zero-denominator':a['inspected']=0
 if mode=='above-denominator':a['nonconforming']=1001
 if mode=='boolean-count':a['nonconforming']=True
 if mode=='wrong-metric':a['metric']='defect_count'
 if mode=='mixed-method':b['method']='different'
 if mode=='duplicate-id':b['observation_id']='A'
 if mode=='zero-baseline':a['nonconforming']=b['nonconforming']=0
 if mode=='all-bad-baseline':a['nonconforming']=1000;b['nonconforming']=3000
 if mode=='sparse':a['nonconforming']=1;b['nonconforming']=3
 if mode=='timezone-order':a['event_time']='2026-01-01T03:00:00+02:00';b['event_time']='2026-01-01T00:00:00Z';f['event_time']='2026-01-01T01:00:00-01:00'
 if expected=='reject':
  with pytest.raises(DomainError):signals.freeze([a,b],['A','B'],policy)
  return
 baseline=signals.freeze([a,b],['A','B'],policy);rows=[a,b,f]
 if mode=='backfill':rows.append(row('LATE','2026-01-01T12:00:00Z'))
 if mode=='correction':rows[0]={**a,'nonconforming':101}
 result=signals.chart(baseline,rows)
 if expected=='invalidated':assert result['status']=='invalidated';return
 if expected=='inconclusive':assert result['status']=='insufficient';return
 assert result['status']=='ready';assert result['p_bar']==(.0625 if mode=='weighted' else .1)
 point=result['points'][0];assert point['observation_id']=='F'
 if mode=='unequal-n-limits':assert point['lower']==pytest.approx(.07) and point['upper']==pytest.approx(.13)
 if mode in ('high','low'):assert result['alerts']==['F']
 if mode=='within':assert result['alerts']==[]

def planning(x,expected):
 mode=x['mode'];stocks=[{'id':k,'units':n,'unit_cents':c,'status':'available','complete':True,'site':'BR-2','product_family':'Blue bracket'} for k,n,c in [('PAL-001',73,219),('PAL-002',41,170),('PAL-003',29,320)]]
 edges=[{'source':s,'target':t,'kind':'confirmed'} for s,t in [('RM-0007','PAL-001'),('RM-X','PAL-002'),('RM-Z','PAL-003')]]
 allocations=[{'row_id':'A1','order_id':'ORD-900','pool_id':'PAL-001','units':40,'due_date':'2030-01-01','status':'open'}];seeds=['RM-0007'];uncertain=[];bounded=True
 expected_units={'direct':73,'split':86,'merge':73,'diamond':73,'possible-edge':73,'unrelated-possible':114,'missing-parent':114,'incomplete-flag':114,'unknown-seed':143,'unbounded':143,'shipped':0,'already-held':73,'zero-stock':0,'duplicate-path':73,'multiple-seeds':114,'uncertain-seed':114}.get(mode)
 if mode=='split':stocks.append({**stocks[0],'id':'PAL-004','units':13});edges.append({'source':'RM-0007','target':'PAL-004','kind':'confirmed'})
 if mode in ('merge','diamond'):
  edges=edges[1:]+([{'source':s,'target':t,'kind':'confirmed'} for s,t in ([('RM-0007','MIX'),('RM-X','MIX'),('MIX','PAL-001')] if mode=='merge' else [('RM-0007','N1'),('RM-0007','N2'),('N1','N3'),('N2','N3'),('N3','PAL-001')])])
 if mode=='possible-edge':edges[0]['kind']='possible'
 if mode=='unrelated-possible':edges.append({'source':'RM-Z','target':'PAL-002','kind':'possible'})
 if mode=='missing-parent':edges.pop(1)
 if mode=='incomplete-flag':stocks[1]['complete']=False
 if mode=='unknown-seed':seeds=['UNREGISTERED']
 if mode=='unbounded':bounded=False
 if mode=='shipped':stocks[0]['status']='shipped'
 if mode=='already-held':stocks[1]['status']='held'
 if mode=='zero-stock':stocks[0]['units']=0;allocations=[]
 if mode=='duplicate-path':edges.append(copy.deepcopy(edges[0]))
 if mode=='multiple-seeds':seeds.append('RM-X')
 if mode=='uncertain-seed':uncertain=['RM-X']
 if mode=='cycle':edges += [{'source':'RM-0007','target':'NODE','kind':'confirmed'},{'source':'NODE','target':'RM-0007','kind':'confirmed'}]
 if mode=='dangling':edges.append({'source':'RM-0007','target':'MISSING','kind':'confirmed'})
 if mode=='terminal-reused':edges.append({'source':'PAL-001','target':'PAL-002','kind':'confirmed'})
 if mode=='allocation-overflow':allocations[0]['units']=74
 if mode=='negative-stock':stocks[0]['units']=-1
 if mode=='boolean-stock':stocks[0]['units']=True
 if mode=='duplicate-stock':stocks.append(copy.deepcopy(stocks[0]))
 if mode=='duplicate-allocation':allocations*=2
 before=copy.deepcopy((stocks,edges,allocations))
 if expected=='reject':
  with pytest.raises(DomainError):calculate(stocks,edges,seeds,allocations,bounded,uncertain)
 else:
  result=calculate(stocks,edges,seeds,allocations,bounded,uncertain);assert result['hold_units']==expected_units
  # Hand-worked physical pool sums above; no production-generated oracle.
  assert len({r['id'] for r in result['rows']})==len(stocks)
 assert (stocks,edges,allocations)==before

def sequence(c,x):
 mode=x['mode'];s=post(c,'/api/cases/demo');route='/api/cases/'+s['id']
 if mode=='unfamiliar-full-flow':
  # Reuse the reviewed import API, not fixture filename interpretation. Source
  # identities are unrelated; a simulated extraction is explicitly injected.
  text='Affected lots: SUP-Z9. The complete incident list is SUP-Z9.';s=upload(c,s,text,'unfamiliar-source.txt')
  # Existing source review can add exact source-backed IDs even when a draft
  # omits them. Missing genealogy must remain conservative (all1430 on-site).
  s=post(c,route+'/analyze',{'document_id':s['documents'][-1]['id'],'mode':'fixture'})
  s=post(c,route+'/reviews',{'run_id':s['runs'][-1]['id'],'revision':s['revision'],'lot_ids':['SUP-Z9'],'accept_scope':True,'bounded_scope_reviewed':True,'incident_scope_status':'resolved','resolution_quote':text,'note':NOTE})
  assert s['plan']['result']['hold_units']==sum(p['units'] for p in s['stocks'] if p['status']!='shipped')
 else:s=review(c,s)
 s=approve(c,s);old=payload(s,'first-exact-effect');s=post(c,route+'/apply',old);receipts=copy.deepcopy(s['receipts'])
 if mode=='duplicate-apply':assert post(c,route+'/apply',old)['receipts']==receipts
 elif mode=='source-failure-after-receipt':
  assert c.post(route+'/documents',json={'filename':'bad.csv','content_base64':base64.b64encode(b'x,x\n1,2').decode()}).status_code==422
  assert c.get(route).json()['receipts']==receipts
 else:
  s=upload(c,s,'Superseding source: incident extent unknown.','changed-source.txt')
  assert c.post(route+'/apply',json={**old,'idempotency_key':'stale-other-key'}).status_code==409
  assert s['receipts']==receipts and s['pending_revision']

def label(c,x,expected,tmp):
 mode=x['mode'];reading={'candidates':['LOT-004'],'unresolved_characters':[],'unreadable':False}
 if mode=='leading-zero':reading['candidates']=['LOT-00004']
 if mode=='O-zero':reading.update(candidates=['LOT-00O4'],unresolved_characters=['O/0'])
 if mode=='multiple':reading['candidates']=['LOT-004','LOT-005']
 if mode=='unreadable':reading.update(candidates=[],unreadable=True)
 if mode=='unreadable-with-candidate':reading['unreadable']=True
 if mode=='duplicate-candidates':reading['candidates']*=2
 if mode=='newline-candidate':reading['candidates']=['LOT-\n004']
 if mode=='oversize-candidate':reading['candidates']=['X'*161]
 if mode in ('unreadable-with-candidate','duplicate-candidates','newline-candidate','oversize-candidate'):
  with pytest.raises(ValueError):label_images.validate_reading(reading)
  return
 assert label_images.validate_reading(reading)==reading
 s=load_demo();spelling={'prefix-mismatch':'LOT-0049','suffix-mismatch':'LOT-004-B','different-case':'lot-004'}.get(mode,reading['candidates'][0] if reading['candidates'] else 'LOT-004')
 d=document('association.txt',('Original lot '+spelling+'.').encode());s['documents'].append(d)
 with repo.write(lambda:repo.connect(tmp/'labels.sqlite',url='')) as db:
  repo.put_record(db,'owner','label','L',{'id':'L','case_id':s['id'],'reading':reading},0)
  if mode in ('O-zero','multiple','unreadable','prefix-mismatch','suffix-mismatch','different-case'):
   with pytest.raises(DomainError):label_images.review_label(db,'owner',s,'L',d['id'],d['blocks'][0]['text'],reading['candidates'][0] if reading['candidates'] else '',True,True,False,NOTE)
  else:assert label_images.review_label(db,'owner',s,'L',d['id'],d['blocks'][0]['text'],reading['candidates'][0],True,True,False,NOTE)['review']

def change_handover(c,x,expected):
 mode=x['mode'];s=applied(c);route='/api/cases/'+s['id'];brief=post(c,route+'/handover',{'idempotency_key':'frozen-handover','previous_id':None})
 snapshot=brief['snapshot'];raw={'statements':[{'fact_id':f['id'],'text':f['text']} for f in snapshot['facts'][:5]]}
 if mode=='invented-quantity':raw['statements'][0]['text']='Proposed 1 unit; applied 0.'
 if mode=='missing-required':raw['statements'].pop()
 if mode=='unknown-fact':raw['statements'][0]['fact_id']='unauthorized-fact'
 if mode=='null-statement':raw['statements'][0]=None
 if mode=='array-fact-id':raw['statements'][0]['fact_id']=[]
 if mode=='extra-statement-field':raw['statements'][0]['approve']=True
 if expected=='reject':
  with pytest.raises(DomainError):assisted.validate_handover(snapshot,raw)
  assert c.get(route).json()['receipts']==s['receipts'];return
 if mode=='exact-handover':assert assisted.validate_handover(snapshot,raw);return
 if mode=='no-new-events':
  nxt=post(c,route+'/handover',{'idempotency_key':'next-shift-snapshot','previous_id':brief['id']});assert nxt['snapshot']['events']==[];return
 if mode.endswith('change'):
  old=next(d for d in s['documents'] if d['filename']=='supplier_notice_v1.txt');s=upload(c,s,'Affected lots: SUP-A and SUP-C. Complete incident list.','new-source.txt');new=s['documents'][-1]
  body={'source_kind':'document','source_id':old['id'],'old_version':str(old['revision']),'new_version':new['id'],'classification':'wording_only' if mode=='wording-change' else 'factual','effective_at':(datetime.now(timezone.utc)+timedelta(days=2) if mode=='future-change' else datetime.now(timezone.utc)).isoformat(),'old_quote':old['blocks'][0]['text'],'new_quote':new['blocks'][0]['text'],'note':NOTE,'event_key':'frozen-revision-change'}
  event=post(c,'/api/assist/source-change',body)
  if mode=='duplicate-change':assert post(c,'/api/assist/source-change',body)==event
 else:
  if mode=='source-stales-brief':s=upload(c,s,'Additional source with unresolved incident extent.')
  if mode=='task-stales-brief':
   q=c.get(route+'/assisted').json()['next_evidence']['requests'][0];post(c,route+'/evidence-task',{'cause_id':q['id'],'role':'Receiver','due_date':'','request_draft':'','idempotency_key':'task-after-handover','revision':s['revision']})
  if mode=='translation-stales-brief':
   d=s['documents'][0];post(c,route+'/translation',{'document_id':d['id'],'language':'en','segments':[{'source':ref(d),'translation':d['blocks'][0]['text']}],'idempotency_key':'translation-after-brief','provenance_reference':'Agent local exact original repetition, not a model'})
  if mode=='label-stales-brief':post(c,route+'/label-image',image_body())
 assert c.get(route+'/assisted').json()['handover'][0]['stale']
 assert c.get(route).json()['receipts']==s['receipts']

def operations(c,x,expected,tmp,mp):
 mode=x['mode']
 if mode.startswith('json-'):
  text={'json-duplicate':'{"x":1,"x":2}','json-trailing':'{"x":1} extra','json-nonfinite':'{"x":NaN}','json-array':'[]','json-fence':'```json\n{"x":1}\n```','json-oversize':'{"x":"'+'x'*48001+'"}'}[mode]
  if expected=='reject':
   with pytest.raises(ValueError):parse_json(text)
  else:assert parse_json(text)=={'x':1}
  return
 if mode.startswith('https-'):
  with pytest.raises(DomainError):external.https_origin('https://user:password@api.example.test' if mode=='https-userinfo' else 'https://api.example.test?token=synthetic')
  return
 if mode.startswith('cross-'):
  s=post(c,'/api/cases/demo');route='/api/cases/'+s['id'];other=TestClient(module.app)
  if mode=='cross-origin':assert c.post('/api/cases/demo',json={},headers={'origin':'https://unrelated.invalid'}).status_code==403;return
  if mode=='cross-source-read':r=other.get('/api/sources/'+s['documents'][0]['original_hash'])
  elif mode=='cross-export':r=other.get(route+'/export')
  elif mode=='cross-job':r=other.post(route+'/assist-poll',json={'job_id':'unknown-owned-job'})
  elif mode=='cross-assist-result':r=other.get(route+'/assisted')
  elif mode=='cross-label':r=other.post(route+'/label-image',json=image_body())
  elif mode=='cross-handover':r=other.post(route+'/handover',json={'idempotency_key':'cross-owner-attempt','previous_id':None})
  else:r=other.get(route)
  assert r.status_code in (403,404);assert other.get('/api/cases').json()==[];return
 if mode=='callback-forgery':assert c.post('/api/assist/callback',json={'approved':True,'execution_id':'forged'}).status_code==403;return
 if mode=='missing-live-token':
  mp.setenv('LIVE_DEMO_TOKEN','synthetic-private-access-token-12345678');s=post(c,'/api/cases/demo')
  assert c.post('/api/cases/'+s['id']+'/analyze',json={'document_id':s['documents'][0]['id'],'mode':'live'}).status_code==403
  assert c.get('/api/cases/'+s['id']).json()['runs']==[];return
 if mode in ('budget-failed-attempt','allowance-expired'):
  now=datetime.now(timezone.utc);a={'provider':'gemma','additional_cash_limit':0,'overages_disabled':True,'storage_network_cash_limit':0,'verified_at':now.isoformat(),'expires_at':(now+timedelta(minutes=-1 if mode=='allowance-expired' else 10)).isoformat(),'max_dispatches':1,'remaining_credits':1,'stop_margin':.1,'max_credits_per_dispatch':.01,'managed_amd_shared_verified':True,'evidence_reference':'Local simulated provider allowance only','allowance_id':'hardening-unit'}
  p=tmp/'allowance.json';p.write_text(json.dumps(a));mp.setenv('GEMMA_COST_APPROVAL_FILE',str(p));mp.setenv('GEMMA_HOSTING_KIND','managed-amd-shared')
  if mode=='allowance-expired':
   with pytest.raises(DomainError):external.allowance('gemma')
  else:
   with repo.write(module.connect) as db:external.reserve(db,'gemma')
   with repo.write(module.connect) as db:
    with pytest.raises(DomainError):external.reserve(db,'gemma')
  return
 with repo.write(module.connect) as db:
  jobs.start(db,'owner','J1','synthetic-test',{'source':'frozen'},'fixture')
  if mode=='duplicate-job-key':
   with pytest.raises(DomainError):jobs.start(db,'owner','J1','synthetic-test',{},'fixture')
  elif mode=='job-cancel-late':jobs.cancel(db,'owner','J1');assert jobs.finish(db,'owner','J1','succeeded','late-hash') is False
  else:
   rev,j=repo.get_record(db,'owner','job','J1');j['lease_until']=time.time()-1;repo.put_record(db,'owner','job','J1',j,rev)
 if mode in ('job-expiry','job-restart'):
  with repo.write(module.connect) as fresh:
   jobs.recover_expired(fresh,'owner');_,saved=repo.get_record(fresh,'owner','job','J1');assert saved['status']=='interrupted' and saved['attempts']==1
   assert jobs.finish(fresh,'owner','J1','succeeded','delayed-result') is False

@pytest.mark.parametrize('case',DATA['cases'],ids=lambda c:c['id']+'-'+c['name'])
def test_frozen_hardening_contract(case,local):
 c,tmp,mp=local;raw=(MANIFEST.parent/case['source_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==case['source_sha256'];x=json.loads(raw);op=case['operation'];expected=case['expected']
 if op=='ingest':ingest(c,x,expected)
 elif op=='proposal':proposal(x,expected)
 elif op.startswith('knowledge_'):knowledge_case(op,x,expected)
 elif op=='statistics':statistics(x,expected)
 elif op=='planning':planning(x,expected)
 elif op=='sequence':sequence(c,x)
 elif op=='translation':assert bool(assisted.translation_flags(x['original'],x['translated']))==(expected=='review_required')
 elif op=='label':label(c,x,expected,tmp)
 elif op=='change_handover':change_handover(c,x,expected)
 elif op=='operations':operations(c,x,expected,tmp,mp)
 else:raise AssertionError('Unexecuted contract operation '+op)
