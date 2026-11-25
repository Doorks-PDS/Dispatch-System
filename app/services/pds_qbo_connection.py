"""Opt-in QuickBooks Online OAuth and read-only company verification for PDS.

No invoice/PO/payment writes. The offline handoff and provider verification stay
separate until an office administrator explicitly approves an accounting sync.
Secrets never leave the server, and provider tokens are encrypted at rest on a
configured durable data volume. QuickBooks Desktop is not an OAuth target.
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request as HTTPRequest, urlopen

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb

AUTHORIZE_URL = 'https://appcenter.intuit.com/connect/oauth2'
TOKEN_URL = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
ACCOUNTING_SCOPE = 'com.intuit.quickbooks.accounting'
SESSION_KEY = 'pds_qbo_oauth_pending'
CONNECTED_FILE = 'pds_qbo_connection.encrypted'
VALID_REALM = re.compile(r'\d{1,32}\Z')
DEFAULT_SESSION_SECRET = 'doorks-local-dev-secret-jason-2026'
MAX_RESPONSE = 1024 * 1024


def _environment():
    env = os.getenv('PDS_QBO_ENVIRONMENT', 'sandbox').strip().lower()
    if env not in ('sandbox', 'production'):
        raise HTTPException(503, 'QuickBooks environment must be sandbox or production')
    return env


def _redirect_uri():
    url = os.getenv('PDS_QBO_REDIRECT_URI', '').strip()
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.netloc or parts.username or parts.password
            or parts.fragment or parts.query or not parts.path.endswith('/pds-quickbooks/oauth/callback')):
        raise HTTPException(503, 'Set an exact HTTPS PDS_QBO_REDIRECT_URI ending in /pds-quickbooks/oauth/callback')
    return url


def _durable_path(request):
    root = Path(request.app.state.data_dir).resolve()
    # Prevent accidental storage of refresh tokens in Render's ephemeral source
    # tree. A configured Render disk or a durable external directory is required.
    if (os.getenv('RENDER') or _environment() == 'production'):
        source_root = Path(getattr(request.app.state, 'project_root', '') or '.').resolve()
        if root == source_root:
            raise HTTPException(503, 'QuickBooks credentials cannot be stored in the application source directory')
        if source_root in root.parents:
            # Render allows persistent disks mounted inside /opt/render/project/src,
            # including PDS's existing /opt/render/project/src/data mount. Requiring
            # data to live *outside* the source tree incorrectly rejects that disk.
            # Confirm a real filesystem mount lies between source_root and data_dir;
            # an ordinary source subdirectory is still ephemeral and is rejected.
            directory = root
            on_persistent_mount = False
            while directory != source_root and directory != directory.parent:
                if os.path.ismount(directory):
                    on_persistent_mount = True
                    break
                directory = directory.parent
            if not on_persistent_mount:
                raise HTTPException(503, 'QuickBooks credentials require a mounted persistent data volume')
    return root / CONNECTED_FILE


def _fernet():
    raw = os.getenv('PDS_QBO_TOKEN_ENCRYPTION_KEY', '').strip().encode('ascii', errors='ignore')
    try:
        from cryptography.fernet import Fernet
        return Fernet(raw)
    except (ImportError, ValueError) as exc:
        raise HTTPException(503, 'QuickBooks token encryption key or cryptography dependency is missing') from exc


def configuration(request):
    qb._admin(request)
    edition = qb._mode(request)
    env = _environment()
    flags = {
        'online_edition_selected': edition == 'online',
        'client_id_present': bool(os.getenv('PDS_QBO_CLIENT_ID', '').strip()),
        'client_secret_present': bool(os.getenv('PDS_QBO_CLIENT_SECRET', '').strip()),
        'redirect_uri_valid': False,
        'token_encryption_ready': False,
        'session_security_ready': False,
        'durable_storage_ready': False,
    }
    try:
        _redirect_uri()
        flags['redirect_uri_valid'] = True
    except HTTPException:
        pass
    try:
        _fernet()
        flags['token_encryption_ready'] = True
    except HTTPException:
        pass
    secret = os.getenv('DOORKS_SESSION_SECRET', '')
    flags['session_security_ready'] = len(secret) >= 32 and secret != DEFAULT_SESSION_SECRET
    try:
        _durable_path(request)
        flags['durable_storage_ready'] = True
    except HTTPException:
        pass
    connected = _read_connection(request, allow_missing_key=True)
    # A saved token is not evidence of provider connectivity or a recent check.
    return {'edition': edition, 'environment': env,
            'configured': all(flags.values()), 'checks': flags,
            'authorized': bool(connected),
            'company_id': connected.get('realm_id') if connected else None,
            'company_name': connected.get('company_name') if connected else None,
            'last_read_only_verification': connected.get('checked_at') if connected else None,
            'posting_enabled': False, 'automatic_sync_enabled': False,
            'payment_sync_enabled': False,
            'note': ('Connect QuickBooks Online, verify the exact company, then validate '
                     'customer/vendor/item/tax mappings. No invoices, purchase orders '
                     'or payments are sent by these tools.')}


def _read_connection(request, *, allow_missing_key=False):
    try:
        path = _durable_path(request)
        if not path.exists():
            return None
        payload = json.loads(_fernet().decrypt(path.read_bytes()))
        if (not isinstance(payload, dict) or not VALID_REALM.fullmatch(str(payload.get('realm_id', '')))
                or payload.get('environment') not in ('sandbox', 'production')
                or not payload.get('refresh_token')):
            raise ValueError('Invalid token record')
        return payload
    except HTTPException:
        if allow_missing_key:
            return None
        raise
    except Exception as exc:
        raise HTTPException(503, 'QuickBooks connection storage requires administrator review') from exc


def _write_connection(request, payload):
    path = _durable_path(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    from tempfile import NamedTemporaryFile
    cipher = _fernet().encrypt(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    with NamedTemporaryFile('wb', dir=path.parent, prefix='.pds-qbo-', delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(cipher)
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def authorization_url(request):
    qb._admin(request, mutation=True)
    config = configuration(request)
    if not config['configured']:
        raise HTTPException(409, 'QuickBooks Online setup checks must pass before connecting')
    if config['authorized']:
        raise HTTPException(409, 'Disconnect existing company before authorizing another')
    nonce = secrets.token_urlsafe(32)
    request.session[SESSION_KEY] = {'state': nonce, 'started': int(time.time()),
                                    'user_id': str(request.state.auth_user.get('id') or ''),
                                    'environment': _environment()}
    params = {'client_id': os.environ['PDS_QBO_CLIENT_ID'].strip(),
              'response_type': 'code', 'scope': ACCOUNTING_SCOPE, 'redirect_uri': _redirect_uri(),
              'state': nonce}
    return {'authorization_url': AUTHORIZE_URL + '?' + urlencode(params),
            'environment': _environment(), 'writes_accounting_transactions': False}


def _token_exchange(fields):
    client = os.getenv('PDS_QBO_CLIENT_ID', '').strip()
    secret = os.getenv('PDS_QBO_CLIENT_SECRET', '').strip()
    credentials = base64.b64encode((client + ':' + secret).encode()).decode()
    req = HTTPRequest(TOKEN_URL, data=urlencode(fields).encode(), method='POST', headers={
        'Authorization': 'Basic ' + credentials,
        'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded',
    })
    try:
        with urlopen(req, timeout=12) as res:
            raw = res.read(128 * 1024 + 1)
        if len(raw) > 128 * 1024:
            raise ValueError('Oversized provider response')
        data = json.loads(raw)
    except (HTTPError, URLError, ValueError, OSError) as exc:
        raise HTTPException(502, 'Intuit token exchange failed; review QuickBooks connection settings') from exc
    if (not isinstance(data, dict) or not data.get('access_token') or not data.get('refresh_token')
            or not isinstance(data.get('expires_in'), (int, float))):
        raise HTTPException(502, 'Intuit returned an incomplete authorization response')
    return data


def finish_authorization(request, *, code, state, realm_id):
    qb._admin(request, mutation=True)
    pending = request.session.pop(SESSION_KEY, None)
    if (not isinstance(pending, dict)
            or not hmac.compare_digest(str(pending.get('state') or ''), str(state or ''))
            or not 0 <= time.time() - int(pending.get('started') or 0) <= 600
            or pending.get('user_id') != str(request.state.auth_user.get('id') or '')
            or pending.get('environment') != _environment()
            or not VALID_REALM.fullmatch(str(realm_id or ''))
            or not 5 <= len(str(code or '')) <= 4096):
        raise HTTPException(403, 'Invalid or expired Intuit authorization; start again')
    path = _durable_path(request)
    with qb._lock(path):
        if _read_connection(request):
            raise HTTPException(409, 'QuickBooks company already authorized; disconnect first')
        data = _token_exchange({'grant_type': 'authorization_code', 'code': code,
                                'redirect_uri': _redirect_uri()})
        _write_connection(request, {'environment': _environment(), 'realm_id': str(realm_id),
                                    'access_token': data['access_token'], 'refresh_token': data['refresh_token'],
                                    'expires_at': int(time.time()) + int(data['expires_in']),
                                    'connected_at': int(time.time()), 'checked_at': None,
                                    'company_name': None})
    return {'authorized': True, 'company_id': str(realm_id),
            'next_step': 'Run read-only company verification in QuickBooks Hub'}


def _access_token(request):
    path = _durable_path(request)
    with qb._lock(path):
        saved = _read_connection(request)
        if not saved:
            raise HTTPException(409, 'QuickBooks Online company is not authorized')
        if saved.get('environment') != _environment():
            raise HTTPException(409, 'QuickBooks environment changed; reconnect explicitly')
        if int(saved.get('expires_at') or 0) - int(time.time()) > 90:
            return saved['access_token'], saved['realm_id']
        data = _token_exchange({'grant_type': 'refresh_token', 'refresh_token': saved['refresh_token']})
        saved.update(access_token=data['access_token'], refresh_token=data['refresh_token'],
                     expires_at=int(time.time()) + int(data['expires_in']))
        _write_connection(request, saved)
        return saved['access_token'], saved['realm_id']


def verify_company(request):
    qb._admin(request)
    if qb._mode(request) != 'online':
        raise HTTPException(409, 'Select QuickBooks Online before verification')
    token, realm = _access_token(request)
    base = ('https://sandbox-quickbooks.api.intuit.com' if _environment() == 'sandbox'
            else 'https://quickbooks.api.intuit.com')
    url = f'{base}/v3/company/{realm}/companyinfo/{realm}'
    req = HTTPRequest(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=12) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError('Oversized provider response')
        parsed = json.loads(raw)
        company = parsed['CompanyInfo']
        if not isinstance(company, dict) or str(company.get('Id') or '') != realm:
            raise ValueError('Realm mismatch')
    except (HTTPError, URLError, ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(502, 'QuickBooks company check failed; no accounting records were changed') from exc
    name = str(company.get('CompanyName') or '')[:160]
    path = _durable_path(request)
    with qb._lock(path):
        saved = _read_connection(request)
        if not saved or saved['realm_id'] != realm:
            raise HTTPException(409, 'QuickBooks authorization changed during verification')
        saved.update(company_name=name, checked_at=int(time.time()))
        _write_connection(request, saved)
    return {'company_id': realm, 'company_name': name,
            'verified_read_only': True, 'posting_enabled': False,
            'next_step': 'Review customer, vendor, item, tax and document-number mappings'}


def disconnect_local(request):
    qb._admin(request, mutation=True)
    path = _durable_path(request)
    with qb._lock(path):
        existed = path.exists()
        path.unlink(missing_ok=True)
    request.session.pop(SESSION_KEY, None)
    return {'local_credentials_deleted': existed, 'intuit_access_revocation_performed': False,
            'message': 'Local connection disconnected; also revoke app access in Intuit if desired'}
