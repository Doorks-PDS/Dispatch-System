from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class LearningStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.feedback_path = self.base_dir / "feedback.jsonl"
        self.teach_path = self.base_dir / "teach.jsonl"

    def _append(self, path: Path, obj: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def save_feedback(
        self,
        conversation_id: str,
        message: str,
        answer_markdown: str,
        rating: int,
        notes: str = "",
    ) -> str:
        fid = str(uuid.uuid4())
        self._append(
            self.feedback_path,
            {
                "id": fid,
                "ts": int(time.time()),
                "conversation_id": conversation_id,
                "message": message,
                "answer_markdown": answer_markdown,
                "rating": rating,
                "notes": notes,
            },
        )
        return fid

    def save_teach(self, title: str, trigger: str, rule: str, tags: List[str]) -> str:
        tid = str(uuid.uuid4())
        self._append(
            self.teach_path,
            {
                "id": tid,
                "ts": int(time.time()),
                "title": title,
                "trigger": trigger,
                "rule": rule,
                "tags": tags,
            },
        )
        return tid

    def load_teach(self) -> List[Dict[str, Any]]:
        if not self.teach_path.exists():
            return []
        items: List[Dict[str, Any]] = []
        for line in self.teach_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
        return items

