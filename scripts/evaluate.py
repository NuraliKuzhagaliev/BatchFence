from pathlib import Path
import hashlib
import json
import time
from backend.domain import calculate, DomainError

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'evals/manifest.json').read_text())
records = []
missed = wrong_outside = expected_documented = 0
for item in manifest:
    raw = (ROOT / 'evals' / item['split'] / (item['id'] + '.json')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise SystemExit('Frozen evaluation content changed')
    c = json.loads(raw)
    started = time.perf_counter()
    try:
        r = calculate(c['stocks'], c['edges'], c['seeds'], c['allocations'], c['bounded'])
        actual = {k: sorted(x['id'] for x in r['rows'] if x['classification'] == k) for k in c['truth']}
        ok = not c['expected_error'] and actual == c['truth']
        expected_documented += len(c['truth']['documented'])
        missed += len(set(c['truth']['documented']) - set(actual['documented']))
        wrong_outside += len(set(actual['outside']) - set(c['truth']['outside']))
        expected_units = sum(s['units'] for s in c['stocks'] if s['id'] in c['truth']['documented'] + c['truth']['uncertain'] and s['status'] != 'shipped')
        expected_cents = sum(s['units'] * s['unit_cents'] for s in c['stocks'] if s['id'] in c['truth']['documented'] + c['truth']['uncertain'] and s['status'] != 'shipped')
        ok = ok and r['hold_units'] == expected_units and r['hold_cents'] == expected_cents
        if c['second_scope']:
            second = c['second_scope']
            revised = calculate(c['stocks'], c['edges'], second['seeds'], c['allocations'], c['bounded'])
            second_actual = {k: sorted(x['id'] for x in revised['rows'] if x['classification'] == k) for k in second['truth']}
            ok = ok and second_actual == second['truth']
        message = 'Exact classification and accounting' if ok else 'Mismatch'
    except DomainError as exc:
        ok = c['expected_error']
        actual = None
        message = str(exc)
    records.append({**item, 'passed': ok, 'actual': actual, 'detail': message,
                    'domain_elapsed_ms': round((time.perf_counter() - started) * 1000, 3)})
report = {'kind': 'Synthetic deterministic domain evaluation; no model inference',
          'cases': len(records), 'passed': sum(r['passed'] for r in records),
          'dev': {'total':18, 'passed':sum(r['passed'] for r in records if r['split']=='dev')},
          'held_out': {'total':12, 'passed':sum(r['passed'] for r in records if r['split']=='test')},
          'documented_stock_truth_denominator': expected_documented,
          'missed_documented_stock':missed, 'wrong_outside_classifications':wrong_outside,
          'raw_model_extraction':'Not part of this deterministic evaluation; see separate live AMD evidence.', 'records':records}
(ROOT / 'docs/evaluation-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='records'}, indent=2))
if not all(r['passed'] for r in records):
    raise SystemExit(1)
