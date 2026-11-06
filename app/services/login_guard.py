"""Persistent login throttling. Shared SQLite volume required across application workers."""
import hashlib
import os
import sqlite3
import time
from pathlib import Path
from fastapi import HTTPException

WINDOW=900
LIMIT=5

def _db(request):
    base=Path(str(request.app.state.data_dir))
    base.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(base/'login_guard.sqlite3'),timeout=15,isolation_level=None)
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS login_failures (key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, first_at INTEGER NOT NULL, locked_until INTEGER NOT NULL DEFAULT 0)')
    return db

def _keys(request, identity, stage):
    # Do not trust arbitrary X-Forwarded-For; only the proxy-derived client host.
    ip=str(request.client.host if request.client else 'unknown')
    name=str(identity or '').strip().casefold()
    values=['ip:'+ip, 'account:'+name] if stage=='password' else ['pin-ip:'+ip, 'pin-account:'+name]
    return [hashlib.sha256((stage+'|'+v).encode()).hexdigest() for v in values]

def check(request,identity,stage='password'):
    now=int(time.time())
    with _db(request) as db:
        for key in _keys(request,identity,stage):
            row=db.execute('SELECT locked_until FROM login_failures WHERE key=?',(key,)).fetchone()
            if row and row[0]>now:
                raise HTTPException(status_code=429,detail='Too many login attempts. Try again in 15 minutes or contact the office.',headers={'Retry-After':str(row[0]-now)})

def failure(request,identity,stage='password'):
    now=int(time.time())
    with _db(request) as db:
        db.execute('BEGIN IMMEDIATE')
        for key in _keys(request,identity,stage):
            row=db.execute('SELECT attempts,first_at FROM login_failures WHERE key=?',(key,)).fetchone()
            count=(row[0]+1 if row and now-row[1]<WINDOW else 1)
            first=(row[1] if row and now-row[1]<WINDOW else now)
            db.execute('INSERT INTO login_failures(key,attempts,first_at,locked_until) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET attempts=excluded.attempts,first_at=excluded.first_at,locked_until=excluded.locked_until',(key,count,first,now+WINDOW if count>=LIMIT else 0))

def success(request,identity,stage='password'):
    # Clear account-specific failures only; keep IP failures to discourage account spraying.
    keys=_keys(request,identity,stage)
    with _db(request) as db:
        db.execute('DELETE FROM login_failures WHERE key=?',(keys[1],))

def unlock(request,identity):
    with _db(request) as db:
        for stage in ('password','pin'):
            db.execute('DELETE FROM login_failures WHERE key=?',(_keys(request,identity,stage)[1],))

def password_policy(password):
    if len(password)<12 or len(password)>128 or not password.strip():
        raise HTTPException(status_code=400,detail='New passwords must contain 12–128 characters.')
