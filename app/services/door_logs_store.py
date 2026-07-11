from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.services.storage import get_writable_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DoorLogsStore:
    def __init__(self, project_root):
        self.path = get_writable_data_dir(project_root) / "door_logs.json"
        self._lock = threading.RLock()
        if not self.path.exists():
            self.save([])

    def load(self):
        with self._lock:
            try:
                data = json.loads(self.path.read_text())
            except Exception:
                data = []
            if not isinstance(data, list):
                data = []
            changed = False
            for item in data:
                if not isinstance(item, dict):
                    continue
                if not isinstance(item.get("history"), list):
                    item["history"] = []
                    changed = True
            if changed:
                self.save(data)
            return deepcopy(data)

    def save(self, data):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(self.path)

    def create(self, log):
        with self._lock:
            data = self.load()
            item = deepcopy(log or {})
            item["id"] = uuid4().hex
            item.setdefault("history", [])
            item.setdefault("created_at", _now_iso())
            item["updated_at"] = _now_iso()
            data.append(item)
            self.save(data)
            return deepcopy(item)

    def update(self, log_id, updates):
        with self._lock:
            data = self.load()
            updated = None
            for item in data:
                if item.get("id") == log_id:
                    original_history = item.get("history") if isinstance(item.get("history"), list) else []
                    item.update(deepcopy(updates or {}))
                    if "history" not in (updates or {}):
                        item["history"] = original_history
                    item["updated_at"] = _now_iso()
                    updated = deepcopy(item)
                    break
            if updated is None:
                raise KeyError(f"Door record not found: {log_id}")
            self.save(data)
            return updated

    def append_history(self, log_id, history_entry):
        with self._lock:
            data = self.load()
            updated = None
            for item in data:
                if item.get("id") != log_id:
                    continue
                history = item.get("history") if isinstance(item.get("history"), list) else []
                entry = deepcopy(history_entry or {})
                entry.setdefault("id", uuid4().hex)
                entry.setdefault("created_at", _now_iso())

                source_key = str(entry.get("source_key") or "").strip()
                duplicate = None
                if source_key:
                    duplicate = next((row for row in history if str(row.get("source_key") or "") == source_key), None)
                if duplicate is not None:
                    duplicate.update(entry)
                else:
                    history.append(entry)

                item["history"] = history
                item["updated_at"] = _now_iso()
                updated = deepcopy(item)
                break
            if updated is None:
                raise KeyError(f"Door record not found: {log_id}")
            self.save(data)
            return updated

    def delete(self, log_id):
        with self._lock:
            data = self.load()
            filtered = [item for item in data if item.get("id") != log_id]
            self.save(filtered)
