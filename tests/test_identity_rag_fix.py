"""Targeted retained failures and held-out contracts; no live inference."""
import copy, json, base64
from pathlib import Path
import pytest
from backend import identity_annotations as ia, evolus_rag as rag
from backend.assist_contracts import validate_draft
from backend.domain import DomainError
from tests.test_api import client, post

ROOT = Path(__file__).resolve().parents[1]


def retained(name):
    value=json.loads((ROOT/'evals/evolus-focused-v1'/name).read_text(encoding='utf-8'))
    execution=value['execution'];old=execution['draft']
    annotations=[{'kind':c['kind'],'value':c['value'],'incident_status':c['incident_status'],'quote':c['source']['quote']}
                 for c in old['candidates'] if c['kind'] in ia.CRITICAL]
    raw={'annotations':annotations,'incident_scope':old['incident_scope'],'scope_evidence':old['scope_evidence'],
         'contradictions':old['contradictions'],'unresolved':old['unresolved']}
    return value,execution,raw


@pytest.mark.parametrize('name',['retained-omission.json','retained-windows-omission.json'])
def test_actual_omissions_retain_all_original_identities_without_facts(name):
    saved,execution,raw=retained(name);doc=saved['source_document']
    draft,provenance=ia.assemble({'documents':[doc]},execution,raw,[doc['id']])
    values={c['value']:c for c in draft['candidates'] if c['kind']=='supplier_lot'}
    assert set(values)=={'SUP-A','SUP-B','SUP-C'}
    assert values['SUP-C']['disposition']=='unresolved' and values['SUP-C']['incident_status']=='uncertain'
    assert values['SUP-B']['incident_status']=='uncertain' # Never infer exclusion from omission.
    assert draft['incident_scope']=='unknown' and provenance['raw_scope_claim']=='complete'
    assert {c['value'] for c in provenance['missing_annotations']}=={'SUP-B','SUP-C'}
    assert validate_draft({'documents':[doc],'edges':[]},draft)['incident_scope']=='unknown'
    assert raw['annotations']==[a for a in raw['annotations']] and execution['draft']==saved['execution']['draft']


def heldout(text):
    doc={'id':'NEW','revision':1,'original_hash':'hash','blocks':[{'id':'line','page':1,'text':text}]}
    candidates=[{'kind':'supplier_lot','value':v,'disposition':'asserted','quote':text,'page':1}
                for v in ['AX-0007','AX-0008']]
    execution={'steps':[{'kind':'extractor','output':json.dumps({'candidates':candidates,'unresolved':[]})}]}
    raw={'annotations':[],'incident_scope':'complete','scope_evidence':[],'contradictions':[],'unresolved':[]}
    return {'documents':[doc],'edges':[]},execution,raw


@pytest.mark.parametrize('text',[
    'AX-0007 is affected. AX-0008 may be affected; ancestry remains unresolved.',
    'AX-0007 is affected. AX-0008 is not affected, but an unsigned conflicting claim remains unresolved.',
])
def test_different_partial_conflicting_notices_stay_uncertain(text):
    state,execution,raw=heldout(text);draft,p=ia.assemble(state,execution,raw,['NEW'])
    assert len(draft['candidates'])==2 and draft['incident_scope']=='unknown'
    assert all(c['incident_status']=='uncertain' for c in draft['candidates'])
    assert validate_draft(state,draft)['unresolved'] and len(p['missing_annotations'])==2


def test_complete_annotations_preserve_distinct_negation_and_all_identities():
    text='AX-0007 is affected. AX-0008 is not affected. Complete incident boundary: no other supplier lots are affected.'
    state,execution,raw=heldout(text)
    raw['annotations']=[{'kind':'supplier_lot','value':v,'incident_status':status,'quote':quote}
                        for v,status,quote in [('AX-0007','affected','AX-0007 is affected.'),('AX-0008','explicitly_excluded','AX-0008 is not affected.')]]
    raw['scope_evidence']=[{'document_id':'NEW','block_id':'line','quote':'Complete incident boundary: no other supplier lots are affected.'}]
    draft,p=ia.assemble(state,execution,raw,['NEW']);draft=validate_draft(state,draft)
    assert [c['incident_status'] for c in draft['candidates']]==['affected','explicitly_excluded']
    assert draft['incident_scope']=='complete' and p['missing_annotations']==[]


@pytest.mark.parametrize('mutation',['foreign','duplicate','unsupported exclusion','bad quote','malformed'])
def test_annotation_injection_and_unsupported_scope_cannot_pass(mutation):
    state,execution,raw=heldout('AX-0007 is affected. AX-0008 may be affected; ancestry remains unresolved.')
    row={'kind':'supplier_lot','value':'AX-0008','incident_status':'uncertain','quote':state['documents'][0]['blocks'][0]['text']}
    raw['annotations']=[row]
    if mutation=='foreign':row['value']='AX-0009'
    elif mutation=='duplicate':raw['annotations'].append(copy.deepcopy(row))
    elif mutation=='unsupported exclusion':row['incident_status']='explicitly_excluded'
    elif mutation=='bad quote':row['quote']='AX-0008 is explicitly excluded'
    else:raw['annotations']='invalid'
    with pytest.raises((DomainError,ValueError)):
        draft,_=ia.assemble(state,execution,raw,['NEW']);validate_draft(state,draft)


def test_new_result_keeps_raw_annotations_separate_and_never_applies(client,monkeypatch):
    from backend import evolus_adapter as external
    saved,execution,raw=retained('retained-windows-omission.json')
    s=post(client,'/api/cases/demo');route='/api/cases/'+s['id']
    s=post(client,route+'/documents',{'filename':'different-name.pdf','content_base64':base64.b64encode((ROOT/'evals/evolus-focused-v1/notice-revised-sup-c.pdf').read_bytes()).decode(),'synthetic':True});doc=s['documents'][-1]
    execution=json.loads(json.dumps(execution).replace(saved['source_document']['id'],doc['id']))
    raw=json.loads(json.dumps(raw).replace(saved['source_document']['id'],doc['id']))
    execution.update(draft=raw,interpretation_contract=ia.VERSION)
    monkeypatch.setattr(external,'contract',lambda:{})
    monkeypatch.setattr(external,'allowance',lambda *a:{})
    monkeypatch.setattr(external,'reserve',lambda *a,**k:{'injected':True})
    for k,v in {'EVOLUS_WORKFLOW_ID':'injected','EVOLUS_EXTRACTOR_ID':execution['steps'][0]['id'],'EVOLUS_AGENT_ID':execution['steps'][1]['id'],'EVOLUS_GEMMA_MODEL_KEY':'own/gemma-4-31b-it','GEMMA_MODEL_ID':'test'}.items():monkeypatch.setenv(k,v)
    monkeypatch.setattr(external,'operation',lambda *a,**k:{'result':execution})
    job=post(client,route+'/assist-run',{'mode':'live','revision':s['revision'],'document_ids':[doc['id']],'idempotency_key':'new-contract-retained-failure'})
    assert job['status']=='unreviewed proposal' and job['raw_draft']==raw
    assert len(job['proposal_assembly']['missing_annotations'])==2 and job['draft']['incident_scope']=='unknown'
    post(client,route+'/assist-intake',{'proposal_id':job['id'],'document_id':doc['id'],'revision':s['revision']})
    state=client.get(route).json();assert state['plan'] is None and state['receipts']==[] and not state.get('approval')


def test_both_stages_omitting_recorded_reference_cannot_hide_it_in_review():
    from tests.test_omission_citation_contracts import source_state
    state=source_state('SUP-A is affected. SUP-B is not affected. SUP-C remains under investigation.')
    e={'steps':[{'kind':'extractor','output':json.dumps({'candidates':[{'kind':'supplier_lot','value':'SUP-A','disposition':'asserted','quote':'SUP-A is affected.','page':None}],'unresolved':[]})}]}
    raw={'annotations':[{'kind':'supplier_lot','value':'SUP-A','incident_status':'affected','quote':'SUP-A is affected.'}],'incident_scope':'complete','scope_evidence':[]}
    draft,p=ia.assemble(state,e,raw,['notice'])
    assert {c['value'] for c in draft['candidates']}=={'SUP-A','SUP-B','SUP-C'}
    assert {c['value'] for c in p['missing_extractions']}=={'SUP-B','SUP-C'}
    assert draft['incident_scope']=='unknown'
    assert all(c['incident_status']=='uncertain' and c['disposition']=='unresolved' for c in draft['candidates'] if c['value']!='SUP-A')
    assert validate_draft(state,draft,['notice'])['incident_scope']=='unknown'


@pytest.mark.parametrize('citations',[{},['fake'],[{'documentId':'other-tenant'}]])
def test_malformed_or_foreign_annotations_cannot_override_index_proof(citations):
    from tests.test_omission_citation_contracts import quoted_fixture
    _,retrieval,binding,raw=quoted_fixture();raw['citations']=citations
    with pytest.raises(DomainError):rag.map_answer(raw,binding,retrieval)

