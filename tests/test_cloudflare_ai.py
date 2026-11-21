"""Cloudflare HTTP contracts and visitor safety. All model responses are mocked."""

from pathlib import Path
import json
import base64

import httpx
import pytest

from backend import cloudflare_ai as cf, visitor_review as visitor
from backend.evolus_adapter import ProviderFailure
from tests.test_api import post
from tests.test_visitor_review import setup, analyze


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'a1' * 16)
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'mock-cloudflare-token')
    monkeypatch.setenv('PUBLIC_REVIEW_PROVIDER', 'cloudflare')


def entitlement_transport(subscriptions, catalog=None, *, status=200, pagination=None):
    def response(request):
        assert request.headers['Authorization'] == 'Bearer mock-cloudflare-token'
        assert request.url.host == 'api.cloudflare.com'
        assert request.method == 'GET'
        if request.url.path.endswith('/subscriptions'):
            return httpx.Response(status, json={'success': status == 200, 'result': subscriptions,
                                                'result_info': pagination})
        assert request.url.path.endswith('/ai/models/search')
        assert request.url.params['search'] == cf.MODEL
        return httpx.Response(200, json={'success': True, 'result': catalog if catalog is not None else [{'name': cf.MODEL}]})
    return httpx.MockTransport(response)


@pytest.mark.parametrize('plans', [[], [{'rate_plan': {'id': 'workers_free'}, 'price': 0}]])
def test_verified_default_or_explicit_free_account(configured, plans):
    value = cf.entitlement(entitlement_transport(plans))
    assert value['daily_limit_neurons'] == 10000 and value['additional_cash'] == 0
    assert value['requested_model_id'] == cf.MODEL and value['quota_reset_at'].endswith('T00:00:00+00:00')
    assert 'mock-cloudflare-token' not in json.dumps(value)


@pytest.mark.parametrize('plans,catalog,status,pagination', [
    ([{'rate_plan': {'id': 'WORKERS_PAID'}, 'price': 0}], None, 200, None),
    ([{'rate_plan': {'id': 'workers_free', 'is_contract': True}}], None, 200, None),
    ([{'rate_plan': {'id': 'workers_free'}, 'price': 5}], None, 200, None),
    ([], None, 403, None),
    ([], None, 200, {'total_count': 1}),
    ([], [], 200, None),
])
def test_missing_free_or_catalog_proof_stops_inference(configured, monkeypatch, plans, catalog, status, pagination):
    monkeypatch.setenv('PUBLIC_REVIEW_ENABLED', 'true')
    monkeypatch.setenv('DEPLOYMENT_PROFILE', 'public')
    with pytest.raises(visitor.HTTPException) as exc:
        visitor.entitlement(entitlement_transport(plans, catalog, status=status, pagination=pagination))
    assert exc.value.status_code == 503


def test_scoped_cloudflare_pdf_proposals(configured, setup, monkeypatch):
    client, state, _ = setup
    payload = (Path(__file__).resolve().parents[1] / 'docs/judge-access/inputs/supplier-quality-helio.pdf').read_bytes()
    state = post(client, f"/api/cases/{state['id']}/documents", {
        'filename': 'own-supplier-notice.pdf', 'content_base64': base64.b64encode(payload).decode(),
    })
    document = state['documents'][0]
    block = next(b for b in document['blocks'] if 'HELIO-731' in b['text'])
    raw = {
        'candidates': [{'kind': 'supplier_lot', 'value': 'HELIO-731',
                        'disposition': 'asserted', 'incident_status': 'affected',
                        'source': {'document_id': document['id'], 'block_id': block['id'], 'quote': block['text']}}],
        'incident_scope': 'partial', 'unresolved': ['Confirm actual receiving lineage.'],
    }
    calls = []
    def response(request):
        calls.append(request.url.path)
        assert request.url.path.endswith('/ai/v1/chat/completions')
        assert request.headers['Authorization'] == 'Bearer mock-cloudflare-token'
        assert request.headers.get('x-bf-demo-token') is None
        body = json.loads(request.content)
        prompt = json.loads(body['messages'][1]['content'])
        assert 'HELIO-731' in json.dumps(prompt['context'])
        assert body['model'] == cf.MODEL and body['store'] is False and body['stream'] is False
        assert body['chat_template_kwargs'] == {'enable_thinking': False}
        assert 'tools' not in body
        return httpx.Response(200, headers={'cf-ray': 'mock-cf-ray-FRA'}, json={
            'id': 'mock-completion', 'model': cf.MODEL, 'choices': [
                {'message': {'content': json.dumps(raw), 'reasoning': 'must not retain'}, 'finish_reason': 'stop'},
            ],
            'usage': {'prompt_tokens': 1750, 'completion_tokens': 350, 'total_tokens': 2100},
        })
    send = cf.gemma
    monkeypatch.setattr(cf, 'gemma', lambda *a, **kw: send(*a, transport=httpx.MockTransport(response), **kw))
    monkeypatch.setattr(visitor.external, 'gemma', lambda *a, **kw: pytest.fail('Unexpected AMD fallback'))
    assert analyze(client, state).status_code == 422
    result = analyze(client, state, processing_provider='cloudflare').json()
    assert result['status'] == 'completed / review required'
    assert result['raw_output'] == raw and result['provenance']['provider'] == cf.PROVIDER
    assert result['provenance']['model_id'] == cf.MODEL
    assert result['provenance']['request_id'] == 'mock-completion'
    assert result['provenance']['cloudflare_ray'] == 'mock-cf-ray-FRA'
    assert 'must not retain' not in json.dumps(result) and 'mock-cloudflare-token' not in json.dumps(result)
    assert {item['value'] for item in result['draft']['candidates']} >= {'HELIO-731', 'HELIO-732', 'HELIO-733'}
    assert all(item['disposition'] == 'unresolved' for item in result['draft']['candidates'])
    assert result['draft']['incident_scope'] == 'unknown'
    assert analyze(client, state, processing_provider='cloudflare').json()['id'] == result['id']
    assert len(calls) == 1


@pytest.mark.parametrize('code,expected', [(3036, 'allowance exhausted'), (3040, 'provider unavailable')])
def test_cloudflare_capacity_is_distinct_from_daily_quota(configured, setup, monkeypatch, code, expected):
    client, _, upload = setup
    state = upload()
    send = cf.gemma
    transport = httpx.MockTransport(lambda _: httpx.Response(429, json={
        'errors': [{'code': code, 'message': 'do not retain upstream details'}],
    }))
    monkeypatch.setattr(cf, 'gemma', lambda *a, **kw: send(*a, transport=transport, **kw))
    result = analyze(client, state, processing_provider='cloudflare').json()
    assert result['status'] == expected and 'draft' not in result
    assert result['failure_evidence']['provider_error_code'] == code
    assert 'do not retain' not in json.dumps(result)
    if code == 3036:
        assert client.get('/api/visitor/status').json()['status'] == 'allowance exhausted'


@pytest.mark.parametrize('content,finish', [('not JSON', 'stop'), ('{"partial": true}', 'length')])
def test_unusable_model_response_never_accepted(configured, content, finish):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        'choices': [{'message': {'content': content}, 'finish_reason': finish}],
    }))
    response = cf.gemma({}, {}, transport=transport)
    assert response['finish_reason'] == finish
    assert response['result']['unparsed_response'] == content
    assert 'raw_extraction_error' in response['result']


def test_cloudflare_timeout_is_recorded_without_retry(configured):
    requests = []
    def fail(request):
        requests.append(request)
        raise httpx.ReadTimeout('Private error detail', request=request)
    with pytest.raises(ProviderFailure) as exc:
        cf.gemma({}, {}, transport=httpx.MockTransport(fail))
    assert len(requests) == 1
    assert exc.value.evidence['transport_error'] == 'ReadTimeout'
    assert 'Private error detail' not in json.dumps(exc.value.evidence)
