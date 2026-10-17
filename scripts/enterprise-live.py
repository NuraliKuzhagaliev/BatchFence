"""Staged, four-request AMD acceptance. Inspect raw output before review steps.

All inputs are synthetic; named identities are operated by the agent. This is
engineering evidence, never independent manufacturing or operator validation.
"""
import base64
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
V2 = '--receiving-v2' in sys.argv
OUT = ROOT / ('docs/enterprise/live/fresh/receiving-v2' if V2 else 'docs/enterprise/live/fresh')
PRIVATE = ROOT / ('work/enterprise-live-v2' if V2 else 'work/enterprise-live')
OUT.mkdir(parents=True, exist_ok=True)
PRIVATE.mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT / '.env')
step = sys.argv[1]
config_path = PRIVATE / 'private.json'
if step == 'init':
    assert not config_path.exists(), 'Preserve existing run; select its next stage'
    config_path.write_text(json.dumps({'session_secret': secrets.token_urlsafe(48),
        'password': secrets.token_urlsafe(32), 'calls': [], 'stages': []}), encoding='utf-8')
private = json.loads(config_path.read_text())
os.environ.update(DATABASE_PATH=str(PRIVATE / 'state.sqlite3'),
    SOURCE_STORAGE_PATH=str(PRIVATE / 'sources'), DEPLOYMENT_PROFILE='pilot',
    PILOT_DATABASE_URL='', PILOT_SESSION_SECRET=private['session_secret'],
    PILOT_AMD_DATA_APPROVED='true', PUBLIC_DEMO='false', LIVE_DEMO_TOKEN='',
    APP_ORIGIN='http://127.0.0.1:8795', MAX_REQUESTS_PER_MINUTE='1000',
    MAX_SESSION_REQUESTS_PER_MINUTE='1000', MAX_ORG_LIVE_JOBS='4', MAX_USER_LIVE_JOBS='4')
from backend import app as module, repository as repo, identity
from fastapi.testclient import TestClient
from tests.test_api import post, review, approve, payload

NOTE = 'Agent-operated review of synthetic engineering evidence; not independent human, supplier, or manufacturing validation.'
PARTIAL = 'Receiving record REC-954 references FG-C and supplier lot SUP-B. FG-C received some material from SUP-B. Other receipts have not been reconciled. The full ancestry remains unknown; this partial record cannot exclude other parent lots.'
COMPLETE = 'Signed receiving reconciliation REC-955: all 100 pieces in FG-C came exclusively from supplier lot SUP-B, with no additional parents. The receiver reconciled every receipt and authenticated the original supplier record. This complete reconciliation supersedes lineage rows LIN-3 and LIN-4. REC-955 is a receipt identifier; FG-C is a stock pool; SUP-B is the supplier lot.'
INSPECTION = 'FG-C: 100 pieces inspected using visual-v1; 0 nonconforming. Passed whole-pool cosmetic inspection.'

def save(name, value):
    text = json.dumps(value, indent=2, ensure_ascii=False)
    assert os.environ['AMD_API_KEY'] not in text and private['password'] not in text
    (OUT / (name + '.json')).write_text(text, encoding='utf-8')

def get(c, path):
    r = c.get(path); assert r.status_code == 200, r.text
    return r.json()

def login(role='reviewer'):
    c = TestClient(module.app)
    post(c, '/api/auth/login', {'username':'fresh-'+role, 'password':private['password'], 'org':'liveeval', 'site':'synthetic'})
    return c

def upload(c, state, text, filename, request_id=None):
    data = {'filename':filename, 'content_base64':base64.b64encode(text.encode()).decode(), 'synthetic':True}
    if request_id:data['request_id'] = request_id
    return post(c, '/api/cases/'+state['id']+'/documents', data)

def reserve(name):
    access = json.loads((ROOT/'docs/enterprise/live/access-recheck.json').read_text())
    assert access['cost_gate']=='verified zero additional charge for shared event endpoint'
    assert access['base_url']==os.environ['AMD_API_BASE_URL'].rstrip('/') and access['requested_model_id']==os.environ['AMD_MODEL_ID']
    assert len(private['calls'])<(2 if V2 else 4) and name not in private['calls'], 'Finite request cap or repeated stage'
    if V2:
        assert access.get('followup_authorized') is True, 'Two-call follow-up requires explicit approval after automatic review blocked the extension'
        assert name in ('partial','complete'), 'Only the two concrete receiving retests are eligible'
    total=sum(len(json.loads(p.read_text())['calls']) for p in (ROOT/'work/enterprise-live/private.json', ROOT/'work/enterprise-live-v2/private.json') if p.exists())
    assert total<6, 'Global bounded evaluation cap exhausted'
    private['calls'].append(name)
    config_path.write_text(json.dumps(private), encoding='utf-8')

try:
    if step=='init':
        with repo.write(module.connect) as db:
            for role, roles in [('reviewer',['reporter','quality_reviewer']),('releaser',['reporter','release_approver'])]:
                identity.create_user(db,'fresh-'+role,private['password'],'liveeval','synthetic',roles)
        c=login();s=post(c,'/api/cases/demo')
        s=post(c,'/api/enterprise/example',{'case_id':s['id'],'acknowledged_synthetic':True})
        s=upload(c,s,INSPECTION,'whole-pool-inspection.txt');private['inspection']=s['documents'][-1]['id']
        route='/api/cases/'+s['id'];private['case_id']=s['id']
        s=approve(c,review(c,s));assert s['plan']['result']['hold_units']==500
        old=payload(s,'fresh-setup-500');s=post(c,route+'/apply',old)
        s=post(c,route+'/revision')
        stale=c.post(route+'/apply',json={**old,'idempotency_key':'fresh-stale-attempt'});assert stale.status_code==409
        s=approve(c,review(c,s,True));assert s['plan']['result']['hold_units']==800
        s=post(c,route+'/apply',payload(s,'fresh-setup-800'));assert s['quantities']['applied_hold_units']==800
        save('setup',{'provenance':'Synthetic fixture extraction and agent review; zero AMD calls', 'case_id':s['id'], 'stale_http':stale.status_code, 'receipts':s['receipts'], 'quantities':s['quantities']})
        obs=get(c,'/api/inspections')
        base=post(c,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in obs['rows'] if r['observation_id'].startswith('BASE-')], 'inspection_revision':obs['revision'],'stable_reviewed':True,'note':NOTE})
        private['baseline_id']=base['id']
        frozen=json.loads((ROOT/'evals/enterprise/frozen-v1.json').read_text())
        inputs={'receiving_partial':PARTIAL,'receiving_complete':COMPLETE,
            'knowledge':next(i for i in frozen['items'] if i['id']=='KNW-01'),
            'signal_chart':get(c,'/api/signals')['results'][0],
            'cap':4,'provenance':'Inputs frozen before calls; two new typed receiving cases, one exact frozen KNW-01 question (applicability label mapped), one synthetic chart. Not 24-item benchmark coverage.'}
        save('inputs',inputs);save('inputs-hash',{'sha256':hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest()})
    else:
        c=login();route='/api/cases/'+private['case_id'];s=get(c,route)
        if step in ('partial','complete'):
            q=next(q for q in s['plan']['result']['requests'] if q['pool_ids']==['FG-C'])
            s=upload(c,s,PARTIAL if step=='partial' else COMPLETE, 'receiving-'+step+'-20261017.txt',q['id'])
            private[step+'_document']=s['documents'][-1]['id']
            reserve(step)
            s=post(c,route+'/receiving-draft',{'document_id':private[step+'_document'],'mode':'live'})
            save(step+'-raw',s['receiving_runs'][-1]);save(step+'-before-review',get(c,route+'/export'))
            print(json.dumps(s['receiving_runs'][-1],indent=2))
        elif step in ('review-partial','review-complete'):
            full=step=='review-complete';name='complete' if full else 'partial'
            run=s['receiving_runs'][-1]
            assert run['mode']=='live' and run['document_id']==private[name+'_document']
            if full:
                assert run['output']['parent_ids']==['SUP-B'] and run['output']['completeness']=='complete'
                assert any(e['id']=='SUP-B' and e['kind']=='supplier_lot' for e in run['output']['entities'])
            data={'revision':s['revision'],'document_id':private[name+'_document'],'review_path':'narrative_draft' if run['status']=='succeeded' or not full else 'structured_record','run_id':run['id'],
                'pool_id':'FG-C','parent_ids':['SUP-B'],'complete':full,'quote':COMPLETE if full else PARTIAL,
                'superseded_row_ids':['LIN-3','LIN-4'] if full else [],'unresolved_contradictions':False,'outcome':'resolved' if full else 'inconclusive',
                'reviewed':True,'replacement_reviewed':True,'completeness_confirmed':full,'note':NOTE+' '+('Full source explicitly reconciles every parent and supersedes both rows.' if full else 'Partial ancestry cannot exclude other lots. Preserve existing relationships and restrictions.')}
            if full and V2:
                data['note']+=' Reviewed the model caution against stored LIN-3 (SUP-A possible) and LIN-4 (SUP-B possible); the complete authenticated synthetic reconciliation explicitly replaces both. This resolves the record question, not an automatic acceptance of model completeness.'
            if full and run['status']=='failed':
                denied=c.post(route+'/receiving-preview',json={**data,'review_path':'narrative_draft'})
                assert denied.status_code==422
                save('failed-narrative-rejection',{'http_status':denied.status_code,'body':denied.json(),'raw_status':run['status'],'correction':'Agent discarded unsupported internal IDs, inspected the original source and both superseded rows, then explicitly used structured-record review. Raw model failure remains unchanged.'})
            preview=post(c,route+'/receiving-preview',data)
            assert preview['after_units']==(700 if full else 800) and preview['applied_hold_units']==800
            s=post(c,route+'/receiving-review',data)
            assert s['quantities']['applied_hold_units']==800 and len(s['receipts'])==2
            save(step,{'review':data,'preview':preview,'quantities':s['quantities'],'proposal_units':s['plan']['result']['hold_units']})
            save(step+'-packet',get(c,route+'/export'))
        elif step=='knowledge':
            question=json.loads((OUT/'inputs.json').read_text())['knowledge']['question']
            reserve(step)
            result=post(c,'/api/knowledge/answer',{'case_id':s['id'],'question':question,'product':'Decorative housing','process':'coating','mode':'live'})
            private['answer_id']=result['id'];save('knowledge-raw',result);print(json.dumps(result,indent=2))
        elif step=='signal':
            result=next(x for x in get(c,'/api/signals')['results'] if x['baseline']['id']==private['baseline_id'])
            reserve(step)
            run=post(c,'/api/signals/explain',{'baseline_id':private['baseline_id'],'chart_digest':result['chart_digest'],'mode':'live'})
            save('signal-raw',run);print(json.dumps(run,indent=2))
        elif step=='finish-reviewed-workflow':
            assert s['plan']['result']['hold_units']==700 and s['quantities']['applied_hold_units']==800
            original_receipts=s['receipts']
            post(c,'/api/recovery/policy-review',{'reviewed':True,'note':NOTE,'expected_revision':0,'procedure_refs':['PROC-100@1']})
            evidence=post(c,route+'/recovery-evidence',{'revision':s['revision'],'pool_id':'FG-C',
                'receiving_document_id':private['complete_document'],'receiving_quote':COMPLETE,'authenticity_verified':True,
                'verification_reference':'Synthetic REC-955 record inspected by the operating agent; no external supplier verification',
                'inspection_document_id':private['inspection'],'inspection_quote':INSPECTION,
                'inspected_units':100,'nonconforming_units':0,'inspection_passed':True,'inspected_at':datetime.now(timezone.utc).isoformat(),'note':NOTE})
            hold=next(h for h in get(c,route+'/recovery')['holds'] if h['pool_id']=='FG-C' and h['incident_id']==s['id'] and h['status']=='active')
            proposal=post(c,route+'/recovery-prepare',{'hold_ids':[hold['id']],'evidence_ids':[evidence['id']],'note':NOTE})
            body={'recovery_id':proposal['id'],'digest':proposal['digest']}
            denied=c.post('/api/recovery/release-approve',json=body);assert denied.status_code in (403,422)
            releaser=login('releaser');approved=post(releaser,'/api/recovery/release-approve',body)
            receipt=post(releaser,'/api/recovery/recovery-execute',{**body,'idempotency_key':'fresh-reviewed-recovery-100'})
            duplicate=post(releaser,'/api/recovery/recovery-execute',{**body,'idempotency_key':'fresh-reviewed-recovery-100'});assert duplicate==receipt
            s=get(c,route);assert s['quantities']=={'applied_hold_units':700,'recovery_pending_units':0,'confirmed_recovery_units':100}
            assert s['receipts']==original_receipts and len(s['recovery_receipts'])==1
            save('recovery',{'approval':approved,'receipt':receipt,'quantities':s['quantities'],'duplicate_identical':True,'reviewer_approval_http':denied.status_code,'original_containment_receipts_unchanged':True,'provenance':('Explicit source review of accepted fresh AMD typed draft' if V2 else 'Explicit agent-operated structured correction after AMD draft failure')+'; distinct named engineering identities, no independent humans or real inventory.'})
            if V2:
                save('final-packet',get(c,route+'/export'))
                save('workflow-summary',{'at':datetime.now(timezone.utc).isoformat(),'fresh_calls':2,'raw_receiving_schema_source_successes':2,'raw_receiving_trials':2,'partial_result':'partial with unresolved other parents; reviewed inconclusive; 800 applied retained','complete_result':'SUP-B typed supplier parent; explicit row/source/completeness review required','model_caution':'Missing old lineage content flagged as possible contradiction; agent inspected both current rows before resolving','proposal_units':700,'applied_before_recovery':800,'confirmed_recovery_units':100,'remaining_applied':700,'containment_receipts':2,'recovery_receipts':1,'provenance':'Repeated inputs after context fix, not new held-out cases; genuine AMD-backed narrative draft drives explicit review and controlled sandbox recovery. All review agent-operated.'})
                private['stages'].append(step)
                print(json.dumps({'stage':step,'raw_source_valid_trials':2,'recovery_units':100,'fresh_calls':2}))
                raise SystemExit(0)
            answer=json.loads((OUT/'knowledge-raw.json').read_text());assert answer['status']=='succeeded'
            assert answer['output']['claims'][0]['document_id']=='PROC-100' and answer['output']['claims'][0]['passage_id']=='P1'
            proof='Synthetic check record: REC-955 source authenticity was inspected by the agent; FG-C complete SUP-B ancestry and both replaced rows were reviewed; the retained whole-pool inspection records 100 inspected pieces with zero nonconforming. Separate reviewed sandbox recovery receipt confirms 100 units.'
            s=upload(c,s,proof,'reviewed-procedure-check.txt');doc=s['documents'][-1]
            s=post(c,route+'/knowledge-check',{'answer_id':answer['id'],'claim_index':0,'evidence_document_id':doc['id'],'evidence_quote':proof,'reviewed':True,'note':NOTE+' Explicitly checked the fresh AMD-selected PROC-100@1/P1 against the retained receiving, inspection and recovery evidence.'})
            assert s['procedure_checks'][-1]['procedure']==answer['output']['claims'][0]
            signal=json.loads((OUT/'signal-raw.json').read_text());assert signal['status']=='succeeded'
            chart=next(x for x in get(c,'/api/signals')['results'] if x['baseline']['id']==private['baseline_id'])
            args={'baseline_id':private['baseline_id'],'chart_digest':chart['chart_digest'],'source_case_id':s['id']}
            invalid=c.post('/api/signals/investigation',json={**args,'observation_id':'STABLE-001'});assert invalid.status_code==422
            linked=post(c,'/api/signals/investigation',{**args,'observation_id':'SHIFT-001'})
            investigation=get(c,'/api/cases/'+linked['case_id'])
            assert investigation['origin_signal']['known_affected']==[] and investigation['plan'] is None and investigation['receipts']==[]
            save('signal-review',{'raw_semantic_error':'First comment incorrectly calls STABLE-001..STABLE-020 the baseline; actual frozen rows are BASE-001..BASE-020. Schema/ID validation does not establish semantic correctness.','correct_baseline_ids':[r['observation_id'] for r in chart['baseline']['rows']],'raw_non_signal_investigation_http':invalid.status_code,'reviewed_signal_id':'SHIFT-001','linked_investigation_id':linked['case_id'],'known_affected':[],'plan':None,'authority':'Agent selected the actual deterministic signal; no model-derived supplier cause, hold or release.'})
            save('final-packet',get(c,route+'/export'))
            save('workflow-summary',{'at':datetime.now(timezone.utc).isoformat(),'fresh_calls':len(private['calls']),
                'raw_receiving_successes':0,'raw_receiving_trials':2,'knowledge_exact_source_successes':1,'knowledge_trials':1,
                'signal_schema_successes':1,'signal_semantic_errors':1,'signal_trials':1,
                'proposed_units_after_explicit_correction':700,'applied_units_before_separate_recovery':800,
                'confirmed_recovery_units':100,'remaining_applied_units':700,'containment_receipts':2,'recovery_receipts':1,
                'knowledge_check_from_fresh_answer':True,'non_signal_investigation_rejected':422,
                'frozen_benchmark_items_attempted':['KNW-01'],'full_frozen_denominator':24,
                'reviewer':'Operating agent with named engineering accounts; no independent human acceptance',
                'receiving_fix_fresh_verification':'Blocked by automatic approval review after original four-call cap; original failures retained; source-only context change requires new accepted live trials.'})
        else:raise ValueError('Unknown staged step')
    private['stages'].append(step)
    print(json.dumps({'stage':step,'reserved_fresh_calls':len(private['calls']),'reviewer':'Agent-operated; not independent human acceptance'}))
finally:
    config_path.write_text(json.dumps(private),encoding='utf-8')
