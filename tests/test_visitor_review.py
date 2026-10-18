"""Targeted local regressions; mocked inference is not live provider evidence."""
import base64,copy,json
from datetime import datetime,timedelta,timezone
import httpx,pytest
from fastapi.testclient import TestClient
from backend import app as module,visitor_review as v
from tests.test_api import post

NOTICE='Supplier quality notice\nAffected lot: VENDOR-Z-928. Hold pending coating inspection.\nLot VENDOR-Z-929 is not affected. The boundary beyond this shipment is unresolved.'


@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'DB',tmp_path/'visitor.sqlite3')
    monkeypatch.setenv('SOURCE_STORAGE_PATH',str(tmp_path/'sources'))
    monkeypatch.setenv('DEPLOYMENT_PROFILE','public')
    monkeypatch.setenv('PUBLIC_DEMO','true')
    monkeypatch.setenv('PUBLIC_REVIEW_ENABLED','true')
    monkeypatch.setenv('LIVE_DEMO_TOKEN','private-owner-token-'+'x'*40)
    v.visitor_limit.buckets.clear();module.limiter.buckets.clear();v.status_cache.clear()
    monkeypatch.setattr(v,'entitlement',lambda **kw:{'status':'available','requested_model_id':v.MODEL,'additional_cash':0})
    c=TestClient(module.app);s=post(c,'/api/cases/visitor')
    def upload(text=NOTICE,filename='external-supplier-notice.txt'):
        return post(c,f"/api/cases/{s['id']}/documents",{'filename':filename,'content_base64':base64.b64encode(text.encode()).decode()})
    return c,s,upload


def proposal(s):
    d=s['documents'][-1];b=d['blocks'][1]
    return {'candidates':[{'kind':'supplier_lot','value':'VENDOR-Z-928','disposition':'asserted','incident_status':'affected','source':{'document_id':d['id'],'block_id':b['id'],'quote':b['text']}}],
        'changes':[],'contradictions':[],'unresolved':['The shipment boundary is unresolved.'],'request_drafts':[],'incident_scope':'partial','scope_evidence':[]}


def analyze(c,s,key='once-only-analysis',**extra):
    return c.post(f"/api/cases/{s['id']}/visitor-analysis",json={'document_id':s['documents'][-1]['id'],'revision':s['revision'],'idempotency_key':key,'external_processing_consent':True,**extra})


def test_anonymous_live_path_retains_unknowns_and_old_budget(setup,monkeypatch):
    c,s,upload=setup;s=upload();calls=[]
    monkeypatch.setenv('MAX_TOTAL_LIVE_RUNS','0')  # old phase ceiling cannot block visitors
    with module.connect() as db:
        v.repo.put_record(db,'system:assisted-budget','gemma','frozen-phase',{'dispatches':18},0)
    monkeypatch.setattr(v.external,'gemma',lambda context,schema,**kw:(calls.append(context) or {'result':proposal(s),'model_id':'mock/local-regression','http_status':200}))
    r=analyze(c,s);assert r.status_code==200,r.text
    result=r.json();assert result['status']=='completed / review required'
    assert {x['value'] for x in result['draft']['candidates']}=={'VENDOR-Z-928','VENDOR-Z-929'}
    assert all('unresolved' in x['inventory_status'] for x in result['draft']['candidates'])
    assert len(result['raw_output']['candidates'])==1  # raw omission preserved
    assert analyze(c,s).json()['id']==result['id'] and len(calls)==1
    with module.connect() as db:assert v.repo.get_record(db,'system:assisted-budget','gemma','frozen-phase')[1]=={'dispatches':18}
    state=c.get('/api/cases/'+s['id']).json();assert not state['stocks'] and not state['edges'] and not state['receipts']
    for route in ('approve','apply','assist-intake','analyze','revision'):
        assert c.post(f"/api/cases/{s['id']}/{route}",json={}).status_code==403
    assert c.post('/api/enterprise/example',json={'case_id':s['id'],'acknowledged_synthetic':True}).status_code==403
    r=c.post(f"/api/cases/{s['id']}/visitor-review",json={'proposal_id':result['id'],'revision':s['revision'],'reviewed':True,'note':'I checked the exact original lot statements.'})
    assert r.status_code==200,r.text
    assert 'authority' in r.json()['review']


def test_cross_session_and_private_route_protection(setup):
    c,s,upload=setup;s=upload();other=TestClient(module.app)
    assert other.get('/api/cases/'+s['id']).status_code==404
    assert other.get(f"/api/cases/{s['id']}/visitor-analysis").status_code==404
    assert other.get('/api/cases').json()==[]
    demo=post(c,'/api/cases/demo')
    assert c.post(f"/api/cases/{demo['id']}/analyze",json={'document_id':demo['documents'][0]['id'],'mode':'live'}).status_code==403


@pytest.mark.parametrize('text',['Pancake recipe: flour and milk.','Welcome to our team newsletter.',''])
def test_unrelated_and_empty_never_call_model(setup,monkeypatch,text):
    c,s,upload=setup
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:pytest.fail('Unexpected inference'))
    if not text:
        assert c.post(f"/api/cases/{s['id']}/documents",json={'filename':'empty.txt','content_base64':''}).status_code!=200
    else:
        s=upload(text);r=analyze(c,s);assert r.status_code==422 and r.json()['detail']['code']=='UNRELATED_INPUT'


def test_format_size_consent_and_stale_controls(setup,monkeypatch):
    c,s,upload=setup
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:pytest.fail('Unexpected inference'))
    for filename in ('file.exe','inventory.csv','source.docx'):
        r=c.post(f"/api/cases/{s['id']}/documents",json={'filename':filename,'content_base64':base64.b64encode(NOTICE.encode()).decode()});assert r.status_code==422
    r=c.post(f"/api/cases/{s['id']}/documents",json={'filename':'large.txt','content_base64':base64.b64encode(b'x'*2000001).decode()});assert r.status_code==413
    s=upload();assert analyze(c,s,external_processing_consent=False).status_code==422
    assert analyze(c,s,revision=0).status_code==409


def test_malformed_response_and_changed_source_remain_non_authoritative(setup,monkeypatch):
    c,s,upload=setup;s=upload()
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:{'result':{'unparsed_response':'malformed'}})
    r=analyze(c,s).json();assert r['status']=='failed validation' and r['raw_output']['unparsed_response']=='malformed'
    assert 'draft' not in r
    s=upload(NOTICE+'\nRevised notice; awaiting supplier response.')
    assert c.get(f"/api/cases/{s['id']}/visitor-analysis").json()[0]['stale']


def test_provider_failure_retained_no_retry(setup,monkeypatch):
    c,s,upload=setup;s=upload();calls=[]
    def fail(*a,**kw):
        calls.append(1);raise v.external.ProviderFailure('Provider unavailable',{'http_status':500,'request_id':'regression-only'})
    monkeypatch.setattr(v.external,'gemma',fail)
    r=analyze(c,s).json();assert r['status']=='provider unavailable' and r['failure_evidence']['http_status']==500
    analyze(c,s);assert len(calls)==1


def test_persistent_session_attempt_bound(setup,monkeypatch):
    c,s,upload=setup;s=upload()
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:pytest.fail('Unexpected inference'))
    owner=__import__('hashlib').sha256(c.cookies.get('bf_session').encode()).hexdigest()
    with module.connect() as db:v.repo.put_record(db,owner,'visitor-usage','current',{'attempts':4},0)
    r=analyze(c,s);assert r.status_code==429 and r.json()['detail']['code']=='SESSION_LIMIT'


def test_stale_source_review_rejects(setup,monkeypatch):
    c,s,upload=setup;s=upload()
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:{'result':proposal(s)})
    result=analyze(c,s).json();updated=upload(NOTICE+'\nAdditional receiving context is awaited.')
    r=c.post(f"/api/cases/{s['id']}/visitor-review",json={'proposal_id':result['id'],'revision':updated['revision'],'reviewed':True,'note':'Attempted inspection after source revision.'})
    assert r.status_code==409 and r.json()['detail']['code']=='STALE_REVIEW'


def test_expired_job_is_reported_without_resubmission(setup,monkeypatch):
    c,s,upload=setup;s=upload()
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:{'result':proposal(s)})
    result=analyze(c,s).json();owner=__import__('hashlib').sha256(c.cookies.get('bf_session').encode()).hexdigest()
    with module.connect() as db:
        rev,job=v.repo.get_record(db,owner,'job',result['id']);job.update(status='running',lease_until=0);v.repo.put_record(db,owner,'job',result['id'],job,rev)
        rev,record=v.repo.get_record(db,owner,'assist',result['id']);record['status']='running';v.repo.put_record(db,owner,'assist',result['id'],record,rev)
    monkeypatch.setattr(v.external,'gemma',lambda *a,**k:pytest.fail('No automatic resubmission'))
    r=c.get(f"/api/cases/{s['id']}/visitor-analysis").json()[0]
    assert r['status']=='provider unavailable' and 'interrupted' in r['error']
    assert analyze(c,s).json()['status']=='provider unavailable'


@pytest.mark.parametrize('remaining,catalog,http_status,expected',[(0.5,True,200,200),(0.001,True,200,429),(0.5,False,200,503),(0.5,True,401,503)])
def test_actual_entitlement_contract(monkeypatch,remaining,catalog,http_status,expected):
    monkeypatch.setenv('PUBLIC_REVIEW_ENABLED','true');monkeypatch.setenv('DEPLOYMENT_PROFILE','public')
    for k,value in {'GEMMA_API_BASE_URL':v.BASE,'GEMMA_MODEL_ID':v.MODEL,'GEMMA_HOSTING_KIND':'managed-amd-shared','GEMMA_API_KEY':'mock-private-test-key'}.items():monkeypatch.setenv(k,value)
    def response(r):
        assert r.headers['Authorization']=='Bearer mock-private-test-key'
        body={'daily_cost_limit_usd':1,'daily_cost_remaining_usd':remaining,'daily_reset_at':(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()} if r.url.path.endswith('/usage') else {'data':[{'id':v.MODEL,'json_output':True,'free':False}] if catalog else []}
        return httpx.Response(http_status,json=body)
    if expected==200:
        result=v.entitlement(httpx.MockTransport(response));assert result['additional_cash']==0 and result['access_expires_at'] is None
    else:
        with pytest.raises(v.HTTPException) as e:v.entitlement(httpx.MockTransport(response))
        assert e.value.status_code==expected


def test_bounded_transport_failure_has_sanitized_evidence(monkeypatch):
    monkeypatch.setenv('GEMMA_API_BASE_URL',v.BASE);monkeypatch.setenv('GEMMA_MODEL_ID',v.MODEL);monkeypatch.setenv('GEMMA_API_KEY','mock-private-test-key')
    def failure(request):raise httpx.ReadTimeout('Do not expose headers or credentials',request=request)
    with pytest.raises(v.external.ProviderFailure) as e:
        v.external.gemma({'task':'Local mocked regression'}, {},transport=httpx.MockTransport(failure),timeout_seconds=90)
    assert e.value.evidence['transport_error']=='ReadTimeout'
    assert e.value.evidence['request_contract']['timeout_seconds']==90
    assert 'mock-private-test-key' not in json.dumps(e.value.evidence)
    with pytest.raises(v.DomainError):v.external.gemma({}, {},timeout_seconds=600)
