"""Image transport/provenance contracts; injected HTTP only, zero live calls."""
import base64,json
import httpx,pytest
from backend import evolus_adapter as provider
from tests.test_continuation import image_bytes
from tests.test_api import client


def test_health_reports_current_application_version(client):
    from backend.app import app
    response=client.get('/api/health')
    assert response.status_code==200
    assert response.json()['version']==app.version=='0.4.0-rc.4'


def configured(monkeypatch):
    monkeypatch.setenv('GEMMA_API_BASE_URL','https://vision.invalid/v1')
    monkeypatch.setenv('GEMMA_API_KEY','unit-private-value')
    monkeypatch.setenv('GEMMA_MODEL_ID','Gemma-4-31B-IT')
    monkeypatch.setenv('GEMMA_JSON_OBJECT','true')
    monkeypatch.setenv('GEMMA_VISION_VERIFIED','true')
    monkeypatch.delenv('GEMMA_VISION_MODEL_ID',raising=False)


def test_png_contract_preserves_pixels_json_and_runtime_identity(monkeypatch):
    configured(monkeypatch);raw=image_bytes();image='data:image/png;base64,'+base64.b64encode(raw).decode()
    def handler(request):
        body=json.loads(request.content);assert body['model']=='Gemma-4-31B-IT'
        assert body['messages'][0]['role']=='system'
        parts=body['messages'][1]['content'];assert base64.b64decode(parts[0]['image_url']['url'].split(',',1)[1],validate=True)==raw
        assert body['response_format']=={'type':'json_object'}
        return httpx.Response(200,json={'id':'injected-request','model':'actual/runtime-model','choices':[{'message':{'content':'{"candidates":["BF-007"],"unresolved_characters":[],"unreadable":false}'}}],'usage':{'prompt_tokens_details':{'image_tokens':264}}})
    result=provider.gemma({'task':'Read pixels only'},{'type':'object'},image=image,transport=httpx.MockTransport(handler))
    assert result['model_id']=='actual/runtime-model' and result['request_contract']['image_bytes']==len(raw)
    assert result['request_contract']['image_mime']=='image/png'


def test_explicit_vision_override_does_not_change_text_model(monkeypatch):
    configured(monkeypatch);monkeypatch.setenv('GEMMA_VISION_MODEL_ID','DeepSeek-V4.1-Flash');models=[]
    def handler(request):
        models.append(json.loads(request.content)['model'])
        return httpx.Response(200,json={'model':models[-1],'choices':[{'message':{'content':'{}'}}]})
    transport=httpx.MockTransport(handler)
    provider.gemma({}, {},image='data:image/png;base64,'+base64.b64encode(image_bytes()).decode(),transport=transport)
    provider.gemma({}, {},transport=transport)
    assert models==['DeepSeek-V4.1-Flash','Gemma-4-31B-IT']
    assert provider.status()['vision_model_id']=='DeepSeek-V4.1-Flash'


def test_error_metadata_is_bounded_redacted_and_carries_contract(monkeypatch):
    configured(monkeypatch)
    def handler(request):
        return httpx.Response(500,headers={'x-request-id':'injected-failure'},json={'detail':{'error':{'type':'upstream_error','code':'image_decode','message':'unit-private-value data:image/png;base64,AAAA source issue','private':'unit-private-value'}}})
    with pytest.raises(provider.ProviderFailure) as caught:
        provider.gemma({}, {},image='data:image/png;base64,'+base64.b64encode(image_bytes()).decode(),transport=httpx.MockTransport(handler))
    evidence=caught.value.evidence
    assert evidence['request_id']=='injected-failure' and evidence['provider_error']['code']=='image_decode'
    assert evidence['request_contract']['image_input'] is True
    encoded=json.dumps(evidence);assert 'unit-private-value' not in encoded and 'AAAA' not in encoded and 'private' not in evidence['provider_error']
