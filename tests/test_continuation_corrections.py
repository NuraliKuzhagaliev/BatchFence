"""Corrections and compact source selection never change raw model quality."""
import copy,json
import pytest
from backend import evolus_adapter as external,repository as repo,app as module,knowledge
from backend.assist_contracts import fingerprint
from backend.knowledge_routes import catalog
from backend.domain import DomainError
from tests.test_continuation import client,post,get,upload,ref,NOTE

def test_rejected_metadata_claim_needs_explicit_source_correction(client):
    s=upload(client,post(client,'/api/cases/demo'),'Affected lots: SUP-A. This is the complete incident boundary.')
    route='/api/cases/'+s['id'];d=s['documents'][-1]
    raw={'candidates':[{'kind':'supplier_lot','value':'SUP-A','disposition':'asserted','incident_status':'affected','source':ref(d)},
        {'kind':'document_id','value':d['id'],'disposition':'asserted','source':ref(d)}],'incident_scope':'unknown'}
    key='ASSIST-correction-test'
    with repo.write(module.connect) as db:
        before={'id':key,'case_id':s['id'],'kind':'document','status':'failed validation','mode':'live','snapshot_hash':fingerprint(s,catalog(db,s['owner'])) if 'owner' in s else None,'raw_output':raw,'error':'Synthetic rejected metadata-ID claim','executions':[]}
        # Session owner is available on the scoped case row; never exported as a cookie.
        owner=db.execute('SELECT owner FROM cases WHERE id=?',(s['id'],)).fetchone()[0];before['snapshot_hash']=fingerprint(s,catalog(db,owner))
        repo.put_record(db,owner,'assist',key,before,0)
    body={'proposal_id':key,'document_id':d['id'],'revision':s['revision']}
    assert client.post(route+'/assist-intake',json=body).status_code==422
    assert client.post(route+'/assist-review',json={'proposal_id':key,'reviewed':True,'note':NOTE,'corrected_draft':raw}).status_code==422
    corrected=copy.deepcopy(raw);corrected['candidates'].pop()
    result=post(client,route+'/assist-review',{'proposal_id':key,'reviewed':True,'note':NOTE,'corrected_draft':corrected})
    assert result['raw_output']==raw and result['raw_quality_status']=='failed validation'
    assert result['correction']['basis'].startswith('Explicit') and get(client,route)['plan'] is None
    state=post(client,route+'/assist-intake',body)
    assert state['plan'] is None and state['scope']==s['scope']
    assert state['runs'][-1]['proposal_correction'] and state['runs'][-1]['output']['facts'][0]['affected'] is False

def test_key_selection_preserves_omitted_caveat_and_rejects_wrong_version():
    p={'document_id':'TRAIN-COSMETIC','version':1,'passage_id':'P1','quote':'Verify identity. This fictional procedure grants no real inventory authority.'}
    retrieval={'passages':[p]};raw={'selections':[{k:p[k] for k in ['document_id','version','passage_id']}],'insufficient_evidence':False,'missing_information':[]}
    answer=knowledge.selected_answer(raw,retrieval)
    assert answer['claims'][0]['quote']==p['quote'] and 'fictional' in answer['claims'][0]['quote']
    raw['selections'][0]['version']=2
    with pytest.raises(DomainError):knowledge.selected_answer(raw,retrieval)
    raw['selections'][0]['version']=1;raw['selections'][0]['quote']='Verify identity.'
    with pytest.raises(ValueError):knowledge.selected_answer(raw,retrieval)

def test_actual_numeric_execution_orders_and_mixed_output_are_not_silently_repaired():
    from backend.evolus_api import normalize_execution
    manifest={'workflow_id':'flow','extractor':{'step_id':'uuid-a','step_order':1,'resource_id':'ext','model_key':'own/gemma'},'agent':{'step_id':'uuid-b','step_order':2,'resource_id':'agent','model_key':'own/gemma'}}
    raw={'workflowId':'flow','id':'execution','status':'Completed','stepStates':{'1':{'status':'done','durationMs':20},'2':{'status':'done','durationMs':30}},'stepOutputs':{'1':'{}','2':'{}'},'output':'{"original":true}\n------\n{"candidates":[]}'}
    result=normalize_execution(raw,manifest)
    assert len(result['steps'])==2 and result['draft']['raw_extraction_error']
    assert result['draft']['unparsed_response']==raw['output']
