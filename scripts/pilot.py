"""Owner-operated private pilot setup and portable isolated backup/restore.

No default credentials. Configuration values and model keys are never included.
Backups contain source bytes and password hashes: use an access-controlled,
encrypted off-device location for operational backups. Local drills are not DR.
"""
import argparse
import getpass
import hashlib
import json
import os
import sqlite3
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from backend import repository as repo
from backend.fixtures import ROOT, now


def backup(db, output):
    output = Path(output)
    if output.exists(): raise ValueError('Backup destination already exists; choose a new path')
    started = time.perf_counter()
    db.execute('BEGIN IMMEDIATE')
    try:
        tables = {}
        for name in repo.TABLES:
            if name == 'bf_sessions': continue  # Restoration requires fresh login.
            cur = db.execute(f'SELECT * FROM {name}')
            tables[name] = {'columns': [c[0] for c in cur.description], 'rows': [list(r) for r in cur.fetchall()]}
        manifest = {'schema': repo.SCHEMA, 'created_at': now(), 'tables': tables,
                    'configuration_references': ['PILOT_DATABASE_URL','SOURCE_STORAGE_PATH','PILOT_SESSION_SECRET','AMD_API_BASE_URL','AMD_MODEL_ID','AMD_API_KEY'],
                    'sources': [], 'sessions': 'Excluded; all users must sign in again after restore'}
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for owner, sha, size, _ in tables['bf_sources']['rows']:
                data = repo.source_path(owner, sha).read_bytes()
                if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
                    raise ValueError('Source integrity failure; backup incomplete')
                name = 'sources/' + hashlib.sha256(owner.encode()).hexdigest() + '/' + sha
                archive.writestr(name, data)
                manifest['sources'].append({'path': name, 'hash': sha, 'size': size})
            payload = json.dumps(manifest, sort_keys=True).encode()
            archive.writestr('manifest.json', payload)
            archive.writestr('manifest.sha256', hashlib.sha256(payload).hexdigest())
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'created_at': manifest['created_at'], 'duration_ms': round((time.perf_counter()-started)*1000),
            'counts': {k: len(v['rows']) for k,v in tables.items()}, 'source_count': len(manifest['sources']),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'bytes': output.stat().st_size,
            'boundary': 'Same-device backup drill does not establish disaster recovery; owner RPO/RTO not agreed.'}


def read_backup(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 250_000_000:
            raise ValueError('Backup exceeds supported 250 MB / 10,000 file envelope')
        names = [i.filename for i in infos]
        if len(set(names)) != len(names) or any('..' in n.split('/') or n.startswith(('/', '\\')) or '\\' in n or ':' in n for n in names):
            raise ValueError('Unsafe or duplicate backup path')
        payload = archive.read('manifest.json')
        if hashlib.sha256(payload).hexdigest() != archive.read('manifest.sha256').decode():
            raise ValueError('Backup manifest changed')
        manifest = json.loads(payload)
        if manifest['schema'] != repo.SCHEMA or set(manifest['tables']) != set(repo.TABLES)-{'bf_sessions'}:
            raise ValueError('Unsupported backup schema')
        sources = {}
        for item in manifest['sources']:
            data = archive.read(item['path'])
            if hashlib.sha256(data).hexdigest() != item['hash'] or len(data) != item['size']:
                raise ValueError('Backup source changed')
            sources[item['path']] = data
        expected = {'sources/'+hashlib.sha256(r[0].encode()).hexdigest()+'/'+r[1] for r in manifest['tables']['bf_sources']['rows']}
        if expected != set(sources) or set(names) != expected | {'manifest.json','manifest.sha256'}:
            raise ValueError('Backup source manifest mismatch')
    return manifest, sources


def restore(db, path, destination):
    """Restore only to empty DB and a new directory; never replace a live store."""
    started = time.perf_counter()
    manifest, sources = read_backup(path)
    destination = Path(destination).resolve()
    if destination.exists(): raise ValueError('Restore source directory must not exist')
    db.execute('BEGIN IMMEDIATE')
    try:
        for table in repo.TABLES:
            if table != 'bf_schema' and db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                raise ValueError('Restore database must be empty and isolated')
        destination.mkdir(parents=True)
        for name, raw in sources.items():
            target = (destination / name.removeprefix('sources/')).resolve()
            if not target.is_relative_to(destination): raise ValueError('Unsafe restore path')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for table, data in manifest['tables'].items():
            if table == 'bf_schema': continue
            actual = [c[0] for c in db.execute(f'SELECT * FROM {table} LIMIT 0').description]
            if data['columns'] != actual: raise ValueError('Backup columns mismatch')
            placeholders = ','.join('?' for _ in actual)
            for row in data['rows']: db.execute(f'INSERT INTO {table} VALUES({placeholders})', row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    counts = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in manifest['tables']}
    for t, count in counts.items():
        if t != 'bf_schema' and count != len(manifest['tables'][t]['rows']): raise ValueError('Restored row count mismatch')
    # Compare complete persisted values, preserving old receipt/snapshot hashes.
    for t, data in manifest['tables'].items():
        if t == 'bf_schema': continue
        actual = sorted(json.dumps(list(r),sort_keys=True) for r in db.execute(f'SELECT * FROM {t}').fetchall())
        expected = sorted(json.dumps(r,sort_keys=True) for r in data['rows'])
        if actual != expected: raise ValueError('Restored record content mismatch')
    return {'restored_at': now(), 'duration_ms': round((time.perf_counter()-started)*1000),
            'backup_age_seconds': round((datetime.now(timezone.utc)-datetime.fromisoformat(manifest['created_at'])).total_seconds(),3),
            'counts': counts, 'source_hashes_verified': len(sources), 'all_record_values_match': True,
            'sessions_restored': 0, 'independent_disaster_recovery': False}


def main():
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['migrate','bootstrap-postgres','create-user','backup','restore','migrate-sqlite'])
    parser.add_argument('--path'); parser.add_argument('--source-directory'); parser.add_argument('--sqlite-source')
    parser.add_argument('--username'); parser.add_argument('--org'); parser.add_argument('--site')
    parser.add_argument('--roles', nargs='+')
    args = parser.parse_args()
    db_path = Path(os.getenv('DATABASE_PATH') or ROOT / 'work/pilot.sqlite3')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with repo.connect(db_path, migration=args.command in ('migrate','bootstrap-postgres')) as db:
        if args.command == 'bootstrap-postgres':
            if not db.postgres: raise ValueError('PostgreSQL required')
            from psycopg import sql
            secret=os.getenv('PILOT_RUNTIME_PASSWORD','')
            if len(secret)<32: raise ValueError('Private runtime password required')
            role='batchfence_runtime'
            if not db.execute('SELECT 1 FROM pg_roles WHERE rolname=?',(role,)).fetchone():
                db.raw.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(secret)))
            db.raw.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
            for table in repo.TABLES:
                grants='SELECT' if table=='bf_schema' else 'SELECT,INSERT' if table=='bf_audit' else 'SELECT,INSERT,UPDATE,DELETE'
                db.raw.execute(sql.SQL('GRANT '+grants+' ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
            print(json.dumps({'schema':repo.SCHEMA,'runtime_role':'least-privilege grants installed','credentials':'not displayed'}))
        elif args.command == 'migrate': print(json.dumps({'schema':repo.SCHEMA,'migrated':True}))
        elif args.command == 'create-user':
            from backend.identity import create_user
            password = getpass.getpass('New password (14+ characters; never echoed): ')
            if password != getpass.getpass('Repeat password: '): raise ValueError('Passwords differ')
            db.execute('BEGIN IMMEDIATE')
            user = create_user(db,args.username,password,args.org,args.site,args.roles)
            print(json.dumps({'created_user_id':user,'password':'not displayed'}))
        elif args.command == 'backup': print(json.dumps(backup(db,args.path)))
        elif args.command == 'restore': print(json.dumps(restore(db,args.path,args.source_directory)))
        else:
            if not db.postgres: raise ValueError('SQLite migration target must be PostgreSQL')
            old = Path(args.sqlite_source)
            if not old.is_file(): raise ValueError('Existing SQLite source required')
            backup_path = old.with_name(old.name+'.before-postgres-backup')
            if backup_path.exists(): raise ValueError('Previous migration backup exists; choose/review explicitly')
            with sqlite3.connect(old) as source, sqlite3.connect(backup_path) as target:
                source.backup(target)
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT count(*) FROM cases').fetchone()[0] or db.execute('SELECT count(*) FROM receipts').fetchone()[0]:
                    raise ValueError('Migration target cases/receipts must be empty')
                counts={}
                for table, n in [('cases',3),('receipts',4)]:
                    rows=source.execute(f'SELECT * FROM {table}').fetchall()
                    for row in rows: db.execute(f"INSERT INTO {table} VALUES({','.join('?' for _ in range(n))})",row)
                    counts[table]=len(rows)
                db.commit()
            print(json.dumps({'migrated':counts,'authority':'Legacy owners and anonymous receipts unchanged; no named approval granted','backup_created':True}))


if __name__ == '__main__': main()
