from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])


def _require_key(request: Request, x_api_key: Optional[str]) -> str:
    require_key = getattr(request.app.state, "require_key", None)
    if callable(require_key):
        return require_key(x_api_key)
    return "tech"


def _calendar(request: Request):
    store = getattr(request.app.state, "calendar_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Calendar store not configured")
    return store


def _legacy(request: Request):
    store = getattr(request.app.state, "legacy_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Legacy store not configured")
    return store


def _timecards(request: Request):
    store = getattr(request.app.state, "timecard_store", None) or getattr(request.app.state, "timecards_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="TimeCard store not configured")
    return store


def _parts_path(request: Request) -> Path:
    root = Path(getattr(request.app.state, "project_root", "."))
    return root / "data" / "parts_catalog.json"


def _read_json_file(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_file(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_sort_date(value: Any):
    s = _norm(value)
    if not s:
        return datetime.min
    for fmt in ("%Y-%m-%d", "%m-%d-%y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def _norm(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s in {"â€”", "â€“", "—", "–", "None", "null"}:
        return ""
    return s


def _date_key(j: Dict[str, Any]) -> str:
    return _norm(j.get("date") or j.get("scheduled_date") or j.get("updated_at"))


def _job_key(j: Dict[str, Any]):
    return (
        _norm(j.get("customer") or j.get("customer_name")),
        _norm(j.get("contact") or j.get("contact_name")),
        _norm(j.get("job_number") or j.get("lead_number")),
        _norm(j.get("estimate_no") or j.get("estimate_number")),
        _norm(j.get("invoice_no") or j.get("invoice_number")),
        _norm(j.get("po_no") or j.get("po_number")),
        _norm(j.get("address")),
        _date_key(j),
        _norm(j.get("source") or j.get("_source")),
    )


def _filter_jobs(jobs: List[Dict[str, Any]], q: str = "", date: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    q = _norm(q).lower()
    status = _norm(status).lower()
    out = []
    for j in jobs:
        if date and not str(j.get("date") or j.get("scheduled_date") or "").startswith(date):
            continue
        if status and _norm(j.get("status")).lower() != status:
            continue
        if q:
            fields = [
                _norm(j.get("customer") or j.get("customer_name")).lower(),
                _norm(j.get("contact") or j.get("contact_name")).lower(),
                _norm(j.get("job_number") or j.get("lead_number")).lower(),
                _norm(j.get("estimate_no") or j.get("estimate_number")).lower(),
                _norm(j.get("invoice_no") or j.get("invoice_number")).lower(),
                _norm(j.get("po_no") or j.get("po_number")).lower(),
                _norm(j.get("address")).lower(),
            ]
            if not any(q in f for f in fields):
                continue
        out.append(j)
    return out


ROLLUP_ALLOWED_STATUSES = {"Additional Work", "Complete/Additional Work", "Complete"}


@router.get("/rollup")
def rollup_data(
    month: Optional[str] = None,
    request: Request = None,
    x_api_key: Optional[str] = Header(default=None),
):
    _require_key(request, x_api_key)
    cal = _calendar(request)

    jobs = cal.all() if hasattr(cal, "all") else cal.list_jobs()
    if month:
        jobs = [j for j in jobs if str(j.get("date") or "").startswith(month)]

    jobs = [
        j for j in jobs
        if (j.get("door_type") or "").strip() == "Roll Up"
        and (j.get("status") or "") in ROLLUP_ALLOWED_STATUSES
    ]

    totals = defaultdict(float)
    for j in jobs:
        tech = (j.get("tech_name") or "").strip() or "Unassigned"
        bh = float(j.get("billed_hours") or 0.0)
        totals[tech] += bh

    totals_list = [{"tech": k, "billed_hours": round(v, 2)} for k, v in sorted(totals.items(), key=lambda x: (-x[1], x[0]))]
    return {"ok": True, "jobs": jobs, "totals": totals_list}


@router.get("/all-jobs")
def list_all_jobs(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
    date: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 500,
):
    _require_key(request, x_api_key)
    cal = _calendar(request)
    legacy = _legacy(request)

    combined: List[Dict[str, Any]] = []

    try:
        for j in (cal.all() if hasattr(cal, "all") else cal.list_jobs()):
            item = dict(j)
            item["source"] = "CURRENT"
            combined.append(item)
    except Exception:
        pass

    try:
        for j in legacy.all():
            item = dict(j)
            item["source"] = str(item.get("source") or item.get("_source") or "LEGACY").upper()
            combined.append(item)
    except Exception:
        pass

    filtered = _filter_jobs(combined, q=q or "", date=date, status=status)

    seen = set()
    deduped = []
    for j in filtered:
        k = _job_key(j)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(j)

    def sort_key(j: Dict[str, Any]):
        has_job = 0 if _norm(j.get("job_number") or j.get("lead_number")) else 1
        parsed = _parse_sort_date(j.get("date") or j.get("scheduled_date") or j.get("updated_at"))
        customer = _norm(j.get("customer") or j.get("customer_name")).lower()
        return (has_job, -parsed.timestamp() if parsed != datetime.min else float("inf"), customer)

    deduped.sort(key=sort_key)
    return {"ok": True, "jobs": deduped[: max(1, min(int(limit), 5000))]}


@router.post("/legacy/{record_id}/promote")
def promote_legacy_job(
    request: Request,
    record_id: str,
    x_api_key: Optional[str] = Header(default=None),
    date: Optional[str] = None,
    kind: Optional[str] = None,
):
    _require_key(request, x_api_key)
    legacy = _legacy(request)
    cal = _calendar(request)

    row = legacy.get(record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Legacy job not found")

    promote_kind = "sales_lead" if str(kind or "").strip().lower() == "sales_lead" else "dispatch"
    payload = {
        "kind": promote_kind,
        "date": (date or row.get("date") or datetime.utcnow().strftime("%Y-%m-%d")),
        "status": "Sales Lead" if promote_kind == "sales_lead" else "Dispatch",
        "customer": row.get("customer") or row.get("customer_name") or "",
        "contact": row.get("contact") or row.get("contact_name") or "",
        "address": row.get("address") or "",
        "estimate_number": row.get("estimate_number") or row.get("estimate_no") or "",
        "invoice_number": row.get("invoice_number") or row.get("invoice_no") or "",
        "po_number": row.get("po_number") or row.get("po_no") or "",
        "job_notes": row.get("job_notes") or row.get("description") or row.get("tech_notes") or "",
        "office_notes": row.get("work_performed") or "",
    }
    job = cal.create_job(payload)
    return {"ok": True, "job": job}


class PartPayload(BaseModel):
    id: str = ""
    manufacturer: str = ""
    part_number: str = ""
    description: str = ""
    price: float | str = ""


@router.get("/parts")
def list_parts(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
    q: str = "",
    limit: int = 500,
):
    _require_key(request, x_api_key)
    data = _read_json_file(_parts_path(request), {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    qn = _norm(q).lower()
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = {
            "id": _norm(item.get("id")),
            "manufacturer": _norm(item.get("manufacturer")),
            "part_number": _norm(item.get("part_number")),
            "description": _norm(item.get("description")),
            "price": item.get("price", ""),
            # compatibility with existing estimate lookup
            "Item": _norm(item.get("part_number")),
            "Description": _norm(item.get("description")),
            "Price": item.get("price", ""),
            "Preferred Vendor": _norm(item.get("manufacturer")),
        }
        hay = " ".join([row["manufacturer"], row["part_number"], row["description"]]).lower()
        if qn and qn not in hay:
            continue
        out.append(row)
        if len(out) >= max(1, min(int(limit), 5000)):
            break
    return {"ok": True, "items": out}


@router.post("/parts")
def create_part(request: Request, payload: PartPayload, x_api_key: Optional[str] = Header(default=None)):
    _require_key(request, x_api_key)
    path = _parts_path(request)
    data = _read_json_file(path, {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    item = {
        "id": uuid.uuid4().hex,
        "manufacturer": _norm(payload.manufacturer),
        "part_number": _norm(payload.part_number),
        "description": _norm(payload.description),
        "price": payload.price,
    }
    items.append(item)
    data = {"items": items}
    _write_json_file(path, data)
    return {"ok": True, "item": item}


@router.put("/parts/{part_id}")
def update_part(request: Request, part_id: str, payload: PartPayload, x_api_key: Optional[str] = Header(default=None)):
    _require_key(request, x_api_key)
    path = _parts_path(request)
    data = _read_json_file(path, {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    for i, item in enumerate(items):
        if _norm(item.get("id")) == _norm(part_id):
            item["manufacturer"] = _norm(payload.manufacturer)
            item["part_number"] = _norm(payload.part_number)
            item["description"] = _norm(payload.description)
            item["price"] = payload.price
            items[i] = item
            _write_json_file(path, {"items": items})
            return {"ok": True, "item": item}
    raise HTTPException(status_code=404, detail="Part not found")


@router.delete("/parts/{part_id}")
def delete_part(request: Request, part_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require_key(request, x_api_key)
    path = _parts_path(request)
    data = _read_json_file(path, {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    items = [x for x in items if _norm(x.get("id")) != _norm(part_id)]
    _write_json_file(path, {"items": items})
    return {"ok": True}


class TimeCardRow(BaseModel):
    id: Optional[str] = None
    user: str = ""
    date: str = ""
    start_time: str = ""
    end_time: str = ""
    lunch_taken: bool = False
    lunch_start: str = ""
    lunch_end: str = ""
    notes: str = ""


@router.get("/timecards")
def list_timecards(
    month: Optional[str] = None,
    request: Request = None,
    x_api_key: Optional[str] = Header(default=None),
):
    _require_key(request, x_api_key)
    tc = _timecards(request)

    rows = tc.by_month(month or "")
    totals = defaultdict(float)
    for r in rows:
        user = (r.get("user") or "").strip() or "Unassigned"
        totals[user] += float(r.get("billed_hours") or 0.0)

    totals_list = [{"user": k, "billed_hours": round(v, 2)} for k, v in sorted(totals.items(), key=lambda x: (-x[1], x[0]))]
    return {"ok": True, "timecards": rows, "totals": totals_list}


@router.post("/timecards")
def create_timecard(
    payload: TimeCardRow,
    request: Request = None,
    x_api_key: Optional[str] = Header(default=None),
):
    _require_key(request, x_api_key)
    tc = _timecards(request)
    saved = tc.upsert(payload.model_dump())
    return {"ok": True, "timecard": saved}


@router.put("/timecards/{row_id}")
def update_timecard(
    row_id: str,
    payload: TimeCardRow,
    request: Request = None,
    x_api_key: Optional[str] = Header(default=None),
):
    _require_key(request, x_api_key)
    tc = _timecards(request)
    row = payload.model_dump()
    row["id"] = row_id
    saved = tc.upsert(row)
    return {"ok": True, "timecard": saved}


@router.delete("/timecards/{row_id}")
def delete_timecard(
    row_id: str,
    request: Request = None,
    x_api_key: Optional[str] = Header(default=None),
):
    _require_key(request, x_api_key)
    tc = _timecards(request)
    ok = tc.delete(row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Timecard not found")
    return {"ok": True}
