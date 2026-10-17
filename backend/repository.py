"""Incremental snapshot repository. No provider calls belong inside write()."""
import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from .domain import digest
from .fixtures import now

SCHEMA = 2
_migration_lock = threading.Lock()
from .migrations.v002 import TABLES


class Connection:
    def __init__(self, raw, postgres=False):
        self.raw, self.postgres = raw, postgres
        self.created_sources=[]

    def execute(self, sql, params=()):
        if self.postgres:
            if sql == 'BEGIN IMMEDIATE':
                # One bounded committing writer across web/worker processes.
                # Reads/model network waits do not take this lock.
                self.raw.execute('BEGIN')
                return self.raw.execute('SELECT pg_advisory_xact_lock(742913005)')
            sql = sql.replace('?', '%s')
        return self.raw.execute(sql, params)

    def commit(self):
        self.raw.commit()
        self.created_sources.clear()
    def rollback(self):
        # Remove only files created by this uncommitted writer, while its database
        # lock still prevents another writer from adopting them.
        for path,root in self.created_sources:
            resolved=path.resolve()
            if not resolved.is_relative_to(root):raise RuntimeError('Source cleanup escaped its owned directory')
            resolved.unlink(missing_ok=True)
        self.created_sources.clear()
        self.raw.rollback()
    def close(self):
        if self.created_sources:self.rollback()
        self.raw.close()
    def __enter__(self): return self
    def __exit__(self, kind, value, trace):
        try:
            self.rollback() if kind else self.commit()
        finally:
            self.close()


def migrate(db):
    """Explicit PostgreSQL migration; SQLite upgrades are backed up before DDL."""
    db.execute('BEGIN IMMEDIATE')
    try:
        for table, columns in TABLES.items():
            db.execute(f'CREATE TABLE IF NOT EXISTS {table} ({columns})')
        db.execute('CREATE INDEX IF NOT EXISTS cases_owner ON cases(owner)')
        db.execute('CREATE INDEX IF NOT EXISTS audit_owner ON bf_audit(owner,at)')
        db.execute('INSERT INTO bf_schema VALUES(?,?) ON CONFLICT(version) DO NOTHING', (SCHEMA, now()))
        if db.postgres:
            db.execute("""CREATE OR REPLACE FUNCTION bf_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN RAISE EXCEPTION 'Audit entries are append-only'; END; $$""")
            db.execute('DROP TRIGGER IF EXISTS bf_audit_no_change ON bf_audit')
            db.execute('CREATE TRIGGER bf_audit_no_change BEFORE UPDATE OR DELETE ON bf_audit FOR EACH ROW EXECUTE FUNCTION bf_audit_immutable()')
        else:
            for operation in ('UPDATE', 'DELETE'):
                db.execute(f"CREATE TRIGGER IF NOT EXISTS audit_no_{operation.lower()} BEFORE {operation} ON bf_audit BEGIN SELECT RAISE(ABORT,'Audit entries are append-only'); END")
            db.execute(f'PRAGMA user_version={SCHEMA}')
        db.commit()
    except Exception:
        db.rollback()
        raise


def connect(path, *, url=None, migration=False):
    url = os.getenv('PILOT_DATABASE_URL') if url is None else url
    if url:
        import psycopg
        db = Connection(psycopg.connect(url, autocommit=True, connect_timeout=10), True)
        if migration:
            migrate(db)
        else:
            version = db.execute('SELECT max(version) FROM bf_schema').fetchone()[0]
            if version != SCHEMA:
                db.close()
                raise RuntimeError('Pilot migration required; run python -m scripts.pilot migrate')
        return db
    path = Path(path)
    raw = sqlite3.connect(path, timeout=15)
    raw.execute('PRAGMA foreign_keys=ON')
    raw.execute('PRAGMA journal_mode=WAL')
    db = Connection(raw)
    with _migration_lock:
        version = raw.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, SCHEMA):
            db.close()
            raise sqlite3.DatabaseError('Unsupported database schema; migration required')
        if version != SCHEMA:
            if version == 1:
                backup = path.with_name(path.name + '.pre-v2-backup')
                if not backup.exists():
                    with sqlite3.connect(backup) as target:
                        raw.backup(target)
            migrate(db)
    return db


@contextmanager
def write(connection_factory):
    with connection_factory() as db:
        db.execute('BEGIN IMMEDIATE')
        yield db


def get_record(db, owner, kind, key, default=None):
    row = db.execute('SELECT revision,data FROM bf_records WHERE owner=? AND kind=? AND id=?', (owner, kind, key)).fetchone()
    return (row[0], json.loads(row[1])) if row else (0, default)


def put_record(db, owner, kind, key, value, expected=None):
    revision, previous = get_record(db, owner, kind, key)
    if expected is not None and revision != expected:
        from .domain import DomainError
        raise DomainError('Record changed; refresh and review the new revision')
    encoded = json.dumps(value, ensure_ascii=False)
    if len(encoded.encode()) > 6_000_000:
        from .domain import DomainError
        raise DomainError('Workspace record exceeds the supported 6 MB envelope')
    count=db.execute('SELECT count(*) FROM bf_records WHERE owner=?',(owner,)).fetchone()[0]
    size_expr='OCTET_LENGTH(data)' if db.postgres else 'LENGTH(CAST(data AS BLOB))'
    owner_size=db.execute(f'SELECT COALESCE(SUM({size_expr}),0) FROM bf_records WHERE owner=?',(owner,)).fetchone()[0]
    global_size=db.execute(f'SELECT COALESCE(SUM({size_expr}),0) FROM bf_records').fetchone()[0]
    delta=len(encoded.encode())-(len(json.dumps(previous,ensure_ascii=False).encode()) if revision else 0)
    if (not revision and count>=300) or owner_size+delta>24_000_000 or global_size+delta>128_000_000:
        from .domain import DomainError
        raise DomainError('Workspace record storage limit reached; no partial authoritative write')
    db.execute('INSERT INTO bf_records VALUES(?,?,?,?,?) ON CONFLICT(owner,kind,id) DO UPDATE SET revision=excluded.revision,data=excluded.data',
               (owner, kind, key, revision + 1, encoded))
    return revision + 1


def audit(db, owner, actor, operation, before, after, sources=(), operation_id=None):
    import uuid
    if db.execute('SELECT count(*) FROM bf_audit WHERE owner=?',(owner,)).fetchone()[0]>=10000 or db.execute('SELECT count(*) FROM bf_audit').fetchone()[0]>=200000:
        from .domain import DomainError
        raise DomainError('Audit capacity reached; preserve and archive the workspace before additional writes')
    row = db.execute('SELECT event_hash FROM bf_audit WHERE owner=? ORDER BY at DESC,id DESC LIMIT 1', (owner,)).fetchone()
    previous = row[0] if row else '0' * 64
    event = {'actor': actor, 'operation': operation, 'operation_id': operation_id or uuid.uuid4().hex,
             'at': now(), 'old_hash': digest(before), 'new_hash': digest(after), 'sources': list(sources)}
    event_hash = digest({'previous_hash': previous, 'event': event})
    db.execute('INSERT INTO bf_audit VALUES(?,?,?,?,?,?)',
               (uuid.uuid4().hex, owner, event['at'], json.dumps(event), previous, event_hash))
    return event_hash


def source_root():
    from .fixtures import ROOT
    return Path(os.getenv('SOURCE_STORAGE_PATH') or ROOT / 'work/sources')


def source_path(owner, sha):
    if not re.fullmatch('[a-f0-9]{64}', sha):
        raise ValueError('Invalid source hash')
    return source_root() / hashlib.sha256(owner.encode()).hexdigest() / sha


def save_source(db, owner, raw):
    """Content addressed bytes; rolled-back writers remove only their new blobs."""
    sha = hashlib.sha256(raw).hexdigest()
    existing=db.execute('SELECT size FROM bf_sources WHERE owner=? AND hash=?',(owner,sha)).fetchone()
    if not existing:
        owner_size=db.execute('SELECT COALESCE(SUM(size),0) FROM bf_sources WHERE owner=?',(owner,)).fetchone()[0]
        global_size=db.execute('SELECT COALESCE(SUM(size),0) FROM bf_sources').fetchone()[0]
        if len(raw)>4_000_000 or owner_size+len(raw)>64_000_000 or global_size+len(raw)>256_000_000:
            from .domain import DomainError
            raise DomainError('Original source storage limit reached; no partial authoritative write')
    path = source_path(owner, sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as file:
            db.created_sources.append((path,source_root().resolve()))
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
    except FileExistsError:
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('Stored source integrity failure')
    db.execute('INSERT INTO bf_sources VALUES(?,?,?,?) ON CONFLICT(owner,hash) DO NOTHING', (owner, sha, len(raw), now()))
    return sha
