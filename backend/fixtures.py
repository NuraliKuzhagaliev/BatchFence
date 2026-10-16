from pathlib import Path
import csv
import hashlib
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def document(filename, raw, revision=1, synthetic=True):
    text = raw.decode('utf-8-sig')
    blocks = [{'id': f'line-{i+1}', 'text': line, 'page': None}
              for i, line in enumerate(text.splitlines()) if line.strip()]
    return {'id': 'DOC-' + uuid.uuid4().hex[:12], 'filename': filename,
            'media_type': 'text/csv' if filename.endswith('.csv') else 'text/plain',
            'revision': revision, 'ingested_at': now(),
            'original_hash': hashlib.sha256(raw).hexdigest(),
            'text_hash': hashlib.sha256(text.encode()).hexdigest(),
            'blocks': blocks, 'synthetic': synthetic}


def load_demo():
    root = ROOT / 'fixtures/demo'
    docs = [document(f.name, f.read_bytes()) for f in sorted(root.glob('*'))
            if f.suffix in ('.txt', '.csv') and 'v2' not in f.name]
    inventory = list(csv.DictReader((root / 'inventory.csv').open()))
    stocks = [{'id': r['pool_id'], 'units': int(r['units']), 'unit_cents': int(r['unit_cents']),
               'status': r['status'], 'complete': r['ancestry_complete'] == 'true',
               'site': r['site'], 'product_family': r['product_family'], 'row_id': r['row_id'],
               'snapshot_version': 1} for r in inventory]
    edoc = next(d for d in docs if d['filename'] == 'lineage.csv')
    edges = []
    for i, r in enumerate(csv.DictReader((root / 'lineage.csv').open())):
        b = edoc['blocks'][i+1]
        edges.append({**r, 'evidence': {'document_id': edoc['id'], 'block_id': b['id'], 'quote': b['text']}})
    allocations = [{**r, 'units': int(r['units'])}
                   for r in csv.DictReader((root / 'order_allocations.csv').open())]
    return {'id': uuid.uuid4().hex, 'name': 'Northstar Enclosures',
            'incident': 'Cosmetic coating defect · decorative housings', 'synthetic': True,
            'revision': 1, 'inventory_version': 1, 'documents': docs, 'stocks': stocks,
            'edges': edges, 'allocations': allocations, 'bounded': True,
            'policy': {'id': 'CONTAIN-1', 'revision': 1,
                       'rule': 'Hold every documented or possible on-site descendant. Never automatically release existing holds.'},
            'scope': {'lot_ids': [], 'revision': 0, 'qualifiers': []}, 'runs': [], 'reviews': [],
            'plans': [], 'plan': None, 'history': [], 'receipts': [], 'pending_data': None,
            'pending_revision': False}
