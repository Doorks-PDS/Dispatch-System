from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import re


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s\-\_]+", " ", s)
    parts = [p for p in s.split() if len(p) > 2]
    return parts


def _overlap_score(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / max(1, len(ta))


@dataclass
class LearnedItem:
    kind: str  # "rule" or "feedback"
    text: str
    meta: Dict[str, Any]
    score: float = 0.0


class AtlasLearningStore:
    """
    Dead-simple “teach Atlas like ChatGPT”:
    - Store RULES (general “trick of trade”)
    - Store FEEDBACK (thumbs up/down + notes)
    - Retrieve relevant learned items by token overlap
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.rules_file = self.base_dir / "rules.jsonl"
        self.feedback_file = self.base_dir / "feedback.jsonl"

    def ensure_ready(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.rules_file.exists():
            self.rules_file.write_text("", encoding="utf-8")
        if not self.feedback_file.exists():
            self.feedback_file.write_text("", encoding="utf-8")

        # Seed playbooks only when rules.jsonl is empty
        try:
            if self.rules_file.exists() and self.rules_file.stat().st_size == 0:
                from app.services.atlas_playbooks import seed_rules_file
                seed_rules_file(self.rules_file)
        except Exception:
            # Never fail startup because of seeding
            pass

    def save_rule(self, title: str, rule: str, tags: Optional[List[str]] = None) -> None:
        rec = {
            "ts": _now_iso(),
            "title": title,
            "rule": rule,
            "tags": tags or [],
        }
        with self.rules_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def save_feedback(self, query: str, answer: str, rating: int, notes: str, meta: Optional[Dict[str, Any]] = None) -> None:
        rec = {
            "ts": _now_iso(),
            "query": query,
            "answer": answer,
            "rating": int(rating),
            "notes": notes,
            "meta": meta or {},
        }
        with self.feedback_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path, limit: int = 5000) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def find_relevant(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        rules = self._read_jsonl(self.rules_file)
        feedback = self._read_jsonl(self.feedback_file)

        items: List[LearnedItem] = []

        for r in rules:
            text = f"{r.get('title','')}\n{r.get('rule','')}".strip()
            score = _overlap_score(query, text)
            if score > 0:
                items.append(LearnedItem(kind="rule", text=text, meta=r, score=score))

        for fb in feedback:
            text = f"{fb.get('query','')}\n{fb.get('notes','')}\n{fb.get('answer','')}".strip()
            score = _overlap_score(query, text)
            if score > 0:
                rating = int(fb.get("rating", 0))
                if rating > 0:
                    score *= 1.25
                elif rating < 0:
                    score *= 0.75
                items.append(LearnedItem(kind="feedback", text=text, meta=fb, score=score))

        items.sort(key=lambda x: x.score, reverse=True)
        return [
            {
                "kind": it.kind,
                "score": round(it.score, 4),
                "text": it.text[:1200],
                "meta": {k: v for k, v in (it.meta or {}).items() if k not in ("answer",)},
            }
            for it in items[: max(0, k)]
        ]
