import asyncio
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
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from .domain import DomainError, calculate, digest, make_plan, validate_dataset
from .fixtures import ROOT, load_demo, document, now
from .provider import extract
from .public_demo import public_demo, limiter, inference_access
from .review_safety import REVIEW_POLICY_VERSION, mentions, scope_concerns, resolution_evidence

load_dotenv(ROOT / '.env')
app = FastAPI(title='BatchFence', version='0.3.0-rc.1')
DB = Path((os.getenv('DATABASE_PATH') or str(ROOT / 'work/batchfence.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
ORIGIN = os.getenv('APP_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL') or 'http://127.0.0.1:8787'
if public_demo() and not ORIGIN.startswith('https://'):
    raise RuntimeError('PUBLIC_DEMO requires APP_ORIGIN or RENDER_EXTERNAL_URL with HTTPS')


from . import repository, identity, workspace


def connect():
    return repository.connect(DB)


with connect():
    pass


def fail(code, message, status=409):
    raise HTTPException(status, {'code': code, 'message': message})


@app.middleware('http')
async def protection(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': {'code': 'CSRF', 'message': 'Cross-site API access denied'}}, 403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            allowed = {ORIGIN} if public_demo() else {ORIGIN, 'http://127.0.0.1:5173', 'http://localhost:5173'}
            if origin and origin not in allowed:
                return JSONResponse({'detail': {'code': 'ORIGIN', 'message': 'Origin denied'}}, 403)
            if 'application/json' not in request.headers.get('content-type', ''):
                return JSONResponse({'detail': {'code': 'CONTENT_TYPE', 'message': 'JSON required'}}, 415)
        secret = request.headers.get('x-bf-session') or request.cookies.get('bf_session')
        if not secret or len(secret) < 32 or len(secret) > 200:
            secret = secrets.token_urlsafe(32)
        request.state.owner = hashlib.sha256(secret.encode()).hexdigest()
        auth_context = None
        if identity.pilot() and request.url.path not in ('/api/health', '/api/auth/login'):
            try:
                with connect() as db:
                    actor = identity.authenticate(db, request.headers.get('x-bf-session') or request.cookies.get('bf_pilot'))
                identity.authorize_route(actor, request.url.path, request.method)
                request.state.owner = identity.scope(actor['org'], actor['site'])
                actor['required_role'] = identity.route_role(request.url.path, request.method)
                request.state.actor = actor
                auth_context = identity.principal.set(actor)
            except HTTPException as exc:
                return JSONResponse({'detail': exc.detail}, exc.status_code)
        if not identity.pilot() and request.url.path != '/api/health':
            with connect() as db:
                _,actor = repository.get_record(db, request.state.owner, 'simulated-identity', 'current')
            if actor: auth_context = identity.principal.set(actor)
        if identity.pilot() and not limiter.allow('pilot:' + (request.client.host if request.client else 'local')):
            if auth_context is not None: identity.principal.reset(auth_context)
            return JSONResponse({'detail': {'code':'RATE_LIMIT','message':'Request limit reached'}},429)
        if public_demo() and request.url.path != '/api/health' and not limiter.allow(request.state.owner):
            if auth_context is not None: identity.principal.reset(auth_context)
            return JSONResponse({'detail': {'code': 'RATE_LIMIT', 'message': 'Request limit reached. Retry in one minute.'}}, 429, headers={'Retry-After': '60'})
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            limit = 8_000_000
            try:
                if int(request.headers.get('content-length', '0')) > limit:
                    if auth_context is not None: identity.principal.reset(auth_context)
                    return JSONResponse({'detail': {'code': 'SIZE', 'message': 'Request exceeds 8 MB'}}, 413)
                async def bounded_body():
                    chunks = []; size = 0
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > limit:
                            raise OverflowError()
                        chunks.append(chunk)
                    # Starlette's cached request replays this bounded body to routing.
                    request._body = b''.join(chunks)
                await asyncio.wait_for(bounded_body(), timeout=15)
            except OverflowError:
                if auth_context is not None: identity.principal.reset(auth_context)
                return JSONResponse({'detail': {'code': 'SIZE', 'message': 'Request exceeds 8 MB'}}, 413)
            except (ValueError, asyncio.TimeoutError):
                if auth_context is not None: identity.principal.reset(auth_context)
                return JSONResponse({'detail': {'code': 'BODY', 'message': 'Invalid or incomplete request body'}}, 400)
        try:
            response = await call_next(request)
        finally:
            if auth_context is not None: identity.principal.reset(auth_context)
        response.set_cookie('bf_session', secret, httponly=True, samesite='strict',
                            secure=ORIGIN.startswith('https://'), max_age=604800)
        if request.headers.get('x-bf-client') == 'desktop' and not identity.pilot():
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
        identity.recheck(db)
        row = db.execute('SELECT state FROM cases WHERE id=? AND owner=?', (case_id, owner)).fetchone()
        if not row:
            fail('NOT_FOUND', 'Case unavailable in this session', 404)
        state = json.loads(row[0])
        workspace.hydrate(db,owner,state)
        before_state = copy.deepcopy(state)
        yield db, state
        workspace.synchronize(db,owner,before_state,state)
        if identity.pilot():
            identity.recheck(db)
            repository.audit(db, owner, identity.current_actor(), 'case.updated', before_state, state, [d['original_hash'] for d in state['documents']])
        encoded = json.dumps(state)
        if len(encoded.encode()) > 6_000_000:
            fail('CASE_SIZE', 'Case storage limit reached; export this case before continuing in a new draft.', 413)
        db.execute('UPDATE cases SET state=? WHERE id=? AND owner=?', (encoded, case_id, owner))
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
        state = json.loads(row[0])
        return workspace.hydrate(db,owner,state)


def insert(state, owner):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if public_demo() and db.execute('SELECT count(*) FROM cases').fetchone()[0] >= int((os.getenv('MAX_STORED_CASES') or '60')):
            fail('DEMO_CAPACITY', 'Workspace storage capacity is reached. Exported packets remain available; contact the workspace owner.', 429)
        if db.execute('SELECT count(*) FROM cases WHERE owner=?', (owner,)).fetchone()[0] >= 12:
            fail('CASE_LIMIT', 'Session limit: 12 cases', 429)
        identity.recheck(db)
        for doc in state['documents']:
            candidate = ROOT / 'fixtures/demo' / doc['filename']
            if doc.get('synthetic') and Path(doc['filename']).name == doc['filename'] and candidate.is_file():
                raw = candidate.read_bytes()
                if hashlib.sha256(raw).hexdigest() == doc['original_hash']:
                    repository.save_source(db, owner, raw)
        if workspace.enabled(state):
            workspace.initialize(db,owner,state)
            workspace.hydrate(db,owner,state)
        db.execute('INSERT INTO cases VALUES(?,?,?)', (state['id'], owner, json.dumps(state)))
        if identity.pilot():
            repository.audit(db, owner, identity.current_actor(), 'case.created', {}, state)
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
    request_id: str | None = Field(default=None, max_length=80)


class Hypothesis(Strict):
    kind: Literal['identity', 'boundary', 'inconclusive']
    pool_id: str = Field(default='', max_length=160)
    supplier_lot_id: str = Field(default='', max_length=80)
    complete: bool = False
    lot_ids: list[str] = Field(default_factory=list, max_length=80)
    uncertain_lot_ids: list[str] = Field(default_factory=list, max_length=80)


class Scenario(Strict):
    revision: int
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=6)


class Reply(Strict):
    revision: int
    document_id: str = Field(max_length=80)
    pool_id: str = Field(max_length=160)
    supplier_lot_id: str = Field(default='', max_length=80)
    outcome: Literal['resolved','inconclusive','conflicting']
    complete: bool = False
    quote: str = Field(min_length=8,max_length=3000)
    reviewed: bool = False
    replacement_reviewed: bool = False
    note: str = Field(default='',max_length=2000)


class Review(Strict):
    run_id: str
    revision: int
    lot_ids: list[str] = Field(max_length=80)
    lot_corrections: dict[str,str] = Field(default_factory=dict,max_length=80)
    uncertain_lot_ids: list[str] = Field(default_factory=list, max_length=80)
    excluded_lot_ids: list[str] = Field(default_factory=list, max_length=80)
    incident_scope_status: Literal['unresolved', 'resolved'] = 'unresolved'
    resolution_quote: str = Field(default='', max_length=3000)
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
    try:
        with connect() as db:
            db.execute('SELECT count(*) FROM cases').fetchone()
            schema = db.execute('SELECT max(version) FROM bf_schema').fetchone()[0]
        if schema != repository.SCHEMA:
            raise sqlite3.DatabaseError()
    except Exception:
        return JSONResponse({'status': 'unavailable', 'database': 'unavailable'}, 503)
    return {'status': 'ok', 'database': 'ready', 'version': '0.3.0-rc.1',
            'commit': os.getenv('RENDER_GIT_COMMIT', 'local'),
            'inference_mode': (os.getenv('INFERENCE_MODE') or 'fixture'),
            'amd_configured': all(os.getenv(k) for k in ['AMD_API_BASE_URL', 'AMD_API_KEY', 'AMD_MODEL_ID', 'AMD_PROVIDER_EVIDENCE']),
            'live_protected': public_demo() or bool(os.getenv('LIVE_DEMO_TOKEN')),
            'profile': 'pilot' if identity.pilot() else 'public' if public_demo() else 'local', 'public_demo': public_demo(), 'storage_mode': os.getenv('STORAGE_MODE') or 'local', 'replay_available': (ROOT / 'fixtures/replay/amd-reviewed.json').exists()}


@app.get('/api/replay')
def replay():
    return FileResponse(ROOT / 'fixtures/replay/amd-reviewed.json', media_type='application/json')


@app.get('/api/cases')
def cases(request: Request):
    with connect() as db:
        rows = db.execute('SELECT state FROM cases WHERE owner=? ORDER BY id DESC', (request.state.owner,)).fetchall()
    return [{'id': s['id'], 'name': s['name'], 'revision': s['revision']}
            for s in [json.loads(r[0]) for r in rows]]


@app.post('/api/cases/demo')
def demo(request: Request):
    return insert(load_demo(), request.state.owner)


@app.post('/api/cases/import')
def promote(packet: Packet, request: Request):
    state = copy.deepcopy(validate_packet(packet))
    for field in ('enterprise_packet','workspace_attached','enterprise_example','hold_ledger','recovery_receipts','quantities','procedure_checks','receiving_runs','origin_signal'):
        state.pop(field,None)
    for stock in state['stocks']:stock['status']='available'
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
    read(case_id, request.state.owner)  # Authorize before expensive untrusted parsing.
    if '/' in data.filename or '\\' in data.filename:
        fail('FILENAME', 'Use a plain filename', 422)
    suffix = Path(data.filename).suffix.lower()
    if suffix not in ('.txt', '.csv', '.pdf'):
        fail('FORMAT', 'Supported inputs: UTF-8 TXT/CSV and text PDF', 422)
    ocr_images = []
    try:
        raw = base64.b64decode(data.content_base64, validate=True)
        if not raw or len(raw) > 2_000_000:
            fail('SIZE', 'File limit: 2 MB', 413)
        if suffix == '.pdf':
            from .documents import process_pdf
            try:
                doc, ocr_images = process_pdf(raw,data.filename,data.synthetic,request.state.owner,case_id,connect)
            except DomainError as exc:
                if 'engine unavailable' in str(exc): fail('OCR_UNSUPPORTED',str(exc),422)
                raise
        else:
            doc = document(data.filename, raw, synthetic=data.synthetic)
    except csv.Error:
        fail('CSV', 'Malformed CSV record quoting', 422)
    except DomainError:
        raise
    except (ValueError, UnicodeDecodeError):
        fail('INPUT', 'Invalid UTF-8 or base64 input', 422)
    except (HTTPException, DomainError):
        raise
    except Exception:
        fail('PDF', 'PDF could not be read; use a supported text PDF', 422)
    if sum(len(b['text']) for b in doc['blocks']) > 80_000:
        fail('TEXT_LIMIT', 'Normalized text exceeds 80,000 characters', 413)
    pending = parse_csv(doc) if suffix == '.csv' else None
    with transaction(case_id, request.state.owner) as (db, s):
        repository.save_source(db, request.state.owner, raw)
        for page in ocr_images:
            repository.save_source(db, request.state.owner, page['raw'])
        if len(s['documents']) >= 24:
            fail('DOCUMENT_LIMIT', 'Case limit: 24 documents', 429)
        if data.request_id:
            cause = next((c for c in make_plan(s)['result']['requests'] if c['id']==data.request_id),None)
            if cause is None or not s['plan']:
                fail('QUESTION_STALE','Evidence question is absent or has changed',422)
            doc.update(request_id=data.request_id,request_snapshot=cause,
                       prior_plan_digest=s['plan']['digest'],prior_pending=s['pending_revision'])
        s['revision'] += 1
        doc['revision'] = s['revision']
        s['documents'].append(doc)
        if pending:
            s['pending_data'] = {**(s['pending_data'] or {}), **pending}
        invalidate(s, 'New source: ' + data.filename + '. Re-extract and review current evidence.')
    return s


@app.post('/api/cases/{case_id}/revision')
def revision(case_id: str, request: Request):
    with transaction(case_id, request.state.owner) as (db, s):
        if not s['synthetic']:
            fail('SYNTHETIC_ONLY', 'Use source upload for a non-synthetic case')
        if any(d['filename'] == 'supplier_notice_v2.txt' for d in s['documents']):
            fail('REVISION_EXISTS', 'Correction already present')
        s['revision'] += 1
        s['documents'].append(document('supplier_notice_v2.txt',
            (ROOT / 'fixtures/demo/supplier_notice_v2.txt').read_bytes(), s['revision']))
        repository.save_source(db, request.state.owner, (ROOT / 'fixtures/demo/supplier_notice_v2.txt').read_bytes())
        invalidate(s, 'Supplier correction expands affected lots. Previous approval is stale immediately.')
    return s


@app.post('/api/cases/{case_id}/analyze')
def analyze(case_id: str, data: Analyze, request: Request):
    with inference_access(data.mode, request.headers.get('x-bf-demo-token', '')):
        with transaction(case_id, request.state.owner) as (job_db, s):
            if len(s['runs']) >= int((os.getenv('MAX_RUNS_PER_SESSION') or '12')):
                fail('RUN_LIMIT', 'Case inference limit reached', 429)
            # Sum across cases to bound session usage as well.
            with connect() as db:
                total = sum(len(json.loads(r[0])['runs']) for r in
                            db.execute('SELECT state FROM cases WHERE owner=?', (request.state.owner,)))
            if total >= int((os.getenv('MAX_RUNS_PER_SESSION') or '12')):
                fail('RUN_LIMIT', 'Session inference limit reached', 429)
            if data.mode == 'live':
                with connect() as db:
                    all_live = sum(sum(r.get('mode') == 'live' for r in json.loads(row[0])['runs'])
                                   for row in db.execute('SELECT state FROM cases'))
                if all_live >= int((os.getenv('MAX_TOTAL_LIVE_RUNS') or '100')):
                    fail('OWNER_BUDGET', 'Owner-controlled total live request limit reached', 429)
            docs = [d for d in s['documents'] if d['id'] == data.document_id]
            if not docs:
                fail('DOCUMENT', 'Select an existing narrative source', 422)
            if data.mode == 'fixture' and not docs[0]['synthetic']:
                fail('FIXTURE_ONLY', 'Fixture parser accepts explicitly synthetic documents only', 422)
            rev = s['revision']
            slot = uuid.uuid4().hex
            from . import jobs
            jobs.start(job_db, request.state.owner, slot, 'extraction', {'case_id':case_id,'document_id':data.document_id,'revision':rev}, data.mode)
            s['runs'].append({'id': slot, 'mode': data.mode, 'status': 'running', 'revision': rev, 'timestamp': now()})
        run = extract(docs, data.mode)
        run['revision'] = rev
        run['document_id'] = data.document_id
        run['scope_concerns'] = scope_concerns(docs[0])
        with transaction(case_id, request.state.owner) as (job_db, s):
            accepted = jobs.finish(job_db, request.state.owner, slot, run['status'], digest(run))
            if not accepted:
                run['status'] = 'cancelled'
                run['error'] = 'Job result not accepted after cancellation or interruption; no review authority'
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
        if data.incident_scope_status == 'resolved':
            from .ocr import require_visual_review
            require_visual_review(source)
        if source.get('request_id'):
            fail('REPLY_REVIEW','Use linked reply reconciliation; receiving candidates cannot replace incident scope',422)
        lots = sorted(set(l.strip() for l in data.lot_ids))
        uncertain = sorted(set(l.strip() for l in data.uncertain_lot_ids))
        excluded = sorted(set(l.strip() for l in data.excluded_lot_ids))
        if set(lots) & set(uncertain) or set(lots) & set(excluded) or set(uncertain) & set(excluded):
            fail('CONFLICTING_REVIEW', 'A lot must have exactly one reviewed disposition', 422)
        for lot in lots + uncertain + excluded:
            if not lot or len(lot) > 80 or not any(mentions(lot, b['text']) for b in source['blocks']):
                fail('UNSUPPORTED_LOT', 'Corrected lot must occur in the selected source; upload evidence first', 422)
        candidates = {f['lot_id'] for f in runs[0]['output']['facts']}
        if not set(data.lot_corrections) <= candidates or (data.lot_corrections and len(data.note.strip()) < 20):
            fail('CORRECTION_REVIEW','Identifier corrections need an original candidate and a review explanation',422)
        candidates = {data.lot_corrections.get(c,c).strip() for c in candidates}
        if not candidates <= set(lots + uncertain + excluded):
            fail('UNREVIEWED_LOTS', 'Review every model candidate, including negative proposals; keep unresolved lots uncertain', 422)
        concerns = scope_concerns(source)
        if any(mentions(lot, c['quote']) for c in concerns for lot in lots + excluded):
            fail('UNRESOLVED_LOT', 'The source leaves this lot unresolved. Keep it uncertain or upload a clarifying notice', 422)
        if data.bounded_scope_reviewed and data.incident_scope_status != 'resolved':
            fail('UNRESOLVED_SCOPE', 'Unresolved incident scope cannot authorize narrowed exclusions', 422)
        if concerns and data.incident_scope_status == 'resolved':
            fail('UNRESOLVED_SCOPE', 'The source explicitly leaves scope unresolved. Upload clarifying evidence before narrowing', 422)
        basis = None
        if data.incident_scope_status == 'resolved':
            basis = resolution_evidence(source, data.resolution_quote)
            if basis is None or len(data.note.strip()) < 20:
                fail('SCOPE_BASIS_REQUIRED', 'A resolved scope needs an exact notice quote and your explanation of its complete boundary', 422)
        if excluded and len(data.note.strip()) < 20:
            fail('EXCLUSION_REVIEW_REQUIRED', 'Explain explicit exclusions; a model false proposal is not an exclusion', 422)
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
                      'source_document_id': source['id'], 'uncertain_lot_ids': uncertain,
                      'excluded_lot_ids': excluded, 'incident_scope_status': data.incident_scope_status,
                      'resolution_evidence': basis, 'review_policy_version': REVIEW_POLICY_VERSION,
                      'resolution_note': data.note, 'scope_concerns': concerns}
        s['reviews'].append({'at': now(), 'reviewer': identity.current_actor() if identity.pilot() else 'Anonymous session reviewer', 'run_id': data.run_id,
                             'suggested_lots': [f['lot_id'] for f in runs[0]['output']['facts'] if f['affected']],
                             'accepted_lots': lots, 'previous_lots': prior,
                             'revision': s['revision'], 'note': data.note,
                             'lot_corrections':data.lot_corrections,
                             'uncertain_lot_ids': uncertain, 'excluded_lot_ids': excluded,
                             'incident_scope_status': data.incident_scope_status, 'resolution_evidence': basis,
                             'review_policy_version': REVIEW_POLICY_VERSION,
                             'bounded_scope_reviewed': data.bounded_scope_reviewed})
        s['plan'] = make_plan(s)
        s['pending_revision'] = False
        s['history'].append({'at': now(), 'type': 'reviewed', 'revision': s['revision'],
                             'previous_lots': prior, 'lot_ids': lots, 'old_units': old_units,
                             'suggested_lots': [f['lot_id'] for f in runs[0]['output']['facts'] if f['affected']],
                             'new_units': s['plan']['result']['hold_units'],
                             'message': 'Critical scope and completeness reviewed; new exact plan calculated.'})
    return s


@app.post('/api/cases/{case_id}/simulate')
def scenario(case_id: str, data: Scenario, request: Request):
    from .scenarios import simulate
    s = read(case_id, request.state.owner)
    if s['revision'] != data.revision:
        fail('STALE_SCENARIO','Evidence changed; refresh the scenario')
    return simulate(s,[h.model_dump() for h in data.hypotheses])


@app.post('/api/cases/{case_id}/reply-preview')
def reply_preview(case_id: str, data: Reply, request: Request):
    from .reconciliation import preview_reply
    return preview_reply(read(case_id, request.state.owner),data)


@app.post('/api/cases/{case_id}/reply-review')
def reply_review(case_id: str, data: Reply, request: Request):
    from .reconciliation import commit_reply
    with transaction(case_id,request.state.owner) as (_,s):
        commit_reply(s,data,now())
    return s


@app.get('/api/cases/{case_id}/comparison')
def comparison(case_id: str, request: Request):
    from .comparison import compare_plans
    s = read(case_id,request.state.owner)
    if not s['plan'] or not s['plans']:
        fail('COMPARISON','Two reviewed plans are required',422)
    return compare_plans(s['plans'][-1],s['plan'])


@app.post('/api/cases/{case_id}/approve')
def approve(case_id: str, data: Approve, request: Request):
    with transaction(case_id, request.state.owner) as (_, s):
        p = s['plan']
        if not approval_current(s,data.plan_id,data.digest):
            fail('STALE_APPROVAL', 'Only the current reviewed exact plan can be approved')
        p['status'] = 'approved'
        p['approval'] = {'at': now(), 'reviewer': identity.current_actor() if identity.pilot() else 'Anonymous session reviewer',
                         'digest': p['digest'], 'plan_id': p['id'], 'authorization': identity.approval_identity()}
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
        if not identity.approval_still_authorized(db, p.get('approval',{}).get('authorization'), 'quality_reviewer'):
            fail('REVOKED_APPROVAL','The named approver no longer holds the approval role')
        fresh = make_plan(s)
        actions = [a.model_dump() for a in data.actions]
        if not actions_exact(actions,fresh):
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


def approval_current(s,plan_id,plan_digest):
    p=s.get('plan')
    return bool(p and not s['pending_revision'] and p['status']=='proposed' and p['id']==plan_id and p['digest']==plan_digest and make_plan(s)['digest']==p['digest'])


def actions_exact(actions,plan):
    return actions == plan['actions']


@app.post('/api/challenges')
def challenges():
    from .challenges import run_challenges
    return {'provenance':'Synthetic in-memory policy checks','timestamp':now(),
            'checks':run_challenges(approval_current,actions_exact)}


@app.get('/api/cases/{case_id}/export')
def export(case_id: str, request: Request):
    s = read(case_id, request.state.owner)
    from .enterprise_routes import snapshot
    with connect() as db:s['enterprise_packet']=snapshot(db,request.state.owner,case_id)
    return {'schema_version': 1, 'exported_at': now(), 'label': 'Historical read-only packet. Hash is change detection, not supplier authentication.',
            'case': s, 'integrity_hash': digest(s)}


from .auth_routes import router as auth_router
app.include_router(auth_router)
from .intake_routes import router as intake_router
app.include_router(intake_router)
from .signal_routes import router as signal_router
from .knowledge_routes import router as knowledge_router
from .enterprise_routes import router as enterprise_router
app.include_router(signal_router)
app.include_router(knowledge_router)
app.include_router(enterprise_router)
from .receiving_routes import router as receiving_router
app.include_router(receiving_router)
from .recovery_routes import router as recovery_router
app.include_router(recovery_router)
from .action_routes import router as action_router
app.include_router(action_router)


if (ROOT / 'dist').exists():
    app.mount('/assets', StaticFiles(directory=ROOT / 'dist/assets'), name='assets')


@app.get('/')
def index():
    if not (ROOT / 'dist/index.html').exists():
        return JSONResponse({'message': 'Run npm run build, then restart backend'}, 503)
    # Keep desktop file:// assets relative; web navigation resolves from its origin.
    return HTMLResponse((ROOT / 'dist/index.html').read_text(encoding='utf-8').replace('src="./assets/', 'src="/assets/').replace('href="./assets/', 'href="/assets/'))


@app.get('/{path:path}')
def spa(path: str, request: Request):
    # Never turn a missing API or asset into a successful HTML response.
    if path.startswith(('api/', 'assets/')) or '.' in path.rsplit('/', 1)[-1] or 'text/html' not in request.headers.get('accept', ''):
        raise HTTPException(404, 'Not found')
    return index()
