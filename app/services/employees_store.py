from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.services.storage import bootstrap_data_file


ROLES = {"tech", "lead", "office", "office_admin"}


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


class EmployeesStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path = bootstrap_data_file(self.project_root, "employees.json")
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self._ensure()

    def _base(self) -> Dict[str, Any]:
        return {"version": 1, "items": []}

    def _normalize(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            data = self._base()
        data.setdefault("version", 1)
        if not isinstance(data.get("items"), list):
            data["items"] = []
        return data

    def _ensure(self) -> None:
        data = _read_json(self.path, None)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            data = _read_json(self.backup_path, self._base())
        _write_json(self.path, self._normalize(data))

    def _load(self) -> Dict[str, Any]:
        self._ensure()
        return self._normalize(_read_json(self.path, self._base()))

    def _save(self, data: Dict[str, Any]) -> None:
        _write_json(self.path, self._normalize(data))

    def _sanitize_role(self, value: Any) -> str:
        role = str(value or "tech").strip().lower() or "tech"
        return role if role in ROLES else "tech"

    def _find_index(self, items: List[Dict[str, Any]], emp_id: str) -> int:
        for idx, item in enumerate(items):
            if isinstance(item, dict) and str(item.get("id", "")) == str(emp_id):
                return idx
        return -1

    def list(self) -> List[Dict[str, Any]]:
        items = self._load().get("items", [])
        if not isinstance(items, list):
            return []
        return sorted([x for x in items if isinstance(x, dict)], key=lambda x: str(x.get("name", "")).lower())

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
            data["items"] = items

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Missing employee name")

        item = {
            "id": uuid.uuid4().hex,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "name": name,
            "role": self._sanitize_role(payload.get("role")),
            "phone": str(payload.get("phone") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "address": str(payload.get("address") or "").strip(),
            "password": str(payload.get("password") or "").strip(),
        }

        items.append(item)
        data["items"] = items
        self._save(data)
        return item

    def update(self, emp_id: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            return None
        idx = self._find_index(items, emp_id)
        if idx < 0:
            return None

        item = items[idx]
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValueError("Missing employee name")
            item["name"] = name
        if "role" in payload:
            item["role"] = self._sanitize_role(payload.get("role"))
        if "phone" in payload:
            item["phone"] = str(payload.get("phone") or "").strip()
        if "email" in payload:
            item["email"] = str(payload.get("email") or "").strip()
        if "address" in payload:
            item["address"] = str(payload.get("address") or "").strip()
        if "password" in payload:
            item["password"] = str(payload.get("password") or "").strip()

        item["updated_at"] = _now_iso()
        items[idx] = item
        data["items"] = items
        self._save(data)
        return item

    def delete(self, emp_id: str) -> None:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            return
        data["items"] = [x for x in items if not (isinstance(x, dict) and str(x.get("id")) == str(emp_id))]
        self._save(data)
