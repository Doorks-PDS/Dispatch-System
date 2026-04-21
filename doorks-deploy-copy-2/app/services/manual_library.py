# doorks/app/services/manual_library.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.storage import first_existing_data_path


_PROJ = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_PATHS = [
    Path(os.getenv("ATLAS_MANUAL_INDEX", "")).expanduser() if os.getenv("ATLAS_MANUAL_INDEX") else None,
    first_existing_data_path(_PROJ, "manual_index.json"),
    Path(__file__).resolve().parent / "manual_index.json",
]


def _first_existing(paths: List[Optional[Path]]) -> Optional[Path]:
    for p in paths:
        if not p:
            continue
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s\-\_\/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _tokens(s: str) -> List[str]:
    t = _norm(s)
    parts = [p for p in t.split() if len(p) >= 2]
    return parts


def _score(query: str, entry: Dict[str, Any]) -> float:
    """
    Lightweight relevance score:
    - match any alias strongly
    - token overlap for manufacturer/model keywords
    """
    qn = _norm(query)
    qtok = set(_tokens(qn))
    if not qtok:
        return 0.0

    aliases = entry.get("aliases") or []
    for a in aliases:
        if a and _norm(a) in qn:
            return 10.0  # hard hit

    # base overlap score
    etok = set(_tokens(" ".join([
        str(entry.get("manufacturer", "")),
        str(entry.get("product", "")),
        str(entry.get("model", "")),
        " ".join(entry.get("tags") or []),
        " ".join(entry.get("aliases") or []),
    ])))
    if not etok:
        return 0.0

    inter = len(qtok & etok)
    if inter == 0:
        return 0.0

    # boost if model token is present exactly
    model = _norm(str(entry.get("model", "")))
    if model and model in qn:
        return 6.0 + inter

    return float(inter)


@dataclass
class ManualRef:
    id: str
    title: str
    url: str
    manufacturer: str
    product: str
    model: str
    doc_type: str
    tags: List[str]
    locators: Dict[str, str]


class ManualLibrary:
    def __init__(self, index_path: Optional[Path] = None) -> None:
        self.index_path = index_path or _first_existing(DEFAULT_INDEX_PATHS)
        self._items: List[Dict[str, Any]] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.index_path:
            self._items = []
            return
        try:
            raw = self.index_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict) and "items" in data:
                data = data["items"]
            self._items = data if isinstance(data, list) else []
        except Exception:
            self._items = []

    def search(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        self.load()
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for it in self._items:
            try:
                s = _score(query, it)
            except Exception:
                s = 0.0
            if s > 0:
                scored.append((s, it))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: List[Dict[str, Any]] = []
        for s, it in scored[: max(0, limit)]:
            out.append({
                "id": it.get("id", ""),
                "title": it.get("title", it.get("model", "Manual")),
                "url": it.get("url", ""),
                "manufacturer": it.get("manufacturer", ""),
                "product": it.get("product", ""),
                "model": it.get("model", ""),
                "doc_type": it.get("doc_type", ""),
                "tags": it.get("tags", []) or [],
                "locators": it.get("locators", {}) or {},
                "_score": s,
            })
        return out


# Singleton helper
_manuals = ManualLibrary()


def search_manuals(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    return _manuals.search(query, limit=limit)
