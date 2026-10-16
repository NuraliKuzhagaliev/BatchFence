"""Two fresh ambiguity checks. Extraction and operator review are separate commands."""
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path
import httpx
from backend.domain import digest
from backend.fixtures import ROOT, now

DEST = ROOT / 'docs/ambiguity-fix'
PRIVATE = ROOT / 'work/ambiguity-live-session.json'
REPORT = DEST / 'live-ambiguity.json'
INPUTS = [
    {'name': 'unknown-involvement', 'text': 'MC-7421-X may be affected by the coating defect.\nWe cannot determine whether BZ-9187 is implicated.\nScope remains unresolved; the current notice is not a complete list.\nSynthetic verification notice only.',
     'expected': {'affected': [], 'uncertain': ['MC-7421-X', 'BZ-9187'], 'excluded': [], 'documented_units': 0, 'uncertain_units': 1200}},
    {'name': 'partial-confirmation', 'text': 'Confirmed defect: MC-7421-X.\nBZ-9187 is awaiting laboratory results; it has not been cleared.\nThe affected batch list is not yet final.\nNX-6130-Z is expressly excluded from this supplier incident.\nSynthetic verification notice only.',
     'expected': {'affected': ['MC-7421-X'], 'uncertain': ['BZ-9187'], 'excluded': ['NX-6130-Z'], 'documented_units': 400, 'uncertain_units': 800}},
]


def save(report):
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')


def post(client, route, body):
    r = client.post(route, json=body)
    r.raise_for_status()
    return r.json()


def main():
    DEST.mkdir(exist_ok=True)
    with httpx.Client(base_url='http://127.0.0.1:8787', timeout=60) as c:
        if sys.argv[1] in ('extract', 'resume', 'alternate'):
            if REPORT.exists() and sys.argv[1] not in ('resume', 'alternate'):
                raise SystemExit('Evidence already exists; refusing to rerun or overwrite live calls')
            if sys.argv[1] in ('resume', 'alternate'):
                report = json.loads(REPORT.read_text())
                assert report['cases'] and all(x['raw_run']['status'] == 'failed' for x in report['cases'])
                if sys.argv[1] == 'alternate':
                    assert not report.get('explicit_alternate_selection')
                    report['explicit_alternate_selection'] = 'MiMo-V2.6-Flash selected after a successful separately labeled probe; Gemma attempts retained. Not automatic fallback.'
                for failed in report['cases']:
                    failed['raw_boolean_quality'] = {'status': 'not_evaluated_no_model_result'}
                    failed['review_status'] = 'blocked_no_model_result'
                report.setdefault('failed_attempts', []).extend(report['cases'])
                report['cases'] = []
                if sys.argv[1] == 'resume':
                    report['retry_reason'] = 'One bounded retry after read-only catalog availability check; original failure retained.'
            else:
                report = {'frozen_at': now(), 'method': 'Fresh AMD requests through application API; synthetic inputs; no fallback.',
                          'review_method': 'Pending agent-operated review; no independent human validation', 'cases': []}
                report['inputs'] = [{**p, 'sha256': hashlib.sha256(p['text'].encode()).hexdigest()} for p in INPUTS]
            save(report)
            health = c.get('/api/health').json()
            assert health['amd_configured']
            seed = json.loads((ROOT / 'docs/live-verification/input-packet.json').read_text())
            for p in report['inputs']:
                s = post(c, '/api/cases/import', seed)
                s = post(c, f"/api/cases/{s['id']}/documents", {'filename': 'supplier-message.txt',
                    'content_base64': base64.b64encode(p['text'].encode()).decode(), 'synthetic': True})
                doc = s['documents'][-1]
                s = post(c, f"/api/cases/{s['id']}/analyze", {'document_id': doc['id'], 'mode': 'live'})
                run = s['runs'][-1]
                proposed = sorted(f['lot_id'] for f in run.get('output', {}).get('facts', []) if f['affected'])
                item = {'name': p['name'], 'case_id': s['id'], 'source': doc, 'raw_run': run,
                        'raw_boolean_quality': {'proposed_true': proposed, 'expected_confirmed': p['expected']['affected'],
                            'extra_as_confirmed': sorted(set(proposed) - set(p['expected']['affected'])),
                            'missing_confirmed': sorted(set(p['expected']['affected']) - set(proposed)),
                            'limitation': 'The boolean schema cannot represent unresolved involvement. Raw output is never rewritten.'},
                        'review_status': 'pending_operator'}
                report['cases'].append(item)
                save(report)
                PRIVATE.write_text(json.dumps(dict(c.cookies)), encoding='utf-8')
                print(json.dumps(item, indent=2))
                if run['status'] != 'succeeded':
                    item['raw_boolean_quality'] = {'status': 'not_evaluated_no_model_result'}
                    item['review_status'] = 'blocked_no_model_result'
                    save(report)
                    print('Live extraction failed; preserved failure, no fallback', flush=True)
        elif sys.argv[1] == 'review':
            report = json.loads(REPORT.read_text())
            assert all(x['review_status'] in ('pending_operator', 'blocked_no_model_result') for x in report['cases'])
            c.cookies.update(json.loads(PRIVATE.read_text()))
            choices = json.loads((ROOT / 'work/ambiguity-reviewed-choices.json').read_text())
            for item, choice, truth in zip(report['cases'], choices, report['inputs'], strict=True):
                assert choice['run_id'] == item['raw_run']['id']
                assert choice['source_hash'] == item['source']['original_hash']
                route = '/api/cases/' + item['case_id']
                s = c.get(route).json()
                request = {'run_id': choice['run_id'], 'revision': s['revision'], 'lot_ids': choice['affected'],
                    'uncertain_lot_ids': choice['uncertain'], 'excluded_lot_ids': choice['excluded'],
                    'incident_scope_status': 'unresolved', 'accept_scope': True, 'bounded_scope_reviewed': False,
                    'note': choice['note']}
                if item['raw_run']['status'] != 'succeeded':
                    blocked = c.post(route + '/reviews', json=request)
                    assert blocked.status_code == 422 and blocked.json()['detail']['code'] == 'REVIEW_REQUIRED'
                    current = c.get(route).json()
                    assert current['plan'] is None and not current['receipts']
                    item['raw_boolean_quality'] = {'status':'not_evaluated_no_accepted_output', 'error':item['raw_run']['error']}
                    item['review_status'] = 'blocked_failed_extraction'
                    item['review_attempt'] = {'http_status':blocked.status_code,'error':blocked.json()['detail']}
                    item['result_after_review'] = None
                    save(report)
                    continue
                bad = {**request, 'bounded_scope_reviewed': True}
                blocked = c.post(route + '/reviews', json=bad)
                assert blocked.status_code == 422 and blocked.json()['detail']['code'] == 'UNRESOLVED_SCOPE'
                item['narrowing_attempt'] = {'http_status': blocked.status_code, 'error': blocked.json()['detail']}
                s = post(c, route + '/reviews', request)
                r = s['plan']['result']
                assert (r['hold_units'], r['outside_units'], r['documented_units'], r['uncertain_units']) == (
                    1200, 0, truth['expected']['documented_units'], truth['expected']['uncertain_units'])
                p = s['plan']
                s = post(c, route + '/approve', {'plan_id': p['id'], 'digest': p['digest']})
                action = {'plan_id': p['id'], 'digest': p['digest'], 'actions': p['actions'],
                          'idempotency_key': 'ambiguity-' + item['name']}
                s = post(c, route + '/apply', action)
                assert sum(x['units'] for x in s['receipts'][-1]['changes']) == 1200
                assert post(c, route + '/apply', action)['receipts'] == s['receipts']
                item.update(review_status='agent_reviewed', reviewed_choices=choice, result_after_review=r,
                            receipt=s['receipts'][-1], refresh_persistence=c.get(route).json()['receipts'] == s['receipts'])
                packet = c.get(route + '/export').json()
                assert digest(packet['case']) == packet['integrity_hash']
                (DEST / (item['name'] + '-packet.json')).write_text(json.dumps(packet, indent=2), encoding='utf-8')
                save(report)
            report['review_method'] = 'Codex inspected sources/raw results and supplied choices; API review/approval/apply were automated. No independent human validation.'
            report['completed_at'] = now()
            report['status'] = 'safety_checks_passed_one_live_workflow_one_extraction_blocked'
            save(report)
            print(json.dumps({'status': report['status'], 'holds': [x['result_after_review']['hold_units'] if x['result_after_review'] else None for x in report['cases']], 'new_http_inference_calls': 0}))
        else:
            raise SystemExit('Use extract or review')


if __name__ == '__main__':
    main()
