import base64
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from .domain import DomainError, calculate, digest, make_plan, validate_dataset
from .fixtures import ROOT, load_demo, document, now
from .provider import extract

load_dotenv(ROOT / '.env')
app = FastAPI(title='BatchFence', version='0.1.0')
DB = Path(os.getenv('DATABASE_PATH', str(ROOT / 'work/batchfence.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
ORIGIN = os.getenv('APP_ORIGIN', 'http://127.0.0.1:8787')


def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS receipts(owner TEXT NOT NULL, key TEXT NOT NULL, request_digest TEXT NOT NULL, receipt TEXT NOT NULL, PRIMARY KEY(owner,key))')
    return db


with connect() as db:
    db.execute('PRAGMA user_version=1')


def fail(code, message, status=409):
    raise HTTPException(status, {'code': code, 'message': message})


@app.middleware('http')
async def protection(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': {'code': 'CSRF', 'message': 'Cross-site API access denied'}}, 403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if origin and origin not in {ORIGIN, 'http://127.0.0.1:5173', 'http://localhost:5173'}:
                return JSONResponse({'detail': {'code': 'ORIGIN', 'message': 'Origin denied'}}, 403)
            if 'application/json' not in request.headers.get('content-type', ''):
                return JSONResponse({'detail': {'code': 'CONTENT_TYPE', 'message': 'JSON required'}}, 415)
            body = await request.body()
            if len(body) > 8_000_000:
                return JSONResponse({'detail': {'code': 'SIZE', 'message': 'Request exceeds 8 MB'}}, 413)
        secret = request.headers.get('x-bf-session') or request.cookies.get('bf_session')
        if not secret or len(secret) < 32 or len(secret) > 200:
            secret = secrets.token_urlsafe(32)
        request.state.owner = hashlib.sha256(secret.encode()).hexdigest()
        response = await call_next(request)
        response.set_cookie('bf_session', secret, httponly=True, samesite='strict',
                            secure=ORIGIN.startswith('https://'), max_age=604800)
        if request.headers.get('x-bf-client') == 'desktop':
            response.headers['x-bf-session'] = secret
        response.headers['Cache-Control'] = 'no-store'
    else:
        response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse({'detail': {'code': 'DOMAIN', 'message': str(exc)}}, 422)


@contextmanager
def transaction(case_id, owner):
    db = connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state FROM cases WHERE id=? AND owner=?', (case_id, owner)).fetchone()
        if not row:
            fail('NOT_FOUND', 'Case unavailable in this session', 404)
        state = json.loads(row[0])
        yield db, state
        db.execute('UPDATE cases SET state=? WHERE id=? AND owner=?', (json.dumps(state), case_id, owner))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def read(case_id, owner):
    with connect() as db:
        row = db.execute('SELECT state FROM cases WHERE id=? AND owner=?', (case_id, owner)).fetchone()
    if not row:
        fail('NOT_FOUND', 'Case unavailable in this session', 404)
    return json.loads(row[0])


def insert(state, owner):
    with connect() as db:
        if db.execute('SELECT count(*) FROM cases WHERE owner=?', (owner,)).fetchone()[0] >= 12:
            fail('CASE_LIMIT', 'Session limit: 12 cases', 429)
        db.execute('INSERT INTO cases VALUES(?,?,?)', (state['id'], owner, json.dumps(state)))
    return state


def invalidate(state, reason):
    if state['plan'] and state['plan']['status'] != 'applied':
        state['plan']['status'] = 'stale'
    state['pending_revision'] = True
    state['history'].append({'at': now(), 'type': 'evidence_changed', 'message': reason,
                              'revision': state['revision']})


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Analyze(Strict):
    document_id: str
    mode: str = Field(pattern='^(live|fixture|recorded)$')


class Upload(Strict):
    filename: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(max_length=4_000_000)
    synthetic: bool = False


class Review(Strict):
    run_id: str
    revision: int
    lot_ids: list[str] = Field(min_length=1, max_length=80)
    accept_scope: bool
    bounded_scope_reviewed: bool
    note: str = Field(default='', max_length=2000)


class Action(Strict):
    type: str = Field(pattern='^hold$')
    pool_id: str


class Approve(Strict):
    plan_id: str
    digest: str


class Apply(Approve):
    actions: list[Action]
    idempotency_key: str = Field(min_length=8, max_length=100)


class Packet(Strict):
    schema_version: int
    exported_at: str
    label: str
    case: dict
    integrity_hash: str


def validate_packet(packet):
    if packet.schema_version != 1 or packet.integrity_hash != digest(packet.case):
        fail('PACKET_INVALID', 'Unsupported schema or changed packet content', 422)
    s = packet.case
    required = {'stocks', 'edges', 'allocations', 'documents', 'scope', 'policy', 'runs',
                'reviews', 'receipts', 'history', 'revision', 'name', 'bounded'}
    if not required.issubset(s) or len(json.dumps(s)) > 6_000_000:
        fail('PACKET_INVALID', 'Incomplete or oversized decision packet', 422)
    try:
        if not isinstance(s['name'], str) or not isinstance(s.get('incident'), str) or type(s.get('synthetic')) is not bool or type(s['bounded']) is not bool:
            raise ValueError()
        if not isinstance(s['policy'], dict) or not all(isinstance(s['policy'][k], str) for k in ('id', 'rule')):
            raise ValueError()
        if not isinstance(s['documents'], list) or len(s['documents']) > 24:
            raise ValueError()
        for d in s['documents']:
            if not all(isinstance(d[k], str) for k in ('id', 'filename', 'media_type', 'original_hash', 'text_hash')):
                raise ValueError()
            if type(d['revision']) is not int or d['revision'] < 1 or type(d['synthetic']) is not bool or len(d['blocks']) > 5000:
                raise ValueError()
            if not all(isinstance(b['id'], str) and isinstance(b['text'], str) for b in d['blocks']) or sum(len(b['text']) for b in d['blocks']) > 80000:
                raise ValueError()
        validate_dataset(s['stocks'], s['edges'], s['allocations'])
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        fail('PACKET_INVALID', 'Malformed packet records or unsupported dataset schema', 422)
    return s


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '0.1.0', 'inference_mode': os.getenv('INFERENCE_MODE', 'fixture'),
            'amd_configured': all(os.getenv(k) for k in ['AMD_API_BASE_URL', 'AMD_API_KEY', 'AMD_MODEL_ID', 'AMD_PROVIDER_EVIDENCE']),
            'desktop_distribution': 'Local unsigned installer; publication pending'}


@app.get('/api/cases')
def cases(request: Request):
    with connect() as db:
        rows = db.execute('SELECT state FROM cases WHERE owner=? ORDER BY rowid DESC', (request.state.owner,)).fetchall()
    return [{'id': s['id'], 'name': s['name'], 'revision': s['revision']}
            for s in [json.loads(r[0]) for r in rows]]


@app.post('/api/cases/demo')
def demo(request: Request):
    return insert(load_demo(), request.state.owner)


@app.post('/api/cases/import')
def promote(packet: Packet, request: Request):
    state = copy.deepcopy(validate_packet(packet))
    state.update({'id': uuid.uuid4().hex, 'revision': 1, 'inventory_version': 1,
                  'scope': {'lot_ids': [], 'revision': 0, 'qualifiers': []},
                  'plan': None, 'plans': [], 'runs': [], 'reviews': [], 'receipts': [],
                  'history': [{'at': now(), 'type': 'imported', 'message': 'New draft from historical packet; approvals are not transferable.'}],
                  'pending_data': None, 'pending_revision': True})
    return insert(state, request.state.owner)


@app.get('/api/cases/{case_id}')
def get_case(case_id: str, request: Request):
    return read(case_id, request.state.owner)


def parse_csv(doc):
    rows = list(csv.DictReader(io.StringIO('\n'.join(b['text'] for b in doc['blocks']))))
    if not rows or len(rows) > 500:
        fail('CSV', 'CSV must have 1–500 data rows', 422)
    keys = set(rows[0])
    try:
        if {'pool_id', 'unit_cents', 'ancestry_complete', 'site', 'product_family', 'status', 'units', 'row_id'} <= keys:
            stocks = [{'id': r['pool_id'], 'units': int(r['units']), 'unit_cents': int(r['unit_cents']),
                       'status': r['status'], 'complete': r['ancestry_complete'] == 'true',
                       'site': r['site'], 'product_family': r['product_family'],
                       'row_id': r['row_id'], 'snapshot_version': doc['revision']} for r in rows]
            return {'stocks': stocks}
        if {'source', 'target', 'kind', 'row_id'} <= keys:
            return {'edges': [{**r, 'evidence': {'document_id': doc['id'], 'block_id': doc['blocks'][i+1]['id'],
                      'quote': doc['blocks'][i+1]['text']}} for i, r in enumerate(rows)]}
        if {'order_id', 'pool_id', 'units', 'due_date', 'row_id', 'revision', 'status'} <= keys:
            return {'allocations': [{**r, 'units': int(r['units'])} for r in rows]}
    except (ValueError, KeyError):
        fail('CSV', 'Malformed CSV values or missing columns', 422)
    fail('CSV', 'Unsupported CSV schema; use fixture headers for inventory, lineage or order allocations', 422)


@app.post('/api/cases/{case_id}/documents')
def upload(case_id: str, data: Upload, request: Request):
    if '/' in data.filename or '\\' in data.filename:
        fail('FILENAME', 'Use a plain filename', 422)
    suffix = Path(data.filename).suffix.lower()
    if suffix not in ('.txt', '.csv', '.pdf'):
        fail('FORMAT', 'Supported inputs: UTF-8 TXT/CSV and text PDF', 422)
    try:
        raw = base64.b64decode(data.content_base64, validate=True)
        if not raw or len(raw) > 2_000_000:
            fail('SIZE', 'File limit: 2 MB', 413)
        if suffix == '.pdf':
            reader = PdfReader(io.BytesIO(raw))
            if len(reader.pages) > 30:
                fail('PDF', 'PDF limit: 30 pages', 422)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            if not text.strip():
                fail('OCR_UNSUPPORTED', 'Image-only PDF is unsupported; upload selectable text', 422)
            doc = document(data.filename, text.encode(), synthetic=data.synthetic)
            doc['original_hash'] = hashlib.sha256(raw).hexdigest()
            doc['media_type'] = 'application/pdf'
        else:
            doc = document(data.filename, raw, synthetic=data.synthetic)
    except csv.Error:
        fail('CSV', 'Malformed CSV record quoting', 422)
    except (ValueError, UnicodeDecodeError):
        fail('INPUT', 'Invalid UTF-8 or base64 input', 422)
    except HTTPException:
        raise
    except Exception:
        fail('PDF', 'PDF could not be read; use a supported text PDF', 422)
    if sum(len(b['text']) for b in doc['blocks']) > 80_000:
        fail('TEXT_LIMIT', 'Normalized text exceeds 80,000 characters', 413)
    pending = parse_csv(doc) if suffix == '.csv' else None
    with transaction(case_id, request.state.owner) as (_, s):
        if len(s['documents']) >= 24:
            fail('DOCUMENT_LIMIT', 'Case limit: 24 documents', 429)
        s['revision'] += 1
        doc['revision'] = s['revision']
        s['documents'].append(doc)
        if pending:
            s['pending_data'] = {**(s['pending_data'] or {}), **pending}
        invalidate(s, 'New source: ' + data.filename + '. Re-extract and review current evidence.')
    return s


@app.post('/api/cases/{case_id}/revision')
def revision(case_id: str, request: Request):
    with transaction(case_id, request.state.owner) as (_, s):
        if not s['synthetic']:
            fail('SYNTHETIC_ONLY', 'Use source upload for a non-synthetic case')
        if any(d['filename'] == 'supplier_notice_v2.txt' for d in s['documents']):
            fail('REVISION_EXISTS', 'Correction already present')
        s['revision'] += 1
        s['documents'].append(document('supplier_notice_v2.txt',
            (ROOT / 'fixtures/demo/supplier_notice_v2.txt').read_bytes(), s['revision']))
        invalidate(s, 'Supplier correction expands affected lots. Previous approval is stale immediately.')
    return s


@app.post('/api/cases/{case_id}/analyze')
def analyze(case_id: str, data: Analyze, request: Request):
    with transaction(case_id, request.state.owner) as (_, s):
        if len(s['runs']) >= int(os.getenv('MAX_RUNS_PER_SESSION', '12')):
            fail('RUN_LIMIT', 'Case inference limit reached', 429)
        # Sum across cases to bound session usage as well.
        with connect() as db:
            total = sum(len(json.loads(r[0])['runs']) for r in
                        db.execute('SELECT state FROM cases WHERE owner=?', (request.state.owner,)))
        if total >= int(os.getenv('MAX_RUNS_PER_SESSION', '12')):
            fail('RUN_LIMIT', 'Session inference limit reached', 429)
        if data.mode == 'live':
            with connect() as db:
                all_live = sum(sum(r.get('mode') == 'live' for r in json.loads(row[0])['runs'])
                               for row in db.execute('SELECT state FROM cases'))
            if all_live >= int(os.getenv('MAX_TOTAL_LIVE_RUNS', '100')):
                fail('OWNER_BUDGET', 'Owner-controlled total live request limit reached', 429)
        docs = [d for d in s['documents'] if d['id'] == data.document_id]
        if not docs:
            fail('DOCUMENT', 'Select an existing narrative source', 422)
        if data.mode == 'fixture' and not docs[0]['synthetic']:
            fail('FIXTURE_ONLY', 'Fixture parser accepts explicitly synthetic documents only', 422)
        rev = s['revision']
        slot = uuid.uuid4().hex
        s['runs'].append({'id': slot, 'mode': data.mode, 'status': 'running', 'revision': rev})
    run = extract(docs, data.mode)
    run['revision'] = rev
    run['document_id'] = data.document_id
    with transaction(case_id, request.state.owner) as (_, s):
        if s['revision'] != rev:
            run['status'] = 'stale'
            run['error'] = 'Evidence changed during inference; analyze current sources'
        s['runs'] = [run if r['id'] == slot else r for r in s['runs']]
    return s


@app.post('/api/cases/{case_id}/reviews')
def review(case_id: str, data: Review, request: Request):
    with transaction(case_id, request.state.owner) as (_, s):
        if data.revision != s['revision']:
            fail('STALE_REVIEW', 'Evidence changed before review')
        runs = [r for r in s['runs'] if r['id'] == data.run_id and r['status'] == 'succeeded' and r['revision'] == s['revision']]
        if not runs or not data.accept_scope:
            fail('REVIEW_REQUIRED', 'A successful current extraction and explicit scope review are required', 422)
        source = next(d for d in s['documents'] if d['id'] == runs[0]['document_id'])
        lots = sorted(set(l.strip() for l in data.lot_ids))
        for lot in lots:
            if not lot or len(lot) > 80 or not any(lot in b['text'] for b in source['blocks']):
                fail('UNSUPPORTED_LOT', 'Corrected lot must occur in the selected source; upload evidence first', 422)
        if s['plan']:
            old = copy.deepcopy(s['plan'])
            if old['status'] != 'applied':
                old['status'] = 'stale'
            s['plans'].append(old)
        if s['pending_data']:
            # Preserve any existing holds through record replacement.
            existing_held = {p['id'] for p in s['stocks'] if p['status'] == 'held'}
            if 'stocks' in s['pending_data']:
                if not existing_held <= {p['id'] for p in s['pending_data']['stocks']}:
                    fail('HELD_STOCK', 'Replacement inventory cannot remove held pools', 422)
                for p in s['pending_data']['stocks']:
                    if p['id'] in existing_held:
                        p['status'] = 'held'
                s['inventory_version'] += 1
            s.update(s['pending_data'])
            s['pending_data'] = None
        prior = s['scope']['lot_ids']
        old_units = s['plan']['result']['hold_units'] if s['plan'] else None
        s['bounded'] = data.bounded_scope_reviewed
        s['scope'] = {'lot_ids': lots, 'revision': s['revision'], 'qualifiers': runs[0]['output']['qualifiers'],
                      'source_document_id': source['id']}
        s['reviews'].append({'at': now(), 'reviewer': 'Anonymous session reviewer', 'run_id': data.run_id,
                             'suggested_lots': [f['lot_id'] for f in runs[0]['output']['facts'] if f['affected']],
                             'accepted_lots': lots, 'previous_lots': prior,
                             'revision': s['revision'], 'note': data.note,
                             'bounded_scope_reviewed': data.bounded_scope_reviewed})
        s['plan'] = make_plan(s)
        s['pending_revision'] = False
        s['history'].append({'at': now(), 'type': 'reviewed', 'revision': s['revision'],
                             'previous_lots': prior, 'lot_ids': lots, 'old_units': old_units,
                             'suggested_lots': [f['lot_id'] for f in runs[0]['output']['facts'] if f['affected']],
                             'new_units': s['plan']['result']['hold_units'],
                             'message': 'Critical scope and completeness reviewed; new exact plan calculated.'})
    return s


@app.post('/api/cases/{case_id}/approve')
def approve(case_id: str, data: Approve, request: Request):
    with transaction(case_id, request.state.owner) as (_, s):
        p = s['plan']
        if not p or s['pending_revision'] or p['status'] != 'proposed' or p['id'] != data.plan_id or p['digest'] != data.digest or make_plan(s)['digest'] != p['digest']:
            fail('STALE_APPROVAL', 'Only the current reviewed exact plan can be approved')
        p['status'] = 'approved'
        p['approval'] = {'at': now(), 'reviewer': 'Anonymous session reviewer',
                         'digest': p['digest'], 'plan_id': p['id']}
        s['history'].append({'at': now(), 'type': 'approved', 'revision': s['revision'],
                             'message': 'Approved exact plan ' + p['id']})
    return s


@app.post('/api/cases/{case_id}/apply')
def apply(case_id: str, data: Apply, request: Request):
    owner = request.state.owner
    fingerprint = digest({'case_id': case_id, **data.model_dump(exclude={'idempotency_key'})})
    with transaction(case_id, owner) as (db, s):
        prior = db.execute('SELECT request_digest,receipt FROM receipts WHERE owner=? AND key=?',
                           (owner, data.idempotency_key)).fetchone()
        if prior:
            if prior[0] != fingerprint:
                fail('IDEMPOTENCY_CONFLICT', 'Key already used for a different request')
            return s
        p = s['plan']
        if not p or s['pending_revision'] or p['id'] != data.plan_id or p['status'] != 'approved' or p['digest'] != data.digest:
            fail('STALE_APPROVAL', 'Approval is absent, stale or already consumed')
        fresh = make_plan(s)
        actions = [a.model_dump() for a in data.actions]
        if actions != fresh['actions']:
            fail('POLICY_VIOLATION', 'Exact required hold set must include uncertain stock; edited or unsupported actions are rejected')
        if p['digest'] != fresh['digest']:
            fail('STALE_INVENTORY', 'Evidence, inventory or policy changed after approval')
        changes = []
        ids = {a['pool_id'] for a in actions}
        for stock in s['stocks']:
            if stock['id'] in ids:
                changes.append({'pool_id': stock['id'], 'units': stock['units'],
                                'before': stock['status'], 'after': 'held'})
                stock['status'] = 'held'
        before = s['inventory_version']
        s['inventory_version'] += 1
        receipt = {'transaction_id': 'TX-' + uuid.uuid4().hex, 'at': now(),
                   'execution': 'SANDBOX INVENTORY', 'plan_id': p['id'], 'digest': p['digest'],
                   'idempotency_key': data.idempotency_key, 'changes': changes,
                   'prior_inventory_version': before, 'current_inventory_version': s['inventory_version'],
                   'evidence_revision': s['revision']}
        p['status'] = 'applied'
        s['receipts'].append(receipt)
        s['history'].append({'at': now(), 'type': 'applied', 'revision': s['revision'],
                             'message': 'Sandbox inventory committed atomically: ' + receipt['transaction_id']})
        db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (owner, data.idempotency_key, fingerprint, json.dumps(receipt)))
    return s


@app.get('/api/cases/{case_id}/export')
def export(case_id: str, request: Request):
    s = read(case_id, request.state.owner)
    return {'schema_version': 1, 'exported_at': now(), 'label': 'Historical read-only packet. Hash is change detection, not supplier authentication.',
            'case': s, 'integrity_hash': digest(s)}


if (ROOT / 'dist').exists():
    app.mount('/assets', StaticFiles(directory=ROOT / 'dist/assets'), name='assets')


@app.get('/')
def index():
    if not (ROOT / 'dist/index.html').exists():
        return JSONResponse({'message': 'Run npm run build, then restart backend'}, 503)
    return FileResponse(ROOT / 'dist/index.html')
