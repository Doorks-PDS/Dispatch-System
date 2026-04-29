from __future__ import annotations

import json
import csv
import uuid
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.storage import (
    bootstrap_data_file,
    bootstrap_data_dir,
    first_existing_data_path,
    get_writable_data_dir,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    try:
        if path.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    _atomic_write_text(path, text)


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _csv_match_job_number(row: Dict[str, Any], job_number: str) -> bool:
    target = str(job_number or "").strip()
    if not target:
        return False
    candidates = [
        row.get("Job Number"),
        row.get("job_number"),
        row.get("Job #"),
        row.get("job #"),
    ]
    return any(str(v or "").strip() == target for v in candidates)


def _csv_pick_address(row: Dict[str, Any]) -> str:
    for key in ["Job Site Address", "Address", "Job Address", "address"]:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _mmddyy(yyyy_mm_dd: str) -> str:
    try:
        y, m, d = yyyy_mm_dd.split("-")
        return f"{m}/{d}/{y[-2:]}"
    except Exception:
        return yyyy_mm_dd


STATUSES = [
    "Sales Lead",
    "Dispatch",
    "Quote",
    "Quote Sent",
    "Parts on Order",
    "Complete/Quote",
    "Complete",
    "Done",
    "Additional Work",
    "Complete/Additional Work",
]


def _normalize_status(status: Any, default: str = "Dispatch") -> str:
    s = str(status or "").strip()
    if not s:
        return default
    aliases = {
        "Additional Work": "Dispatch",
        "Complete/Additional Work": "Dispatch",
    }
    s = aliases.get(s, s)
    return s if s in STATUSES else default


DOOR_TYPES = [
    "Automatic Door",
    "Man Door",
    "Storefront Door",
    "Herculite Door",
    "Roll Up",
    "Glass",
    "Roll/Swing Gate",
    "Other",
]


@dataclass
class CalendarStore:
    project_root: Path | str

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        self.data_dir = get_writable_data_dir(self.project_root)
        self.path = bootstrap_data_file(self.project_root, "calendar_jobs.json")
        self.legacy_path = bootstrap_data_file(self.project_root, "calendar", "jobs.json")
        self.billable_time_csv = first_existing_data_path(self.project_root, "billable_time.csv")
        self.tech_notes_csv = first_existing_data_path(self.project_root, "tech_notes.csv")
        self.upload_root = bootstrap_data_dir(self.project_root, "calendar", "uploads")
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self._lock = threading.RLock()
        self._ensure_schema()

    def _base_schema(self) -> Dict[str, Any]:
        return {
            "version": 3,
            "dispatch_counters": {},
            "sales_lead_counter": 100001,
            "jobs": [],
            "deleted_legacy_ids": [],
        }


    def _legacy_csv_address(self, job_number: str) -> str:
        target = str(job_number or "").strip()
        if not target:
            return ""

        for path in [self.tech_notes_csv, self.billable_time_csv]:
            for row in _read_csv_rows(path):
                if not isinstance(row, dict):
                    continue
                if _csv_match_job_number(row, target):
                    address = _csv_pick_address(row)
                    if address:
                        return address
        return ""

    def _normalize_legacy_job(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        status = _normalize_status(legacy.get("status"), "Dispatch")
        kind = "sales_lead" if status == "Sales Lead" else "dispatch"

        checked_in_at = legacy.get("checked_in_at")
        checked_out_at = legacy.get("checked_out_at")
        checked_in = bool(legacy.get("checked_in"))

        completion_forms: List[Dict[str, Any]] = []
        tech_name = str(legacy.get("tech_name") or "").strip()
        notes = str(legacy.get("tech_notes") or "").strip()
        parts_used = str(legacy.get("parts_used") or "").strip()
        addl = str(legacy.get("additional_recommendations") or "").strip()
        lead_recs = str(legacy.get("lead_recommendations") or "").strip()
        lead_parts = str(legacy.get("lead_parts_required") or "").strip()
        lead_time = str(legacy.get("lead_time_required") or "").strip()
        ready_to_quote = bool(legacy.get("ready_to_quote"))
        onsite_minutes = legacy.get("time_onsite_minutes")
        time_onsite_hours = None
        try:
            if onsite_minutes not in (None, ""):
                time_onsite_hours = max(0.0, round((float(onsite_minutes) / 60.0) * 2) / 2.0)
        except Exception:
            time_onsite_hours = None

        if any([tech_name, notes, parts_used, addl, lead_recs, lead_parts, lead_time, ready_to_quote, time_onsite_hours is not None]):
            completion_forms.append({
                "id": uuid.uuid4().hex,
                "date": str(legacy.get("date") or legacy.get("scheduled_date") or "").strip(),
                "created_at": str(legacy.get("updated_at") or legacy.get("created_at") or _now_iso()),
                "updated_at": str(legacy.get("updated_at") or legacy.get("created_at") or _now_iso()),
                "technician_name": tech_name,
                "door_type": "Other",
                "door_location": "",
                "tech_notes": notes,
                "parts_used": parts_used,
                "additional_recommendations": addl,
                "recommendations": lead_recs,
                "parts_required": lead_parts,
                "time_required": lead_time,
                "ready_to_quote": ready_to_quote,
                "time_onsite_hours": time_onsite_hours,
                "status_update": status,
                "attachments": legacy.get("completion_attachments") or [],
            })

        csv_address = self._legacy_csv_address(str(legacy.get("job_number") or legacy.get("lead_number") or "").strip())

        return {
            "id": str(legacy.get("id") or uuid.uuid4().hex),
            "kind": kind,
            "job_number": str(legacy.get("job_number") or legacy.get("lead_number") or "").strip(),
            "date": str(legacy.get("date") or legacy.get("scheduled_date") or "").strip(),
            "date_display": _mmddyy(str(legacy.get("date") or legacy.get("scheduled_date") or "").strip()),
            "status": status,
            "status_history": [],
            "customer": str(legacy.get("customer") or legacy.get("customer_name") or "").strip(),
            "contact": str(legacy.get("contact") or legacy.get("contact_name") or "").strip(),
            "phone": str(legacy.get("phone") or "").strip(),
            "email": str(legacy.get("email") or "").strip(),
            "address": str(legacy.get("address") or csv_address or "").strip(),
            "estimate_number": str(legacy.get("estimate_number") or legacy.get("estimate_no") or "").strip(),
            "invoice_number": str(legacy.get("invoice_number") or legacy.get("invoice_no") or "").strip(),
            "po_number": str(legacy.get("po_number") or legacy.get("po_no") or "").strip(),
            "job_notes": str(legacy.get("job_notes") or "").strip(),
            "office_notes": str(legacy.get("office_notes") or "").strip(),
            "attachments": legacy.get("job_attachments") or [],
            "completion_forms": completion_forms,
            "check_in": {
                "active": checked_in,
                "started_at": str(checked_in_at or "") or None,
                "stopped_at": None if checked_in else (str(checked_out_at or "") or None),
            },
            "created_at": str(legacy.get("created_at") or _now_iso()),
            "updated_at": str(legacy.get("updated_at") or legacy.get("created_at") or _now_iso()),
        }

    def _merge_legacy_jobs(self, cur: Dict[str, Any]) -> Dict[str, Any]:
        legacy_jobs = _read_json(self.legacy_path, [])
        if not isinstance(legacy_jobs, list) or not legacy_jobs:
            return cur

        jobs = cur.get("jobs", [])
        if not isinstance(jobs, list):
            jobs = []
            cur["jobs"] = jobs

        existing_ids = {str(j.get("id")) for j in jobs if isinstance(j, dict)}
        deleted_legacy_ids = {str(x) for x in (cur.get("deleted_legacy_ids") or [])}
        added = 0
        for old in legacy_jobs:
            if not isinstance(old, dict):
                continue
            old_id = str(old.get("id") or "")
            if old_id and (old_id in existing_ids or old_id in deleted_legacy_ids):
                continue
            jobs.append(self._normalize_legacy_job(old))
            if old_id:
                existing_ids.add(old_id)
            added += 1

        if added:
            cur["jobs"] = jobs
        return cur

    def _ensure_schema(self) -> None:
        base = self._base_schema()
        cur = _read_json(self.path, base)
        if not isinstance(cur, dict):
            cur = base
        cur.setdefault("version", 3)
        cur.setdefault("dispatch_counters", {})
        cur.setdefault("sales_lead_counter", 100001)
        cur.setdefault("jobs", [])
        cur.setdefault("deleted_legacy_ids", [])
        cur = self._merge_legacy_jobs(cur)

        jobs = cur.get("jobs", [])
        if isinstance(jobs, list):
            changed = False
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                kind = str(job.get("kind") or "dispatch").strip().lower()
                default_status = "Sales Lead" if kind == "sales_lead" else "Dispatch"
                normalized = _normalize_status(job.get("status"), default_status)
                if str(job.get("status") or "") != normalized:
                    job["status"] = normalized
                    changed = True
                forms = job.get("completion_forms") or []
                if isinstance(forms, list):
                    for form in forms:
                        if not isinstance(form, dict):
                            continue
                        current_form_status = form.get("status_update")
                        if current_form_status not in (None, ""):
                            normalized_form_status = _normalize_status(current_form_status, normalized)
                            if current_form_status != normalized_form_status:
                                form["status_update"] = normalized_form_status
                                changed = True
            if changed:
                cur["jobs"] = jobs

        _write_json(self.path, cur)

    def _load(self) -> Dict[str, Any]:
        self._ensure_schema()
        data = _read_json(self.path, {})
        if not isinstance(data, dict):
            raise ValueError("calendar_jobs.json invalid")
        data.setdefault("dispatch_counters", {})
        data.setdefault("sales_lead_counter", 100001)
        data.setdefault("jobs", [])
        data.setdefault("deleted_legacy_ids", [])
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        _write_json(self.path, data)

    def _append_status_history(self, job: Dict[str, Any], old_status: str, new_status: str) -> None:
        if not old_status or not new_status or old_status == new_status:
            return
        job.setdefault("status_history", [])
        job["status_history"].append({
            "from": old_status,
            "to": new_status,
            "changed_at": _now_iso(),
        })

    def _backfill_approved(self, job: Dict[str, Any]) -> None:
        approved_statuses = {"Dispatch", "Parts on Order", "Complete/Quote", "Complete", "Done"}
        history = job.get("status_history") if isinstance(job.get("status_history"), list) else []
        approved_from_history = any(
            str(item.get("from") or "") == "Quote Sent" and str(item.get("to") or "") in approved_statuses
            for item in history
            if isinstance(item, dict)
        )
        approved_now = str(job.get("status") or "") in approved_statuses and str(job.get("estimate_number") or "").strip()
        if approved_from_history or approved_now:
            job["approved"] = True
            if not job.get("approved_at"):
                job["approved_at"] = _now_iso()

    def _next_dispatch_job_number(self, data: Dict[str, Any], date_yyyy_mm_dd: str) -> str:
        try:
            y, m, _ = date_yyyy_mm_dd.split("-")
            mmyy = f"{m}{y[-2:]}"
        except Exception:
            now = datetime.now()
            mmyy = f"{now.month:02d}{now.year % 100:02d}"

        counters = data.get("dispatch_counters", {})
        if not isinstance(counters, dict):
            counters = {}
            data["dispatch_counters"] = counters

        jobs = data.get("jobs", [])
        used: set[int] = set()
        if isinstance(jobs, list):
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                num = str(job.get("job_number") or "").strip()
                m = __import__("re").match(rf"^{mmyy}-(\d+)$", num)
                if m:
                    try:
                        used.add(int(m.group(1)))
                    except Exception:
                        pass

        nxt = int(counters.get(mmyy, 1))
        while nxt in used:
            nxt += 1
        counters[mmyy] = nxt + 1
        return f"{mmyy}-{nxt}"

    def _next_sales_lead_number(self, data: Dict[str, Any]) -> str:
        n = int(data.get("sales_lead_counter", 100001))
        jobs = data.get("jobs", [])
        used: set[int] = set()
        if isinstance(jobs, list):
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                num = str(job.get("job_number") or "").strip()
                if num.isdigit():
                    try:
                        used.add(int(num))
                    except Exception:
                        pass
        while n in used:
            n += 1
        data["sales_lead_counter"] = n + 1
        return str(n)

    def list_jobs(self) -> List[Dict[str, Any]]:
        data = self._load()
        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        changed = False
        for j in jobs:
            if isinstance(j, dict):
                before = bool(j.get("approved"))
                before_at = str(j.get("approved_at") or "")
                self._backfill_approved(j)
                if bool(j.get("approved")) != before or str(j.get("approved_at") or "") != before_at:
                    changed = True

        if changed:
            data["jobs"] = jobs
            self._save(data)

        def key(j: Dict[str, Any]) -> Tuple[str, str]:
            return (str(j.get("date", "")), str(j.get("created_at", "")))

        return sorted(jobs, key=key)

    def all(self) -> List[Dict[str, Any]]:
        return self.list_jobs()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        for j in self.list_jobs():
            if str(j.get("id")) == job_id:
                return j
        return None

    def get_by_job_number(self, job_number: str) -> Optional[Dict[str, Any]]:
        job_number = str(job_number or "").strip()
        if not job_number:
            return None
        for j in self.list_jobs():
            if str(j.get("job_number", "")).strip() == job_number:
                return j
        return None


    def _job_number_exists(self, data: Dict[str, Any], job_number: str, exclude_id: str = "") -> bool:
        target = str(job_number or "").strip()
        if not target:
            return False
        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return False
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if exclude_id and str(job.get("id") or "") == str(exclude_id):
                continue
            if str(job.get("job_number") or "").strip() == target:
                return True
        return False

    def preview_next_job_number(self, kind: str, date_yyyy_mm_dd: str) -> str:
        data = self._load()
        normalized_kind = str(kind or "dispatch").strip().lower()
        if normalized_kind == "sales_lead":
            return self._next_sales_lead_number(data)
        return self._next_dispatch_job_number(data, date_yyyy_mm_dd)

    def create_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        kind = str(payload.get("kind") or "dispatch").strip().lower()
        date = str(payload.get("date") or "").strip()
        if not date:
            raise ValueError("Missing date")

        default_status = "Sales Lead" if kind == "sales_lead" else "Dispatch"
        status = _normalize_status(payload.get("status"), default_status)

        job_id = uuid.uuid4().hex

        manual_job_number = str(payload.get("job_number") or "").strip()
        if manual_job_number:
            if self._job_number_exists(data, manual_job_number):
                raise ValueError(f"Job number already exists: {manual_job_number}")
            job_number = manual_job_number
        elif kind == "sales_lead":
            job_number = self._next_sales_lead_number(data)
        else:
            job_number = self._next_dispatch_job_number(data, date)

        job = {
            "id": job_id,
            "kind": "sales_lead" if kind == "sales_lead" else "dispatch",
            "job_number": job_number,
            "date": date,
            "date_display": _mmddyy(date),
            "status": status,
            "status_history": [],
            "customer": str(payload.get("customer") or "").strip(),
            "contact": str(payload.get("contact") or "").strip(),
            "phone": str(payload.get("phone") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "address": str(payload.get("address") or "").strip(),
            "estimate_number": str(payload.get("estimate_number") or "").strip(),
            "invoice_number": str(payload.get("invoice_number") or "").strip(),
            "po_number": str(payload.get("po_number") or "").strip(),
            "job_notes": str(payload.get("job_notes") or "").strip(),
            "office_notes": str(payload.get("office_notes") or "").strip(),
            "attachments": [],
            "completion_forms": [],
            "parts_order": {
                "supplier": "",
                "po_number": "",
                "order_date": "",
                "expected_arrival_date": "",
                "notes": "",
            },
            "approved": False,
            "approved_at": None,
            "check_in": {
                "active": False,
                "started_at": None,
                "stopped_at": None,
            },
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

        jobs.append(job)
        self._save(data)
        return job

    def update_job(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        idx = None
        for i, j in enumerate(jobs):
            if str(j.get("id")) == job_id:
                idx = i
                break
        if idx is None:
            raise KeyError("Job not found")

        j = jobs[idx]
        old_status = str(j.get("status") or "")
        old_kind = str(j.get("kind") or "dispatch")

        for k in [
            "date", "status", "customer", "contact", "phone", "email", "address",
            "estimate_number", "invoice_number", "po_number", "job_notes", "office_notes",
            "job_number", "kind", "completion_forms", "parts_order"
        ]:
            if k in payload:
                if k == "completion_forms":
                    if isinstance(payload.get(k), list):
                        j[k] = payload.get(k)
                elif k == "parts_order":
                    if isinstance(payload.get(k), dict):
                        cur_po = j.get("parts_order") if isinstance(j.get("parts_order"), dict) else {}
                        merged = {
                            "supplier": str(payload.get(k, {}).get("supplier") or cur_po.get("supplier") or "").strip(),
                            "po_number": str(payload.get(k, {}).get("po_number") or cur_po.get("po_number") or "").strip(),
                            "order_date": str(payload.get(k, {}).get("order_date") or cur_po.get("order_date") or "").strip(),
                            "expected_arrival_date": str(payload.get(k, {}).get("expected_arrival_date") or cur_po.get("expected_arrival_date") or "").strip(),
                            "notes": str(payload.get(k, {}).get("notes") or cur_po.get("notes") or "").strip(),
                        }
                        j[k] = merged
                else:
                    if k == "job_number":
                        candidate = str(payload.get(k) or "").strip()
                        if candidate and self._job_number_exists(data, candidate, exclude_id=job_id):
                            raise ValueError(f"Job number already exists: {candidate}")
                        j[k] = candidate
                    else:
                        j[k] = str(payload.get(k) or "").strip()

        if "date" in payload:
            j["date_display"] = _mmddyy(str(j.get("date", "")))

        if "kind" in payload:
            new_kind = str(j.get("kind") or "dispatch").strip().lower()
            if new_kind not in {"dispatch", "sales_lead"}:
                new_kind = "dispatch"
            j["kind"] = new_kind

            if old_kind == "sales_lead" and new_kind == "dispatch":
                if not str(payload.get("job_number") or "").strip():
                    j["job_number"] = self._next_dispatch_job_number(data, str(j.get("date") or ""))
                if j.get("status") == "Sales Lead":
                    j["status"] = "Dispatch"

        if "status" in payload:
            default_status = "Sales Lead" if str(j.get("kind") or "dispatch") == "sales_lead" else "Dispatch"
            j["status"] = _normalize_status(j.get("status"), default_status)

        new_status = str(j.get("status") or "")
        if old_status == "Quote Sent" and new_status in {"Dispatch", "Parts on Order", "Complete/Quote", "Complete", "Done"}:
            j["approved"] = True
            j["approved_at"] = _now_iso()
        self._append_status_history(j, old_status, new_status)
        self._backfill_approved(j)

        j["updated_at"] = _now_iso()
        jobs[idx] = j
        self._save(data)
        return j

    def delete_job(self, job_id: str) -> None:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]
        removed: Optional[Dict[str, Any]] = None
        kept = []
        for j in jobs:
            if str(j.get("id")) == job_id and removed is None:
                removed = j
                continue
            kept.append(j)
        data["jobs"] = kept

        if isinstance(removed, dict):
            deleted_legacy_ids = data.get("deleted_legacy_ids", [])
            if not isinstance(deleted_legacy_ids, list):
                deleted_legacy_ids = []
            removed_id = str(removed.get("id") or "")
            if removed_id and removed_id not in deleted_legacy_ids:
                legacy_jobs = _read_json(self.legacy_path, [])
                if isinstance(legacy_jobs, list) and any(str(x.get("id") or "") == removed_id for x in legacy_jobs if isinstance(x, dict)):
                    deleted_legacy_ids.append(removed_id)
            data["deleted_legacy_ids"] = deleted_legacy_ids

        self._save(data)

    def start_check_in(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) == job_id:
                j.setdefault("check_in", {})
                j["check_in"]["active"] = True
                j["check_in"]["started_at"] = _now_iso()
                j["check_in"]["stopped_at"] = None
                j["updated_at"] = _now_iso()
                jobs[i] = j
                self._save(data)
                return j
        raise KeyError("Job not found")

    def stop_check_in(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) == job_id:
                j.setdefault("check_in", {})
                j["check_in"]["active"] = False
                j["check_in"]["stopped_at"] = _now_iso()
                j["updated_at"] = _now_iso()
                jobs[i] = j
                self._save(data)
                return j
        raise KeyError("Job not found")

    def add_completion_form(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) != job_id:
                continue

            form_id = uuid.uuid4().hex
            door_type = str(payload.get("door_type") or "").strip()
            if not door_type:
                raise ValueError("Door type is required")
            if door_type and door_type not in DOOR_TYPES:
                door_type = "Other"

            def round_half(x: float) -> float:
                return round(x * 2) / 2.0

            time_hours = payload.get("time_onsite_hours")
            try:
                time_hours_f = float(time_hours) if time_hours is not None and str(time_hours).strip() != "" else None
            except Exception:
                time_hours_f = None
            if time_hours_f is not None:
                time_hours_f = max(0.0, round_half(time_hours_f))

            ready_to_quote = bool(payload.get("ready_to_quote", False))
            old_status = str(j.get("status") or "")

            status_update = _normalize_status(payload.get("status_update"), str(j.get("status") or "Dispatch"))
            if j.get("kind") == "sales_lead" and ready_to_quote:
                j["status"] = "Quote"
            elif status_update in STATUSES:
                j["status"] = status_update

            if old_status == "Quote Sent" and str(j.get("status") or "") in {"Dispatch", "Parts on Order", "Complete/Quote", "Complete", "Done"}:
                j["approved"] = True
                j["approved_at"] = _now_iso()
            self._append_status_history(j, old_status, str(j.get("status") or ""))
            self._backfill_approved(j)

            form = {
                "id": form_id,
                "date": str(payload.get("date") or payload.get("form_date") or datetime.now().strftime("%Y-%m-%d")).strip(),
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "technician_name": str(payload.get("technician_name") or "").strip(),
                "door_type": door_type,
                "door_location": str(payload.get("door_location") or "").strip(),
                "tech_notes": str(payload.get("tech_notes") or "").strip(),
                "parts_used": str(payload.get("parts_used") or "").strip(),
                "additional_recommendations": str(payload.get("additional_recommendations") or "").strip(),
                "recommendations": str(payload.get("recommendations") or "").strip(),
                "parts_required": str(payload.get("parts_required") or "").strip(),
                "time_required": str(payload.get("time_required") or "").strip(),
                "ready_to_quote": ready_to_quote,
                "time_onsite_hours": time_hours_f,
                "status_update": j.get("status"),
                "attachments": [],
            }

            j.setdefault("completion_forms", [])
            j["completion_forms"].append(form)

            j["updated_at"] = _now_iso()
            jobs[i] = j
            self._save(data)
            return form

        raise KeyError("Job not found")

    def update_completion_form(self, job_id: str, form_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) != job_id:
                continue

            forms = j.get("completion_forms", [])
            if not isinstance(forms, list):
                forms = []
                j["completion_forms"] = forms

            for fi, f in enumerate(forms):
                if str(f.get("id")) != form_id:
                    continue

                if "form_date" in payload and "date" not in payload:
                    payload["date"] = payload.get("form_date")

                for k in [
                    "date",
                    "technician_name",
                    "door_type",
                    "door_location",
                    "tech_notes",
                    "parts_used",
                    "additional_recommendations",
                    "recommendations",
                    "parts_required",
                    "time_required",
                ]:
                    if k in payload:
                        f[k] = str(payload.get(k) or "").strip()

                if "ready_to_quote" in payload:
                    f["ready_to_quote"] = bool(payload.get("ready_to_quote", False))

                if "time_onsite_hours" in payload:
                    try:
                        x = float(payload.get("time_onsite_hours"))
                        f["time_onsite_hours"] = max(0.0, round(x * 2) / 2.0)
                    except Exception:
                        pass

                old_status = str(j.get("status") or "")

                if "status_update" in payload:
                    st = _normalize_status(payload.get("status_update"), str(j.get("status") or "Dispatch"))
                    if j.get("kind") == "sales_lead" and bool(f.get("ready_to_quote")):
                        j["status"] = "Quote"
                        f["status_update"] = "Quote"
                    elif st in STATUSES:
                        j["status"] = st
                        f["status_update"] = st

                if old_status == "Quote Sent" and str(j.get("status") or "") in {"Dispatch", "Parts on Order"}:
                    j["approved"] = True
                    j["approved_at"] = _now_iso()
                self._append_status_history(j, old_status, str(j.get("status") or ""))

                f["updated_at"] = _now_iso()
                forms[fi] = f

                j["updated_at"] = _now_iso()
                jobs[i] = j
                self._save(data)
                return f

        raise KeyError("Completion form not found")

    def add_job_attachments(self, job_id: str, files: List[Tuple[str, bytes]]) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) != job_id:
                continue

            saved_meta: List[Dict[str, Any]] = []
            job_dir = self.upload_root / job_id / "job"
            job_dir.mkdir(parents=True, exist_ok=True)

            j.setdefault("attachments", [])
            for (filename, content) in files:
                safe = filename.replace("/", "_").replace("\\", "_")
                dest = job_dir / safe
                dest.write_bytes(content)
                meta = {"filename": safe, "path": str(dest), "bytes": len(content), "created_at": _now_iso()}
                j["attachments"].append(meta)
                saved_meta.append(meta)

            j["updated_at"] = _now_iso()
            jobs[i] = j
            self._save(data)
            return saved_meta

        raise KeyError("Job not found")

    def add_completion_attachments(self, job_id: str, form_id: str, files: List[Tuple[str, bytes]]) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._load()
        jobs = data["jobs"]

        for i, j in enumerate(jobs):
            if str(j.get("id")) != job_id:
                continue

            forms = j.get("completion_forms", [])
            if not isinstance(forms, list):
                raise KeyError("Completion form not found")

            for fi, f in enumerate(forms):
                if str(f.get("id")) != form_id:
                    continue

                saved_meta: List[Dict[str, Any]] = []
                form_dir = self.upload_root / job_id / "completion" / form_id
                form_dir.mkdir(parents=True, exist_ok=True)

                f.setdefault("attachments", [])
                for (filename, content) in files:
                    safe = filename.replace("/", "_").replace("\\", "_")
                    dest = form_dir / safe
                    dest.write_bytes(content)
                    meta = {"filename": safe, "path": str(dest), "bytes": len(content), "created_at": _now_iso()}
                    f["attachments"].append(meta)
                    saved_meta.append(meta)

                f["updated_at"] = _now_iso()
                forms[fi] = f

                j["updated_at"] = _now_iso()
                jobs[i] = j
                self._save(data)
                return saved_meta

        raise KeyError("Completion form not found")

    def query_jobs(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        jobs = self.list_jobs()

        if date:
            jobs = [j for j in jobs if str(j.get("date")) == date]

        if status:
            jobs = [j for j in jobs if str(j.get("status")) == status]

        if q:
            s = q.strip().lower()

            def hit(j: Dict[str, Any]) -> bool:
                hay = " | ".join([
                    str(j.get("job_number", "")),
                    str(j.get("customer", "")),
                    str(j.get("address", "")),
                    str(j.get("estimate_number", "")),
                    str(j.get("invoice_number", "")),
                    str(j.get("po_number", "")),
                    str(j.get("contact", "")),
                    str(j.get("phone", "")),
                    str(j.get("email", "")),
                    str(j.get("job_notes", "")),
                    str(j.get("office_notes", "")),
                ]).lower()
                if s in hay:
                    return True

                for f in (j.get("completion_forms") or []):
                    if s in str(f.get("technician_name", "")).lower():
                        return True
                    if s in str(f.get("tech_notes", "")).lower():
                        return True
                    if s in str(f.get("recommendations", "")).lower():
                        return True
                return False

            jobs = [j for j in jobs if hit(j)]

        return jobs[: max(1, min(int(limit), 1000))]
