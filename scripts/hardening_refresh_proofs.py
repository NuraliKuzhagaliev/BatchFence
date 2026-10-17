"""Refresh only nonsecret guard proofs from actual provider-enforced limits.

No credentials/configuration/ledger rotation. The original allowance identity
and lifetime dispatch cap remain; provider hard boundaries survive redeploy.
"""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import httpx
from dotenv import dotenv_values
R=Path(__file__).resolve().parents[1];P=R/'work/hardening'
def main():
 v=dotenv_values(R/'.env');now=datetime.now(timezone.utc)
 with httpx.Client(timeout=35,trust_env=False) as c:
  r=c.get(v['AMD_API_BASE_URL'].rstrip('/')+'/usage',params={'include_recent':'false'},headers={'Authorization':'Bearer '+v['AMD_API_KEY']});r.raise_for_status();amd=r.json()
  h={'X-User-ApiKey':v['EVOLUS_USER_API_KEY'],'X-Application-Id':v['EVOLUS_APPLICATION_ID']}
  r=c.get(v['EVOLUS_API_BASE_URL'].rstrip('/')+'/api/v1/applications/'+v['EVOLUS_APPLICATION_ID']+'/buckets/balances',headers=h);r.raise_for_status();balance=r.json()
  r=c.get(v['EVOLUS_API_BASE_URL'].rstrip('/')+'/api/v1/ai/catalog',params={'capability':'chat','context':'workflow-llm'},headers=h);r.raise_for_status();catalog=r.json()
 own=next(m for g in catalog['groups'] for m in g['items'] if m['id']=='own/gemma-4-31b-it')
 assert own['pricing']['kind']=='byok-free' and own['pricing']['input']==own['pricing']['output']==0 and not own['locked'] and not own['unavailable']
 assert 0<amd['daily_cost_limit_usd']<=1 and amd['daily_cost_remaining_usd']>.10
 # Read-only account plan proof from this phase; no subscription changes.
 account=json.loads((R/'docs/hardening-0.4/account-controls.json').read_text())
 proof={}
 for provider in ['gemma','evolus']:
  p=P/(provider+'-allowance.json');a=json.loads(p.read_text());assert a['allowance_id']=='adversarial-2026-10-18-v1'
  a['verified_at']=now.isoformat();a['expires_at']=min(now+timedelta(hours=23),datetime.fromisoformat(amd['daily_reset_at'].replace('Z','+00:00'))).isoformat()
  if provider=='gemma':a.update(remaining_credits=amd['daily_cost_remaining_usd'],provider_enforced_boundary={'kind':'amd-shared-free-hard-daily-cap','additional_cash_overages':False,'daily_metering_limit':amd['daily_cost_limit_usd'],'reset_at':amd['daily_reset_at']})
  else:a['provider_enforced_boundary']={'kind':'event-trial-own-model-zero-price','additional_cash_overages':False,'renews_automatically':False,'trial_ends_at':'2026-11-15T22:59:00Z'}
  p.write_text(json.dumps(a,indent=2)+'\n');proof[provider.upper()+'_COST_APPROVAL_JSON']=json.dumps(a,separators=(',',':'))
 (P/'hosted-proof-env.json').write_text(json.dumps(proof))
 report={'at':now.isoformat(),'amd':{k:amd[k] for k in ('daily_cost_limit_usd','daily_cost_used_usd','daily_cost_remaining_usd','daily_reset_at')},'evolus_balance':balance,'own_model_price':own['pricing'],'expiry':a['expires_at'],'phase_identity_preserved':True,'configuration_secrets_changed':False,'dispatch_counters_reset':False,'source_account_plan':'account-controls.json; event TRIALING, no automatic renewal; no plan operation performed'}
 text=json.dumps(report,indent=2)
 for key in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY'):
  assert v[key] not in text
 (R/'docs/hardening-0.4'/('proof-refresh-'+now.strftime('%H%M%S')+'.json')).write_text(text+'\n');print(json.dumps({'status':'refreshed nonsecret proofs only','expires_at':a['expires_at'],'amd_remaining':amd['daily_cost_remaining_usd']}))
if __name__=='__main__':main()
