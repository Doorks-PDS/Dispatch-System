from __future__ import annotations
 
import json
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
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
 
 
class TimeCardsStore:
    """
    Backend-persisted time cards.
    Saved to data/time_cards.json
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path = bootstrap_data_file(self.project_root, "time_cards.json")
        self._ensure()
 
    def _ensure(self) -> None:
        base = {"version": 1, "items": []}
        cur = _read_json(self.path, base)
        if not isinstance(cur, dict):
            cur = base
        cur.setdefault("version", 1)
        cur.setdefault("items", [])
        _write_json(self.path, cur)
 
    def list(self, technician: Optional[str] = None, month: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
 
        out = items[:]
        if technician:
            t = technician.strip().lower()
            out = [x for x in out if t in str(x.get("technician_name", "")).lower()]
 
        # month = "YYYY-MM"
        if month:
            out = [x for x in out if str(x.get("date", "")).startswith(month)]
 
        out.sort(key=lambda x: str(x.get("date", "")) + str(x.get("created_at", "")), reverse=True)
        return out[: max(1, min(int(limit), 2000))]
 
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
            data["items"] = items
 
        item = {
            "id": uuid.uuid4().hex,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
 
            "technician_name": str(payload.get("technician_name") or "").strip(),
            "date": str(payload.get("date") or "").strip(),  # YYYY-MM-DD
            "start_time": str(payload.get("start_time") or "").strip(),  # HH:MM
            "end_time": str(payload.get("end_time") or "").strip(),      # HH:MM
 
            "lunch_taken": bool(payload.get("lunch_taken", False)),
            "lunch_start": str(payload.get("lunch_start") or "").strip(),
            "lunch_end": str(payload.get("lunch_end") or "").strip(),
 
            "notes": str(payload.get("notes") or "").strip(),
            "supervisor_approved": bool(payload.get("supervisor_approved", False)),
            "supervisor_approved_at": str(payload.get("supervisor_approved_at") or "").strip(),
        }
 
        items.append(item)
        data["items"] = items
        _write_json(self.path, data)
        return item
 
    def update(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
            data["items"] = items
        for i, existing in enumerate(items):
            if str(existing.get("id")) == str(item_id):
                merged = dict(existing)
                merged.update({
                    "updated_at": _now_iso(),
                    "technician_name": str(payload.get("technician_name") or existing.get("technician_name") or "").strip(),
                    "date": str(payload.get("date") or existing.get("date") or "").strip(),
                    "start_time": str(payload.get("start_time") or existing.get("start_time") or "").strip(),
                    "end_time": str(payload.get("end_time") or existing.get("end_time") or "").strip(),
                    "lunch_taken": bool(payload.get("lunch_taken", existing.get("lunch_taken", False))),
                    "lunch_start": str(payload.get("lunch_start") or existing.get("lunch_start") or "").strip(),
                    "lunch_end": str(payload.get("lunch_end") or existing.get("lunch_end") or "").strip(),
                    "notes": str(payload.get("notes") or existing.get("notes") or "").strip(),
                    "supervisor_approved": bool(payload.get("supervisor_approved", existing.get("supervisor_approved", False))),
                    "supervisor_approved_at": str(payload.get("supervisor_approved_at") or existing.get("supervisor_approved_at") or "").strip(),
                })
                items[i] = merged
                _write_json(self.path, data)
                return merged
        return self.create(payload)

    def delete(self, item_id: str) -> None:
        self._ensure()
        data = _read_json(self.path, {"items": []})
        items = data.get("items", [])
        if not isinstance(items, list):
            return
        data["items"] = [x for x in items if str(x.get("id")) != item_id]
        _write_json(self.path, data)
