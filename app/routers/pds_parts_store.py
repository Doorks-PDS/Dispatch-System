"""PDS public parts storefront, reading the EXISTING PDS parts catalog.

No PDS master data is modified. Orders are a separate durable ledger; Stripe is
opt-in and server-side only. No assumption that local warehouse stock is held.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/pds-parts", tags=["PDS Parts Store"])

CATEGORIES = (
    "Automatic Doors", "Exit Devices", "Door Closers", "Hinges & Pivots",
    "Locks & Latches", "Storefront & Glass", "Accessories & Hardware",
)
IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)$")
STATES = {"requested", "needs_quote", "contacted", "cancelled", "paid", "supplier_ordered", "shipped", "completed", "needs_review"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _enabled(name):
    return os.getenv(name, "").strip().lower() == "true"


def _category(row):
    words = " ".join(str(row.get(k) or "") for k in ("part_number", "manufacturer", "description")).lower()
    if any(x in words for x in ("exit device", "panic", "crash bar", "push bar", "pushbar", "von duprin", "rim device")):
        return "Exit Devices"
    if any(x in words for x in ("closer", "lcn ", "surface closer")):
        return "Door Closers"
    if any(x in words for x in ("automatic", "operator", "presence sensor", "activation sensor", "motion sensor", "handicap opener", "actuator", "controller", "control board", "motor", "gearbox", "drive assembly")):
        return "Automatic Doors"
    if any(x in words for x in ("hinge", "pivot", "continuous hinge", "offset pivot")):
        return "Hinges & Pivots"
    if any(x in words for x in ("lock", "latch", "strike", "cylinder", "deadbolt", "electrified trim")):
        return "Locks & Latches"
    if any(x in words for x in ("storefront", "glass", "glazing", "threshold", "weatherstrip")):
        return "Storefront & Glass"
    return "Accessories & Hardware"



def _auto_door_part(row):
    """Conservative lockout: all automatic-door parts must be quoted first.

    Even where a legacy item was categorized as a closer/exit device, an
    automatic-door part still cannot reach a Stripe Checkout Session.
    """
    words = " ".join(str(row.get(k) or "") for k in
                     ("description", "part_number", "manufacturer")).casefold()
    if _category(row) == "Automatic Doors":
        return True
    return any(key in words for key in (
        "automatic door", "automatic sliding", "automatic swing",
        "operator", "controller", "control board", "motor", "gearbox",
        "drive assembly", "drive unit", "activation sensor", "presence sensor",
        "motion sensor", "handicap opener", "actuator", "pedestrian sensor",
    ))


def _has_core_charge(row):
    value = str(row.get("core_charge") or '').strip()
    if not value:
        return False
    try:
        amount = Decimal(value)
        return not amount.is_finite() or amount != 0
    except (InvalidOperation, ValueError, TypeError):
        return True  # Ambiguous legacy amounts must not flow to checkout.


def _inquiry_only(row):
    # Specialty/core flags fail closed: no automatic core billing or refunds.
    return (row.get("store_inquiry_only") is True or
            row.get("core_return_required") is True or
            _has_core_charge(row) or _auto_door_part(row))


def _cents(value):
    if value is None or isinstance(value, bool):
        return None
    s = str(value).replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite() or d < Decimal("0.50") or d > Decimal("100000.00"):
        return None
    n = d * 100
    if n != n.to_integral_value():
        return None
    return int(n)


def _raw_items(request):
    from app.routers import data
    path = data._parts_path(request)  # PDS's single authoritative catalog, no copies.
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Parts catalog temporarily unavailable") from exc
    if not isinstance(stored, dict) or not isinstance(stored.get("items"), list):
        raise HTTPException(503, "Parts catalog needs review")
    return [r for r in stored["items"] if isinstance(r, dict) and r.get("item_type", "part") != "service"]


def _public_item(row):
    part_id = str(row.get("id") or "")
    title = str(row.get("description") or row.get("part_number") or "").strip()[:400]
    if not part_id or not title:
        return None
    number = str(row.get("part_number") or "").strip()[:120]
    manufacturer = str(row.get("manufacturer") or "").strip()[:140]
    src = str(row.get("image_url") or "").strip()
    image_url = ""
    if src.startswith("/moses/part-image/pds/") and IMAGE_NAME.fullmatch(src.rsplit("/", 1)[-1]):
        image_url = "/pds-parts/image/" + part_id
    elif src.startswith("https://"):
        p = urlsplit(src)
        if p.hostname and not p.username and not p.password:
            image_url = src
    return {"id": part_id, "part_number": number, "description": title,
            "manufacturer": manufacturer, "category": _category(row),
            "price_cents": _cents(row.get("price")), "image_url": image_url,
            "inquiry_only": _inquiry_only(row),
            "core_review": (bool(row.get("core_return_required")) or
                            _has_core_charge(row) or _auto_door_part(row))}


def _catalog(request):
    return [p for p in (_public_item(r) for r in _raw_items(request)) if p]


def _admin(request):
    if not getattr(request.state, "auth_user", None):
        raise HTTPException(401, "Log in to view PDS orders")
    if (getattr(request.state, "auth_role", None) != "office_admin"
            or request.session.get("active_platform") != "pds"):
        raise HTTPException(403, "PDS office admin required")


def _sdc_sales_admin(request):
    # Narrow, explicit SDC report bridge. PDS catalog and accounting remain PDS-owned.
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if (getattr(request.state, 'auth_role', None) != 'office_admin'
            or request.session.get('active_platform') != 'sdc'):
        raise HTTPException(403, 'SDC office admin required')


def _payment_settings():
    if not _enabled("PDS_PARTS_STORE_PAYMENTS_ENABLED"):
        raise HTTPException(503, "Card checkout is not enabled yet. Contact PDS for a quote.")
    # A dedicated parts-store key takes priority. Reuse the existing sandbox
    # key only for test sessions, never silently charge through a live key.
    dedicated = os.getenv("PDS_PARTS_STORE_STRIPE_SECRET_KEY", "").strip()
    key = dedicated or os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key.startswith(("sk_test_", "sk_live_")):
        raise HTTPException(503, "Stripe key is not configured")
    if key.startswith("sk_live_") and (not dedicated or not _enabled("PDS_PARTS_STORE_LIVE_ENABLED")):
        raise HTTPException(503, "Live checkout requires a dedicated key and explicit launch approval")
    shipping_raw = os.getenv("PDS_PARTS_STORE_SHIPPING_USD", "").strip()
    shipping = _cents(shipping_raw)
    if shipping_raw in ("0", "0.00", "0.0"):
        shipping = 0
    if shipping is None or shipping > 50000:
        raise HTTPException(503, "Configure the verified flat shipping fee before checkout")
    origin = os.getenv("PDS_PARTS_STORE_PUBLIC_ORIGIN", "").strip().rstrip("/")
    url = urlsplit(origin)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.path or url.query or url.fragment):
        raise HTTPException(503, "Configure the public HTTPS storefront origin")
    if not os.getenv("PDS_PARTS_STORE_STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"):
        raise HTTPException(503, "Dedicated Stripe webhook secret required")
    return key, shipping, origin


def _orders_path(request):
    # Existing Render persistent volume; never write customer data in static/ or Git.
    root = Path(request.app.state.data_dir) / "pds_parts_store"
    root.mkdir(parents=True, exist_ok=True)
    return root / "orders.json"


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _load(path):
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(items, list):
            return items
    except (OSError, ValueError):
        pass
    raise HTTPException(503, "Parts orders require manual storage review")


def _save(path, items):
    fd, tmp = tempfile.mkstemp(prefix="orders-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@router.get("")
def storefront(request: Request):
    return FileResponse(Path(request.app.state.project_root) / "static" / "pds_parts_store.html",
                        media_type="text/html", headers={"Cache-Control": "no-store"})


def _checkout_mode():
    try:
        key, _, _ = _payment_settings()
        return "test" if key.startswith("sk_test_") else "live"
    except HTTPException:
        return "off"


def _checkout_ready():
    return _checkout_mode() != "off"


@router.get("/api/catalog")
def catalog(request: Request, q: str = "", category: str = "All", limit: int = 10000):
    if len(q) > 120 or category not in ("All", *CATEGORIES):
        raise HTTPException(422, "Invalid search")
    items = _catalog(request)
    if category != "All":
        items = [p for p in items if p["category"] == category]
    words = q.casefold().strip()
    if words:
        items = [p for p in items if words in " ".join((p["description"], p["part_number"], p["manufacturer"], p["category"])).casefold()]
    return {"items": items[:max(1, min(limit, 20000))], "categories": list(CATEGORIES),
            "matching": len(items), "checkout_enabled": _checkout_ready(),
            "shipping_note": "Usually ships in 1–3 business days after order confirmation. Manufacturer and specialty items may take longer. Shipping dates are confirmed by email.",
            "checkout_mode": _checkout_mode(),
            "tax_mode": "sandbox_no_tax" if (_checkout_mode() == "test" and _enabled("PDS_PARTS_STORE_TEST_NO_TAX")) else "automatic"}


@router.get("/image/{part_id}")
def public_part_image(part_id: str, request: Request):
    # Publicly serve ONLY a PDS image referenced by an actual current catalog part.
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,90}", part_id):
        raise HTTPException(404, "Image not found")
    row = next((x for x in _raw_items(request) if str(x.get("id")) == part_id), None)
    if not row:
        raise HTTPException(404, "Image not found")
    path_value = str(row.get("image_url") or "")
    if not path_value.startswith("/moses/part-image/pds/"):
        raise HTTPException(404, "Image not found")
    name = path_value.rsplit("/", 1)[-1]
    if not IMAGE_NAME.fullmatch(name):
        raise HTTPException(404, "Image not found")
    path = Path(request.app.state.data_dir) / "business_workspaces" / "pds" / "part_images" / name
    if not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


class Line(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    qty: int = Field(ge=1, le=20)


class Cart(BaseModel):
    lines: list[Line] = Field(min_length=1, max_length=15)
    token: uuid.UUID
    name: str = Field(default='', max_length=120)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=40)
    postal_code: str = Field(default='', max_length=16)


class OrderRequest(BaseModel):
    lines: list[Line] = Field(min_length=1, max_length=15)
    token: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default='', max_length=40)
    postal_code: str = Field(default='', max_length=16)
    note: str = Field(default='', max_length=800)
    website: str = Field(default='', max_length=200)  # honeypot
    shipping_line1: str = Field(default='', max_length=150)
    shipping_line2: str = Field(default='', max_length=150)
    shipping_city: str = Field(default='', max_length=100)
    shipping_state: str = Field(default='', max_length=40)


def _price_lines(request, entries):
    products = {p['id']: p for p in _catalog(request)}
    if len({line.id for line in entries}) != len(entries):
        raise HTTPException(422, 'Duplicate products in cart')
    lines = []
    for entry in entries:
        p = products.get(entry.id)
        if p is None or p['price_cents'] is None:
            raise HTTPException(409, 'A selected item needs a current price review')
        if p['inquiry_only']:
            raise HTTPException(409, 'This part requires a direct quote and core review. Remove it from the cart.')
        lines.append({**{k: p[k] for k in ('id', 'description', 'part_number', 'manufacturer', 'price_cents')}, 'qty': entry.qty})
    if sum(x['price_cents'] * x['qty'] for x in lines) > 2000000:
        raise HTTPException(422, 'Large orders require a manual quote')
    return lines


@router.post('/api/cart-quote')
def cart_quote(request: Request, payload: Cart):
    """Read-only, authoritative preview. Never trust browser prices or quantities."""
    lines = _price_lines(request, payload.lines)
    subtotal = sum(p['price_cents'] * p['qty'] for p in lines)
    mode = _checkout_mode()
    shipping = None
    if mode != 'off':
        try:
            _, shipping, _ = _payment_settings()
        except HTTPException:
            mode = 'off'
    return {
        'lines': lines,
        'subtotal_cents': subtotal,
        'shipping_cents': shipping,
        'before_tax_cents': subtotal + shipping if shipping is not None else None,
        'tax_note': 'Calculated at secure Stripe checkout' if mode != 'off' else 'Confirmed before payment',
        'checkout_mode': mode,
    }



class PartInquiry(BaseModel):
    part_id: str = Field(min_length=1, max_length=100)
    qty: int = Field(ge=1, le=20)
    token: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default='', max_length=40)
    note: str = Field(default='', max_length=800)
    website: str = Field(default='', max_length=200)


@router.post('/api/part-inquiries', status_code=201)
def part_inquiry(request: Request, payload: PartInquiry):
    """Capture a specialty-part inquiry. Never bill for an unverified core."""
    from datetime import timedelta
    if payload.website:
        return {'ok': True, 'message': 'Inquiry received'}
    email = payload.email.strip().lower()
    name = payload.name.strip()
    if not name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter a name and valid email')
    if any(ord(c) < 32 and c not in '\t\r\n' for c in
           (payload.note + payload.name + payload.phone)):
        raise HTTPException(422, 'Invalid inquiry details')
    row = next((p for p in _catalog(request) if p['id'] == payload.part_id), None)
    if row is None:
        raise HTTPException(404, 'Part not found')
    # Inquiries are also supported for ordinary products where a buyer
    # wants to confirm suitability before paying.
    line = {k: row[k] for k in ('id', 'description', 'part_number',
                                'manufacturer', 'price_cents')}
    line['qty'] = payload.qty
    token = str(payload.token)
    path = _orders_path(request)
    with _locked(path):
        rows = _load(path)
        existing = next((r for r in rows if r.get('token') == token), None)
        if existing:
            if (existing.get('customer_email') != email or
                    existing.get('lines') != [line] or
                    existing.get('kind') != 'part_inquiry'):
                raise HTTPException(409, 'Inquiry reference was already used')
            return {'ok': True, 'reference': existing['id'][:8], 'duplicate': True}
        recent = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        for previous in rows:
            if str(previous.get('customer_email') or '').lower() != email:
                continue
            try:
                when = datetime.fromisoformat(str(previous.get('created_at', '')).replace('Z', '+00:00'))
                if when.tzinfo and when >= cutoff:
                    recent += 1
            except ValueError:
                pass
        if recent >= 5:
            raise HTTPException(429, 'Too many inquiries. Please contact PDS directly.')
        # Private reference for staff; NOT a billed line item or a quoted fee.
        master = next((m for m in _raw_items(request) if str(m.get('id')) == row['id']), {})
        core_estimate_cents = None
        if str(master.get('core_charge') or '').strip():
            try:
                core_amount = Decimal(str(master['core_charge']))
                if (core_amount.is_finite() and core_amount >= 0 and
                        core_amount * 100 == (core_amount * 100).to_integral_value()):
                    core_estimate_cents = int(core_amount * 100) * payload.qty
            except (InvalidOperation, ValueError, TypeError):
                pass
        stamp = _now()
        record = {'id': uuid.uuid4().hex, 'token': token, 'kind': 'part_inquiry',
                  'created_at': stamp, 'updated_at': stamp, 'state': 'needs_quote',
                  'lines': [line], 'subtotal_cents': None, 'shipping_cents': None,
                  'currency': 'usd', 'customer_name': name, 'customer_email': email,
                  'customer_phone': payload.phone.strip(),
                  'customer_note': payload.note.strip(),
                  'core_review_required': row['core_review'],
                  'core_estimate_cents': core_estimate_cents,
                  'core_return_status': 'unconfirmed' if row['core_review'] else 'not_applicable',
                  'customer_price_estimate_cents': (
                      (row['price_cents'] or 0) * payload.qty
                      if row['price_cents'] is not None else None),
                  'paid_at': None, 'test_mode': False}
        rows.append(record)
        _save(path, rows)
    return {'ok': True, 'reference': record['id'][:8],
            'payment_received': False, 'core_review_required': row['core_review']}


@router.get('/api/checkout-status')
def checkout_status(request: Request, session_id: str = Query(min_length=15, max_length=255)):
    """Non-sensitive payment-return status; only signed webhooks mark orders paid."""
    if not re.fullmatch(r'cs_(?:test|live)_[a-zA-Z0-9_]{5,250}', session_id):
        raise HTTPException(404, 'Order not found')
    path = _orders_path(request)
    with _locked(path):
        match = next((r for r in _load(path) if r.get('stripe_session_id') == session_id), None)
    if not match:
        raise HTTPException(404, 'Order not found')
    state = str(match.get('state') or '')
    return {'reference': str(match['id'])[:8],
            'payment_status': 'paid' if match.get('paid_at') else 'pending',
            'order_status': state if state in STATES else 'processing',
            'test_mode': bool(match.get('test_mode'))}


@router.post('/api/order-requests', status_code=201)
def request_order(request: Request, payload: OrderRequest):
    """No charge or supplier order. Request status is never treated as paid."""
    from datetime import timedelta
    if payload.website:
        return {'ok': True, 'message': 'Request received'}
    name, email = payload.name.strip(), payload.email.strip().lower()
    if not name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter your name and a valid email address')
    if any(ord(c) < 32 and c not in '\n\t\r' for c in payload.note):
        raise HTTPException(422, 'Invalid request note')
    ship_fields = (payload.shipping_line1, payload.shipping_line2,
                   payload.shipping_city, payload.shipping_state)
    if any(ord(c) < 32 for f in ship_fields for c in f):
        raise HTTPException(422, 'Invalid shipping address')
    if (payload.shipping_line1 or payload.shipping_city or payload.shipping_state) and not (
            payload.shipping_line1.strip() and payload.shipping_city.strip() and
            payload.shipping_state.strip() and payload.postal_code.strip()):
        raise HTTPException(422, 'Complete shipping address required')
    lines = _price_lines(request, payload.lines)
    token = str(payload.token)
    path = _orders_path(request)
    with _locked(path):
        rows = _load(path)
        old = next((row for row in rows if row.get('token') == token), None)
        if old:
            if old.get('lines') != lines or old.get('customer_email') != email:
                raise HTTPException(409, 'This order reference was already used')
            return {'ok': True, 'reference': old['id'][:8], 'duplicate': True}
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        recent = 0
        for row in rows:
            if row.get('customer_email', '').lower() != email:
                continue
            try:
                stamp = datetime.fromisoformat(str(row.get('created_at', '')).replace('Z', '+00:00'))
                if stamp.tzinfo and stamp >= cutoff:
                    recent += 1
            except ValueError:
                pass
        if recent >= 5:
            raise HTTPException(429, 'Too many requests; please contact our parts team')
        now = _now()
        record = {'id': uuid.uuid4().hex, 'token': token, 'created_at': now,
                  'updated_at': now, 'requested_at': now, 'state': 'requested',
                  'lines': lines, 'subtotal_cents': sum(p['price_cents'] * p['qty'] for p in lines),
                  'shipping_cents': None, 'currency': 'usd',
                  'customer_name': name, 'customer_email': email,
                  'customer_phone': payload.phone.strip(),
                  'postal_code': payload.postal_code.strip(), 'customer_note': payload.note.strip(),
                  'shipping_address': {'line1': payload.shipping_line1.strip(),
                                       'line2': payload.shipping_line2.strip(),
                                       'city': payload.shipping_city.strip(),
                                       'state': payload.shipping_state.strip(),
                                       'postal_code': payload.postal_code.strip(), 'country': 'US'},
                  'paid_at': None}
        rows.append(record)
        _save(path, rows)
    return {'ok': True, 'reference': record['id'][:8], 'payment_received': False}


def _checkout_payload(order, origin, shipping):
    fields = {"mode": "payment", "payment_method_types[0]": "card",
              "client_reference_id": order["id"],
              "metadata[pds_parts_order_id]": order["id"],
              "success_url": origin + "/pds-parts?payment=success&session_id={CHECKOUT_SESSION_ID}",
              "cancel_url": origin + "/pds-parts?payment=cancel",
              "shipping_address_collection[allowed_countries][0]": "US",
              "phone_number_collection[enabled]": "true",
              "automatic_tax[enabled]": "false" if (
                  _enabled("PDS_PARTS_STORE_TEST_NO_TAX") and
                  (os.getenv("PDS_PARTS_STORE_STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY", "")).startswith("sk_test_")
              ) else "true",  # Test-only bypass; production always requires Stripe Tax.
              "shipping_options[0][shipping_rate_data][type]": "fixed_amount",
              "shipping_options[0][shipping_rate_data][fixed_amount][amount]": str(shipping),
              "shipping_options[0][shipping_rate_data][fixed_amount][currency]": "usd",
              "shipping_options[0][shipping_rate_data][display_name]": "Standard shipping"}
    if order.get('customer_email'):
        fields['customer_email'] = order['customer_email']
    for i, line in enumerate(order["lines"]):
        pre = f"line_items[{i}]"
        fields[f"{pre}[price_data][currency]"] = "usd"
        fields[f"{pre}[price_data][unit_amount]"] = str(line["price_cents"])
        fields[f"{pre}[price_data][product_data][name]"] = (line["manufacturer"] + " " + line["part_number"]).strip()[:160] or line["description"][:160]
        fields[f"{pre}[quantity]"] = str(line["qty"])
    return fields


def _stripe_session(key, order, origin, shipping):
    body = urlencode(_checkout_payload(order, origin, shipping)).encode()
    req = UrlRequest("https://api.stripe.com/v1/checkout/sessions", body, {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Idempotency-Key": "pds-parts-" + order["id"],
    }, method="POST")
    with urlopen(req, timeout=15) as response:
        return json.loads(response.read(100000))


@router.post("/api/checkout")
def checkout(request: Request, cart: Cart):
    key, shipping, origin = _payment_settings()
    lines = _price_lines(request, cart.lines)
    subtotal = sum(line['price_cents'] * line['qty'] for line in lines)
    name, email, phone = cart.name.strip(), cart.email.strip().lower(), cart.phone.strip()
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter a valid email address')
    if any(ord(ch) < 32 for field in (name, email, phone, cart.postal_code) for ch in field):
        raise HTTPException(422, 'Invalid contact details')
    token = str(cart.token)
    path = _orders_path(request)
    # Lock held through provider response. A retried token cannot create a second session.
    with _locked(path):
        orders = _load(path)
        previous = next((x for x in orders if x.get("token") == token), None)
        if previous:
            if (previous.get("lines") != lines or previous.get("shipping_cents") != shipping):
                raise HTTPException(409, "Cart changed; refresh checkout")
            if previous.get("state") == "checkout_pending" and previous.get("checkout_url"):
                return {"checkout_url": previous["checkout_url"], "reference": previous["id"][:8]}
            raise HTTPException(409, "Existing checkout needs review; do not retry payment")
        record = {"id": uuid.uuid4().hex, "token": token, "created_at": _now(),
                  "updated_at": _now(), "state": "creating", "lines": lines,
                  "subtotal_cents": subtotal, "shipping_cents": shipping, "currency": "usd",
                  "customer_name": name, "customer_email": email,
                  "customer_phone": phone, "postal_code": cart.postal_code.strip(),
                  "test_mode": key.startswith("sk_test_")}
        orders.append(record)
        _save(path, orders)
        try:
            session = _stripe_session(key, record, origin, shipping)
            session_id = str(session.get("id") or "")
            checkout_url = str(session.get("url") or "")
            url = urlsplit(checkout_url)
            expected_prefix = "cs_live_" if key.startswith("sk_live_") else "cs_test_"
            if (not session_id.startswith(expected_prefix) or url.scheme != "https"
                    or url.hostname not in ("checkout.stripe.com", "checkout.stripe.dev")
                    or session.get("mode") != "payment" or session.get("currency") != "usd"
                    or (session.get("amount_subtotal") is not None and session.get("amount_subtotal") != subtotal)):
                raise ValueError("Stripe checkout mismatch")
        except Exception:
            record.update(state="checkout_uncertain", updated_at=_now())
            _save(path, orders)
            raise HTTPException(503, "Checkout needs review. Please contact PDS before retrying payment.")
        record.update(state="checkout_pending", checkout_url=checkout_url,
                      stripe_session_id=session_id, updated_at=_now())
        _save(path, orders)
    return {"checkout_url": checkout_url, "reference": record["id"][:8]}


def _signed_event(raw: bytes, signature: str, secret: str):
    if not secret or len(raw) > 300000:
        raise HTTPException(400, "Invalid Stripe event")
    chunks = [p.strip().split("=", 1) for p in signature.split(",") if "=" in p]
    timestamps = [v for k, v in chunks if k == "t"]
    signatures = [v for k, v in chunks if k == "v1"]
    if len(timestamps) != 1 or not signatures:
        raise HTTPException(400, "Invalid signature")
    try:
        stamp = int(timestamps[0])
    except ValueError as exc:
        raise HTTPException(400, "Invalid signature time") from exc
    if abs(time.time() - stamp) > 300:
        raise HTTPException(400, "Signature expired")
    calculated = hmac.new(secret.encode(), str(stamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(calculated, x) for x in signatures):
        raise HTTPException(400, "Invalid signature")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise HTTPException(400, "Invalid Stripe payload") from exc


@router.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("stripe-signature", "")
    secret = os.getenv("PDS_PARTS_STORE_STRIPE_WEBHOOK_SECRET", "")
    event = _signed_event(raw, signature, secret)
    if event.get("type") not in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        return {"received": True, "processed": False}
    session = event.get("data", {}).get("object", {})
    if session.get("payment_status") != "paid":
        return {"received": True, "processed": False}
    order_id = str(session.get("client_reference_id") or "")
    session_id = str(session.get("id") or "")
    if not order_id or not session_id or str(session.get("currency")) != "usd":
        raise HTTPException(400, "Unexpected Stripe session")
    path = _orders_path(request)
    with _locked(path):
        orders = _load(path)
        order = next((x for x in orders if x["id"] == order_id), None)
        if not order:
            raise HTTPException(404, "Order not found")
        if (order.get("stripe_session_id") != session_id
                or str(session.get("metadata", {}).get("pds_parts_order_id")) != order_id):
            raise HTTPException(409, "Payment does not match order")
        if (bool(event.get("livemode")) != session_id.startswith("cs_live_")
                or bool(order.get("test_mode")) == bool(event.get("livemode"))):
            raise HTTPException(409, "Stripe payment mode mismatch")
        # Check Stripe's authoritative breakdown, not the redirect URL or a
        # browser-supplied amount. Tax can vary by customer's shipping address.
        details = session.get("total_details") or {}
        amount_subtotal = session.get("amount_subtotal")
        amount_shipping = details.get("amount_shipping")
        amount_tax = details.get("amount_tax")
        total = session.get("amount_total")
        if (not isinstance(amount_subtotal, int) or amount_subtotal != order["subtotal_cents"]
                or not isinstance(amount_shipping, int) or amount_shipping != order["shipping_cents"]
                or not isinstance(amount_tax, int) or amount_tax < 0
                or not isinstance(total, int)
                or total != amount_subtotal + amount_shipping + amount_tax):
            raise HTTPException(409, "Payment total needs reconciliation")
        if order["state"] in STATES:
            return {"received": True, "processed": False, "duplicate": True}
        if order["state"] != "checkout_pending":
            raise HTTPException(409, "Order requires manual review")
        details = session.get("customer_details") or {}
        collected = session.get("collected_information") or {}
        ship = collected.get("shipping_details") or session.get("shipping_details") or {}
        order.update(state="paid", paid_at=_now(), updated_at=_now(),
                     tax_cents=amount_tax, total_cents=total,
                     stripe_payment_intent=str(session.get("payment_intent") or ""),
                     customer_email=str(details.get("email") or order.get("customer_email") or "")[:254],
                     customer_phone=str(details.get("phone") or order.get("customer_phone") or "")[:45],
                     shipping_name=str(ship.get("name") or details.get("name") or "")[:150],
                     shipping_address=ship.get("address") or details.get("address") or {})
        _save(path, orders)
    return {"received": True, "processed": True}


def _public_order_rows(request):
    path = _orders_path(request)
    with _locked(path):
        orders = list(reversed(_load(path)))
    # Omit internal token and hosted checkout session URL.
    public = []
    for row in orders[:1000]:
        safe = {k: v for k, v in row.items() if k not in ('token', 'checkout_url')}
        safe['test_mode'] = bool(row.get('test_mode') or str(row.get('stripe_session_id') or '').startswith('cs_test_'))
        public.append(safe)
    return {'items': public}


@router.get('/api/sdc/orders')
def sdc_order_report(request: Request):
    _sdc_sales_admin(request)
    return _public_order_rows(request)


@router.get("/orders")
def order_manager(request: Request):
    _admin(request)
    return FileResponse(Path(request.app.state.project_root) / "static" / "pds_parts_orders.html",
                        media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/api/orders")
def list_orders(request: Request):
    _admin(request)
    return _public_order_rows(request)


class OrderUpdate(BaseModel):
    status: str
    tracking: str = Field(default='', max_length=160)
    carrier: str = Field(default='', max_length=80)
    eta_date: str = Field(default='', max_length=10)
    staff_notes: str = Field(default='', max_length=1600)


def _update_fulfillment(order_id, payload, request):
    if not re.fullmatch(r'[0-9a-f]{32}', order_id):
        raise HTTPException(404, 'Order not found')
    if payload.eta_date:
        from datetime import date
        try:
            date.fromisoformat(payload.eta_date)
        except ValueError as exc:
            raise HTTPException(422, 'Invalid estimated delivery date') from exc
    path = _orders_path(request)
    with _locked(path):
        orders = _load(path)
        order = next((x for x in orders if x.get('id') == order_id), None)
        if not order:
            raise HTTPException(404, 'Order not found')
        if order['state'] not in STATES:
            raise HTTPException(409, 'Checkout is not confirmed')
        paid = bool(order.get('paid_at'))
        statuses = ('paid', 'supplier_ordered', 'shipped', 'completed', 'needs_review') if paid else ('requested', 'needs_quote', 'contacted', 'needs_review', 'cancelled')
        if payload.status not in statuses:
            raise HTTPException(409, 'Confirm payment before fulfillment')
        before = order['state']
        order.update(state=payload.status, tracking=payload.tracking.strip(),
                     carrier=payload.carrier.strip(), eta_date=payload.eta_date.strip(),
                     staff_notes=payload.staff_notes.strip(), updated_at=_now(),
                     updated_by=str(request.state.auth_user.get('id') or '')[:90])
        if payload.status == 'shipped' and before != 'shipped':
            order['shipped_at'] = _now()
        history = order.setdefault('history', [])
        history.append({'at': _now(), 'status': payload.status, 'by': order['updated_by']})
        order['history'] = history[-100:]
        _save(path, orders)
    return {'ok': True, 'status': order['state'], 'paid': paid}


@router.patch('/api/orders/{order_id}')
def update_order(order_id: str, payload: OrderUpdate, request: Request):
    _admin(request)
    return _update_fulfillment(order_id, payload, request)


@router.patch('/api/sdc/orders/{order_id}')
def sdc_update_order(order_id: str, payload: OrderUpdate, request: Request):
    _sdc_sales_admin(request)
    return _update_fulfillment(order_id, payload, request)
