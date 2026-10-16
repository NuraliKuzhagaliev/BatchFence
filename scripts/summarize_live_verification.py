"""Summarize preserved observations; verify restarted backend without inference."""
import hashlib
import json
import statistics
import xml.etree.ElementTree as ET
import httpx
from backend.fixtures import ROOT, now
from backend.domain import digest

dest = ROOT / 'docs/live-verification'
report = json.loads((dest / 'browser-results.json').read_text(encoding='utf-8'))
packet = json.loads((dest / 'packet-2.json').read_text(encoding='utf-8'))
private = json.loads((__import__('pathlib').Path(report['review_directory']) / 'private-browser-session.json').read_text(encoding='utf-8'))
with httpx.Client(base_url='http://127.0.0.1:8787', timeout=15) as client:
    for cookie in private['cookies']:
        client.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])
    response = client.get('/api/cases/' + report['case_id'])
    response.raise_for_status()
    current = response.json()
    assert current['receipts'] == packet['case']['receipts']
    assert current['stocks'] == packet['case']['stocks']
    assert current['runs'] == packet['case']['runs']
    assert sum(s['units'] for s in current['stocks'] if s['status'] == 'held') == 800
    assert digest(packet['case']) == packet['integrity_hash']
    health = client.get('/api/health').json()
persistence = {'at': now(), 'status': 'passed', 'case_id': current['id'],
    'method': 'Actual owned uvicorn process stopped and relaunched; same private browser-session capability fetched identical runs, stock and receipts.',
    'receipt_ids': [r['transaction_id'] for r in current['receipts']], 'held_units': 800,
    'additional_model_calls': 0, 'health': health}
(dest / 'restart-results.json').write_text(json.dumps(persistence, indent=2), encoding='utf-8')

probe = json.loads((ROOT / 'docs/amd-probe.json').read_text(encoding='utf-8'))
initial = json.loads((dest / 'initial-test-attempt/browser-results.json').read_text(encoding='utf-8'))
runs = [p['run'] for p in probe['probes']] + [s['raw_run'] for s in initial['stages']] + [s['raw_run'] for s in report['stages']]
assert len({r['id'] for r in runs}) == 7
times = [r['elapsed_ms'] for r in runs]
summary = {'at': now(), 'requested_model_id': 'Gemma-4-31B-IT',
    'returned_model_ids': sorted({r['model_id'] for r in runs}), 'live_http_calls': len(runs),
    'schema_and_exact_quote_validation_successes': sum(r['status'] == 'succeeded' for r in runs),
    'transport_failures': 0, 'repairs': 0, 'fixture_fallback_used': False,
    'observed_latency_ms': {'min': min(times), 'median': statistics.median(times), 'max': max(times),
        'sample_count': len(times), 'limitation': 'Small sequential mixed-prompt sample with provider-reported cached tokens; not a performance benchmark.'},
    'raw_semantics': {'clear_capability_probes': 'clean, adversarial and changed cases supported expected lot facts',
        'ambiguous_probe': 'NOT a semantic pass: SUP-R may be affected but was marked true; unresolved SUP-S was marked false. An unresolved-scope qualifier survived. These booleans do not establish confirmed affected or unaffected status.',
        'fresh_and_revised_unique_notices': 2, 'missing_affected_ids': 0, 'extra_affected_ids': 0,
        'explicitly_excluded_id': 'NX-6130-Z correctly marked false in both', 'human_or_operator_corrections': 0},
    'workflow': {'status': report['status'], 'review_method': 'Codex source review plus automated product review/approval controls; no independent human validation',
        'held_units': [500, 800], 'newly_held_on_revision': 300, 'uncertain_units': [100, 100],
        'receipt_ids': persistence['receipt_ids'], 'stale_request': report['stale_request_recheck'],
        'process_restart_persistence': 'passed'},
    'runs': [{'id':r['id'], 'request_id':r.get('request_id'), 'timestamp':r['timestamp'],
              'model_id':r['model_id'], 'elapsed_ms':r['elapsed_ms'], 'status':r['status']} for r in runs],
    'not_claimed': ['broad model accuracy', 'independent customer/domain validation', 'physical GPU model',
                    'hosted deployment', 'public download', 'competition eligibility or submission acceptance']}
(dest / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
xml_path = dest / 'pytest-results.xml'
tree = ET.parse(xml_path)
for suite in tree.iter('testsuite'):
    suite.attrib.pop('hostname', None)
tree.write(xml_path, encoding='utf-8', xml_declaration=True)
print(json.dumps({'live_calls':len(runs), 'latency_ms':summary['observed_latency_ms'],
    'restart_persistence':persistence['status'], 'held_units':[500,800], 'corrections':0}, indent=2))
