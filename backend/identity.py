"""Local pilot identities: Argon2 passwords, revocable server sessions and scoped roles."""
import hashlib
import json
import os
import re
import secrets
import time
import uuid
from contextvars import ContextVar
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import HTTPException
from . import repository as repo

ROLES = {'reporter', 'quality_reviewer', 'release_approver', 'auditor', 'administrator'}
principal = ContextVar('batchfence_principal', default=None)
passwords = PasswordHasher()


def pilot(): return os.getenv('DEPLOYMENT_PROFILE') == 'pilot'


def deny(message='Named authenticated access is required', status=403):
    raise HTTPException(status, {'code': 'ACCESS_DENIED', 'message': message})


def scope(org, site):
    if not all(isinstance(x, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', x) for x in (org, site)):
        deny('Invalid organization/site selector')
    return f'pilot:{org}:{site}'


def signer():
    key = os.getenv('PILOT_SESSION_SECRET', '')
    if len(key) < 32:
        deny('Pilot session secret is not configured', 503)
    return URLSafeTimedSerializer(key, salt='batchfence-pilot-session-v1')


def public_actor(p):
    return {k: p[k] for k in ('user_id', 'username', 'org', 'site', 'roles', 'identity_mode')}


def current_actor():
    p = principal.get()
    return public_actor(p) if p else {'user_id': None, 'identity_mode': 'anonymous session; not independent identity'}


def create_user(db, username, password, org, site, roles):
    scope(org, site)
    if not re.fullmatch(r'[A-Za-z0-9._@-]{3,120}', username) or not 14 <= len(password) <= 256:
        raise ValueError('Username must be 3–120 safe characters; password must be 14–256 characters')
    if not roles or not set(roles) <= ROLES:
        raise ValueError('Choose explicit supported roles')
    user_id = uuid.uuid4().hex
    db.execute('INSERT INTO bf_users VALUES(?,?,?,1)', (user_id, username.lower(), passwords.hash(password)))
    db.execute('INSERT INTO bf_members VALUES(?,?,?,?,1,1)', (user_id, org, site, json.dumps(sorted(set(roles)))))
    repo.audit(db, scope(org, site), current_actor(), 'identity.created', {}, {'user_id': user_id, 'roles': sorted(roles)})
    return user_id


def login(db, username, password, org, site):
    scope(org, site)
    row = db.execute('SELECT id,password_hash,active FROM bf_users WHERE username=?', (username.lower(),)).fetchone()
    try:
        # Same expensive verification path for unknown users; no account enumeration.
        encoded = row[1] if row else _dummy_hash()
        valid = passwords.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not row or not row[2]:
        deny('Sign-in failed', 401)
    member = db.execute('SELECT roles,revision,active FROM bf_members WHERE user_id=? AND org=? AND site=?', (row[0], org, site)).fetchone()
    if not member or not member[2]:
        deny('Sign-in failed', 401)
    token = signer().dumps(secrets.token_urlsafe(32))
    hashed = hashlib.sha256(token.encode()).hexdigest()
    db.execute('INSERT INTO bf_sessions VALUES(?,?,?,?,?,?)', (hashed, row[0], org, site, int(time.time()) + 28800, member[1]))
    repo.audit(db, scope(org, site), {'user_id': row[0], 'org': org, 'site': site}, 'identity.login', {}, {'session_created': True})
    return token


_dummy = None
def _dummy_hash():
    global _dummy
    if _dummy is None: _dummy = passwords.hash(secrets.token_urlsafe(24))
    return _dummy


def authenticate(db, token):
    if not token or len(token) > 300: deny(status=401)
    try:
        signer().loads(token, max_age=28800)
    except (BadSignature, SignatureExpired):
        deny(status=401)
    hashed = hashlib.sha256(token.encode()).hexdigest()
    row = db.execute('SELECT user_id,org,site,expires,membership_revision FROM bf_sessions WHERE token_hash=?', (hashed,)).fetchone()
    if not row or row[3] <= int(time.time()): deny('Session expired or revoked', 401)
    user_id, org, site, _, revision = row
    user = db.execute('SELECT username,active FROM bf_users WHERE id=?', (user_id,)).fetchone()
    member = db.execute('SELECT roles,revision,active FROM bf_members WHERE user_id=? AND org=? AND site=?', (user_id, org, site)).fetchone()
    if not user or not user[1] or not member or not member[2] or member[1] != revision:
        deny('Membership changed or revoked; sign in again', 401)
    return {'user_id': user_id, 'username': user[0], 'org': org, 'site': site, 'roles': json.loads(member[0]),
            'identity_mode': 'named local pilot user', 'token_hash': hashed, 'membership_revision': revision}


def recheck(db, required=None):
    """Runs inside committing transaction, so role changes serialize with decisions."""
    p = principal.get()
    if not pilot(): return
    if not p: deny(status=401)
    row = db.execute('SELECT roles,revision,active FROM bf_members WHERE user_id=? AND org=? AND site=?', (p['user_id'], p['org'], p['site'])).fetchone()
    user = db.execute('SELECT active FROM bf_users WHERE id=?', (p['user_id'],)).fetchone()
    session = db.execute('SELECT expires FROM bf_sessions WHERE token_hash=?', (p['token_hash'],)).fetchone()
    if not row or not row[2] or row[1] != p['membership_revision'] or not user or not user[0] or not session or session[0] <= int(time.time()):
        deny('Access was revoked before commit')
    required = required or p.get('required_role')
    if required and required not in json.loads(row[0]): deny('This action requires role: ' + required)


def approval_identity():
    p = principal.get()
    return public_actor(p) | {'membership_revision': p.get('membership_revision',0)} if p else None


def approval_still_authorized(db, approval, required):
    if not pilot(): return True
    if not isinstance(approval, dict) or not approval.get('user_id'): return False
    row = db.execute('SELECT roles,revision,active FROM bf_members WHERE user_id=? AND org=? AND site=?',
                     (approval['user_id'], approval['org'], approval['site'])).fetchone()
    user = db.execute('SELECT active FROM bf_users WHERE id=?', (approval['user_id'],)).fetchone()
    return bool(row and row[2] and user and user[0] and row[1] == approval.get('membership_revision') and required in json.loads(row[0]))


def route_role(path, method):
    if method == 'GET': return None
    end = path.rsplit('/', 1)[-1]
    if end in {'release-approve','recovery-execute','connector-dispatch','connector-enqueue'}:return 'release_approver'
    if end in {'reviews', 'approve', 'apply', 'reply-review', 'receiving-review','intake-review','ocr-review','baseline-review','procedure-review','knowledge-check','policy-review','recovery-evidence','recovery-prepare','investigation-review','plan-review','implementation-review','monitoring-start','outcome-review','recurrence-review','reopen-review'}: return 'quality_reviewer'
    if path.startswith('/api/auth/'): return None
    if end == 'challenges': return None
    return 'reporter'


def authorize_route(p, path, method):
    role = route_role(path, method)
    if role and role not in p['roles']: deny('This action requires role: ' + role)


def change_membership(db, user_id, org, site, roles, active):
    recheck(db, 'administrator')
    p = principal.get()
    if (org, site) != (p['org'], p['site']): deny('Membership outside your organization/site')
    if not set(roles) <= ROLES: deny('Unsupported roles')
    before = db.execute('SELECT roles,revision,active FROM bf_members WHERE user_id=? AND org=? AND site=?', (user_id, org, site)).fetchone()
    if not before: deny('Membership unavailable', 404)
    db.execute('UPDATE bf_members SET roles=?,revision=revision+1,active=? WHERE user_id=? AND org=? AND site=?',
               (json.dumps(sorted(set(roles))), int(active), user_id, org, site))
    db.execute('DELETE FROM bf_sessions WHERE user_id=? AND org=? AND site=?', (user_id, org, site))
    repo.audit(db, scope(org, site), public_actor(p), 'identity.membership_changed', list(before), {'user_id': user_id, 'roles': roles, 'active': active})
