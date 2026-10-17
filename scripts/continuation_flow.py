"""Fresh Gemma -> original review -> real deterministic sandbox workflow.

Synthetic sources; agent-operated review and role simulation, NOT independent
human/domain/language acceptance. No fixture extraction or external inventory.
"""
import base64,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from dotenv import set_key
from fastapi.testclient import TestClient
from scripts.continuation_live import ROOT,PRIVATE,OUT,refresh_quota,safe_save
from backend import app as module

NOTE='Agent-operated synthetic engineering review; not independent human, language, source-authenticity or manufacturing validation.'
STATE=PRIVATE/'flow-session.json'


def post(c,path,body=None):
    r=c.post(path,json=body or {})
    if r.status_code!=200:raise RuntimeError(f'Application HTTP {r.status_code}: '+str(r.json())[:600])
    return r.json()


def run():
    if STATE.exists():raise RuntimeError('Prior flow session exists. Inspect its exact saved phase and failures; no automatic rerun.')
    # Enable image requests only after real model image responses passed the
    # bounded synthetic capability check. No real-photo robustness is claimed.
    expected={'IMG-01':['SUP-001'],'IMG-02':['SUP-002'],'IMG-03':['LOT-00O7'],'IMG-04-retest-1':['SUP-001','SUP-002'],'IMG-05':[]}
    for key,ids in expected.items():
        result=json.loads((OUT/(key+'.json')).read_text(encoding='utf-8'))['response']
        if result['http_status']!=200 or result['model_id']!='self-dploy/Gemma-4-31B-IT' or result['result']['candidates']!=ids:raise RuntimeError('Vision capability gate did not pass')
    set_key(str(ROOT/'.env'),'GEMMA_VISION_VERIFIED','true');os.environ['GEMMA_VISION_VERIFIED']='true'
    safe_save(OUT/'vision-capability.json',{'model_id':'self-dploy/Gemma-4-31B-IT','actual_image_requests':6,'first_attempts':5,'first_responses':4,'first_429':1,'explicit_retest_responses':1,
        'source_files':list(expected),'physical_photographs':0,'limits':'Synthetic rendered images only. Exact O spelling was preserved, but the model did not flag O/0 ambiguity. Explicit relationship review and exact mismatch gates remain mandatory.'})
    refresh_quota('before-product-flow');c=TestClient(module.app);start=time.perf_counter();s=post(c,'/api/cases/demo');route='/api/cases/'+s['id'];events=[];calls=0;phase='create'
    def checkpoint(label):
        nonlocal s,phase
        phase=label;s=c.get(route).json()
        STATE.write_text(json.dumps({'case_id':s['id'],'cookies':dict(c.cookies),'phase':phase,'at':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
        safe_save(OUT/('flow-'+label+'.json'),{'phase':label,'case':s,'review_provenance':NOTE})
        print(json.dumps({'phase':label,'proposal':s.get('plan',{}).get('result',{}).get('hold_units') if s.get('plan') else None,'applied':s.get('quantities',{}).get('applied_hold_units'),'original_receipts':len(s['receipts'])}),flush=True)
    def upload(name,text,**extra):
        nonlocal s
        s=post(c,route+'/documents',{'filename':name,'content_base64':base64.b64encode(text.encode('utf-8')).decode(),'synthetic':True,**extra});checkpoint('source-'+str(s['revision']));return s['documents'][-1]
    def generate(kind,label,**extra):
        nonlocal calls
        if calls%3==0:refresh_quota('flow-'+str(calls))
        current=c.get(route).json();record=post(c,route+'/assist-generate',{'kind':kind,'revision':current['revision'],'idempotency_key':'fresh-product-'+label,**extra});calls+=1
        safe_save(OUT/('flow-model-'+label+'.json'),record);time.sleep(6)
        if record['status']!='unreviewed proposal':raise RuntimeError('Fresh '+label+' failed; raw record retained, no automatic retry or fixture substitution')
        return record
    def interpret(doc,lots,label):
        nonlocal s
        proposal=generate('document',label,document_ids=[doc['id']])
        s=post(c,route+'/assist-intake',{'proposal_id':proposal['id'],'document_id':doc['id'],'revision':s['revision']})
        raw_ids={f['lot_id'] for f in s['runs'][-1]['output']['facts']}
        events.append({'stage':label,'raw_candidate_ids':sorted(raw_ids),'agent_reviewed_affected_ids':lots,'added_during_review':sorted(set(lots)-raw_ids),'review':NOTE})
        s=post(c,route+'/reviews',{'run_id':s['runs'][-1]['id'],'revision':s['revision'],'lot_ids':lots,'uncertain_lot_ids':sorted(raw_ids-set(lots)),'excluded_lot_ids':[],'lot_corrections':{},'accept_scope':True,'incident_scope_status':'resolved','resolution_quote':doc['blocks'][0]['text'],'bounded_scope_reviewed':True,'note':NOTE})
        return s
    def contain(label):
        nonlocal s
        s=post(c,route+'/approve',{'plan_id':s['plan']['id'],'digest':s['plan']['digest']})
        body={'plan_id':s['plan']['id'],'digest':s['plan']['digest'],'actions':s['plan']['actions'],'idempotency_key':label}
        s=post(c,route+'/apply',body);assert post(c,route+'/apply',body)['receipts']==s['receipts'];return body
    try:
        s=post(c,'/api/enterprise/example',{'case_id':s['id'],'acknowledged_synthetic':True})
        inspection='FG-C: 100 pieces inspected using visual-v1; 0 nonconforming. Passed whole-pool cosmetic inspection.'
        inspection_doc=upload('fresh-whole-pool-inspection.txt',inspection)
        notice1=upload('supplier-letter-alpha.txt','Affected lots: SUP-A. Scope is complete. This supplier notice lists the entire incident boundary.')
        interpret(notice1,['SUP-A'],'notice-500');assert s['plan']['result']['hold_units']==500;old=contain('fresh-gemma-containment-500');checkpoint('500-applied')
        notice2=upload('revised-letter-beta.txt','Revision replaces the initial notice. Affected supplier lots are SUP-A and SUP-C. This is the complete incident list; no other supplier lots are affected.')
        assert c.post(route+'/apply',json={**old,'idempotency_key':'stale-after-new-notice'}).status_code==409
        interpret(notice2,['SUP-A','SUP-C'],'notice-800');assert s['plan']['result']['hold_units']==800;contain('fresh-gemma-containment-800');checkpoint('800-applied')
        q=next(q for q in s['plan']['result']['requests'] if q['pool_ids']==['FG-C'])
        ambiguous=upload('receiving-uncertain.txt','FG-C may contain SUP-A or SUP-B. The complete parent list has not been established.',request_id=q['id'])
        raw_ambiguous=generate('document','ambiguous-response',document_ids=[ambiguous['id']])
        common={'revision':s['revision'],'document_id':ambiguous['id'],'review_path':'structured_record','pool_id':'FG-C','parent_ids':[],'complete':False,'quote':ambiguous['blocks'][0]['text'],'superseded_row_ids':[],'unresolved_contradictions':True,'outcome':'inconclusive','reviewed':True,'replacement_reviewed':True,'completeness_confirmed':False,'note':NOTE}
        s=post(c,route+'/receiving-review',common);assert s['plan']['result']['hold_units']==800;checkpoint('ambiguity-contained')
        q=next(q for q in s['plan']['result']['requests'] if q['pool_ids']==['FG-C']);draft=generate('request','next-evidence',cause_id=q['id'])['draft']
        task=post(c,route+'/evidence-task',{'cause_id':q['id'],'role':'Receiving supervisor','due_date':'','request_draft':draft['draft'],'idempotency_key':'fresh-missing-ancestry-request','revision':s['revision']})
        italian='FG-C è composto esclusivamente dal lotto SUP-B. Tutti i genitori sono elencati; la registrazione è completa.'
        reply=upload('ricevimento-completo.txt',italian,request_id=q['id'],evidence_language='it')
        translated=generate('translation','italian-response',document_ids=[reply['id']],language='it')['draft']
        post(c,route+'/translation-review',{'translation_id':translated['id'],'can_verify_original':True,'qualified_reference':'Agent-operated Italian/English engineering review; independent qualified acceptance pending','critical_fields_confirmed':True,'note':NOTE})
        receiving={**common,'revision':s['revision'],'document_id':reply['id'],'parent_ids':['SUP-B'],'complete':True,'quote':italian,'superseded_row_ids':['LIN-3','LIN-4'],'unresolved_contradictions':False,'outcome':'resolved','completeness_confirmed':True}
        preview=post(c,route+'/receiving-preview',receiving);assert preview['after_units']==700 and preview['applied_hold_units']==800
        s=post(c,route+'/receiving-review',receiving)
        post(c,route+'/response-review',{'task_id':task['id'],'document_id':reply['id'],'outcome':'resolved','quote':italian,'reviewed':True,'note':NOTE});checkpoint('700-proposed-800-applied')
        image=ROOT/'evals/continuation/images/IMG-01.png';label=post(c,route+'/label-image',{'filename':'synthetic-label-SUP-001.png','content_base64':base64.b64encode(image.read_bytes()).decode(),'crop_xywh':[]})
        reading=generate('label','label-mismatch',label_id=label['id']);rejected=c.post(route+'/label-review',json={'label_id':label['id'],'document_id':reply['id'],'quote':italian,'selected_id':'SUP-B','identity_confirmed':True,'relationship_verified':True,'unresolved':False,'note':NOTE})
        assert rejected.status_code==422;events.append({'stage':'live-label-mismatch','reading':reading['draft']['reading'],'document_id':'SUP-B','association_rejected_http':422,'physical_photo':False})
        post(c,'/api/auth/simulate',{'role':'preparer','acknowledge_simulation':True})
        post(c,'/api/recovery/policy-review',{'reviewed':True,'note':NOTE,'expected_revision':0,'procedure_refs':['PROC-100@1']})
        proof={'revision':s['revision'],'pool_id':'FG-C','receiving_document_id':reply['id'],'receiving_quote':italian,'authenticity_verified':True,'verification_reference':NOTE,'inspection_document_id':inspection_doc['id'],'inspection_quote':inspection,'inspected_units':100,'nonconforming_units':0,'inspection_passed':True,'inspected_at':datetime.now(timezone.utc).isoformat(),'note':NOTE}
        evidence=post(c,route+'/recovery-evidence',proof);recovery=c.get(route+'/recovery').json();hold=next(h for h in recovery['holds'] if h['incident_id']==s['id'] and h['pool_id']=='FG-C' and h['status']=='active')
        prepared=post(c,route+'/recovery-prepare',{'hold_ids':[hold['id']],'evidence_ids':[evidence['id']],'note':NOTE})
        assert c.post('/api/recovery/release-approve',json={'recovery_id':prepared['id'],'digest':prepared['digest']}).status_code in (403,422)
        post(c,'/api/auth/simulate',{'role':'approver','acknowledge_simulation':True});post(c,'/api/recovery/release-approve',{'recovery_id':prepared['id'],'digest':prepared['digest']})
        post(c,'/api/auth/simulate',{'role':'preparer','acknowledge_simulation':True})
        replacement=upload('supplier-clarification-gamma.txt','The complete incident boundary remains supplier lots SUP-A and SUP-C. This clarification replaces the prior notice wording; there are no additional affected supplier lots.')
        event=post(c,'/api/assist/source-change',{'source_kind':'document','source_id':notice2['id'],'old_version':str(notice2['revision']),'new_version':replacement['id'],'classification':'uncertain','effective_at':datetime.now(timezone.utc).isoformat(),'old_quote':notice2['blocks'][0]['text'],'new_quote':replacement['blocks'][0]['text'],'note':NOTE,'event_key':'fresh-source-clarification-review'})
        post(c,'/api/auth/simulate',{'role':'approver','acknowledge_simulation':True});assert c.post('/api/recovery/recovery-execute',json={'recovery_id':prepared['id'],'digest':prepared['digest'],'idempotency_key':'stale-source-recovery-attempt'}).status_code==422
        post(c,'/api/auth/simulate',{'role':'preparer','acknowledge_simulation':True});s=c.get(route).json();interpret(replacement,['SUP-A','SUP-C'],'source-reassessment')
        reassessment=c.get(route+'/assisted').json()['rereview'][-1];post(c,route+'/rereview-review',{'task_id':reassessment['id'],'revision':s['revision'],'old_quote':notice2['blocks'][0]['text'],'new_quote':replacement['blocks'][0]['text'],'reviewed':True,'note':NOTE})
        evidence=post(c,route+'/recovery-evidence',{**proof,'revision':s['revision']});prepared=post(c,route+'/recovery-prepare',{'hold_ids':[hold['id']],'evidence_ids':[evidence['id']],'note':NOTE})
        post(c,'/api/auth/simulate',{'role':'approver','acknowledge_simulation':True});body={'recovery_id':prepared['id'],'digest':prepared['digest']};post(c,'/api/recovery/release-approve',body)
        receipt=post(c,'/api/recovery/recovery-execute',{**body,'idempotency_key':'fresh-recovery-ack-100'});assert post(c,'/api/recovery/recovery-execute',{**body,'idempotency_key':'fresh-recovery-ack-100'})==receipt
        checkpoint('700-applied-100-acknowledged');assert s['quantities']['applied_hold_units']==700 and s['quantities']['confirmed_recovery_units']==100 and len(s['receipts'])==2
        post(c,'/api/auth/simulate',{'role':'preparer','acknowledge_simulation':True});handover=generate('handover','shift-brief')['draft'];post(c,route+'/handover-review',{'handover_id':handover['id'],'reviewed':True,'note':NOTE})
        checkpoint('complete');safe_save(OUT/'product-packet.json',c.get(route+'/export').json())
        safe_save(OUT/'product-flow.json',{'status':'completed','case_id':s['id'],'actual_gemma_jobs':calls,'events':events,'original_receipts':len(s['receipts']),'recovery_receipts':len(s['recovery_receipts']),'quantities':s['quantities'],'review_provenance':NOTE,
            'engineering_end_to_end_ms':round((time.perf_counter()-start)*1000),'timing_limits':'Scripted engineering timing includes model waiting and scripted correction/review; no independent operator comparison or claimed 30% improvement.','evolus':'This walkthrough uses the direct managed Gemma adapter. Real Evolus workflow acceptance is separate.'})
    except Exception as error:
        safe_save(OUT/'product-flow-blocked.json',{'status':'blocked at '+phase,'error':str(error)[:1500],'case_id':s['id'],'attempted_jobs':calls,'events':events,'review_provenance':NOTE});raise
    finally:refresh_quota('after-product-flow')


if __name__=='__main__':run()
