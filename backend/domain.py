"""Deterministic containment. Narrative model output cannot authorize actions."""
import hashlib
import rfc8785
from collections import defaultdict
from datetime import date
from .review_safety import REVIEW_POLICY_VERSION


class DomainError(ValueError):
    pass


def canonical(value):
    # Match JS number formatting and UTF-16 key ordering, including tiny AMD
    # usage costs. Python json.dumps(8.33e-5) differs from JSON.stringify.
    return rfc8785.dumps(value).decode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_dataset(stocks, edges, allocations):
    if not all(isinstance(x, list) and len(x) <= 500 for x in (stocks, edges, allocations)):
        raise DomainError('Each record dataset must have at most 500 rows')
    if not all(isinstance(x, dict) for x in stocks + edges + allocations):
        raise DomainError('Record rows must be objects')
    ids = [s['id'] for s in stocks]
    if any(not isinstance(x, str) or not x or len(x) > 160 for x in ids):
        raise DomainError('Stock identifiers must be nonempty bounded strings')
    if len(ids) != len(set(ids)) or not ids:
        raise DomainError('Duplicate logical stock or empty inventory')
    by_id = {s['id']: s for s in stocks}
    for s in stocks:
        if type(s.get('complete', False)) is not bool:
            raise DomainError('Completeness must be an explicit reviewed boolean')
        for k in ('units', 'unit_cents'):
            if type(s[k]) is not int or s[k] < 0 or s[k] > 9_000_000_000_000:
                raise DomainError('Discrete stock and cents must be nonnegative integers')
        if s['status'] not in ('available', 'held', 'shipped'):
            raise DomainError('Unsupported stock status')
    graph = defaultdict(list)
    sources = {e['source'] for e in edges}
    for e in edges:
        if any(not isinstance(e[k], str) or not e[k] or len(e[k]) > 160 for k in ('source', 'target')):
            raise DomainError('Lineage identifiers must be nonempty bounded strings')
        if e['kind'] not in ('confirmed', 'possible'):
            raise DomainError('Invalid lineage certainty')
        if e['target'] not in sources | set(ids):
            raise DomainError('Dangling lineage target')
        if e['source'] in by_id:
            raise DomainError('Current terminal inventory cannot be a component')
        graph[e['source']].append(e['target'])
    visited, active = set(), set()

    def visit(n):
        if n in active:
            raise DomainError('Lineage cycle; model rework with versioned event nodes')
        if n in visited:
            return
        active.add(n)
        for nxt in graph[n]:
            visit(nxt)
        active.remove(n)
        visited.add(n)

    for n in list(graph):
        visit(n)
    sums = defaultdict(int)
    rowids = set()
    for a in allocations:
        try:
            date.fromisoformat(a['due_date'])
        except (ValueError, TypeError):
            raise DomainError('Order due date must be a valid ISO calendar date')
        if a['row_id'] in rowids:
            raise DomainError('Duplicate allocation row')
        rowids.add(a['row_id'])
        if a['pool_id'] not in by_id or type(a['units']) is not int or a['units'] < 0:
            raise DomainError('Invalid order allocation')
        sums[a['pool_id']] += a['units']
    if any(n > by_id[k]['units'] for k, n in sums.items()):
        raise DomainError('Allocations exceed current stock')
    if sum(s['units'] * s['unit_cents'] for s in stocks) > 9_007_199_254_740_991:
        raise DomainError('Inventory value exceeds portable exact-integer range')


def calculate(stocks, edges, seeds, allocations, bounded=True, uncertain_seeds=None):
    validate_dataset(stocks, edges, allocations)
    uncertain_seeds = uncertain_seeds or []
    if not seeds and not uncertain_seeds and bounded:
        raise DomainError('Review at least one affected or unresolved lot')
    graph = defaultdict(list)
    for e in edges:
        graph[e['source']].append(e)
    documented, possible = {}, {}

    def walk(node, uncertain, path, refs):
        target = possible if uncertain else documented
        if node in target:
            return
        target[node] = (path, refs)
        for e in graph[node]:
            walk(e['target'], uncertain or e['kind'] == 'possible',
                 path + [e['target']], refs + [e.get('evidence')])

    for seed in sorted(set(seeds)):
        walk(seed, False, [seed], [])
    for seed in sorted(set(uncertain_seeds)):
        walk(seed, True, [seed], [])
    # Possible ancestry is unresolved even outside the chosen seed branches.
    # A completeness flag cannot convert a possible link into a proven exclusion.
    for e in sorted(edges, key=canonical):
        if e['kind'] == 'possible':
            walk(e['target'], True, [e['source'], e['target']], [e.get('evidence')])
    known = {e['source'] for e in edges}
    narrow = bounded and all(seed in known for seed in set(seeds) | set(uncertain_seeds))
    rows = []
    for s in sorted(stocks, key=lambda x: x['id']):
        sid, path, refs = s['id'], [], []
        if sid in documented:
            classification = 'documented'
            path, refs = documented[sid]
            reason = 'Confirmed ancestry reaches a reviewed affected lot.'
        elif sid in possible:
            classification = 'uncertain'
            path, refs = possible[sid]
            reason = 'Unresolved incident involvement or possible ancestry. This stock remains uncertain and in the hold.'
        elif not narrow or not s.get('complete', False) or not any(e['target'] == sid for e in edges):
            classification = 'uncertain'
            reason = 'Insufficient reviewed ancestry or bounded scope. Narrowed exclusion is unavailable.'
        else:
            classification = 'outside'
            reason = 'Reviewed complete ancestry has no affected-lot path within the declared incident universe.'
            incoming = [e for e in edges if e['target'] == sid]
            # Multiple parents are alternative links, never a fabricated serial path.
            path = [incoming[0]['source'], sid] if incoming else [sid]
            refs = [e.get('evidence') for e in incoming]
        rows.append({**s, 'classification': classification, 'reason': reason,
                     'path': path, 'evidence': [r for r in refs if r]})
    exposed = [s for s in rows if s['classification'] != 'outside']
    onsite = [s for s in rows if s['status'] != 'shipped']
    hold = [s for s in exposed if s['status'] != 'shipped']
    uncertain = [s for s in exposed if s['classification'] == 'uncertain']
    outside = [s for s in onsite if s['classification'] == 'outside']

    def units(xs):
        return sum(s['units'] for s in xs)

    def cents(xs):
        return sum(s['units'] * s['unit_cents'] for s in xs)

    orders = []
    exposed_ids = {s['id'] for s in exposed}
    for oid in sorted({a['order_id'] for a in allocations
                       if a['pool_id'] in exposed_ids and a['status'] == 'open'}):
        aa = [a for a in allocations if a['order_id'] == oid
              and a['pool_id'] in exposed_ids and a['status'] == 'open']
        orders.append({'order_id': oid, 'due_date': min(a['due_date'] for a in aa),
                       'pool_ids': sorted({a['pool_id'] for a in aa}),
                       'units': sum(a['units'] for a in aa),
                       'reason': 'Allocated stock intersects exposure; needs review.',
                       'source_rows': [a['row_id'] for a in aa]})
    requests = [{
        'id': 'REQ-' + s['id'], 'pool_ids': [s['id']], 'units': s['units'],
        'value_cents': s['units'] * s['unit_cents'],
        'missing': 'Receiving identity / complete ancestry for ' + s['id'],
        'reason': s['reason'],
        'draft': f"Please provide the original receiving lot record for {s['id']} ({s['units']} units), including supplier lot ID, receipt row and revision. An inconclusive response preserves uncertainty. This request does not authorize release."
    } for s in uncertain]
    requests.sort(key=lambda x: (-x['value_cents'], x['id']))
    return {
        'rows': rows,
        'node_states': {n: ('documented' if n in documented else 'uncertain' if n in possible or not narrow else 'outside')
                        for n in {e['source'] for e in edges} | {e['target'] for e in edges}},
        'documented_units': units([s for s in exposed if s['classification'] == 'documented']),
        'uncertain_units': units(uncertain), 'hold_units': units(hold),
        'outside_units': units(outside), 'broad_units': units(onsite),
        'hold_cents': cents(hold), 'broad_cents': cents(onsite),
        'excluded_cents': cents(outside),
        'reduction_percent': round(100 * (1 - units(hold) / units(onsite)), 1) if units(onsite) else 0,
        'actions': [{'type': 'hold', 'pool_id': s['id']} for s in hold],
        'requests': requests, 'request_unique_units': units(uncertain),
        'request_unique_cents': cents(uncertain), 'orders': orders,
        'shipment_reviews': [s['id'] for s in exposed if s['status'] == 'shipped'],
        'narrowing_available': narrow
    }


def plan_inputs(state, actions):
    return {
        'incident_id': state['id'],
        'review_policy_version': REVIEW_POLICY_VERSION,
        'evidence_revision': state['revision'],
        'inventory_version': state['inventory_version'],
        'documents': sorted([(d['id'], d['revision'], d['original_hash'], d['text_hash'])
                             for d in state['documents']]),
        'reviewed_scope': state['scope'], 'stocks': sorted(state['stocks'], key=lambda s: s['id']),
        'lineage': sorted(state['edges'], key=canonical),
        'allocations': sorted(state['allocations'], key=canonical),
        'policy': state['policy'], 'bounded': state['bounded'], 'actions': actions
    }


def make_plan(state):
    scope = state['scope']
    bounded = (state['bounded'] and scope.get('incident_scope_status') == 'resolved'
               and scope.get('review_policy_version') == REVIEW_POLICY_VERSION)
    result = calculate(state['stocks'], state['edges'], state['scope']['lot_ids'],
                       state['allocations'], bounded, scope.get('uncertain_lot_ids', []))
    from .causes import evidence_queue
    result['requests'], result['request_unique_units'], result['request_unique_cents'] = evidence_queue(state, result)
    result['node_states'].update({r['id']: r['classification'] for r in result['rows']})
    inputs = plan_inputs(state, result['actions'])
    return {'id': 'PLAN-' + digest(inputs)[:12], 'digest': digest(inputs),
            'source_claims': [r.get('output', {}) for r in state.get('runs', [])
                              if r.get('document_id') == scope.get('source_document_id') and r.get('status') == 'succeeded'][-1:],
            'status': 'proposed', 'revision': state['revision'],
            'inventory_version': state['inventory_version'],
            'actions': result['actions'], 'result': result, 'inputs': inputs}
