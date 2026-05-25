from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

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
    _atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


class DocumentApprovalsStore:
    """Render-backed approval overrides for estimates not tied to calendar jobs."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.path = bootstrap_data_file(self.project_root, "document_approvals.json")
        self._lock = threading.RLock()
        self._ensure()

    def _base(self) -> Dict[str, Any]:
        return {"version": 1, "items": {}, "updated_at": _now_iso()}

    def _ensure(self) -> None:
        with self._lock:
            data = _read_json(self.path, self._base())
            if not isinstance(data, dict):
                data = self._base()
            if not isinstance(data.get("items"), dict):
                data["items"] = {}
            data.setdefault("version", 1)
            data.setdefault("updated_at", _now_iso())
            _write_json(self.path, data)

    def get_all(self) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, self._base())
        if not isinstance(data, dict):
            data = self._base()
        if not isinstance(data.get("items"), dict):
            data["items"] = {}
        return data

    def set_approval(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = str(key or "").strip()
        if not key:
            raise ValueError("Approval key is required")
        with self._lock:
            data = self.get_all()
            approved = bool(payload.get("approved"))
            item = {
                "key": key,
                "approved": approved,
                "approved_at": str(payload.get("approved_at") or (_now_iso() if approved else "")).strip(),
                "estimate_number": str(payload.get("estimate_number") or "").strip(),
                "filename": str(payload.get("filename") or "").strip(),
                "customer": str(payload.get("customer") or "").strip(),
                "updated_at": _now_iso(),
            }
            data["items"][key] = item
            data["updated_at"] = _now_iso()
            _write_json(self.path, data)
            return item
