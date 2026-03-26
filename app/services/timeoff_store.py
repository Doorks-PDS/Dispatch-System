from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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


@dataclass
class TimeOffStore:
    project_root: Path | str

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        self.path = self.project_root / "data" / "timeoff_requests.json"
        self._ensure()

    def _ensure(self) -> None:
        base = {"version": 1, "items": []}
        cur = _read_json(self.path, base)
        if not isinstance(cur, dict):
            cur = base
        if not isinstance(cur.get("items"), list):
            cur["items"] = []
        cur.setdefault("version", 1)
        _write_json(self.path, cur)

    def _load(self) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"version": 1, "items": []})
        if not isinstance(data, dict):
            data = {"version": 1, "items": []}
        if not isinstance(data.get("items"), list):
            data["items"] = []
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        _write_json(self.path, data)

    def list_items(self, employee_name: str = "", status: str = "", limit: int = 500) -> List[Dict[str, Any]]:
        items = self._load().get("items", [])
        out: List[Dict[str, Any]] = []
        emp = employee_name.strip().lower()
        stat = status.strip().lower()
        for item in items:
            if not isinstance(item, dict):
                continue
            if emp and emp not in str(item.get("employee_name") or "").lower():
                continue
            if stat and stat != str(item.get("status") or "").lower():
                continue
            out.append(item)
        out.sort(key=lambda x: (1 if x.get("emergency") else 0, str(x.get("start_date") or ""), str(x.get("created_at") or "")), reverse=True)
        return out[: max(1, min(limit, 5000))]

    def create_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        item = {
            "id": uuid.uuid4().hex[:12],
            "employee_name": str(payload.get("employee_name") or "").strip(),
            "start_date": str(payload.get("start_date") or "").strip(),
            "end_date": str(payload.get("end_date") or payload.get("start_date") or "").strip(),
            "notes": str(payload.get("notes") or "").strip(),
            "emergency": bool(payload.get("emergency", False)),
            "status": str(payload.get("status") or "pending").strip().lower() or "pending",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data["items"].append(item)
        self._save(data)
        return item

    def update_item(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        items = data.get("items", [])
        for idx, item in enumerate(items):
            if str(item.get("id") or "") != str(item_id):
                continue
            updated = dict(item)
            for key in ["employee_name", "start_date", "end_date", "notes", "status"]:
                if key in payload and payload[key] is not None:
                    updated[key] = str(payload[key]).strip()
            if "emergency" in payload and payload["emergency"] is not None:
                updated["emergency"] = bool(payload["emergency"])
            updated["status"] = str(updated.get("status") or "pending").lower()
            updated["updated_at"] = _now_iso()
            items[idx] = updated
            data["items"] = items
            self._save(data)
            return updated
        raise KeyError("Time off request not found")

    def delete_item(self, item_id: str) -> None:
        data = self._load()
        items = data.get("items", [])
        kept = [x for x in items if str(x.get("id") or "") != str(item_id)]
        if len(kept) == len(items):
            raise KeyError("Time off request not found")
        data["items"] = kept
        self._save(data)
