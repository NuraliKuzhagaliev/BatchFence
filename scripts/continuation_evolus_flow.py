"""Finite actual Evolus extractor -> Gemma -> original review -> receipts.

No fixture extraction, human acceptance claim, automatic retries or messages.
The direct AMD and Evolus-mediated evidence are deliberately separate.
"""
import base64,json,os,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from dotenv import load_dotenv,set_key
from fastapi.testclient import TestClient
from scripts.continuation_live import ROOT,PRIVATE,OUT,refresh_quota,safe_save
load_dotenv(ROOT/'.env',override=False)
from backend import app as module,repository as repo,evolus_api as api
from backend.domain import digest

NOTE='Agent-operated synthetic engineering review; not independent human/domain validation.'
STATE=PRIVATE/'evolus-flow-v2-session.json'

def setup_allowance():
    # Actual current own-model catalog explicitly returns byok-free / 0,0.
    # No embeddings, platform OCR/AI tools, fallback, delivery or GPU allocation.
    current=datetime.now(timezone.utc)
    path=PRIVATE/'evolus-allowance.json'
    proof={'provider':'evolus','additional_cash_limit':0,'storage_network_cash_limit':0,'overages_disabled':True,
        'verified_at':current.isoformat(),'expires_at':min(current+timedelta(hours=1),datetime(2026,11,16,tzinfo=timezone.utc)).isoformat(),
        'max_dispatches':64,'remaining_credits':50000,'stop_margin':1000,'max_credits_per_dispatch':0,
        'allowance_id':'continuation-evolus-f50349c-v1','cost_basis':'Documented own-model LLM, native text and read-only Blob library only; no embeddings or platform AI tools',
        'evidence_reference':'Developer Event account, 50K credits observed; verified own Gemma catalog byok-free pricing input=0/output=0; API native TXT + read-only Blob documented no vector store. Trial ends with service stop, no paid plan accepted.',
        'balance_observation':'Authenticated 50Kcredits link on own-models page, 2026-10-17; exact execution consumption is recorded separately.'}
    safe_save(path,proof);set_key(str(ROOT/'.env'),'EVOLUS_COST_APPROVAL_FILE',str(path));os.environ['EVOLUS_COST_APPROVAL_FILE']=str(path)
    refresh_quota('before-evolus-flow')

def run():
    if STATE.exists():raise RuntimeError('Existing Evolus flow attempt retained; inspect before an explicit diagnostic retest')
    setup_allowance();c=TestClient(module.app)
    def post(path,body=None):
        r=c.post(path,json=body or {})
        if r.status_code!=200:raise RuntimeError('Application HTTP '+str(r.status_code)+': '+str(r.json())[:500])
        return r.json()
    s=post('/api/cases/demo');route='/api/cases/'+s['id'];events=[];phase='created'
    def checkpoint():
        STATE.write_text(json.dumps({'case_id':s['id'],'cookies':dict(c.cookies),'phase':phase,'at':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
    checkpoint()
    try:
        for label,text,lots,total in [
            ('first','Affected lots: SUP-A. This is the complete incident list; no other supplier lots are affected.',['SUP-A'],500),
            ('revision','This revision supersedes the earlier notice. Affected lots: SUP-A and SUP-C. The entire incident boundary consists of these two lots; the list is complete.',['SUP-A','SUP-C'],800)]:
            phase=label+'-uploaded'
            s=post(route+'/documents',{'filename':'unseen-evolus-'+label+'.txt','content_base64':base64.b64encode(text.encode()).decode(),'synthetic':True});checkpoint();doc=s['documents'][-1]
            record=post(route+'/assist-run',{'document_ids':[doc['id']],'revision':s['revision'],'mode':'live','idempotency_key':'actual-evolus-'+label})
            safe_save(OUT/('evolus-'+label+'-start.json'),record)
            phase=label+'-dispatched';checkpoint()
            # Polls are bounded status reads, never a repeated inference dispatch.
            for n in range(12):
                if record['status']!='running':break
                time.sleep(5)
                record=post(route+'/assist-poll',{'job_id':record['id']})
                safe_save(OUT/('evolus-'+label+'-poll-'+str(n+1)+'.json'),record)
            if record['status']!='unreviewed proposal':raise RuntimeError('Evolus '+label+' '+record['status']+': '+str(record.get('error','No completion within bounded polling')))
            phase=label+'-proposed';checkpoint()
            s=post(route+'/assist-intake',{'proposal_id':record['id'],'document_id':doc['id'],'revision':s['revision']})
            candidate_ids=[f['lot_id'] for f in s['runs'][-1]['output']['facts']]
            assert not s['plan'] or not s.get('approved')
            s=post(route+'/reviews',{'run_id':s['runs'][-1]['id'],'revision':s['revision'],'lot_ids':lots,'uncertain_lot_ids':sorted(set(candidate_ids)-set(lots)),
                'excluded_lot_ids':[],'lot_corrections':{},'accept_scope':True,'incident_scope_status':'resolved','resolution_quote':text,'bounded_scope_reviewed':True,'note':NOTE})
            assert s['plan']['result']['hold_units']==total
            s=post(route+'/approve',{'plan_id':s['plan']['id'],'digest':s['plan']['digest']})
            body={'plan_id':s['plan']['id'],'digest':s['plan']['digest'],'actions':s['plan']['actions'],'idempotency_key':'evolus-'+label+'-receipt'}
            s=post(route+'/apply',body);assert post(route+'/apply',body)['receipts']==s['receipts']
            if label=='first':old=body
            else:assert c.post(route+'/apply',json={**old,'idempotency_key':'evolus-stale-rejection'}).status_code==409
            events.append({'stage':label,'raw_supplier_ids':candidate_ids,'reviewed_affected_ids':lots,'added_by_agent_review':sorted(set(lots)-set(candidate_ids)),
                'applied_units':total,'receipts':len(s['receipts']),'runtime_model_identity':record.get('runtime_model_identity'),'review':NOTE})
            phase=label+'-applied';checkpoint();safe_save(OUT/('evolus-'+label+'-case.json'),{'case':s,'review':NOTE})
        safe_save(OUT/'evolus-product-flow.json',{'status':'completed','events':events,'original_receipts':len(s['receipts']),
            'model_dispatch_reservations':4,'model_identity_basis':'Actual execution step outputs plus verified own/gemma-4-31b-it connection; provider does not return runtime model ID per step.',
            'human_acceptance':False,'direct_gemma_flow':'Separate product-flow.json, not counted as Evolus execution'})
        print(json.dumps({'status':'complete','evolus_flows':2,'applied':800,'receipts':len(s['receipts'])}))
    except Exception as e:
        safe_save(OUT/'evolus-product-flow-blocked.json',{'status':'blocked','phase':phase,'error':str(e)[:900],'events':events,'no_automatic_retry':True})
        print(json.dumps({'status':'blocked','phase':phase,'error':str(e)[:900]}));raise
    finally:refresh_quota('after-evolus-flow')

if __name__=='__main__':run()
