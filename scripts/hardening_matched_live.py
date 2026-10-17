"""One finite matched twelve-case rerun/model. No configuration writes or retries.

Existing team key is retained at the owner's explicit instruction. Current free
shared endpoint, provider hard daily cap, bounded payloads and local reservation
evidence apply. Never executes inventory or claims independent human review.
"""
import hashlib,json,os,time,sys
from pathlib import Path
from datetime import datetime,timezone
import httpx
from dotenv import dotenv_values
from backend.scope_proposals import ScopeProposals,INSTRUCTIONS,VERSION,parse_json,validate_proposals,legacy_output
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/hardening-0.4/matched';PRIVATE=ROOT/'work/hardening'
MODELS=['Gemma-4-31B-IT','MiMo-V2.6-Flash'];BASE='https://developer.amd.com.cn/radeon/api/v1'

def main():
 global OUT
 resume='--resume' in sys.argv
 prior=OUT
 if resume:OUT=prior/'resume-1'
 v={k:x for k,x in dotenv_values(ROOT/'.env').items() if x};secrets=[x for k,x in v.items() if 'KEY' in k or 'TOKEN' in k or 'SECRET' in k]
 if v['AMD_API_BASE_URL'].rstrip('/')!=BASE:raise RuntimeError('Configured endpoint differs; no inference')
 source=ROOT/'evals/enterprise/frozen-v1.json';sha=hashlib.sha256(source.read_bytes()).hexdigest()
 if sha!='6d13cbbbf017b5b87508b87e26f484454cf4bd53a115e8ffcdfdfbc04840c3e2':raise RuntimeError('Original benchmark changed')
 items=[x for x in json.loads(source.read_text(encoding='utf-8'))['items'] if x['task']=='extraction'];assert len(items)==12
 OUT.mkdir(exist_ok=True)
 if (OUT/'plan.json').exists():raise RuntimeError('Batch already started. Inspect retained attempts; no implicit retry/reset')
 def save(path,value):
  text=json.dumps(value,ensure_ascii=False,indent=2)
  if any(k and k in text for k in secrets):raise RuntimeError('Private value detected; evidence suppressed')
  path.write_text(text+'\n',encoding='utf-8')
 plan={'phase':'adversarial-2026-10-18-v1','at':datetime.now(timezone.utc).isoformat(),'calls':23 if resume else 24,'per_model':12,'automatic_retries':0,'benchmark_sha256':sha,'prompt_version':VERSION,'prompt_sha256':hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(),'schema_sha256':hashlib.sha256(json.dumps(ScopeProposals.model_json_schema(),sort_keys=True).encode()).hexdigest(),'settings':{'temperature':0,'max_tokens':1600,'response_format':{'type':'json_object'}},'max_request_bytes':20000,'max_response_bytes':48000,'purpose':'Once/model matched comparison; local validation only. No human correction, independent review, superiority claim or product inventory effects.','credit_boundary':'Documented free shared AMD gateway; current account hard daily cap and remaining allowance checked before batch. Stop affected provider on quota/auth failure, no purchasing or automatic retry.'}
 if resume:plan['resume_reason']='One bounded MiMo EXT01 retry after >25 minutes, original Retry-After1 and preserved429; execute only original unrun cases. Stop MiMo on repeated429 and finish independent Gemma cases. Passed Gemma EXT01 is never rerun.'
 save(OUT/'plan.json',plan);ledger_path=PRIVATE/'phase-ledger.json'
 ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'phase':plan['phase'],'maximum_model_attempts':64,'attempts':[]}
 def quota(client,label):
  r=client.get(BASE+'/usage',params={'include_recent':'false'},headers={'Authorization':'Bearer '+v['AMD_API_KEY']});r.raise_for_status();d=r.json()
  selected={k:d[k] for k in ('daily_cost_limit_usd','daily_cost_used_usd','daily_cost_remaining_usd','daily_reset_at')};selected.update(at=datetime.now(timezone.utc).isoformat(),http_status=r.status_code,today_requests=d.get('today',{}).get('requests'),unit='Provider shared-service metering units; not a cash purchase')
  save(OUT/('quota-'+label+'.json'),selected)
  if not 0<d['daily_cost_limit_usd']<=1 or d['daily_cost_remaining_usd']<.10:raise RuntimeError('Provider hard cap/headroom changed; no inference')
  return d
 rows=[];blocked=set()
 with httpx.Client(timeout=45,trust_env=False,follow_redirects=False) as client:
  q=quota(client,'before')
  for item in items:
   doc={'id':'MATCHED-'+item['id'],'blocks':[{'id':'original-1','text':item['text'],'page':None}]}
   context={'schema':ScopeProposals.model_json_schema(),'documents':[doc]};content=json.dumps(context,ensure_ascii=False)
   for model in MODELS:
    rid=item['id']+'-'+('gemma' if model.startswith('Gemma') else 'mimo');path=OUT/(rid+'.json')
    if model in blocked:continue
    if resume and (prior/(rid+'.json')).exists():
     old=json.loads((prior/(rid+'.json')).read_text())
     if old.get('http_status')==200:continue
     if rid!='EXT-01-mimo' or old.get('http_status')!=429:raise RuntimeError('No disclosed retry for this failure')
    if path.exists() or len(ledger['attempts'])>=ledger['maximum_model_attempts']:raise RuntimeError('Attempt already exists or finite cap reached')
    if model.startswith('MiMo') and sum(a['model']==model for a in ledger['attempts'])>=14:raise RuntimeError('MiMo phase ceiling reached')
    stamp=datetime.now(timezone.utc).isoformat();record={'id':rid+('-retry1' if resume and rid=='EXT-01-mimo' else ''),'at':stamp,'requested_model':model,'source':doc,'original_labels':item['labels'],'benchmark_sha256':sha,'settings':plan['settings'],'prompt_version':VERSION,'source_hash':hashlib.sha256(item['text'].encode()).hexdigest(),'user_context_hash':hashlib.sha256(content.encode()).hexdigest(),'state_effect':'None; standalone raw benchmark and application validator only','review':'No corrections or independent human validation'}
    payload={'model':model,'messages':[{'role':'system','content':INSTRUCTIONS},{'role':'user','content':content}],**plan['settings']}
    if len(json.dumps(payload,ensure_ascii=False).encode())>plan['max_request_bytes']:raise RuntimeError('Request exceeds frozen envelope')
    ledger=json.loads(ledger_path.read_text());assert len(ledger['attempts'])<ledger['maximum_model_attempts']
    ledger['attempts'].append({'id':record['id'],'model':model,'at':stamp,'steps':1,'outcome':'reserved before dispatch'})
    temp=ledger_path.with_suffix('.pending');temp.write_text(json.dumps(ledger,indent=2),encoding='utf-8');os.replace(temp,ledger_path);save(path,record)
    start=time.perf_counter()
    try:
     with client.stream('POST',BASE+'/chat/completions',headers={'Authorization':'Bearer '+v['AMD_API_KEY']},json=payload) as response:
      raw=b''
      for chunk in response.iter_bytes():
       raw+=chunk
       if len(raw)>48000:raise ValueError('Bounded response exceeded48KB; no accepted proposal')
      record.update(http_status=response.status_code,request_id=response.headers.get('x-request-id'),response_hash=hashlib.sha256(raw).hexdigest(),quota_headers={k:x for k,x in response.headers.items() if k.lower().startswith('x-ratelimit-')},retry_after=response.headers.get('retry-after'))
      if response.status_code!=200:
       try:record['provider_error_code']=json.loads(raw).get('error',{}).get('code')
       except (ValueError,AttributeError):pass
       raise ValueError('Provider HTTP '+str(response.status_code)+'; affected model stops, no automatic retry')
      body=json.loads(raw);answer=body['choices'][0]['message'].get('content')
      record.update(actual_model=body.get('model'),request_id=record['request_id'] or body.get('id'),usage=body.get('usage'),finish_reason=body['choices'][0].get('finish_reason'))
      if not isinstance(answer,str):raise ValueError('Model returned no text JSON')
      if any(secret in answer for secret in secrets):raise ValueError('Private value in response; content discarded')
      record['raw_response']=answer;parsed=parse_json(answer);record['parsed']=parsed
      actual=sorted((f.get('lot_id'),f.get('status')=='affected') for f in parsed.get('facts',[]) if isinstance(f,dict) and f.get('kind')=='supplier_lot')
      expected=sorted([(a,True) for a in item['labels']['affected_supplier_lots']]+[(a,False) for a in item['labels']['mentioned_supplier_lots']])
      record['original_supplier_pairs_exact']=actual==expected;record['expected_pairs']=expected;record['actual_pairs']=actual
      try:record['validated']=validate_proposals(parsed,[doc]);record['application']='accepted unreviewed proposal; mandatory source/scope review remains'
      except Exception as exc:record.update(application='rejected by source/schema validator',validation_error=str(exc)[:600])
    except Exception as exc:record.update(failure=str(exc)[:400] if isinstance(exc,ValueError) else type(exc).__name__+'; private transport detail omitted',application='rejected / no usable result')
    record['elapsed_ms']=round((time.perf_counter()-start)*1000);save(path,record);rows.append(record)
    ledger['attempts'][-1].update(outcome=record['application'],http_status=record.get('http_status'));temp=ledger_path.with_suffix('.pending');temp.write_text(json.dumps(ledger,indent=2));os.replace(temp,ledger_path)
    print(json.dumps({'id':rid,'http':record.get('http_status'),'original_pairs_exact':record.get('original_supplier_pairs_exact',False),'application':record['application']}),flush=True)
    if record.get('http_status') in (401,402,403,429) or record.get('http_status') is None:blocked.add(model)
    # Sequential pace stays well below the documented20 account requests/minute.
    time.sleep(3)
   if len(blocked)==len(MODELS):break
  quota(client,'after')
 summary={'planned':24,'attempted':len(rows),'models':{m:{'attempts':sum(r['requested_model']==m for r in rows),'original_supplier_pairs_exact':sum(r['requested_model']==m and r.get('original_supplier_pairs_exact',False) for r in rows),'validator_rejections':sum(r['requested_model']==m and r['application'].startswith('rejected') for r in rows)} for m in MODELS},'original_frozen_benchmark_unchanged':True,'state_effects':0,'independent_human_validation':False,'limitation':'Small same-agent synthetic benchmark. Binary original labels collapse mentioned/uncertain/excluded; complete-boundary auxiliary label disputes remain separate. Equivalent requested settings do not guarantee identical provider sampling or reasoning.'}
 save(OUT/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
