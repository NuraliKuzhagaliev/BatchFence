"""Focused source, language and transport controls; no live calls."""
import copy,json,base64,io
from pathlib import Path
import pytest
import httpx
from backend import knowledge
from backend.domain import digest,DomainError
from tests.test_api import client,post


def procedure(text,identity='SOP-FOCUSED'):
    passages=[{'id':'p1','page':1,'text':text}]
    return {'id':identity,'version':1,'status':'approved','valid_from':'2026-01-01T00:00:00Z','valid_to':None,'products':['Decorative housing'],'processes':['coating'],'owner':'Fictional quality reviewer','passages':passages,'source_hash':digest(passages),'synthetic':True}


@pytest.mark.parametrize('question,text',[
    ('Какие доказательства нужны для снятия блокировки?','Для снятия блокировки нужны доказательства проверки и отдельное разрешение. Не снимать блокировку автоматически.'),
    ('Which evidence is required for recovery?','Recovery requires recorded evidence and a separate approval; never release automatically.'),
    ('Quali prove sono necessarie per il rilascio?','Il rilascio richiede prove registrate e una approvazione separata; non autorizza un rilascio automatico.'),
    ('VERIFICA QUALITÀ','Verifica qualita\u0300 e revisione: nessun rilascio automatico.'),
])
def test_unicode_supported_lexical_originals(client,question,text):
    state=post(client,'/api/cases/demo');d=procedure(text)
    post(client,'/api/knowledge/procedure-review',{'document':d,'reviewed':True,'note':'Agent-operated fictional procedure applicability review.'})
    result=post(client,'/api/knowledge/answer',{'case_id':state['id'],'question':question,'product':'Decorative housing','process':'coating','mode':'fixture'})
    assert result['status']=='succeeded'
    assert result['output']['claims'][0]['quote']==text
    assert result['retrieval']['passages'][0]['source_hash']==d['source_hash']


def test_cross_language_irrelevance_and_identifier_boundaries():
    d=procedure('Recovery requires recorded evidence and separate approval.')
    assert knowledge.retrieve([d],'Какие доказательства нужны для снятия блокировки?','Decorative housing','coating',True)['status']=='insufficient'
    assert knowledge.retrieve([d],'unrelated astronomy nebula','Decorative housing','coating',True)['status']=='insufficient'
    assert knowledge.lexical_terms('LOT-0007 O0 AА')=={'lot','0007','o0','aа'}
    assert knowledge.lexical_terms('A')!=knowledge.lexical_terms('А')
    old=copy.deepcopy(d);old['status']='obsolete'
    assert knowledge.retrieve([old],'recovery evidence','Decorative housing','coating',True)['status']=='insufficient'
    with pytest.raises(DomainError):knowledge.retrieve([d],'x'*1001,'Decorative housing','coating',True)


def test_ui_encoding_literals_repaired_without_rewriting_evidence():
    root=Path(__file__).resolve().parents[1]
    text=(root/'frontend/main.tsx').read_text(encoding='utf-8')
    assert '\u0412\u00b7' not in text and '\u0432\u0402\u2122' not in text and '\u0432\u2020\u2019' not in text
    assert '·' in text and 'workspace’s inventory' in text


def test_submission_parse_failure_retains_known_execution_id(monkeypatch):
    from backend import evolus_api
    monkeypatch.setenv('EVOLUS_API_BASE_URL','https://api.evolus.ai')
    monkeypatch.setenv('EVOLUS_API_KEY','test-key');monkeypatch.setenv('EVOLUS_APPLICATION_ID','app')
    eid='11111111-1111-1111-1111-111111111111'
    def handler(request):return httpx.Response(202,headers={'x-workflow-execution-id':eid},content=b'broken-json')
    with pytest.raises(evolus_api.UncertainExecution) as failure:
        evolus_api.workflow_start({'workflow_id':'flow','text':'Fictional source','file_items':[]},httpx.MockTransport(handler))
    assert failure.value.execution_id==eid


def test_uncertain_submission_deduplicates_and_reconciles_without_new_inference(client,monkeypatch):
    from backend import evolus_adapter as external,evolus_api
    state=post(client,'/api/cases/demo');doc=state['documents'][0];r='/api/cases/'+state['id'];calls=[]
    monkeypatch.setattr(external,'contract',lambda:{})
    monkeypatch.setattr(external,'reserve',lambda *a,**k:{'injected':True})
    for k,v in {'EVOLUS_WORKFLOW_ID':'flow','EVOLUS_EXTRACTOR_ID':'extractor','EVOLUS_AGENT_ID':'agent','EVOLUS_GEMMA_MODEL_KEY':'own/test','GEMMA_MODEL_ID':'test'}.items():monkeypatch.setenv(k,v)
    eid='11111111-1111-1111-1111-111111111111'
    def operation(name,inputs,**kwargs):
        calls.append(name)
        if name=='workflow_start':raise evolus_api.UncertainExecution(eid)
        return {'result':{'execution_id':eid,'status':'completed','draft':{'candidates':[],'unresolved':['No supported supplier lot in this injected source.']},'steps':[{'kind':'extractor','id':'extractor'},{'kind':'agent','id':'agent','configured_model_key':'own/test'}]}}
    monkeypatch.setattr(external,'operation',operation)
    payload={'document_ids':[doc['id']],'revision':state['revision'],'idempotency_key':'uncertain-first','mode':'live'}
    first=post(client,r+'/assist-run',payload);assert first['external_execution_id']==eid
    again=post(client,r+'/assist-run',{**payload,'idempotency_key':'uncertain-other'})
    assert again['id']==first['id'] and calls==['workflow_start']
    done=post(client,r+'/assist-poll',{'job_id':first['id']});assert done['status']=='unreviewed proposal'
    repeat=post(client,r+'/assist-poll',{'job_id':first['id']});assert repeat['id']==done['id']
    assert calls==['workflow_start','workflow_status']
    assert client.get(r).json()['plan'] is None and client.get(r).json()['receipts']==[]


def test_original_pdf_envelope_keeps_all_pages_and_rejects_unsafe_input(client):
    from pypdf import PdfReader,PdfWriter
    from backend import app as module
    state=post(client,'/api/cases/demo');route='/api/cases/'+state['id'];root=Path(__file__).resolve().parents[1]
    raw=(root/'evals/evolus-focused-v1/incomplete.pdf').read_bytes()
    good=post(client,route+'/documents',{'filename':'retained-original.pdf','content_base64':base64.b64encode(raw).decode(),'synthetic':True})
    d=good['documents'][-1];assert d['page_count']==2 and {b['page'] for b in d['blocks']}=={1,2}
    assert any('under dispute' in b['text'] for b in d['blocks'])
    for broken in (b'not a PDF',b'%PDF-1.7\ntruncated'):
        assert client.post(route+'/documents',json={'filename':'invalid.pdf','content_base64':base64.b64encode(broken).decode(),'synthetic':True}).status_code==422
    w=PdfWriter();w.clone_document_from_reader(PdfReader(io.BytesIO(raw)));w.encrypt('synthetic-unit-password');b=io.BytesIO();w.write(b)
    assert client.post(route+'/documents',json={'filename':'locked.pdf','content_base64':base64.b64encode(b.getvalue()).decode(),'synthetic':True}).status_code==422
    w=PdfWriter()
    for i in range(9):w.add_blank_page(width=612,height=792)
    b=io.BytesIO();w.write(b)
    assert client.post(route+'/documents',json={'filename':'too-many-pages.pdf','content_base64':base64.b64encode(b.getvalue()).decode(),'synthetic':True}).status_code==422
    final=client.get(route).json();assert len(final['documents'])==len(state['documents'])+1 and final['receipts']==[]


def test_funded_credits_keep_phase_boundary_and_metadata_separate(client,tmp_path,monkeypatch):
    from datetime import datetime,timezone,timedelta
    from backend import app as module,evolus_adapter as e
    at=datetime.now(timezone.utc);expiry=at+timedelta(hours=2)
    proof={'provider':'evolus','phase_id':'synthetic-focused','allowance_id':'synthetic-focused','verified_at':at.isoformat(),'expires_at':expiry.isoformat(),'max_dispatches':10,'remaining_credits':50000,'stop_margin':49000,'max_credits_per_dispatch':100,'additional_cash_limit':0,'storage_network_cash_limit':0,'overages_disabled':True,'platform_credit_cap':1000,'ocr_credits_per_page':10.466666666666667,'max_ocr_pages_per_dispatch':8,'embedding_indexing_authorized':False,'evidence_reference':'Injected current event proof, not live evidence','provider_enforced_boundary':{'kind':'event-trial-bounded-document-credits','additional_cash_overages':False,'renews_automatically':False,'trial_ends_at':expiry.isoformat()}}
    p=tmp_path/'proof.json';p.write_text(json.dumps(proof));monkeypatch.setenv('EVOLUS_COST_APPROVAL_FILE',str(p));monkeypatch.setenv('EVOLUS_COST_APPROVAL_JSON',json.dumps(proof))
    with module.connect() as db:
        m=e.reserve(db,'evolus',metadata=True);assert m['model_dispatches']==0
        assert e.reserve(db,'evolus')['dispatch']==1
    monkeypatch.setenv('EVOLUS_COST_APPROVAL_JSON',json.dumps({**proof,'embedding_indexing_authorized':True}))
    with pytest.raises(DomainError):e.allowance('evolus')


def test_rag_agent_uses_documented_agentid_and_retains_before_binding(monkeypatch):
    from backend import evolus_rag as rag
    monkeypatch.setenv('EVOLUS_GEMMA_MODEL_KEY','own/test');events=[]
    def call(method,path,**kwargs):
        events.append(path)
        return {'result':{'agentId':'known-agent'}} if path=='/api/v1/agents' else {'result':None}
    monkeypatch.setattr(rag.api,'call',call)
    result=rag.create_agent('known-library',retain=lambda value:events.append('retained:'+value['agent_id']))
    assert result['agent_id']=='known-agent'
    assert events==['/api/v1/agents','retained:known-agent','/api/v1/agents/known-agent/memories']


def test_rag_missing_foreign_and_obsolete_citations_abstain_full_passage_retained():
    from backend import evolus_rag as rag
    d=procedure('Recorded evidence and separate approval are required. A citation never releases an applied hold.')
    retrieval={'passages':[{'document_id':d['id'],'version':1,'passage_id':'p1','quote':d['passages'][0]['text']}]}
    selected={'selections':[{'document_id':d['id'],'version':1,'passage_id':'p1'}],'insufficient_evidence':False,'missing_information':[]}
    raw={'answer':json.dumps(selected),'citations':[]};binding={'documents':[{'document_id':d['id'],'version':1,'remote_document_id':'remote-current'}]}
    # Exact fresh failure: correct passage key, but zero returned provider citations.
    with pytest.raises(DomainError,match='lacks a returned citation'):rag.map_answer(raw,binding,retrieval)
    for foreign in ('remote-obsolete','remote-other-tenant'):
        with pytest.raises(DomainError,match='outside-scope'):rag.map_answer({**raw,'citations':[{'documentId':foreign}]},binding,retrieval)
    answer=rag.map_answer({**raw,'citations':[{'documentId':'remote-current'}]},binding,retrieval)
    assert answer['claims'][0]['quote']==d['passages'][0]['text']
    assert 'never releases' in answer['claims'][0]['quote']
    with pytest.raises(DomainError):rag.map_answer({'answer':'malformed','citations':[]},binding,retrieval)


def test_rag_unverified_capability_blocks_before_dispatch(client,monkeypatch):
    from backend import evolus_adapter as e
    s=post(client,'/api/cases/demo');monkeypatch.delenv('EVOLUS_RAG_ENABLED',raising=False)
    monkeypatch.setattr(e,'gemma',lambda *a,**k:pytest.fail('Blocked mode dispatched a model'))
    result=client.post('/api/cases/'+s['id']+'/assist-generate',json={'kind':'knowledge','retrieval_mode':'rag','revision':s['revision'],'idempotency_key':'blocked-rag-citations','question':'Recovery evidence?','product':'Decorative housing','process':'coating'})
    assert result.status_code==422 and 'no resolvable citations' in result.text


def test_rag_membership_or_incomplete_index_prevents_content_read(monkeypatch):
    from backend import evolus_api as api
    binding={'library_id':'isolated','library_type':'Rag','documents':[{'remote_document_id':'expected'}]};calls=[]
    def call(*args,**kwargs):calls.append(args);return {'result':[{'id':'expected','ingestionStatus':1}]}
    monkeypatch.setattr(api,'call',call)
    with pytest.raises(DomainError,match='not complete'):api.library_passages(binding,[])
    assert len(calls)==1
    monkeypatch.setattr(api,'call',lambda *a,**k:{'result':[{'id':'outside','ingestionStatus':2}]})
    with pytest.raises(DomainError,match='membership drifted'):api.library_passages(binding,[])


def test_rag_unauthorized_fictional_source_has_no_remote_upload(client,monkeypatch):
    from backend import evolus_adapter as e,evolus_api as api
    post(client,'/api/cases/demo');d=procedure('Review evidence before any release.')
    post(client,'/api/knowledge/procedure-review',{'document':d,'reviewed':True,'note':'Synthetic regression for exact authorized hash egress boundary.'})
    monkeypatch.setattr(e,'allowance',lambda *a:{'embedding_indexing_authorized':True,'rag_source_hashes':['different'],'rag_max_documents':1})
    monkeypatch.setattr(api,'call',lambda *a,**k:pytest.fail('Unauthorized source reached provider'))
    result=client.post('/api/assist/knowledge-index',json={'library_type':'Rag','product':'Decorative housing','process':'coating','synthetic':True,'reviewed':True,'note':'No remote action allowed with a source outside this exact test phase.'})
    assert result.status_code==422 and 'exact fictional hashes' in result.text
