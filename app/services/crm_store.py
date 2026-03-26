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
 
    def _seed_customers(self):
      items: List[Dict[str, Any]] = []
      if self.customers_seed_csv.exists():
        with self.customers_seed_csv.open("r", encoding="utf-8-sig", newline="") as f:
          reader = csv.DictReader(f)
          for row in reader:
            name = str(row.get("Company Name") or "").strip()
            if not name:
              continue
            items.append({
              "id": uuid.uuid4().hex,
              "company_name": name,
            })
      _write_json(self.customers_path, {"items": items})
 
    def _seed_contacts(self):
      items: List[Dict[str, Any]] = []
      if self.contacts_seed_csv.exists():
        with self.contacts_seed_csv.open("r", encoding="utf-8-sig", newline="") as f:
          reader = csv.DictReader(f)
          for row in reader:
            name = str(row.get("Name") or "").strip()
            if not name:
              continue
            items.append({
              "id": uuid.uuid4().hex,
              "name": name,
              "company_name": str(row.get("Customer - Company Name") or "").strip(),
              "phone_number": str(row.get("Phone Number") or "").strip(),
              "cell_phone": str(row.get("Cell Phone") or "").strip(),
              "email": str(row.get("Email") or "").strip(),
            })
      _write_json(self.contacts_path, {"items": items})
 
    def list_customers(self) -> List[Dict[str, Any]]:
      self._ensure()
      data = _read_json(self.customers_path, {"items": []})
      items = data.get("items", [])
      return sorted(items, key=lambda x: str(x.get("company_name", "")).lower())
 
    def create_customer(self, company_name: str) -> Dict[str, Any]:
      self._ensure()
      name = (company_name or "").strip()
      if not name:
        raise ValueError("Missing company name")
      data = _read_json(self.customers_path, {"items": []})
      items = data.get("items", [])
      item = {"id": uuid.uuid4().hex, "company_name": name}
      items.append(item)
      data["items"] = items
      _write_json(self.customers_path, data)
      return item
 
    def list_contacts(self, company_name: str | None = None) -> List[Dict[str, Any]]:
      self._ensure()
      data = _read_json(self.contacts_path, {"items": []})
      items = data.get("items", [])
      if company_name:
        company_name = company_name.strip().lower()
        items = [x for x in items if str(x.get("company_name", "")).strip().lower() == company_name]
      return sorted(items, key=lambda x: str(x.get("name", "")).lower())
 
    def create_contact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
      self._ensure()
      name = str(payload.get("name") or "").strip()
      if not name:
        raise ValueError("Missing contact name")
      data = _read_json(self.contacts_path, {"items": []})
      items = data.get("items", [])
      item = {
        "id": uuid.uuid4().hex,
        "name": name,
        "company_name": str(payload.get("company_name") or "").strip(),
        "phone_number": str(payload.get("phone_number") or "").strip(),
        "cell_phone": str(payload.get("cell_phone") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
      }
      items.append(item)
      data["items"] = items
      _write_json(self.contacts_path, data)
      return item
