from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _clean(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip()


def _join_list(x: Any) -> str:
    if isinstance(x, list):
        return " ".join(_clean(i) for i in x if _clean(i))
    return _clean(x)


def _case_text(case: Dict[str, Any]) -> str:
    # What we embed/search against
    parts = [
        _clean(case.get("query")),
        _clean(case.get("equipment_type")),
        _clean(case.get("manufacturer")),
        _clean(case.get("model")),
        _clean(case.get("symptom")),
        _clean(case.get("observed")),
        _clean(case.get("root_cause")),
        _clean(case.get("fix_summary")),
        _join_list(case.get("steps")),
        _join_list(case.get("parts_used")),
        _join_list(case.get("tags")),
    ]
    return " | ".join(p for p in parts if p)


class AtlasMemory:
    """
    Simple “living” memory:
    - persists cases in JSONL
    - builds TF-IDF index on load/append
    - retrieves similar cases by cosine similarity
    """

    def __init__(self, jsonl_path: str):
        self.path = Path(jsonl_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.cases: List[Dict[str, Any]] = []
        self._vec: Optional[TfidfVectorizer] = None
        self._mat = None  # TF-IDF matrix

    def count(self) -> int:
        return len(self.cases)

    def load(self) -> None:
        self.cases = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    self.cases.append(json.loads(line))
                except Exception:
                    continue
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        texts = [_case_text(c) for c in self.cases]
        if not texts:
            self._vec = None
            self._mat = None
            return
        self._vec = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=50000,
        )
        self._mat = self._vec.fit_transform(texts)

    def add_case(self, payload: Dict[str, Any]) -> str:
        case_id = payload.get("case_id") or uuid.uuid4().hex

        case = {
            "case_id": case_id,
            "ts": int(time.time()),
            "query": _clean(payload.get("query")),
            "equipment_type": _clean(payload.get("equipment_type")),
            "manufacturer": _clean(payload.get("manufacturer")),
            "model": _clean(payload.get("model")),
            "symptom": _clean(payload.get("symptom")),
            "observed": _clean(payload.get("observed")),
            "root_cause": _clean(payload.get("root_cause")),
            "fix_summary": _clean(payload.get("fix_summary")),
            "steps": payload.get("steps") if isinstance(payload.get("steps"), list) else [],
            "parts_used": payload.get("parts_used") if isinstance(payload.get("parts_used"), list) else [],
            "docs_used": payload.get("docs_used") if isinstance(payload.get("docs_used"), list) else [],
            "confidence": payload.get("confidence"),
            "tags": payload.get("tags") if isinstance(payload.get("tags"), list) else [],
        }

        # Append to disk
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

        # Update memory in RAM and rebuild index (simple + reliable)
        self.cases.append(case)
        self._rebuild_index()
        return case_id

    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        q = _clean(query)
        if not q or not self.cases or self._vec is None or self._mat is None:
            return []

        q_vec = self._vec.transform([q])
        sims = cosine_similarity(q_vec, self._mat)[0]  # shape: (n_cases,)
        idxs = sims.argsort()[::-1][: max(0, k * 3)]  # take more then filter

        out: List[Dict[str, Any]] = []
        for i in idxs:
            score = float(sims[i])
            if score < 0.10:
                continue
            c = dict(self.cases[i])
            c["similarity"] = round(score, 4)
            # return a short version
            out.append({
                "case_id": c.get("case_id"),
                "similarity": c.get("similarity"),
                "manufacturer": c.get("manufacturer"),
                "model": c.get("model"),
                "symptom": c.get("symptom"),
                "observed": c.get("observed"),
                "root_cause": c.get("root_cause"),
                "fix_summary": c.get("fix_summary"),
                "parts_used": c.get("parts_used") or [],
                "docs_used": c.get("docs_used") or [],
                "tags": c.get("tags") or [],
            })
            if len(out) >= k:
                break
        return out

