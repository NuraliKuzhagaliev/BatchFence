"""Migration 002: additive foundations; existing case/receipt bytes remain unchanged.

Freeze this schema once released. Subsequent changes require a new migration version.
"""
TABLES = {
    'cases': 'id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL',
    'receipts': 'owner TEXT NOT NULL, key TEXT NOT NULL, request_digest TEXT NOT NULL, receipt TEXT NOT NULL, PRIMARY KEY(owner,key)',
    'bf_records': 'owner TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(owner,kind,id)',
    'bf_users': 'id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL',
    'bf_members': 'user_id TEXT NOT NULL, org TEXT NOT NULL, site TEXT NOT NULL, roles TEXT NOT NULL, revision INTEGER NOT NULL, active INTEGER NOT NULL, PRIMARY KEY(user_id,org,site)',
    'bf_sessions': 'token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, org TEXT NOT NULL, site TEXT NOT NULL, expires INTEGER NOT NULL, membership_revision INTEGER NOT NULL',
    'bf_audit': 'id TEXT PRIMARY KEY, owner TEXT NOT NULL, at TEXT NOT NULL, event TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL',
    'bf_sources': 'owner TEXT NOT NULL, hash TEXT NOT NULL, size INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner,hash)',
    'bf_schema': 'version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL',
}
