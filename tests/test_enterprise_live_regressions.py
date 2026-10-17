"""Replay observed AMD errors without network calls; never fresh inference evidence."""
import base64
import copy
import json
from pathlib import Path
import pytest
from backend import receiving, receiving_routes
from backend.domain import DomainError
from tests.test_api import client, post, review, approve, payload
from tests.test_signals_knowledge import training

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/enterprise/live/fresh'


@pytest.mark.parametrize('name',['partial','complete'])
def test_observed_metadata_entities_never_narrow_or_replace(client,monkeypatch,name):
    c=client;s=training(c);route='/api/cases/'+s['id']
    s=approve(c,review(c,s));s=post(c,route+'/apply',payload(s,'recorded-500'))
    s=post(c,route+'/revision');s=approve(c,review(c,s,True));s=post(c,route+'/apply',payload(s,'recorded-800'))
    old_edges=copy.deepcopy(s['edges']);old_receipts=copy.deepcopy(s['receipts'])
    source=json.loads((EVIDENCE/'inputs.json').read_text())['receiving_'+name]
    recorded=json.loads((EVIDENCE/(name+'-raw.json')).read_text())
    question=next(q for q in s['plan']['result']['requests'] if q['pool_ids']==['FG-C'])
    s=post(c,route+'/documents',{'filename':'arbitrary-'+name+'.txt','synthetic':True,'request_id':question['id'],'content_base64':base64.b64encode(source.encode()).decode()})
    doc=s['documents'][-1];captured=[]
    def replay(task,system,schema,context,mode,fixture):
        captured.append(context)
        return {**recorded,'status':'succeeded','mode':'recorded regression replay','output':copy.deepcopy(recorded['raw_output'])}
    monkeypatch.setattr(receiving_routes,'infer',replay)
    s=post(c,route+'/receiving-draft',{'document_id':doc['id'],'mode':'fixture'})
    run=s['receiving_runs'][-1]
    assert run['status']=='failed' and run['raw_output']==recorded['raw_output']
    assert s['edges']==old_edges and s['receipts']==old_receipts and s['quantities']['applied_hold_units']==800
    assert captured==[{'source_passages':[b['text'] for b in doc['blocks']]}]
    assert doc['id'] not in json.dumps(captured) and 'line-1' not in json.dumps(captured)
    body={'revision':s['revision'],'document_id':doc['id'],'review_path':'narrative_draft','run_id':run['id'],'pool_id':'FG-C','parent_ids':['SUP-B'],
        'complete':True,'quote':source,'superseded_row_ids':['LIN-3','LIN-4'],'unresolved_contradictions':False,'outcome':'resolved',
        'reviewed':True,'replacement_reviewed':True,'completeness_confirmed':True,'note':'Recorded-error regression; explicit flags cannot turn a rejected model draft into authority.'}
    assert c.post(route+'/receiving-preview',json=body).status_code==422
    assert c.post(route+'/receiving-review',json=body).status_code==422
    s=post(c,route+'/receiving-review',{**body,'outcome':'inconclusive','complete':False,'completeness_confirmed':False})
    assert s['plan']['result']['hold_units']==800 and s['edges']==old_edges and s['receipts']==old_receipts


def test_source_context_preserves_real_document_ids_only_when_source_says_them():
    doc={'id':'INTERNAL-DOC-17','blocks':[{'id':'line-1','text':'Supplier record DOC-123 names lot SUP-B.'}]}
    before=copy.deepcopy(doc)
    assert receiving.source_context(doc)=={'source_passages':['Supplier record DOC-123 names lot SUP-B.']}
    assert doc==before


@pytest.mark.parametrize('key',['EXT-04','EXT-07','EXT-11'])
def test_frozen_ambiguous_response_cannot_resolve_incident_scope(client,monkeypatch,key):
    """Exact frozen source/response replay; IDs are mapped only to local source storage."""
    from backend import app as module
    c=client;s=post(c,'/api/cases/demo');route='/api/cases/'+s['id']
    evidence=json.loads((ROOT/'docs/enterprise/live/frozen'/(key+'.json')).read_text())
    s=post(c,route+'/documents',{'filename':'notice-unrelated-name.txt','synthetic':True,
        'content_base64':base64.b64encode(evidence['item']['text'].encode()).decode()})
    doc=s['documents'][-1];raw=copy.deepcopy(evidence['run'])
    assert raw['status']=='succeeded'
    raw['mode']='recorded regression replay'
    for fact in raw['output']['facts']:
        for citation in fact['evidence']:citation['document_id']=doc['id']
    monkeypatch.setattr(module,'extract',lambda docs,mode:copy.deepcopy(raw))
    s=post(c,route+'/analyze',{'document_id':doc['id'],'mode':'fixture'})
    assert s['plan'] is None and s['receipts']==[] and s['runs'][-1]['scope_concerns']
    lots=[f['lot_id'] for f in raw['output']['facts']]
    request={'run_id':raw['id'],'revision':s['revision'],'lot_ids':lots,'accept_scope':True,
        'bounded_scope_reviewed':True,'incident_scope_status':'resolved',
        'resolution_quote':evidence['item']['text'],'note':'Recorded regression: copying model candidates must not resolve explicit source uncertainty.'}
    denied=c.post(route+'/reviews',json=request)
    assert denied.status_code==422 and denied.json()['detail']['code']=='UNRESOLVED_LOT'
    s=post(c,route+'/reviews',{**request,'lot_ids':[],'uncertain_lot_ids':lots,
        'bounded_scope_reviewed':False,'incident_scope_status':'unresolved'})
    assert s['plan']['result']['hold_units']==1200 and s['plan']['result']['outside_units']==0
    assert s['receipts']==[] and s['runs'][-1]['output']==raw['output']


def test_observed_signal_misdescription_has_no_investigation_authority(client,monkeypatch):
    from backend import provider_tasks
    c=client;s=training(c);obs=c.get('/api/inspections').json()
    baseline=post(c,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in obs['rows'] if r['observation_id'].startswith('BASE-')],
        'inspection_revision':obs['revision'],'stable_reviewed':True,'note':'Recorded semantic-error regression with synthetic baseline.'})
    chart=c.get('/api/signals').json()['results'][0]
    raw=json.loads((EVIDENCE/'signal-raw.json').read_text())
    contexts=[]
    def replay(*args,**kwargs):
        contexts.append(args[3])
        return copy.deepcopy(raw)
    monkeypatch.setattr(provider_tasks,'infer',replay)
    result=post(c,'/api/signals/explain',{'baseline_id':baseline['id'],'chart_digest':chart['chart_digest'],'mode':'fixture'})
    assert result['output']['comments'][0]['observation_id']=='STABLE-001'
    assert contexts[0]['baseline_observation_ids']==[r['observation_id'] for r in baseline['rows']]
    assert all(i.startswith('BASE-') for i in contexts[0]['baseline_observation_ids'])
    assert result['status']=='failed'  # Old response cites a point outside this bounded context.
    assert contexts[0]['signal_count']==5 and contexts[0]['omitted_followup_count']==20
    expected=[p for p in chart['chart']['points'] if p['status']=='signal']
    for actual,point in zip(contexts[0]['observations'],expected):
        assert all(actual[k]==point[k] for k in actual)
    assert len(json.dumps(contexts[0])) < len(json.dumps(chart['chart']))/2
    body={'baseline_id':baseline['id'],'observation_id':'STABLE-001','chart_digest':chart['chart_digest'],'source_case_id':s['id']}
    assert c.post('/api/signals/investigation',json=body).status_code==422
    unchanged=c.get('/api/cases/'+s['id']).json()
    assert unchanged['plan'] is None and unchanged['receipts']==[]
    linked=post(c,'/api/signals/investigation',{**body,'observation_id':'SHIFT-001'})
    state=c.get('/api/cases/'+linked['case_id']).json()
    assert state['origin_signal']['known_affected']==[] and state['plan'] is None and state['receipts']==[]


def test_prior_review_policy_approval_is_stale(client):
    from backend import app as module
    from backend.review_safety import REVIEW_POLICY_VERSION
    import hashlib
    c=client;s=approve(c,review(c,post(c,'/api/cases/demo')))
    owner=hashlib.sha256(c.cookies.get('bf_session').encode()).hexdigest()
    with module.transaction(s['id'],owner) as (_,state):
        state['scope']['review_policy_version']=REVIEW_POLICY_VERSION-1
    assert c.post('/api/cases/'+s['id']+'/apply',json=payload(s,'old-policy-approval')).status_code==409
    assert c.get('/api/cases/'+s['id']).json()['receipts']==[]
