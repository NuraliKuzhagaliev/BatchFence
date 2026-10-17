"""Actual exported API envelopes; all network calls here are simulated."""
import copy,json
from datetime import datetime,timezone,timedelta
import httpx,pytest
from backend import evolus_api as api,evolus_adapter as external,assisted as a,repository as repo,app as module
from backend.domain import DomainError
from backend.review_safety import require_language_review
from tests.test_continuation import client,post,get,upload,ref,NOTE,image_body


def credentials(monkeypatch):
    for key,value in {'EVOLUS_API_BASE_URL':'https://api.evolus.ai','EVOLUS_API_KEY':'synthetic-application-key','EVOLUS_APPLICATION_ID':'synthetic-app'}.items():monkeypatch.setenv(key,value)


def test_actual_export_202_and_completed_step_envelopes(monkeypatch):
    credentials(monkeypatch)
    def handler(req):
        assert req.headers['X-ApiKey']=='synthetic-application-key'
        assert 'multipart/form-data' in req.headers['Content-Type'] and b'name="input"' in req.content
        return httpx.Response(202,json={'executionId':'execution-1','jobId':'job-1','enqueuedAt':'2026-10-17T00:00:00Z','traceId':'trace-1'})
    result=api.workflow_start({'workflow_id':'flow-1','text':'Untrusted source context','file_items':[{'filename':'notice.txt','raw':b'SUP-A may be affected','media_type':'text/plain'}]},httpx.MockTransport(handler))
    assert result['result']['status']=='running' and result['result']['execution_id']=='execution-1'
    manifest={'workflow_id':'flow-1','extractor':{'step_id':'extract-step','resource_id':'extract-agent','model_key':'own/gemma'},'agent':{'step_id':'agent-step','resource_id':'interpret-agent','model_key':'own/gemma'}}
    raw={'id':'execution-1','workflowId':'flow-1','status':'Completed','output':json.dumps({'candidates':[],'unresolved':['Unknown scope']}),'stepStates':{'extract-step':{'durationMs':140},'agent-step':{'durationMs':210}},'stepOutputs':{'extract-step':'{}','agent-step':'{}'},'consumption':{'credits':None,'pendingEntries':2}}
    normalized=api.normalize_execution(raw,manifest)
    assert normalized['status']=='completed' and len(normalized['steps'])==2
    assert all('model_id' not in s for s in normalized['steps'])
    assert normalized['consumption']['credits'] is None and 'Not returned' in normalized['runtime_model_identity']
    with pytest.raises(DomainError):api.normalize_execution({**raw,'workflowId':'other-flow'},manifest)


def test_library_membership_checked_before_any_chunk_read(monkeypatch):
    credentials(monkeypatch);calls=[]
    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(200,json=[{'id':'known-document'},{'id':'wrong-product-document'}])
    binding={'library_id':'library-1','documents':[{'remote_document_id':'known-document','document_id':'PROC-100','version':1}]}
    with pytest.raises(DomainError,match='before reading'):api.library_passages(binding,[{'document_id':'PROC-100','version':1,'quote':'Required original passage'}],httpx.MockTransport(handler))
    assert calls==['/api/v1/memories/library-1/documents']


def test_knowledge_applicability_is_before_external_retrieval():
    now=datetime.now(timezone.utc)
    base={'id':'PROC-1','version':1,'source_hash':'hash','status':'approved','products':['NX-1'],'processes':['coating'],'valid_from':(now-timedelta(days=1)).isoformat(),'valid_to':None,'synthetic':False}
    assert api.applicable_documents([base], 'NX-2','coating',False)==[]
    assert api.applicable_documents([{**base,'valid_to':(now-timedelta(seconds=1)).isoformat()}],'NX-1','coating',False)==[]
    assert api.library_scope('org:a','NX-1','coating',[base])!=api.library_scope('org:b','NX-1','coating',[base])
    assert api.library_scope('org:a','NX-1','coating',[base])!=api.library_scope('org:a','NX-2','coating',[base])
    with pytest.raises(DomainError):api.applicable_documents([base,{**base,'version':2}], 'NX-1','coating',False)


def test_real_proposal_drives_existing_review_but_not_facts(client,monkeypatch):
    s=post(client,'/api/cases/demo');s=upload(client,s,'Supplier lot SUP-A is affected. This notice covers only SUP-A; the supplier declares the incident list complete.')
    doc=s['documents'][-1];route='/api/cases/'+s['id']
    raw={'candidates':[{'kind':'supplier_lot','value':'SUP-A','disposition':'asserted','source':ref(doc)}],'changes':[],'contradictions':[],'unresolved':[],'request_drafts':[]}
    monkeypatch.setattr(external,'reserve',lambda *args:{'synthetic_test':True});monkeypatch.setattr(external,'allowance',lambda *args:{})
    monkeypatch.setattr(external,'gemma',lambda *args,**kwargs:{'result':copy.deepcopy(raw),'provider':'Simulated Gemma adapter / not live','model_id':'synthetic-model','elapsed_ms':1})
    b={'kind':'document','revision':s['revision'],'document_ids':[doc['id']],'idempotency_key':'proposal-intake-test'}
    proposal=post(client,route+'/assist-generate',b);assert proposal['status']=='unreviewed proposal'
    before=get(client,route);assert before['plan'] is None and before['reviews']==[]
    state=post(client,route+'/assist-intake',{'proposal_id':proposal['id'],'document_id':doc['id'],'revision':s['revision']})
    assert state['plan'] is None and state['runs'][-1]['output']['facts'][0]['lot_id']=='SUP-A'
    assert state['runs'][-1]['model_id']=='synthetic-model' and state['scope']==before['scope']
    reviewed=post(client,route+'/reviews',{'run_id':state['runs'][-1]['id'],'revision':state['revision'],'lot_ids':['SUP-A'],'uncertain_lot_ids':[],'excluded_lot_ids':[],'lot_corrections':{},'accept_scope':True,'incident_scope_status':'resolved','resolution_quote':ref(doc)['quote'],'bounded_scope_reviewed':True,'note':NOTE})
    assert reviewed['plan']['result']['hold_units']==500 and not reviewed['receipts']
    assert post(client,route+'/assist-generate',b)==proposal


def test_language_review_is_enforced_outside_translation_panel(client):
    s=post(client,'/api/cases/demo');s=upload(client,s,'SUP-A incluso. Elenco completo.',evidence_language='it');doc=s['documents'][-1];route='/api/cases/'+s['id']
    with pytest.raises(DomainError):require_language_review(doc)
    tr=post(client,route+'/translation',{'document_id':doc['id'],'language':'it','segments':[{'source':ref(doc),'translation':'SUP-A included. Complete list.'}],'provenance_reference':'Synthetic engineering bilingual check','idempotency_key':'qualified-guard-test'})
    with pytest.raises(DomainError):require_language_review(get(client,route)['documents'][-1])
    post(client,route+'/translation-review',{'translation_id':tr['id'],'can_verify_original':True,'qualified_reference':'Agent-operated language engineering test; no independent acceptance','critical_fields_confirmed':True,'note':NOTE})
    require_language_review(get(client,route)['documents'][-1])


def test_handover_stales_on_material_label_record_and_requires_quantities(client):
    s=post(client,'/api/cases/demo');route='/api/cases/'+s['id']
    h=post(client,route+'/handover',{'idempotency_key':'handover-before-label','previous_id':None})
    with pytest.raises(DomainError,match='omitted'):a.validate_handover(h['snapshot'],{'statements':[]})
    post(client,route+'/label-image',image_body())
    assert get(client,route+'/assisted')['handover'][0]['stale']


def test_cancelled_generation_never_enters_review(client,monkeypatch):
    s=post(client,'/api/cases/demo');route='/api/cases/'+s['id'];doc=s['documents'][0]
    monkeypatch.setattr(external,'reserve',lambda *args:{});monkeypatch.setattr(external,'allowance',lambda *args:{})
    def cancelled(*args,**kwargs):
        running=get(client,'/api/jobs')[-1]
        post(client,'/api/jobs/'+running['id']+'/cancel',{})
        return {'result':{'candidates':[],'unresolved':['No supported fact']},'provider':'Simulated transport / cancellation test'}
    monkeypatch.setattr(external,'gemma',cancelled)
    result=post(client,route+'/assist-generate',{'kind':'document','document_ids':[doc['id']],'revision':s['revision'],'idempotency_key':'cancel-during-model'})
    assert result['status']=='obsolete / changed or cancelled' and 'draft' not in result
    assert get(client,route)['plan'] is None
