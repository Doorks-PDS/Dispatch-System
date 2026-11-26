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

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/pds-parts", tags=["PDS Parts Store"])

CATEGORIES = (
    "Automatic Doors", "Exit Devices", "Door Closers", "Hinges & Pivots",
    "Locks & Latches", "Storefront & Glass", "Accessories & Hardware",
)
IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)$")
STATES = {"paid", "supplier_ordered", "shipped", "completed", "needs_review"}


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
    if any(x in words for x in ("automatic", "operator", "presence sensor", "activation sensor", "motion sensor", "handicap opener", "actuator")):
        return "Automatic Doors"
    if any(x in words for x in ("hinge", "pivot", "continuous hinge", "offset pivot")):
        return "Hinges & Pivots"
    if any(x in words for x in ("lock", "latch", "strike", "cylinder", "deadbolt", "electrified trim")):
        return "Locks & Latches"
    if any(x in words for x in ("storefront", "glass", "glazing", "threshold", "weatherstrip")):
        return "Storefront & Glass"
    return "Accessories & Hardware"


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
            "price_cents": _cents(row.get("price")), "image_url": image_url}


def _catalog(request):
    return [p for p in (_public_item(r) for r in _raw_items(request)) if p]


def _admin(request):
    if not getattr(request.state, "auth_user", None):
        raise HTTPException(401, "Log in to view PDS orders")
    if (getattr(request.state, "auth_role", None) != "office_admin"
            or request.session.get("active_platform") != "pds"):
        raise HTTPException(403, "PDS office admin required")


def _payment_settings():
    if not _enabled("PDS_PARTS_STORE_PAYMENTS_ENABLED"):
        raise HTTPException(503, "Card checkout is not enabled yet. Contact PDS for a quote.")
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key.startswith(("sk_test_", "sk_live_")):
        raise HTTPException(503, "Stripe key is not configured")
    if key.startswith("sk_live_") and not _enabled("PDS_PARTS_STORE_LIVE_ENABLED"):
        raise HTTPException(503, "Live checkout requires an explicit launch approval")
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


def _checkout_ready():
    try:
        _payment_settings()
        return True
    except HTTPException:
        return False


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
            "shipping_note": "Usually ships in 1–3 business days after order confirmation. Manufacturer and specialty items may take longer. Shipping dates are confirmed by email."}


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


def _checkout_payload(order, origin, shipping):
    fields = {"mode": "payment", "payment_method_types[0]": "card",
              "client_reference_id": order["id"],
              "metadata[pds_parts_order_id]": order["id"],
              "success_url": origin + "/pds-parts?payment=success",
              "cancel_url": origin + "/pds-parts?payment=cancel",
              "shipping_address_collection[allowed_countries][0]": "US",
              "phone_number_collection[enabled]": "true",
              "automatic_tax[enabled]": "true",  # Fail closed if Stripe Tax is not configured.
              "shipping_options[0][shipping_rate_data][type]": "fixed_amount",
              "shipping_options[0][shipping_rate_data][fixed_amount][amount]": str(shipping),
              "shipping_options[0][shipping_rate_data][fixed_amount][currency]": "usd",
              "shipping_options[0][shipping_rate_data][display_name]": "Standard shipping"}
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
    products = {p["id"]: p for p in _catalog(request)}
    if len({l.id for l in cart.lines}) != len(cart.lines):
        raise HTTPException(422, "Duplicate products in cart")
    lines = []
    for line in cart.lines:
        p = products.get(line.id)
        if p is None or p["price_cents"] is None:
            raise HTTPException(409, "An item in the cart needs a price review")
        lines.append({**{k: p[k] for k in ("id", "description", "part_number", "manufacturer", "price_cents")}, "qty": line.qty})
    subtotal = sum(line["price_cents"] * line["qty"] for line in lines)
    if subtotal > 2000000:
        raise HTTPException(422, "Large orders require a manual quote")
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
                  "subtotal_cents": subtotal, "shipping_cents": shipping, "currency": "usd"}
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
                    or session.get("mode") != "payment" or session.get("currency") != "usd"):
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
        if bool(event.get("livemode")) != session_id.startswith("cs_live_"):
            raise HTTPException(409, "Stripe payment mode mismatch")
        if int(session.get("amount_total") or -1) < order["subtotal_cents"] + order["shipping_cents"]:
            raise HTTPException(409, "Payment total needs reconciliation")
        if order["state"] in STATES:
            return {"received": True, "processed": False, "duplicate": True}
        if order["state"] != "checkout_pending":
            raise HTTPException(409, "Order requires manual review")
        details = session.get("customer_details") or {}
        collected = session.get("collected_information") or {}
        ship = collected.get("shipping_details") or session.get("shipping_details") or {}
        order.update(state="paid", paid_at=_now(), updated_at=_now(),
                     stripe_payment_intent=str(session.get("payment_intent") or ""),
                     customer_email=str(details.get("email") or "")[:254],
                     customer_phone=str(details.get("phone") or "")[:45],
                     shipping_name=str(ship.get("name") or details.get("name") or "")[:150],
                     shipping_address=ship.get("address") or details.get("address") or {})
        _save(path, orders)
    return {"received": True, "processed": True}


@router.get("/orders")
def order_manager(request: Request):
    _admin(request)
    return FileResponse(Path(request.app.state.project_root) / "static" / "pds_parts_orders.html",
                        media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/api/orders")
def list_orders(request: Request):
    _admin(request)
    path = _orders_path(request)
    with _locked(path):
        orders = list(reversed(_load(path)))
    return {"items": [{k: v for k, v in row.items() if k not in ("token", "checkout_url")}
                      for row in orders[:500]]}


class OrderUpdate(BaseModel):
    status: str
    tracking: str = Field(default="", max_length=160)


@router.patch("/api/orders/{order_id}")
def update_order(order_id: str, payload: OrderUpdate, request: Request):
    _admin(request)
    if payload.status not in ("supplier_ordered", "shipped", "completed", "needs_review"):
        raise HTTPException(422, "Invalid fulfillment status")
    if not re.fullmatch(r"[0-9a-f]{32}", order_id):
        raise HTTPException(404, "Order not found")
    path = _orders_path(request)
    with _locked(path):
        orders = _load(path)
        order = next((x for x in orders if x["id"] == order_id), None)
        if not order:
            raise HTTPException(404, "Order not found")
        if order["state"] not in STATES:
            raise HTTPException(409, "Only paid or review orders can be updated")
        if payload.status in ("supplier_ordered", "shipped", "completed") and not order.get("paid_at"):
            raise HTTPException(409, "Payment must be confirmed first")
        order["state"] = payload.status
        order["tracking"] = payload.tracking.strip()
        order["updated_at"] = _now()
        order["updated_by"] = str(request.state.auth_user.get("id") or "")[:90]
        _save(path, orders)
    return {"ok": True, "status": order["state"]}
