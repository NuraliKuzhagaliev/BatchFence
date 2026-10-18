"""Small source-coverage and citation-contract regressions; no provider calls."""
import json
import pytest
from backend.domain import DomainError
from backend.assist_contracts import extractor_coverage, source_context
from backend import evolus_rag as rag
from tests.test_api import client


def source_state(text):
    return {'documents':[{'id':'notice','revision':1,'original_hash':'original','blocks':[{'id':'line','text':text}]}],
            'edges':[{'source':'SUP-A','target':'FG-A'},{'source':'SUP-B','target':'FG-B'},{'source':'SUP-C','target':'FG-C'}],
            'stocks':[{'id':'FG-A'},{'id':'FG-B'},{'id':'FG-C'}]}


def test_both_stages_cannot_omit_a_negated_recorded_lot():
    state=source_state('SUP-A is affected. SUP-B is not affected. SUP-C remains under investigation.')
    extraction={'kind':'supplier_lot','value':'SUP-A','quote':'SUP-A is affected.'}
    execution={'steps':[{'kind':'extractor','output':json.dumps({'candidates':[extraction]})}]}
    with pytest.raises(DomainError,match='SUP-B'):
        extractor_coverage(state,execution,{'candidates':[extraction]},['notice'])


def test_original_input_contains_source_grounded_identity_checklist_not_dispositions():
    context=source_context(source_state('SUP-A is affected; SUP-B is not affected.'),['notice'])
    values=context['required_recorded_identities']
    assert {(v['kind'],v['value']) for v in values}=={('supplier_lot','SUP-A'),('supplier_lot','SUP-B')}
    assert all(v['source']['document_id']=='notice' for v in values)
    assert all('incident_status' not in v for v in values)


def test_inventory_exact_identity_and_selected_document_boundaries():
    state=source_state('SUP-A2 is affected. SUP-B is not affected.')
    state['documents'].append({'id':'other','revision':1,'original_hash':'other','blocks':[{'id':'x','text':'SUP-C is affected.'}]})
    context=source_context(state,['notice'])
    assert [v['value'] for v in context['required_recorded_identities']]==['SUP-B']


def quoted_fixture():
    quote='Before recovery, recorded evidence and separate approval are required. A citation never releases existing holds.'
    claim={'document_id':'SOP','version':1,'passage_id':'release','quote':quote}
    retrieval={'passages':[{**claim,'source_hash':'original-hash','provider_chunk_proof':{'remote_document_id':'remote-1','source_hash':'original-hash','chunks':[{'id':'chunk-1','body_hash':'a'*64}]}}]}
    binding={'citation_protocol':rag.CITATION_PROTOCOL,'documents':[{'document_id':'SOP','version':1,'source_hash':'original-hash','remote_document_id':'remote-1'}]}
    raw={'answer':json.dumps({'selections':[{k:v for k,v in claim.items() if k!='quote'}],'insufficient_evidence':False,'missing_information':[]}),'citations':[]}
    return quote,retrieval,binding,raw


def test_full_quote_requires_independent_indexed_source_proof_not_invented_native_citation():
    quote,retrieval,binding,raw=quoted_fixture()
    assert rag.map_answer(raw,binding,retrieval)['claims']==[{'document_id':'SOP','version':1,'passage_id':'release','quote':quote}]


@pytest.mark.parametrize('failure',['missing','foreign','changed-version','changed-hash','unidentified-chunk','unsupported-prose'])
def test_full_quote_never_substitutes_plausible_keys_for_independent_source_proof(failure):
    quote,retrieval,binding,raw=quoted_fixture()
    selected=json.loads(raw['answer']);p=retrieval['passages'][0]
    if failure=='missing':p.pop('provider_chunk_proof')
    elif failure=='foreign':raw['citations']=[{'documentId':'remote-obsolete'}]
    elif failure=='changed-version':binding['documents'][0]['version']=2
    elif failure=='changed-hash':p['provider_chunk_proof']['source_hash']='different'
    elif failure=='unidentified-chunk':p['provider_chunk_proof']['chunks'][0]['id']=''
    elif failure=='unsupported-prose':selected['selections'][0]['quote']='Release all stock now.'
    raw['answer']=json.dumps(selected)
    with pytest.raises((DomainError,ValueError)):rag.map_answer(raw,binding,retrieval)


def test_legacy_citation_protocol_still_rejects_old_native_citation_failure():
    _,retrieval,binding,raw=quoted_fixture()
    binding.pop('citation_protocol')
    with pytest.raises(DomainError,match='returned citation'):rag.map_answer(raw,binding,retrieval)


def test_truncated_indexed_passage_cannot_supply_source_proof(monkeypatch):
    from backend import evolus_api as api
    quote,retrieval,binding,_=quoted_fixture();binding.update(library_type='Rag',library_id='isolated')
    monkeypatch.setattr(api,'call',lambda m,p,**k:{'result':[{'id':'remote-1','ingestionStatus':2}]} if p.endswith('/documents') else {'result':[{'id':'chunk-1','body':quote.split('. ')[0]+'.'}]})
    with pytest.raises(DomainError,match='exact approved original'):api.library_passages(binding,retrieval['passages'])


def test_quoted_abstention_is_explicit_and_has_no_claims():
    _,retrieval,binding,_=quoted_fixture()
    value={'selections':[],'insufficient_evidence':True,'missing_information':['No supported evidence']}
    assert rag.map_answer({'answer':json.dumps(value),'citations':[]},binding,retrieval)=={'claims':[],'insufficient_evidence':True,'missing_information':['No supported evidence']}


def test_index_proof_requires_full_quote_in_an_identified_remote_chunk(monkeypatch):
    from backend import evolus_api as api
    quote,retrieval,binding,raw=quoted_fixture();binding.update(library_type='Rag',library_id='isolated')
    original=[{k:v for k,v in retrieval['passages'][0].items() if k!='provider_chunk_proof'}]
    def call(method,path,**kwargs):
        return {'result':[{'id':'remote-1','ingestionStatus':2}]} if path.endswith('/documents') else {'result':[{'id':'chunk-1','body':quote}]}
    monkeypatch.setattr(api,'call',call)
    passages,_=api.library_passages(binding,original)
    assert rag.map_answer(raw,binding,{'passages':passages})['claims'][0]['quote']==quote
    monkeypatch.setattr(api,'call',lambda m,p,**k:{'result':[{'id':'remote-1','ingestionStatus':2}]} if p.endswith('/documents') else {'result':[{'id':None,'body':quote}]})
    with pytest.raises(DomainError,match='identified indexed chunk'):api.library_passages(binding,original)


@pytest.mark.parametrize('valid_proof',[True,False])
def test_rag_route_persists_chunk_proof_and_never_changes_applied_holds(client,monkeypatch,valid_proof):
    import hashlib
    from backend import app as module, repository as repo, evolus_api as api, evolus_adapter as external
    from backend.knowledge_indexing import scope_for
    from tests.test_focused_evolus import procedure
    from tests.test_api import post,prepare,approve,payload
    state=approve(client,prepare(client));state=post(client,'/api/cases/'+state['id']+'/apply',payload(state))
    quote,retrieval,binding,raw=quoted_fixture();doc=procedure(quote,identity='SOP');doc['passages'][0]['id']='release'
    from backend.domain import digest
    doc['source_hash']=digest(doc['passages'])
    binding['documents'][0]['source_hash']=doc['source_hash']
    retrieval['passages'][0]['source_hash']=doc['source_hash']
    retrieval['passages'][0]['provider_chunk_proof']['source_hash']=doc['source_hash']
    post(client,'/api/knowledge/procedure-review',{'document':doc,'reviewed':True,'note':'Explicit fictional approved source and applicability review.'})
    owner=hashlib.sha256(client.cookies.get('bf_session').encode()).hexdigest()
    scope=scope_for(owner,'Decorative housing','coating',[doc],'Rag')
    binding.update(scope=scope,status='indexed verified scope',library_type='Rag',library_id='isolated')
    with module.connect() as db:repo.put_record(db,owner,'knowledge-binding',scope,binding,0);db.commit()
    monkeypatch.setattr(external,'contract',lambda:{})
    monkeypatch.setattr(external,'allowance',lambda *a,**k:{})
    monkeypatch.setattr(external,'reserve',lambda *a,**k:{'injected':True})
    monkeypatch.setattr(external,'gemma',lambda *a,**k:pytest.fail('RAG must not use direct or fixture model fallback'))
    monkeypatch.setattr(api,'library_passages',lambda *a,**k:(retrieval['passages'] if valid_proof else [{k:v for k,v in retrieval['passages'][0].items() if k!='provider_chunk_proof'}],[{'injected':True}]))
    monkeypatch.setattr(rag,'ask',lambda *a,**k:{'result':raw,'provider':'Injected transport; not live evidence'})
    result=post(client,'/api/cases/'+state['id']+'/assist-generate',{'kind':'knowledge','retrieval_mode':'rag','revision':state['revision'],'idempotency_key':'source-citation-route-'+str(valid_proof),'question':'What evidence is needed for recovery?','product':'Decorative housing','process':'coating'})
    assert result['status']==('unreviewed proposal' if valid_proof else 'failed validation')
    if valid_proof:
        assert result['linked_answer']['output']['claims'][0]['quote']==quote
        assert 'not provider native annotations' in result['linked_answer']['quote_origin']
        assert result['retrieval']['passages'][0]['provider_chunk_proof']
    current=client.get('/api/cases/'+state['id']).json()
    assert current['receipts']==state['receipts'] and current['plan']==state['plan']
