"""Exactly four matched fresh calls, inside the existing aggregate 48 cap.

Two new notices x Gemma/MiMo. Common JSON-object mode, source IDs, schema,
prompt, temperature and output cap. No retries or changes to frozen labels.
"""
import hashlib,json,os,time
from pathlib import Path
import httpx
from scripts.continuation_live import ROOT,PRIVATE,OUT,refresh_quota,reserve,safe_save,BASE
from backend.scope_proposals import ScopeProposals,INSTRUCTIONS,VERSION,parse_json,validate_proposals
from backend.fixtures import document,now
from backend.domain import digest

FROZEN=ROOT/'evals/continuation/scope-heldout-v3.json'

def main():
 data=json.loads(FROZEN.read_text(encoding='utf-8'));frozen_hash=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 freeze=OUT/'heldout-v3-freeze.json'
 if freeze.exists():raise RuntimeError('This four-call evaluation has already been started; no implicit retry')
 safe_save(freeze,{'at':now(),'sha256':frozen_hash,'call_cap':4,'aggregate_amd_cap':48,'mimo_additional_calls':2,
    'prior_mimo_phase_attempts':27,'mimo_original_phase_cap':30,'prompts_version':VERSION,'labels_change_after_freeze':False})
 refresh_quota('before-heldout-v3');rows=[]
 with httpx.Client(timeout=40,trust_env=False,follow_redirects=False) as client:
  models=client.get(BASE+'/models',headers={'Authorization':'Bearer '+os.environ['AMD_API_KEY']});models.raise_for_status()
  available={m['id'] for m in models.json()['data']}
  assert {'Gemma-4-31B-IT','MiMo-V2.6-Flash'}<=available
  for item in data['items']:
   if not item['live_pair']:continue
   d=document('heldout-original.txt',item['source'].encode(),synthetic=True)
   context={'schema':ScopeProposals.model_json_schema(),'documents':[{'id':d['id'],'blocks':d['blocks']}]}
   settings={'temperature':0,'max_tokens':1600,'response_format':{'type':'json_object'}}
   for model in ['Gemma-4-31B-IT','MiMo-V2.6-Flash']:
    cid=item['id']+'-'+('gemma' if model.startswith('Gemma') else 'mimo');path=OUT/(cid+'.json')
    if path.exists():raise RuntimeError('Attempt file exists; no overwrite or retry')
    reservation=reserve();r={'id':cid,'at':now(),'requested_model_id':model,'reservation':reservation,'source':d,'frozen_sha256':frozen_hash,
      'prompt_version':VERSION,'system_prompt_hash':digest(INSTRUCTIONS),'user_context_hash':digest(context),'settings':settings,
      'provenance':'Fresh inference, synthetic held-out source. No human correction in raw scoring; no inventory actions.'}
    safe_save(path,r);started=time.perf_counter()
    try:
     payload={'model':model,'messages':[{'role':'system','content':INSTRUCTIONS},{'role':'user','content':json.dumps(context,ensure_ascii=False)}],**settings}
     with client.stream('POST',BASE+'/chat/completions',headers={'Authorization':'Bearer '+os.environ['AMD_API_KEY']},json=payload) as response:
      chunks=[];n=0
      for b in response.iter_bytes():
       n+=len(b)
       if n>48000:raise ValueError('Response exceeded 48 KB')
       chunks.append(b)
      raw=b''.join(chunks);r.update(http_status=response.status_code,request_id=response.headers.get('x-request-id'),response_hash=hashlib.sha256(raw).hexdigest())
      if response.status_code!=200:raise ValueError('Provider HTTP '+str(response.status_code)+'; no retry')
      body=json.loads(raw);message=body['choices'][0]['message'].get('content')
      r.update(model_id=body.get('model'),usage=body.get('usage'),request_id=r['request_id'] or body.get('id'),finish_reason=body['choices'][0].get('finish_reason'),raw_response=message)
      parsed=parse_json(message);r['parsed']=parsed
      actual={f['lot_id']:f['status'] for f in parsed.get('facts',[]) if f.get('kind')=='supplier_lot'}
      r['raw_supplier_status_exact']=actual==item['expected_supplier_statuses'];r['raw_scope_exact']=parsed.get('scope_status')==item['expected_scope'];r['expected']=item
      try:r['validated']=validate_proposals(parsed,[d]);r['application_result']='Accepted unreviewed proposal; no fact/scope/approval/stock mutation'
      except Exception as e:r['application_result']='Rejected / source or schema validation';r['validation_error']=str(e)[:700]
    except Exception as e:r['failure']=str(e)[:500];r.setdefault('application_result','Rejected / no accepted proposal')
    r['elapsed_ms']=round((time.perf_counter()-started)*1000);safe_save(path,r);rows.append(r)
    print(json.dumps({'id':cid,'http':r.get('http_status'),'raw_status_exact':r.get('raw_supplier_status_exact'),'raw_scope_exact':r.get('raw_scope_exact'),'application':r['application_result']}),flush=True)
    time.sleep(8 if r.get('http_status')!=429 else 30)
 refresh_quota('after-heldout-v3')
 safe_save(OUT/'heldout-v3-results.json',{'rows':rows,'fresh_calls':4,'original_benchmark_changed':False,'review_corrections':0,
    'conditions':'Identical source IDs, prompt, schema, temperature0, max_tokens1600, JSON-object mode. Provider reasoning/sampling/runtime may differ. MiMo production can use strict JSON schema; common JSON-object mode used here for equivalence.',
    'limits':'Two notices per model; tiny agent-authored synthetic diagnostic, no model-superiority or production-accuracy claim. Remaining three held-out notices were local contract regressions, not fresh inference.'})

if __name__=='__main__':main()
