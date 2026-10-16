"""Exact observed AMD failure plus independent boundary/ancestry regressions.

Stored output is a regression replay, never a new live inference claim.
"""
import copy
import hashlib
import json
import uuid
import pytest
from backend import app as module
from backend.domain import calculate, make_plan
from backend.fixtures import ROOT, document, load_demo
from backend.provider import validate_output
from .test_api import client, post, approve, payload, prepare

EXACT = 'Lot SUP-R may be affected. We cannot determine whether SUP-S is implicated. Scope remains unresolved.'


def recorded_case(c, monkeypatch):
    raw = next(p['run'] for p in json.loads((ROOT / 'docs/amd-probe.json').read_text())['probes'] if p['probe'] == 'ambiguous')
    s = post(c, '/api/cases/demo')
    d = document('ambiguous.txt', EXACT.encode())
    d['id'] = raw['output']['facts'][0]['evidence'][0]['document_id']
    assert validate_output(raw['output'], [d]) == raw['output']
    owner = hashlib.sha256(c.cookies.get('bf_session').encode()).hexdigest()
    with module.transaction(s['id'], owner) as (_, current):
        current['documents'].append(d)
        for edge in current['edges']:
            edge['source'] = {'SUP-A': 'SUP-R', 'SUP-C': 'SUP-S'}.get(edge['source'], edge['source'])
    monkeypatch.setattr(module, 'extract', lambda docs, mode: copy.deepcopy(raw))
    s = post(c, f"/api/cases/{s['id']}/analyze", {'document_id': d['id'], 'mode': 'fixture'})
    request = {'run_id': s['runs'][-1]['id'], 'revision': s['revision'], 'lot_ids': ['SUP-R'],
               'accept_scope': True, 'bounded_scope_reviewed': True}
    return s, request, owner


def test_exact_observed_false_proposal_cannot_exclude(client, monkeypatch):
    s, legacy, _ = recorded_case(client, monkeypatch)
    route = f"/api/cases/{s['id']}/reviews"
    rejected = client.post(route, json=legacy)
    assert rejected.status_code == 422
    assert rejected.json()['detail']['code'] == 'UNREVIEWED_LOTS'
    assert client.get(f"/api/cases/{s['id']}").json()['plan'] is None
    # Even explicitly copying the wrong booleans cannot turn uncertainty into fact.
    wrong = {**legacy, 'excluded_lot_ids': ['SUP-S'], 'incident_scope_status': 'resolved',
             'resolution_quote': EXACT, 'note': 'Attempting to narrow despite unresolved source.'}
    assert client.post(route, json=wrong).json()['detail']['code'] == 'UNRESOLVED_LOT'
    reviewed = {**legacy, 'lot_ids': [], 'uncertain_lot_ids': ['SUP-R', 'SUP-S'],
                'bounded_scope_reviewed': False, 'incident_scope_status': 'unresolved',
                'note': 'Regression operator retained both lots as unresolved; scope is not bounded.'}
    s = post(client, route, reviewed)
    assert s['scope']['lot_ids'] == [] and s['scope']['uncertain_lot_ids'] == ['SUP-R', 'SUP-S']
    r = s['plan']['result']
    assert (r['documented_units'], r['uncertain_units'], r['hold_units'], r['outside_units']) == (0, 1200, 1200, 0)
    assert not r['narrowing_available']
    # Raw AMD boolean error is retained, not silently rewritten as a better model answer.
    assert s['runs'][-1]['output']['facts'][1]['affected'] is False
    s = approve(client, s)
    request = payload(s, 'ambiguity-regression-receipt')
    s = post(client, f"/api/cases/{s['id']}/apply", request)
    assert sum(x['units'] for x in s['receipts'][-1]['changes']) == 1200
    assert len(post(client, f"/api/cases/{s['id']}/apply", request)['receipts']) == 1


def test_unresolved_global_scope_cannot_be_narrowed_even_after_lot_review(client, monkeypatch):
    s, request, _ = recorded_case(client, monkeypatch)
    request.update(lot_ids=[], uncertain_lot_ids=['SUP-R', 'SUP-S'])
    route = f"/api/cases/{s['id']}/reviews"
    assert client.post(route, json=request).json()['detail']['code'] == 'UNRESOLVED_SCOPE'
    request.update(incident_scope_status='resolved', resolution_quote=EXACT,
                   note='A generic acknowledgement cannot resolve this source.')
    assert client.post(route, json=request).json()['detail']['code'] == 'UNRESOLVED_SCOPE'


@pytest.mark.parametrize('text', [
    'Lot SUP-A is confirmed affected. SUP-C is awaiting laboratory results; the affected batch list is not yet final. SUP-E is excluded.',
    'SUP-A is defective. The extent of this incident is under investigation. SUP-C could be implicated. SUP-E is unrelated.',
])
def test_distinct_ambiguity_without_model_qualifier(client, monkeypatch, text):
    s = post(client, '/api/cases/demo')
    d = document('different-wording.txt', text.encode())
    owner = hashlib.sha256(client.cookies.get('bf_session').encode()).hexdigest()
    with module.transaction(s['id'], owner) as (_, current):
        current['documents'].append(d)
    # Deliberately bad, syntactically valid output with no qualifier at all.
    raw = {'id': str(uuid.uuid4()), 'mode': 'test-double', 'status': 'succeeded',
           'output': {'facts': [{'lot_id': 'SUP-C', 'affected': False, 'evidence': [
               {'document_id': d['id'], 'block_id': 'line-1', 'quote': text}]}], 'qualifiers': []}}
    monkeypatch.setattr(module, 'extract', lambda docs, mode: copy.deepcopy(raw))
    s = post(client, f"/api/cases/{s['id']}/analyze", {'document_id': d['id'], 'mode': 'fixture'})
    assert s['runs'][-1]['scope_concerns']
    request = {'run_id': raw['id'], 'revision': s['revision'], 'lot_ids': [],
               'excluded_lot_ids': ['SUP-C'], 'accept_scope': True, 'bounded_scope_reviewed': True,
               'incident_scope_status': 'resolved', 'resolution_quote': text,
               'note': 'Bad output must not override unresolved source language.'}
    assert client.post(f"/api/cases/{s['id']}/reviews", json=request).json()['detail']['code'] == 'UNRESOLVED_LOT'


def test_possible_ancestry_outside_affected_branch_stays_uncertain():
    s = load_demo()
    # Previously FG-D was outside because SUP-C was not an affected seed.
    next(e for e in s['edges'] if e['target'] == 'FG-D')['kind'] = 'possible'
    r = calculate(s['stocks'], s['edges'], ['SUP-A'], s['allocations'])
    assert next(p['classification'] for p in r['rows'] if p['id'] == 'FG-D') == 'uncertain'
    assert r['hold_units'] == 800
    # Uncertainty must propagate through a versioned intermediary too.
    edge = next(e for e in s['edges'] if e['target'] == 'FG-D')
    edge['target'] = 'EV-UNRESOLVED'
    s['edges'].append({'source': 'EV-UNRESOLVED', 'target': 'FG-D', 'kind': 'confirmed'})
    assert calculate(s['stocks'], s['edges'], ['SUP-A'], s['allocations'])['hold_units'] == 800


def test_uncertain_supplier_seed_is_never_documented():
    s = load_demo()
    r = calculate(s['stocks'], s['edges'], ['SUP-A'], s['allocations'], True, ['SUP-C'])
    assert (r['documented_units'], r['uncertain_units'], r['hold_units']) == (400, 400, 800)
    assert next(p['classification'] for p in r['rows'] if p['id'] == 'FG-D') == 'uncertain'


def test_resolved_scope_requires_source_basis_and_old_approval_is_invalid(client):
    s = prepare(client)
    old = copy.deepcopy(s['plan'])
    owner = hashlib.sha256(client.cookies.get('bf_session').encode()).hexdigest()
    with module.transaction(s['id'], owner) as (_, current):
        # Simulate an old persisted approval with no new review policy version.
        current['scope'].pop('review_policy_version')
        current['plan']['status'] = 'approved'
    response = client.post(f"/api/cases/{s['id']}/apply", json=payload({**s, 'plan': old}, 'legacy-plan-key'))
    assert response.status_code == 409
    assert client.get(f"/api/cases/{s['id']}").json()['receipts'] == []
    assert make_plan({**s, 'scope': {'lot_ids': ['SUP-A']}})['result']['hold_units'] == 1200


def test_incomplete_disposition_and_fabricated_resolution_quote_rejected(client):
    s = prepare(client)
    request = {'run_id': s['runs'][-1]['id'], 'revision': s['revision'], 'lot_ids': ['SUP-A'],
               'accept_scope': True, 'bounded_scope_reviewed': True, 'incident_scope_status': 'resolved',
               'resolution_quote': 'Invented complete boundary', 'note': 'Operator explanation does not make a fabricated quote supported.'}
    route = f"/api/cases/{s['id']}/reviews"
    assert client.post(route, json=request).json()['detail']['code'] == 'SCOPE_BASIS_REQUIRED'
    request.update(uncertain_lot_ids=['SUP-A'])
    assert client.post(route, json=request).json()['detail']['code'] == 'CONFLICTING_REVIEW'
