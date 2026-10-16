import hashlib
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, ConfigDict, Field
from . import identity, repository

router = APIRouter()


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=256)
    org: str = Field(max_length=80)
    site: str = Field(max_length=80)


class Membership(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user_id: str = Field(max_length=80)
    roles: list[str] = Field(max_length=5)
    active: bool


class SimulatedRole(BaseModel):
    model_config=ConfigDict(extra='forbid')
    role: str = Field(pattern='^(preparer|approver)$')
    acknowledge_simulation:bool


@router.post('/api/auth/simulate')
def simulate_role(data:SimulatedRole,request:Request):
    from .app import connect
    if identity.pilot() or not data.acknowledge_simulation:identity.deny('Simulation is available only outside the named pilot profile')
    roles=['reporter','quality_reviewer'] if data.role=='preparer' else ['release_approver']
    actor={'user_id':'sim-'+data.role+'-'+request.state.owner[:12],'username':'Simulated '+data.role,'org':'session','site':'training',
           'roles':roles,'identity_mode':'simulated demonstration role'}
    with repository.write(connect) as db:
        repository.put_record(db,request.state.owner,'simulated-identity','current',actor)
        repository.audit(db,request.state.owner,actor,'simulation.role_selected',{},actor)
    return actor


@router.post('/api/auth/login')
def login(data: Login, request: Request):
    from .app import connect, ORIGIN
    if not identity.pilot(): identity.deny('Named sign-in is available in the private pilot profile', 404)
    with repository.write(connect) as db:
        token = identity.login(db, data.username, data.password, data.org, data.site)
        actor = identity.authenticate(db, token)
    response = JSONResponse(identity.public_actor(actor))
    response.set_cookie('bf_pilot', token, httponly=True, secure=ORIGIN.startswith('https://'), samesite='strict', max_age=28800)
    if request.headers.get('x-bf-client') == 'desktop': response.headers['x-bf-session'] = token
    return response


@router.get('/api/auth/me')
def me():
    return {'profile': 'pilot' if identity.pilot() else 'demo', 'actor': identity.current_actor(),
            'roles_available': sorted(identity.ROLES) if not identity.pilot() else []}


@router.post('/api/auth/logout')
def logout(request: Request):
    from .app import connect
    p = identity.principal.get()
    if p:
        with repository.write(connect) as db:
            db.execute('DELETE FROM bf_sessions WHERE token_hash=?', (p['token_hash'],))
    response = JSONResponse({'signed_out': True})
    response.delete_cookie('bf_pilot')
    response.headers['x-bf-session'] = ''
    return response


@router.post('/api/auth/membership')
def membership(data: Membership):
    from .app import connect
    if not identity.pilot(): identity.deny()
    p = identity.principal.get()
    with repository.write(connect) as db:
        identity.change_membership(db, data.user_id, p['org'], p['site'], data.roles, data.active)
    return {'updated': True, 'sessions_revoked': True}


@router.get('/api/sources/{sha}')
def source(sha: str, request: Request):
    from .app import connect
    with connect() as db:
        row = db.execute('SELECT size FROM bf_sources WHERE owner=? AND hash=?', (request.state.owner, sha)).fetchone()
    if not row: raise HTTPException(404, 'Source unavailable')
    path = repository.source_path(request.state.owner, sha)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise HTTPException(409, 'Source integrity check failed')
    return FileResponse(path, media_type='application/octet-stream', filename=sha + '.bin')


@router.get('/api/audit')
def audit(request: Request):
    from .app import connect
    import json
    with connect() as db:
        rows = db.execute('SELECT event,previous_hash,event_hash FROM bf_audit WHERE owner=? ORDER BY at,id', (request.state.owner,)).fetchall()
    return {'events': [{'event': json.loads(r[0]), 'previous_hash': r[1], 'event_hash': r[2]} for r in rows],
            'boundary': 'Append-only application ledger; database administrator can rewrite storage. Not an electronic signature.'}


@router.get('/api/jobs')
def jobs(request: Request):
    from .app import connect
    from .jobs import recover_expired
    import json
    with repository.write(connect) as db:
        identity.recheck(db)
        recover_expired(db,request.state.owner)
        rows=db.execute("SELECT data FROM bf_records WHERE owner=? AND kind='job' ORDER BY id",(request.state.owner,)).fetchall()
    return [json.loads(row[0]) for row in rows]


@router.post('/api/jobs/{key}/cancel')
def cancel_job(key: str,request: Request):
    from .app import connect
    from .jobs import cancel
    with repository.write(connect) as db:
        identity.recheck(db)
        return cancel(db,request.state.owner,key)
