"""Persisted single-attempt jobs. Interrupted calls are never automatically retried."""
import os
import time
from . import repository as repo, identity
from .domain import DomainError
from .fixtures import now


def recover_expired(db, owner):
    rows = db.execute("SELECT id,revision,data FROM bf_records WHERE owner=? AND kind='job'", (owner,)).fetchall()
    import json
    for key, rev, encoded in rows:
        job = json.loads(encoded)
        if job['status'] == 'running' and job['lease_until'] < time.time():
            job.update(status='interrupted', finished_at=now(), error='Worker ended or timed out; charge status may be unknown. An explicit new request is required. No automatic retry.')
            repo.put_record(db, owner, 'job', key, job, rev)


def start(db, owner, key, kind, inputs, mode,lease_seconds=120):
    recover_expired(db, owner)
    import json
    jobs = [json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='job'", (owner,)).fetchall()]
    actor = identity.current_actor()
    if any(j['status']=='running' for j in jobs): raise DomainError('Another organization/session job is running')
    if len(jobs) >= 60: raise DomainError('Workspace job history limit reached')
    if mode == 'live':
        all_jobs=[json.loads(r[0]) for r in db.execute("SELECT data FROM bf_records WHERE kind='job'").fetchall()]
        if sum(j['mode']=='live' for j in all_jobs)>=int(os.getenv('MAX_TOTAL_LIVE_RUNS') or '100'):
            raise DomainError('Owner-controlled global live-job budget reached')
        org_count = sum(j['mode']=='live' for j in jobs)
        user_count = sum(j['mode']=='live' and j['actor'].get('user_id')==actor.get('user_id') for j in jobs)
        if org_count >= int(os.getenv('MAX_ORG_LIVE_JOBS') or '20') or user_count >= int(os.getenv('MAX_USER_LIVE_JOBS') or '8'):
            raise DomainError('Persisted live job budget reached; failed/cancelled attempts count')
    if not 1<=lease_seconds<=600:raise DomainError('Job lease must stay within ten minutes')
    job={'id':key,'kind':kind,'inputs':inputs,'mode':mode,'actor':actor,'status':'running',
         'started_at':now(),'lease_until':time.time()+lease_seconds,'attempts':1,'automatic_retry':False}
    repo.put_record(db,owner,'job',key,job,0)
    return job


def finish(db,owner,key,status,result_hash):
    rev,job=repo.get_record(db,owner,'job',key)
    if not job: raise DomainError('Job unavailable')
    if job['status'] != 'running': return False
    if job['lease_until'] < time.time():
        recover_expired(db,owner)
        return False
    job.update(status=status,finished_at=now(),result_hash=result_hash)
    repo.put_record(db,owner,'job',key,job,rev)
    return True


def cancel(db,owner,key):
    rev,job=repo.get_record(db,owner,'job',key)
    if not job: raise DomainError('Job unavailable')
    if job['status']=='running':
        before=dict(job)
        job.update(status='cancelled',finished_at=now(),error='Result acceptance cancelled. A dispatched provider request may still finish and consume quota; no automatic retry.')
        repo.put_record(db,owner,'job',key,job,rev)
        repo.audit(db,owner,identity.current_actor(),'job.cancelled',before,job)
    return job
