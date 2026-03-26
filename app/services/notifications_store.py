from __future__ import annotations

import json
import uuid
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


class NotificationsStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path = self.project_root / "data" / "notifications.json"
        self._ensure()

    def _ensure(self) -> None:
        base = {"version": 2, "items": []}
        cur = _read_json(self.path, base)
        if not isinstance(cur, dict):
            cur = base
        cur.setdefault("version", 2)
        if not isinstance(cur.get("items"), list):
            cur["items"] = []
        _write_json(self.path, cur)

    def _load(self) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.path, {"version": 2, "items": []})
        if not isinstance(data, dict):
            return {"version": 2, "items": []}
        if not isinstance(data.get("items"), list):
            data["items"] = []
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        _write_json(self.path, data)

    def _viewer_keys(self, viewer: Optional[Dict[str, Any]]) -> List[str]:
        if not viewer:
            return []
        keys = []
        for raw in [viewer.get("id"), viewer.get("username"), viewer.get("name"), viewer.get("email")]:
            val = str(raw or "").strip().lower()
            if val:
                keys.append(val)
        return keys

    def _recipient_matches(self, item: Dict[str, Any], viewer: Optional[Dict[str, Any]]) -> bool:
        if not viewer:
            return True
        to_val = str(item.get("to") or "").strip().lower()
        if not to_val or to_val in {"__all__", "all", "broadcast"}:
            return True
        return to_val in set(self._viewer_keys(viewer))

    def _is_sender(self, item: Dict[str, Any], viewer: Optional[Dict[str, Any]]) -> bool:
        if not viewer:
            return False
        sender = str(item.get("from") or "").strip().lower()
        return sender in set(self._viewer_keys(viewer))

    def _normalize(self, item: Dict[str, Any], viewer: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        out = dict(item)
        out.setdefault("kind", "broadcast" if not str(out.get("to") or "").strip() or str(out.get("to") or "").strip() == "__ALL__" else "direct")
        out.setdefault("read_by", [])
        read_by = [str(x).strip().lower() for x in out.get("read_by", []) if str(x).strip()]
        out["read_by"] = read_by
        if viewer:
            keys = set(self._viewer_keys(viewer))
            out["is_mine"] = self._is_sender(out, viewer)
            out["read"] = bool(keys.intersection(read_by)) or bool(out["is_mine"])
        else:
            out["is_mine"] = False
            out["read"] = bool(out.get("read", False))
        return out

    def list(self, limit: int = 200) -> List[Dict[str, Any]]:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        items = sorted(items, key=lambda x: str(x.get("created_at", "")), reverse=True)
        return [self._normalize(x) for x in items[: max(1, min(int(limit), 1000))] if isinstance(x, dict)]

    def list_for(self, viewer: Dict[str, Any], limit: int = 200) -> List[Dict[str, Any]]:
        data = self._load()
        items = data.get("items", [])
        visible: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if self._recipient_matches(item, viewer) or self._is_sender(item, viewer):
                visible.append(self._normalize(item, viewer))
        visible.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return visible[: max(1, min(int(limit), 1000))]

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
            data["items"] = items

        to_raw = str(payload.get("to") or "").strip()
        kind = "broadcast" if not to_raw or to_raw == "__ALL__" else "direct"
        item = {
            "id": uuid.uuid4().hex,
            "created_at": _now_iso(),
            "from": str(payload.get("from") or "").strip(),
            "from_name": str(payload.get("from_name") or "").strip(),
            "to": "__ALL__" if kind == "broadcast" else to_raw,
            "to_name": str(payload.get("to_name") or "").strip(),
            "kind": kind,
            "message": str(payload.get("message") or "").strip(),
            "read_by": [str(payload.get("from") or "").strip().lower()] if str(payload.get("from") or "").strip() else [],
        }
        items.append(item)
        self._save(data)
        return self._normalize(item)

    def mark_read(self, notif_id: str, viewer: Dict[str, Any], read: bool = True) -> Dict[str, Any]:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            raise KeyError("Not found")
        keys = self._viewer_keys(viewer)
        for i, it in enumerate(items):
            if str(it.get("id")) == notif_id:
                if not self._recipient_matches(it, viewer) and not self._is_sender(it, viewer):
                    raise PermissionError("Forbidden")
                read_by = [str(x).strip().lower() for x in it.get("read_by", []) if str(x).strip()]
                for key in keys:
                    if read and key not in read_by:
                        read_by.append(key)
                    if not read and key in read_by:
                        read_by.remove(key)
                it["read_by"] = read_by
                items[i] = it
                data["items"] = items
                self._save(data)
                return self._normalize(it, viewer)
        raise KeyError("Not found")

    def delete(self, notif_id: str, viewer: Optional[Dict[str, Any]] = None, allow_admin: bool = False) -> None:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            return
        kept: List[Dict[str, Any]] = []
        found = False
        for it in items:
            if str(it.get("id")) != notif_id:
                kept.append(it)
                continue
            found = True
            if viewer and not allow_admin and not self._is_sender(it, viewer):
                raise PermissionError("Forbidden")
        if not found:
            raise KeyError("Not found")
        data["items"] = kept
        self._save(data)
