"""Reproduce final public image failure; injected transport, zero live calls."""
import copy
import httpx
import pytest
from backend import evolus_adapter as external
from tests.test_continuation import client, post, get, image_body, review, approve, payload


@pytest.mark.parametrize('fault', ['http500', 'timeout', 'malformed'])
def test_image_error_is_terminal_and_preserves_applied_authority(client, monkeypatch, fault):
    state = approve(client, review(client, post(client, '/api/cases/demo')))
    route = '/api/cases/' + state['id']
    state = post(client, route + '/apply', payload(state, 'image-failure-original-receipt'))
    before = copy.deepcopy(state)
    label = post(client, route + '/label-image', image_body())
    monkeypatch.setenv('GEMMA_VISION_VERIFIED', 'true')
    monkeypatch.setattr(external, 'allowance', lambda *args: {})
    monkeypatch.setattr(external, 'reserve', lambda *args: {})
    calls = []
    def fail(*args, **kwargs):
        calls.append(kwargs['image'])
        if fault == 'http500':
            raise external.ProviderFailure('Gemma endpoint HTTP 500; no retry', {'http_status': 500, 'requested_model_id': 'synthetic-model', 'request_id': 'synthetic-request'})
        if fault == 'timeout':
            raise httpx.ReadTimeout('Synthetic test timeout')
        return {'result': {'candidates': ['LOT-007'], 'unreadable': 'not-a-bool'}, 'provider': 'injected malformed response'}
    monkeypatch.setattr(external, 'gemma', fail)
    body = {'kind': 'label', 'label_id': label['id'], 'revision': state['revision'], 'idempotency_key': 'same-image-failure-' + fault}
    result = post(client, route + '/assist-generate', body)
    assert result['status'] == ('failed validation' if fault == 'malformed' else 'failed provider request')
    assert 'draft' not in result
    if fault == 'http500':
        assert result['failed_request_metadata']['http_status'] == 500
    if fault != 'malformed':
        assert 'raw_output' not in result and 'provenance' not in result
    assert get(client, route) == before
    assert not get(client, route + '/assisted')['label'][0].get('reading')
    assert next(j for j in get(client, '/api/jobs') if j['id'] == result['id'])['status'] == 'failed'
    assert post(client, route + '/assist-generate', body) == result
    assert len(calls) == 1
