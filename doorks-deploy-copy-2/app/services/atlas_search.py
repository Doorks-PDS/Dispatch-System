from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List

from app.services.storage import first_existing_data_path

@dataclass
class TechMatch:
    type: str
    score: float
    record: Dict[str, Any]

def _similarity(a: str, b: str) -> float:
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def _default_notes_csv_candidates() -> List[Path]:
    env = os.getenv("ATLAS_TECH_NOTES_CSV")
    cands: List[Path] = []
    if env:
        cands.append(Path(env).expanduser().resolve())

    here = Path(__file__).resolve()
    proj = here.parents[2]
    cands += [
        first_existing_data_path(proj, "tech_notes.csv"),
        first_existing_data_path(proj, "tech_notes_export.csv"),
    ]
    return cands

def _load_notes() -> List[Dict[str, Any]]:
    for p in _default_notes_csv_candidates():
        if p.exists():
            rows: List[Dict[str, Any]] = []
            with p.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(dict(r))
            return rows
    return []

def search_tech_notes(q: str, top_k: int = 6) -> List[Dict[str, Any]]:
    """
    Returns a list of dicts shaped like your previous output:
      { type, score, record }
    """
    notes = _load_notes()
    if not notes:
        return []

    scored: List[TechMatch] = []
    for r in notes:
        blob = " | ".join(
            str(r.get(k, "") or "")
            for k in [
                "Description Of Problem",
                "Job - Work Performed",
                "Additional Repairs Needed/Recommended",
                "Material Used",
                "notes",
            ]
        )
        s = _similarity(q, blob)
        if s > 0:
            scored.append(TechMatch(type="note_match", score=s, record=r))

    scored.sort(key=lambda x: x.score, reverse=True)
    return [{"type": m.type, "score": m.score, "record": m.record} for m in scored[:top_k]]
