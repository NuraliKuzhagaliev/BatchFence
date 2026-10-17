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

@pytest.mark.parametrize('drift',['none','output-mode','agent-tools','structure-script','own-base'])
def test_remote_configuration_is_checked_before_dispatch(monkeypatch,drift):
    from backend import evolus_api as api
    from backend.domain import digest
    from tests.test_continuation_contract import credentials
    credentials(monkeypatch);monkeypatch.setenv('EVOLUS_USER_API_KEY','synthetic-personal-key')
    manifest={'workflow_id':'flow','connection_id':'connection','provider_base_url':'https://example.invalid/v1','provider_model_id':'Gemma'}
    steps=[];responses={}
    for order,(kind,typ,mode) in enumerate([('extractor',13,1),('agent',1,4),('output',14,0)],1):
        expected={'step_id':kind+'-step','step_order':order,'input_mode':mode,'input_step_ids':[] if order==1 else [('extractor' if order==2 else 'agent')+'-step'],'prompt':None}
        step={'id':expected['step_id'],'order':order,'stepType':typ,'inputMode':mode,'inputStepIds':expected['input_step_ids'],'prompt':None}
        if kind!='output':
            expected.update(resource_id=kind+'-agent',output_structure_id=kind+'-json',model_key='own/gemma',prompt_hash=digest('bounded original instructions'),schema_hash=digest({'candidates':[]}),structure_prompt_hash=digest('explicit schema'))
            step.update(agentId=expected['resource_id'],outputStructureId=expected['output_structure_id'])
            responses[f'/api/v1/agents/{expected["resource_id"]}']={'modelKey':'own/gemma','prompt':'bounded original instructions','isExtractor':kind=='extractor','webSearchType':'NONE','modelParameters':{'max_tokens':1600,'temperature':0}}
            responses[f'/api/v1/agents/{expected["resource_id"]}/json/{expected["output_structure_id"]}']={'structure':'{"candidates":[]}','userPrompt':'explicit schema','maxCorrections':0,'canUseOCR':False}
        steps.append(step);manifest[kind]=expected
    responses['/api/v1/workflows/flow']={'applicationId':'synthetic-app','isActive':True,'multiFileMode':1,'steps':steps}
    responses['/api/v1/own-models/connections']=[{'id':'connection','apiBaseUrl':'https://example.invalid/v1','hasApiKey':True,'disabled':False,'models':[{'modelId':'Gemma'}]}]
    if drift=='output-mode':steps[-1]['inputMode']=2
    if drift=='agent-tools':responses['/api/v1/agents/agent-agent']['scriptToolEnabled']=True
    if drift=='structure-script':responses['/api/v1/agents/extractor-agent/json/extractor-json']['checkScript']='return true;'
    if drift=='own-base':responses['/api/v1/own-models/connections'][0]['apiBaseUrl']='https://other.invalid'
    calls=[]
    def fake(method,path,**kwargs):
        calls.append((method,path));assert method=='GET';return {'result':responses[path],'path':path,'http_status':200}
    monkeypatch.setattr(api,'call',fake)
    if drift=='none':assert len(api.verify_workflow(manifest)['requests'])==6
    else:
        with pytest.raises(DomainError):api.verify_workflow(manifest)
    assert all(m=='GET' for m,p in calls)

def test_response_cannot_borrow_a_different_sources_resolution(client,monkeypatch):
    from backend import assisted as a
    from tests.test_continuation import review
    s=review(client,post(client,'/api/cases/demo'));route='/api/cases/'+s['id']
    q=next(q for q in get(client,route+'/assisted')['next_evidence']['requests'] if q['pool_ids']==['FG-C'])
    task=post(client,route+'/evidence-task',{'cause_id':q['id'],'role':'Receiver','due_date':'','request_draft':'','revision':s['revision'],'idempotency_key':'test-no-borrowed-resolution'})
    s=upload(client,s,'FG-C may contain SUP-A; incomplete ancestry.',request_id=q['id']);older=s['documents'][-1]
    s=upload(client,s,'FG-C contains SUP-B only; all parent receipts were reconciled.',request_id=q['id']);newer=s['documents'][-1]
    s['pending_revision']=False;s['reconciliations']=[{'outcome':'resolved','evidence':{'document_id':newer['id']}}]
    monkeypatch.setattr(a,'evidence_requests',lambda *args:{'requests':[]})
    with repo.write(module.connect) as db:
        owner=db.execute('SELECT owner FROM cases WHERE id=?',(s['id'],)).fetchone()[0]
        with pytest.raises(DomainError,match='cannot borrow'):a.task_response(db,owner,s,task['id'],older['id'],'resolved',older['blocks'][0]['text'],True,NOTE)
        assert a.task_response(db,owner,s,task['id'],newer['id'],'resolved',newer['blocks'][0]['text'],True,NOTE)['status']=='closed after current source review'

def test_handover_separates_a_stale_proposal_from_current_applied_holds(client):
    from tests.test_continuation import review,approve
    from tests.test_api import payload
    s=approve(client,review(client,post(client,'/api/cases/demo')));route='/api/cases/'+s['id']
    s=post(client,route+'/apply',payload(s,'handover-old-500'))
    s=upload(client,s,'Changed supplier evidence: scope is unresolved.')
    brief=post(client,route+'/handover',{'idempotency_key':'stale-proposal-not-current','previous_id':None})
    assert brief['snapshot']['quantities']['proposed_hold_units'] is None
    assert brief['snapshot']['quantities']['applied_hold_units']==500
    assert any('Historical proposal: 500' in f['text'] for f in brief['snapshot']['facts'])
