import copy
import pytest
from backend.domain import calculate, DomainError, digest, make_plan
from backend.fixtures import load_demo


def calc(s, seeds=None):
    return calculate(s['stocks'], s['edges'], seeds or ['SUP-A'], s['allocations'], s['bounded'])


def test_exact_main_fixture():
    s = load_demo()
    a = calc(s)
    assert (a['documented_units'], a['uncertain_units'], a['hold_units'], a['outside_units']) == (400, 100, 500, 700)
    assert (a['hold_cents'], a['broad_cents'], a['excluded_cents'], a['reduction_percent']) == (2000000, 4800000, 2800000, 58.3)
    assert len(a['orders']) == 3
    assert (a['request_unique_units'], a['request_unique_cents']) == (100, 400000)
    b = calc(s, ['SUP-A', 'SUP-C'])
    assert (b['documented_units'], b['uncertain_units'], b['hold_units'], b['outside_units']) == (700, 100, 800, 400)
    assert b['excluded_cents'] == 1600000 and len(b['orders']) == 4


def test_metamorphic_duplicate_paths_reordering_widening():
    s = load_demo()
    original = calc(s)
    s['edges'] += copy.deepcopy(s['edges'][:2])
    s['stocks'].reverse()
    s['edges'].reverse()
    s['allocations'].reverse()
    assert calc(s) == original
    wide = calc(s, ['SUP-A', 'SUP-C'])
    assert {a['pool_id'] for a in original['actions']} <= {a['pool_id'] for a in wide['actions']}


def test_missing_ancestry_cannot_create_exclusion():
    s = load_demo()
    s['stocks'][3]['complete'] = False
    assert calc(s)['hold_units'] == 800
    s['bounded'] = False
    assert calc(s)['hold_units'] == 1200


def test_merged_pool_full_hold_and_documented_precedence():
    s = load_demo()
    s['edges'].append({'source': 'SUP-A', 'target': 'FG-E', 'kind': 'confirmed'})
    s['edges'].append({'source': 'SUP-A', 'target': 'FG-C', 'kind': 'confirmed'})
    a = calc(s)
    assert a['hold_units'] == 750 and a['uncertain_units'] == 0


def test_shipped_stock_review_not_hold():
    s = load_demo()
    s['stocks'][0]['status'] = 'shipped'
    a = calc(s)
    assert 'FG-A' in a['shipment_reviews'] and all(x['pool_id'] != 'FG-A' for x in a['actions'])
    assert a['hold_units'] == 260 and a['documented_units'] == 400


@pytest.mark.parametrize('kind', ['negative', 'float', 'duplicate', 'cycle', 'dangling', 'allocation', 'terminal'])
def test_contradictions_rejected(kind):
    s = load_demo()
    if kind == 'negative': s['stocks'][0]['units'] = -1
    if kind == 'float': s['stocks'][0]['unit_cents'] = 40.5
    if kind == 'duplicate': s['stocks'].append(copy.deepcopy(s['stocks'][0]))
    if kind == 'cycle': s['edges'] += [{'source': 'EV1', 'target': 'EV2', 'kind': 'confirmed'}, {'source': 'EV2', 'target': 'EV1', 'kind': 'confirmed'}]
    if kind == 'dangling': s['edges'][0]['target'] = 'NO-STOCK'
    if kind == 'allocation': s['allocations'][0]['units'] += 1
    if kind == 'terminal': s['edges'].append({'source': 'FG-A', 'target': 'FG-B', 'kind': 'confirmed'})
    with pytest.raises(DomainError): calc(s)
