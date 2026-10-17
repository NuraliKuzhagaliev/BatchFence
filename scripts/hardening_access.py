"""Read-only account preflight. Never imports app state or displays key values."""
import hashlib,json,os,time
from pathlib import Path
from datetime import datetime,timezone
import httpx
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/hardening-0.4';PRIVATE=ROOT/'work/hardening'
KEYS=('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY')
def main():
 values={k:v for k,v in dotenv_values(ROOT/'.env').items() if v};OUT.mkdir(exist_ok=True);PRIVATE.mkdir(exist_ok=True)
 report={'at':datetime.now(timezone.utc).isoformat(),'phase':'adversarial-2026-10-18-v1','inference_calls':0,'configuration_file':str(ROOT/'.env'),'present':{k:bool(values.get(k)) for k in (*KEYS,'EVOLUS_APPLICATION_ID','GEMMA_MODEL_ID')},'reads':[]}
 secrets=[values[k] for k in KEYS if values.get(k)]
 def get(label,url,headers,params=None):
  start=time.perf_counter()
  try:
   with httpx.Client(timeout=35,follow_redirects=False,trust_env=False) as c:
    with c.stream('GET',url,headers=headers,params=params) as r:
     chunks=[];size=0
     for b in r.iter_bytes():
      size+=len(b)
      if size>2500000:raise ValueError('Account response exceeded2.5MB bound')
      chunks.append(b)
     raw=b''.join(chunks)
   meta={'label':label,'http_status':r.status_code,'elapsed_ms':round((time.perf_counter()-start)*1000),'response_hash':hashlib.sha256(raw).hexdigest()};report['reads'].append(meta)
   if r.status_code!=200:return None
   data=json.loads(raw)
   # Provider connections may include masked/key fields; never emit full objects.
   return data
  except (httpx.HTTPError,ValueError):report['reads'].append({'label':label,'status':'transport/JSON/size failure; details omitted'});return None
 base=values.get('AMD_API_BASE_URL','').rstrip('/');key=values.get('AMD_API_KEY')
 if base and key:
  auth={'Authorization':'Bearer '+key};usage=get('amd-current-usage',base+'/usage',auth,{'include_recent':'false'})
  if usage:
   report['amd']={k:usage.get(k) for k in ('daily_cost_limit_usd','daily_cost_used_usd','daily_cost_remaining_usd','daily_reset_at','daily_request_limit','requests_remaining')}
   report['amd']['today']={k:usage.get('today',{}).get(k) for k in ('requests','errors','prompt_tokens','completion_tokens','cost')}
   report['amd']['returned_field_names']=sorted(usage)
  models=get('amd-current-catalog',base+'/models',auth)
  if models:
   entries=models.get('data',models.get('models',[])) if isinstance(models,dict) else models
   wanted={values.get('AMD_MODEL_ID'),values.get('GEMMA_MODEL_ID')}
   report['amd_models']=[{k:m.get(k) for k in ('id','name','owned_by','free','pricing','context_length','max_output_tokens','capabilities')} for m in entries if m.get('id') in wanted or m.get('name') in wanted]
 evo=values.get('EVOLUS_API_BASE_URL','').rstrip('/');aid=values.get('EVOLUS_APPLICATION_ID');personal=values.get('EVOLUS_USER_API_KEY')
 if evo and aid and personal:
  headers={'X-User-ApiKey':personal,'X-Application-Id':aid}
  balance=get('evolus-current-bucket-balances',evo+'/api/v1/applications/'+aid+'/buckets/balances',headers)
  if balance is not None:report['evolus_balance']=balance
  connections=get('evolus-current-own-connection',evo+'/api/v1/own-models/connections',headers)
  if isinstance(connections,list):report['evolus_connections']=[{k:c.get(k) for k in ('id','name','baseUrl','isDisabled','hasApiKey','lastVerifiedAt','lastVerificationStatus')} for c in connections]
  catalog=get('evolus-current-catalog',evo+'/api/v1/ai/catalog',headers,{'capability':'chat','context':'workflow-llm'})
  if catalog is not None:
   # Discover shape without publishing account-wide configuration.
   def find(x):
    if isinstance(x,list):return [v for a in x for v in find(a)]
    if isinstance(x,dict):
     if x.get('key')==values.get('EVOLUS_GEMMA_MODEL_KEY') or x.get('modelKey')==values.get('EVOLUS_GEMMA_MODEL_KEY'):return [{k:x.get(k) for k in ('key','modelKey','name','source','pricing','available','isAvailable','capabilities','contextWindow')}]
     return [v for a in x.values() for v in find(a)]
    return []
   report['evolus_model']=find(catalog)
 text=json.dumps(report,ensure_ascii=False,indent=2)
 if any(s in text for s in secrets):raise RuntimeError('Secret in account response; publication suppressed')
 path=OUT/('access-'+str(time.time_ns())+'.json');path.write_text(text+'\n',encoding='utf-8')
 (PRIVATE/'configuration-fingerprints.json').write_text(json.dumps({k:hashlib.sha256(values[k].encode()).hexdigest() for k in KEYS if values.get(k)},indent=2),encoding='utf-8')
 print(text)
if __name__=='__main__':main()
