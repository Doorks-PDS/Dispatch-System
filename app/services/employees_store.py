from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.storage import bootstrap_data_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, indent=2, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


class EmployeesStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path = bootstrap_data_file(self.project_root, "employees.json")
        self._ensure()

    def _ensure(self) -> None:
        base = {"version": 1, "items": []}
        cur = _read_json(self.path, base)
        if not isinstance(cur, dict):
            cur = base
        cur.setdefault("version", 1)
        cur.setdefault("items", [])
        _write_json(self.path, cur)

    def _load(self) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"version": 1, "items": []})
        if not isinstance(data, dict):
            data = {"version": 1, "items": []}
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
        data["items"] = items
        return data

    def _find_index(self, items: List[Dict[str, Any]], emp_id: str) -> int:
        for idx, item in enumerate(items):
            if isinstance(item, dict) and str(item.get("id") or "") == str(emp_id):
                return idx
        return -1

    def list(self) -> List[Dict[str, Any]]:
        data = self._load()
        items = data.get("items", [])
        return sorted(items, key=lambda x: str(x.get("name", "")).lower())

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        items = data.get("items", [])

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Missing employee name")

        item = {
            "id": uuid.uuid4().hex,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "name": name,
            "role": (str(payload.get("role") or "tech").strip() or "tech"),
            "phone": str(payload.get("phone") or "").strip(),
            "email": str(payload.get("email") or "").strip(),
            "address": str(payload.get("address") or "").strip(),
            "password": str(payload.get("password") or "").strip(),
        }

        items.append(item)
        data["items"] = items
        _write_json(self.path, data)
        return item

    def update(self, emp_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = self._load()
        items = data.get("items", [])
        idx = self._find_index(items, emp_id)
        if idx < 0:
            return None

        item = items[idx]
        if "name" in payload and payload.get("name") is not None:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValueError("Missing employee name")
            item["name"] = name
        if "role" in payload and payload.get("role") is not None:
            item["role"] = str(payload.get("role") or "tech").strip() or "tech"
        if "phone" in payload and payload.get("phone") is not None:
            item["phone"] = str(payload.get("phone") or "").strip()
        if "email" in payload and payload.get("email") is not None:
            item["email"] = str(payload.get("email") or "").strip()
        if "address" in payload and payload.get("address") is not None:
            item["address"] = str(payload.get("address") or "").strip()
        item["updated_at"] = _now_iso()

        items[idx] = item
        data["items"] = items
        _write_json(self.path, data)
        return item

    def delete(self, emp_id: str) -> None:
        data = self._load()
        items = data.get("items", [])
        data["items"] = [x for x in items if str(x.get("id")) != emp_id]
        _write_json(self.path, data)
