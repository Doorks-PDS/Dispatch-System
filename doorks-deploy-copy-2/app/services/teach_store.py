from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class TeachStore:
    """
    Disk-backed storage so Atlas can "learn" from techs.

    Files:
      data/atlas_learning/teach_rules.jsonl
      data/atlas_learning/teach_cases.jsonl
      data/atlas_learning/ratings.jsonl
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.rules_path = self.data_dir / "teach_rules.jsonl"
        self.cases_path = self.data_dir / "teach_cases.jsonl"
        self.ratings_path = self.data_dir / "ratings.jsonl"

        for p in [self.rules_path, self.cases_path, self.ratings_path]:
            if not p.exists():
                p.write_text("", encoding="utf-8")

    def _append_jsonl(self, path: Path, obj: Dict[str, Any]) -> None:
        obj = dict(obj)
        obj.setdefault("ts", int(time.time()))
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def save_teach(self, payload: Dict[str, Any]) -> None:
        t = (payload.get("type") or "").strip().lower()
        if t not in ("rule", "case"):
            t = "rule"

        entry = {
            "type": t,
            "title": (payload.get("title") or "").strip(),
            "trigger": (payload.get("trigger") or "").strip(),
            "content": (payload.get("content") or "").strip(),
            "equipment_type": (payload.get("equipment_type") or "").strip(),
            "manufacturer": (payload.get("manufacturer") or "").strip(),
            "model": (payload.get("model") or "").strip(),
        }

        if t == "case":
            self._append_jsonl(self.cases_path, entry)
        else:
            self._append_jsonl(self.rules_path, entry)

    def save_rating(self, payload: Dict[str, Any]) -> None:
        entry = {
            "thread_id": (payload.get("thread_id") or "").strip(),
            "message_id": (payload.get("message_id") or "").strip(),
            "rating": int(payload.get("rating") or 0),
            "note": (payload.get("note") or "").strip(),
        }
        self._append_jsonl(self.ratings_path, entry)

    def _read_jsonl(self, path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not path.exists():
            return out
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        if limit is not None:
            return out[-limit:]
        return out

    def get_rules(self, limit: int = 500) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.rules_path, limit=limit)

    def get_cases(self, limit: int = 500) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.cases_path, limit=limit)

