from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm(value: Any) -> str:
    return "".join(ch.lower() for ch in str(value or "").strip() if ch.isalnum())


class CRMStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.customers_path = self.project_root / "data" / "customers_db.json"
        self.contacts_path = self.project_root / "data" / "contacts_db.json"
        self.customers_seed_csv = self.project_root / "data" / "Customers.csv"
        self.contacts_seed_csv = self.project_root / "data" / "Contacts.csv"
        self._ensure()

    def _ensure(self):
        if not self.customers_path.exists():
            self._seed_customers()
        if not self.contacts_path.exists():
            self._seed_contacts()

    def _load_items(self, path: Path) -> List[Dict[str, Any]]:
        data = _read_json(path, {"items": []})
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = []
        return [x for x in items if isinstance(x, dict)]

    def _save_items(self, path: Path, items: List[Dict[str, Any]]) -> None:
        _write_json(path, {"items": items})

    def _seed_customers(self):
        items: List[Dict[str, Any]] = []
        if self.customers_seed_csv.exists():
            with self.customers_seed_csv.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = str(row.get("Company Name") or row.get("company_name") or "").strip()
                    if not name:
                        continue
                    items.append({
                        "id": uuid.uuid4().hex,
                        "company_name": name,
                        "address": str(row.get("Address") or "").strip(),
                        "city": str(row.get("City") or "").strip(),
                        "state": str(row.get("State") or "").strip(),
                        "zip_code": str(row.get("ZIP") or row.get("Zip") or "").strip(),
                        "phone_number": str(row.get("Phone Number") or "").strip(),
                        "email": str(row.get("Email") or "").strip(),
                        "notes": str(row.get("Notes") or "").strip(),
                    })
        self._save_items(self.customers_path, items)

    def _seed_contacts(self):
        items: List[Dict[str, Any]] = []
        if self.contacts_seed_csv.exists():
            with self.contacts_seed_csv.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = str(row.get("Name") or row.get("name") or "").strip()
                    if not name:
                        continue
                    company_name = str(row.get("Customer - Company Name") or row.get("company_name") or "").strip()
                    items.append({
                        "id": uuid.uuid4().hex,
                        "name": name,
                        "company_name": company_name,
                        "customer_id": "",
                        "phone_number": str(row.get("Phone Number") or "").strip(),
                        "cell_phone": str(row.get("Cell Phone") or "").strip(),
                        "email": str(row.get("Email") or "").strip(),
                        "title": str(row.get("Title") or "").strip(),
                        "notes": str(row.get("Notes") or "").strip(),
                    })
        self._save_items(self.contacts_path, items)


    def _backfill_contact_links(self) -> None:
        customers = self._load_items(self.customers_path)
        contacts = self._load_items(self.contacts_path)
        if not contacts or not customers:
            return
        customer_map = {_norm(c.get("company_name")): str(c.get("id") or "") for c in customers}
        changed = False
        for item in contacts:
            if not str(item.get("customer_id") or "").strip():
                company_name = str(item.get("company_name") or "").strip()
                link = customer_map.get(_norm(company_name), "")
                if link:
                    item["customer_id"] = link
                    changed = True
        if changed:
            self._save_items(self.contacts_path, contacts)

    def list_customers(self) -> List[Dict[str, Any]]:
        self._ensure()
        self._backfill_contact_links()
        items = self._load_items(self.customers_path)
        return sorted(items, key=lambda x: str(x.get("company_name", "")).lower())

    def create_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        company_name = str(payload.get("company_name") or "").strip()
        if not company_name:
            raise ValueError("Missing company name")
        items = self._load_items(self.customers_path)
        item = {
            "id": uuid.uuid4().hex,
            "company_name": company_name,
            "address": str(payload.get("address") or "").strip(),
            "city": str(payload.get("city") or "").strip(),
            "state": str(payload.get("state") or "").strip(),
            "zip_code": str(payload.get("zip_code") or "").strip(),
            "phone_number": str(payload.get("phone_number") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "notes": str(payload.get("notes") or "").strip(),
        }
        items.append(item)
        self._save_items(self.customers_path, items)
        return item

    def update_customer(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        items = self._load_items(self.customers_path)
        for item in items:
            if str(item.get("id")) == str(item_id):
                for key in ["company_name", "address", "city", "state", "zip_code", "phone_number", "email", "notes"]:
                    if key in payload:
                        item[key] = str(payload.get(key) or "").strip()
                self._save_items(self.customers_path, items)
                return item
        raise ValueError("Customer not found")

    def list_contacts(self, company_name: str | None = None, customer_id: str | None = None) -> List[Dict[str, Any]]:
        self._ensure()
        self._backfill_contact_links()
        items = self._load_items(self.contacts_path)
        if customer_id:
            want_id = str(customer_id).strip()
            items = [x for x in items if str(x.get("customer_id") or "").strip() == want_id]
        elif company_name:
            want = _norm(company_name)
            items = [
                x for x in items
                if want and (
                    _norm(x.get("company_name")) == want
                    or want in _norm(x.get("company_name"))
                    or _norm(x.get("company_name")) in want
                )
            ]
        return sorted(items, key=lambda x: str(x.get("name", "")).lower())

    def create_contact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Missing contact name")
        items = self._load_items(self.contacts_path)
        item = {
            "id": uuid.uuid4().hex,
            "name": name,
            "company_name": str(payload.get("company_name") or "").strip(),
            "customer_id": str(payload.get("customer_id") or "").strip(),
            "phone_number": str(payload.get("phone_number") or "").strip(),
            "cell_phone": str(payload.get("cell_phone") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "title": str(payload.get("title") or "").strip(),
            "notes": str(payload.get("notes") or "").strip(),
        }
        items.append(item)
        self._save_items(self.contacts_path, items)
        return item

    def update_contact(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        items = self._load_items(self.contacts_path)
        for item in items:
            if str(item.get("id")) == str(item_id):
                for key in ["name", "company_name", "customer_id", "phone_number", "cell_phone", "email", "title", "notes"]:
                    if key in payload:
                        item[key] = str(payload.get(key) or "").strip()
                self._save_items(self.contacts_path, items)
                return item
        raise ValueError("Contact not found")
