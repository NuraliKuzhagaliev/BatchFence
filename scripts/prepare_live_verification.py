"""Freeze synthetic, unseen narrative inputs before any workflow inference.

This prepares test data only. It neither invokes a model nor grants review/approval.
"""
import hashlib
import json
from pathlib import Path
from backend.domain import digest
from backend.fixtures import ROOT, load_demo, now

DEST = ROOT / 'docs/live-verification'
DEST.mkdir(parents=True, exist_ok=True)
if (DEST / 'input-manifest.json').exists():
    raise SystemExit('Frozen input manifest already exists; preserving it.')

mapping = {'SUP-A': 'MC-7421-X', 'SUP-B': 'RZ-2650', 'SUP-C': 'BZ-9187',
           'SUP-D': 'PQ-4806', 'SUP-E': 'NX-6130-Z'}
def replace(text):
    for old, new in mapping.items():
        text = text.replace(old, new)
    return text

state = json.loads(replace(json.dumps(load_demo(), ensure_ascii=False)))
state['name'] = 'Northstar · fresh live verification'
state['documents'] = [d for d in state['documents'] if d['filename'] != 'supplier_notice_v1.txt']
for doc in state['documents']:
    raw = replace((ROOT / 'fixtures/demo' / doc['filename']).read_text(encoding='utf-8'))
    (DEST / doc['filename']).write_text(raw, encoding='utf-8')
    doc['original_hash'] = doc['text_hash'] = hashlib.sha256(raw.encode()).hexdigest()
packet = {'schema_version': 1, 'exported_at': now(), 'label': 'Synthetic verification input; no model output or approval',
          'case': state, 'integrity_hash': digest(state)}
(DEST / 'input-packet.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')

notices = [
    ('fresh-notice.txt', '''SYNTHETIC VERIFICATION DATA — not a real customer or supplier notice.
Meridian Coatings containment advisory MC-2026-1016-A.
Our adhesion audit confirmed a cosmetic coating defect in material batch MC-7421-X.
Please contain all on-site stock descended from MC-7421-X pending quality review.
Batch NX-6130-Z appears on the delivery paperwork for traceability only; it is not covered by this defect notice.
This is the complete supplier batch scope for this advisory. Warehouse lots with uncertain ancestry still require conservative review.
'''),
    ('revised-notice.txt', '''SYNTHETIC VERIFICATION DATA — not a real customer or supplier notice.
Meridian Coatings replacement advisory MC-2026-1016-B.
This message supersedes advisory A in its entirety, following our second inspection.
The complete set of defective coating batches is now BZ-9187 together with MC-7421-X; retain on-site descendants of both.
NX-6130-Z remains outside this supplier notice. A missing warehouse receiving record does not establish that mixed stock is unaffected.
Do not release previously contained stock automatically.
''')]
manifest = {'frozen_at': now(), 'synthetic': True, 'uploaded_filename_for_both': 'supplier-message.txt',
            'purpose': 'Two live model responses must drive reviewed plans and real sandbox receipts; no fixture-parser execution.',
            'lot_mapping': mapping, 'cases': []}
for (filename, text), expected, units, documented, outside in zip(notices,
        [['MC-7421-X'], ['BZ-9187', 'MC-7421-X']], [500, 800], [400, 700], [700, 400]):
    raw = text.encode('utf-8')
    (DEST / filename).write_bytes(raw)
    manifest['cases'].append({'file': filename, 'sha256': hashlib.sha256(raw).hexdigest(),
        'affected_lots': expected, 'explicitly_not_affected': ['NX-6130-Z'],
        'documented_units': documented, 'uncertain_units': 100, 'hold_units': units,
        'outside_units': outside, 'hold_cents': units * 4000,
        'hold_pools': ['FG-A', 'FG-B', 'FG-C'] + (['FG-D'] if units == 800 else [])})
(DEST / 'input-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Frozen two new notices and independent expected sets; no inference performed.')
