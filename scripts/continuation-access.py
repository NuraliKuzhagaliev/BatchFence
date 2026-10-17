"""Read-only provider preflight. No inference, resource creation or key output."""
import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone,timedelta
import httpx
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')


def main():
    directory=ROOT/'docs/continuation';directory.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).isoformat()
    required=['EVOLUS_API_KEY','EVOLUS_APPLICATION_ID','EVOLUS_USER_API_KEY']
    report={'at':stamp,'config_file':str(ROOT/'.env'),'evolus_credentials':{k:bool(os.getenv(k)) for k in required},
        'inference_calls':0,'resources_created':0,'cash_spend':0,
        'evolus_account_observation':{'source':'Authenticated plan/credits/limits UI, 2026-10-17','plan':'Developer Event','balance_credits':50000,'trial_expiry':'2026-11-16','expiry_behavior':'Service stops; choose a plan to continue','api_caps':'Portal per-person caps do not apply to developer keys/workflows; local persisted cap required'},
        'amd_cloud':{'allocation_verified':False,'gpu_allocated_by_this_phase':False,'own_vllm_verified':False},
        'eligibility':'UNVERIFIED: managed TokenFactory is not an owned AMD Developer Cloud vLLM endpoint'}
    base=os.getenv('AMD_API_BASE_URL','').rstrip('/')
    if base!='https://developer.amd.com.cn/radeon/api/v1':
        report['amd_shared']={'status':'unavailable','reason':'Configured AMD base differs from the observed shared-model manual; no guessed URL or inference'}
    else:
        with httpx.Client(timeout=25,trust_env=False,follow_redirects=False) as client:
            headers={'Authorization':'Bearer '+os.environ['AMD_API_KEY']}
            catalog=client.get(base+'/models',headers=headers);catalog.raise_for_status()
            quota=client.get(base+'/usage',params={'include_recent':'false'},headers=headers);quota.raise_for_status()
        models=catalog.json().get('data',[]);gemma=next((m for m in models if m.get('id')=='Gemma-4-31B-IT'),None)
        report['amd_shared']={'base':base,'model':gemma,'models_http':catalog.status_code,'usage_http':quota.status_code,
            'usage':{k:v for k,v in quota.json().items() if not any(x in k.lower() for x in ('key','token','org','project','user','recent','requests'))},
            'free_basis':'Authenticated AMD TokenFactory User Manual: shared public models free daily-capped; points relative usage, not charges. Catalog free=false discrepancy preserved.',
            'hosting_kind':'managed-amd-shared / sglang-router, not owned ADC vLLM'}
    # Sanitize known local secrets before publishing any provider metadata.
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    for key in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY','LIVE_DEMO_TOKEN','PILOT_SESSION_SECRET'):
        value=os.getenv(key)
        if value and value in encoded:raise RuntimeError('Private value detected; access report not written')
    (directory/'access-current.json').write_text(encoded+'\n',encoding='utf-8')
    print(json.dumps({'report':'docs/continuation/access-current.json','evolus_credentials':report['evolus_credentials'],'gemma_catalog_present':bool(report.get('amd_shared',{}).get('model')),'inference_calls':0,'cash_spend':0}))


if __name__=='__main__':main()
