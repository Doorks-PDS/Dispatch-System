from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


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

    def list(self) -> List[Dict[str, Any]]:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        return sorted(items, key=lambda x: str(x.get("name", "")).lower())

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"items": []})
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

    def delete(self, emp_id: str) -> None:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            return
        data["items"] = [x for x in items if str(x.get("id")) != emp_id]
        _write_json(self.path, data)
