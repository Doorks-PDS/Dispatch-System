from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.storage import get_writable_data_dir, first_existing_data_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
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


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", "\n").split())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _clean_job_site_address(raw: Any, company: str = "") -> str:
    text = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = [" ".join(line.split()) for line in text.split("\n") if " ".join(line.split())]
    company_key = _normalize_key(company)
    kept: List[str] = []
    for line in lines:
        if company_key and _normalize_key(line) == company_key:
            continue
        kept.append(line)
    if not kept:
        kept = lines
    return ", ".join(kept)


class AddressStore:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.data_dir = get_writable_data_dir(self.project_root)
        self.path = self.data_dir / "addresses.json"
        self.billable_time_csv = first_existing_data_path(self.project_root, "billable_time.csv")
        self.tech_notes_csv = first_existing_data_path(self.project_root, "tech_notes.csv")
        self._ensure()

    def _ensure(self) -> None:
        if not self.path.exists():
            _atomic_write_json(self.path, {"version": 1, "items": []})

    def _load_manual(self) -> List[Dict[str, Any]]:
        self._ensure()
        data = _read_json(self.path, {"version": 1, "items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        return [x for x in items if isinstance(x, dict)]

    def _save_manual(self, items: List[Dict[str, Any]]) -> None:
        _atomic_write_json(self.path, {"version": 1, "items": items})

    def _read_csv_rows(self, path: Optional[Path], source: str) -> List[Dict[str, Any]]:
        if not path or not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    company = _clean(row.get("Company Name") or row.get("Customer") or row.get("customer") or "")
                    raw_addr = row.get("Job Site Address") or row.get("Address") or row.get("Job Address") or row.get("address") or ""
                    address = _clean_job_site_address(raw_addr, company)
                    if not address:
                        continue
                    out.append({
                        "id": f"{source}-{uuid.uuid5(uuid.NAMESPACE_URL, source + '|' + address + '|' + _clean(row.get('Job Number'))).hex}",
                        "address": address,
                        "customer": company,
                        "company_name": company,
                        "contact": _clean(row.get("Contact Name") or ""),
                        "job_number": _clean(row.get("Job Number") or row.get("Job #") or ""),
                        "date": _clean(row.get("Date Job Performed") or row.get("Date") or ""),
                        "source": source,
                    })
        except Exception:
            return []
        return out

    def _seed_addresses(self) -> List[Dict[str, Any]]:
        rows = []
        rows.extend(self._read_csv_rows(self.billable_time_csv, "billable_time"))
        rows.extend(self._read_csv_rows(self.tech_notes_csv, "tech_notes"))
        return rows

    def list(self, q: str = "", limit: int = 1000) -> List[Dict[str, Any]]:
        qn = _normalize_key(q)
        combined = []
        combined.extend(self._load_manual())
        combined.extend(self._seed_addresses())

        dedup: Dict[str, Dict[str, Any]] = {}
        for item in combined:
            address = _clean(item.get("address"))
            if not address:
                continue
            key = _normalize_key(address)
            existing = dedup.get(key)
            if existing:
                # Prefer manual/customer-enriched records, but keep legacy job number/source hints when missing.
                for k in ["customer", "company_name", "contact", "job_number", "label", "notes"]:
                    if not existing.get(k) and item.get(k):
                        existing[k] = item.get(k)
                existing["source"] = existing.get("source") or item.get("source") or "saved"
            else:
                dedup[key] = dict(item)

        items = list(dedup.values())
        if qn:
            items = [
                item for item in items
                if qn in _normalize_key(" ".join(str(item.get(k) or "") for k in ["address", "customer", "company_name", "contact", "job_number", "label", "notes", "source"]))
            ]
        items.sort(key=lambda x: (_clean(x.get("customer") or x.get("company_name")), _clean(x.get("address"))))
        return items[: max(1, min(int(limit or 1000), 5000))]

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        address = _clean(payload.get("address"))
        if not address:
            raise ValueError("Address is required")
        items = self._load_manual()
        key = _normalize_key(address)
        for item in items:
            if _normalize_key(item.get("address")) == key:
                item.update({
                    "customer": _clean(payload.get("customer") or payload.get("company_name") or item.get("customer")),
                    "company_name": _clean(payload.get("company_name") or payload.get("customer") or item.get("company_name")),
                    "label": _clean(payload.get("label") or item.get("label")),
                    "notes": _clean(payload.get("notes") or item.get("notes")),
                    "updated_at": _now_iso(),
                    "source": "saved",
                })
                self._save_manual(items)
                return item
        item = {
            "id": uuid.uuid4().hex,
            "address": address,
            "customer": _clean(payload.get("customer") or payload.get("company_name")),
            "company_name": _clean(payload.get("company_name") or payload.get("customer")),
            "label": _clean(payload.get("label")),
            "notes": _clean(payload.get("notes")),
            "source": "saved",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        items.append(item)
        self._save_manual(items)
        return item

    def update(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        item_id = str(item_id or "").strip()
        if not item_id:
            raise ValueError("Address ID is required")
        address = _clean(payload.get("address"))
        if not address:
            raise ValueError("Address is required")

        items = self._load_manual()
        for item in items:
            if str(item.get("id") or "") == item_id:
                item.update({
                    "address": address,
                    "customer": _clean(payload.get("customer") or payload.get("company_name") or item.get("customer")),
                    "company_name": _clean(payload.get("company_name") or payload.get("customer") or item.get("company_name")),
                    "label": _clean(payload.get("label") or item.get("label")),
                    "notes": _clean(payload.get("notes") or item.get("notes")),
                    "updated_at": _now_iso(),
                    "source": "saved",
                })
                self._save_manual(items)
                return item

        raise ValueError("Address not found")
