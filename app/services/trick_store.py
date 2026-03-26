# app/services/trick_store.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

PENDING_PATH = DATA_DIR / "tricks_pending.json"
APPROVED_PATH = DATA_DIR / "tricks_approved.json"


def _ensure_file(path: Path) -> None:
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
        return
    # If file exists but empty/corrupt, reset to []
    try:
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            path.write_text("[]", encoding="utf-8")
        else:
            json.loads(txt)
    except Exception:
        path.write_text("[]", encoding="utf-8")


def _load(path: Path) -> List[Dict[str, Any]]:
    _ensure_file(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: List[Dict[str, Any]]) -> None:
    _ensure_file(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_pending() -> List[Dict[str, Any]]:
    return _load(PENDING_PATH)


def find_best_approved_for_query(query: str):
    """
    Simple exact/contains match for now.
    Later we can do fuzzy similarity or TF-IDF on approved tricks too.
    """
    q = (query or "").strip().lower()
    if not q:
        return None

    approved = get_approved()
    if not approved:
        return None

    # Exact match first
    for t in approved:
        if str(t.get("problem", "")).strip().lower() == q:
            t2 = dict(t)
            t2["type"] = "approved_trick"
            t2["label"] = "Trick of the Trade (Approved)"
            t2["match_similarity"] = 1.0
            return t2

    # Contains match next
    for t in approved:
        p = str(t.get("problem", "")).strip().lower()
        if p and (p in q or q in p):
            t2 = dict(t)
            t2["type"] = "approved_trick"
            t2["label"] = "Trick of the Trade (Approved)"
            t2["match_similarity"] = 0.7
            return t2

    return None


def get_approved() -> List[Dict[str, Any]]:
    return _load(APPROVED_PATH)


def add_pending(trick: Dict[str, Any]) -> Dict[str, Any]:
    pending = _load(PENDING_PATH)

    # normalize fields so KeyError never happens
    normalized = {
        "id": str(trick.get("id") or ""),
        "title": str(trick.get("title") or "Trick of the Trade"),
        "problem": str(trick.get("problem") or "").strip(),
        "recommendation": str(trick.get("recommendation") or "").strip(),
        "confidence": float(trick.get("confidence") or 0.0),
        "confidence_pct": int(trick.get("confidence_pct") or 0),
        "frequency": int(trick.get("frequency") or 0),
        "source_query": str(trick.get("source_query") or "").strip(),
        "created_at": str(trick.get("created_at") or ""),
        "status": "pending",
    }

    if not normalized["problem"]:
        return {"ok": False, "error": "Missing problem"}

    # If no id provided, create one
    if not normalized["id"]:
        normalized["id"] = str(len(pending) + 1)

    # de-dupe by problem text
    for t in pending:
        if str(t.get("problem") or "").strip().lower() == normalized["problem"].lower():
            return {"ok": True, "message": "Already pending", "id": t.get("id")}

    pending.append(normalized)
    _save(PENDING_PATH, pending)
    return {"ok": True, "message": "Added to pending", "id": normalized["id"]}


def approve_pending(pending_id: str) -> Dict[str, Any]:
    pending = _load(PENDING_PATH)
    approved = _load(APPROVED_PATH)

    keep = []
    moved = None
    for t in pending:
        if str(t.get("id")) == str(pending_id):
            moved = t
        else:
            keep.append(t)

    if not moved:
        return {"ok": False, "error": "Pending id not found"}

    moved["status"] = "approved"
    approved.append(moved)

    _save(PENDING_PATH, keep)
    _save(APPROVED_PATH, approved)
    return {"ok": True, "message": "Approved", "id": pending_id}


def reject_pending(pending_id: str, reason: str = "") -> Dict[str, Any]:
    pending = _load(PENDING_PATH)

    keep = []
    found = False
    for t in pending:
        if str(t.get("id")) == str(pending_id):
            found = True
            continue
        keep.append(t)

    if not found:
        return {"ok": False, "error": "Pending id not found"}

    _save(PENDING_PATH, keep)
    return {"ok": True, "message": "Rejected", "id": pending_id, "reason": reason}

