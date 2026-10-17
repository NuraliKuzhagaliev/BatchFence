"""Local injected account proofs; no provider calls or real credits."""
import json
from datetime import datetime,timezone,timedelta
import pytest
from backend import evolus_adapter as external
from backend.domain import DomainError

@pytest.mark.parametrize('provider',['gemma','evolus'])
@pytest.mark.parametrize('variant',['valid','old','no-boundary','renewing','past-expiry','nonzero-cash'])
def test_provider_boundary_keeps_time_and_cash_limits(tmp_path,monkeypatch,provider,variant):
 now=datetime.now(timezone.utc);checked=now-timedelta(hours=2 if variant!='old' else 25);expiry=now+timedelta(hours=3)
 boundary={'additional_cash_overages':False,'kind':'amd-shared-free-hard-daily-cap','daily_metering_limit':1,'reset_at':expiry.isoformat()} if provider=='gemma' else {'additional_cash_overages':False,'kind':'event-trial-own-model-zero-price','renews_automatically':False,'trial_ends_at':expiry.isoformat()}
 d={'provider':provider,'additional_cash_limit':0,'storage_network_cash_limit':0,'overages_disabled':True,'verified_at':checked.isoformat(),'expires_at':expiry.isoformat(),'max_dispatches':64,'remaining_credits':1,'stop_margin':.1,'max_credits_per_dispatch':.01 if provider=='gemma' else 0,'managed_amd_shared_verified':True,'evidence_reference':'Simulated proof for a local guard regression','cost_basis':'Documented own-model LLM, native text and read-only Blob library only; no embeddings or platform AI tools','provider_enforced_boundary':boundary}
 if variant=='no-boundary':d.pop('provider_enforced_boundary')
 if variant=='renewing':boundary['additional_cash_overages']=True;boundary['renews_automatically']=True
 if variant=='past-expiry':d['expires_at']=(now-timedelta(minutes=1)).isoformat()
 if variant=='nonzero-cash':d['additional_cash_limit']=1
 p=tmp_path/'proof.json';p.write_text(json.dumps(d));monkeypatch.setenv(provider.upper()+'_COST_APPROVAL_FILE',str(p));monkeypatch.setenv('GEMMA_HOSTING_KIND','managed-amd-shared');monkeypatch.delenv(provider.upper()+'_COST_APPROVAL_JSON',raising=False)
 if variant=='valid':assert external.allowance(provider)==d
 else:
  with pytest.raises(DomainError):external.allowance(provider)
 # Nonsecret hosted proof has the same validation and never resets a ledger.
 monkeypatch.setenv(provider.upper()+'_COST_APPROVAL_JSON',json.dumps(d));p.write_text('{}')
 if variant=='valid':assert external.allowance(provider)==d
 else:
  with pytest.raises(DomainError):external.allowance(provider)

def test_contract_file_uses_release_line_endings():
 import hashlib
 from pathlib import Path
 p=Path(__file__).resolve().parents[1]/'backend/contracts/evolus-api-contract.json'
 assert b'\r\n' not in p.read_bytes()
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='05b1fc45f691be03bc584815bac57f60330710d88ebdd79531265b68791d0b5a'
