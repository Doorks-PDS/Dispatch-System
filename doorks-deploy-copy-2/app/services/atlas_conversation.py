from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _clean(x: Any) -> str:
    return ("" if x is None else str(x)).strip()


def build_intake_from_text(text: str) -> Dict[str, str]:
    """
    Lightweight extraction to keep follow-ups on-topic.
    You can expand this over time.
    """
    t = (text or "").lower()

    intake: Dict[str, str] = {}

    # Manufacturer
    if "stanley" in t:
        intake["manufacturer"] = "Stanley"
    if "record" in t and "record 8100" in t:
        intake["manufacturer"] = "Record"
        intake["model"] = "8100"
    if "bea" in t:
        intake["manufacturer"] = "BEA"

    # Models
    if "mc521" in t:
        intake["model"] = "MC521"
    if "ixio" in t:
        intake["model"] = "IXIO"

    # Equipment type hints
    if any(k in t for k in ["automatic slider", "automatic sliding", "sliding door", "single slider"]):
        intake["equipment_type"] = "automatic sliding door"
    if any(k in t for k in ["automatic swing", "swing operator"]):
        intake["equipment_type"] = "automatic swing door"
    if any(k in t for k in ["roll up", "roll-up", "coiling", "rolling steel", "rsd", "security gate"]):
        intake["equipment_type"] = "roll-up / security gate"
    if "maglock" in t or "mag lock" in t:
        intake["equipment_type"] = "maglock"

    # Symptom shaping
    # If user explicitly says "no binding" etc., that’s valuable context, not a full symptom.
    if "sensor" in t and any(k in t for k in ["not working", "not work", "dead", "bad", "no detect", "won't detect", "won’t detect"]):
        intake["symptom"] = "automatic door sensor not working"

    if ("ixio" in t) and any(k in t for k in ["has power", "powered"]) and any(k in t for k in ["won't pickup", "won’t pick up", "won't detect", "won’t detect", "not picking up"]):
        intake["symptom"] = "BEA IXIO has power but not detecting people"

    if "maglock" in t and any(k in t for k in ["won't lock", "won’t lock", "not locking", "not lock", "every time", "intermittent"]):
        intake["symptom"] = "maglock intermittent bonding"

    if "roll up" in t and any(k in t for k in ["not staying up", "won't stay up", "won’t stay up", "falls", "drops"]):
        intake["symptom"] = "roll-up door not staying up"

    if "security gate" in t and any(k in t for k in ["stuck closed", "won't open", "won’t open"]):
        intake["symptom"] = "security gate stuck closed"

    # Observed code like ".6"
    m = re.search(r"\b(showing|shows|display)\s*([0-9]*\.[0-9]+)\b", t)
    if m:
        intake["observed"] = f"display shows {m.group(2)}"

    return intake


class AtlasConversations:
    def __init__(self, threads_path: str, ratings_path: str):
        self.threads_path = Path(threads_path)
        self.ratings_path = Path(ratings_path)
        self.threads_path.parent.mkdir(parents=True, exist_ok=True)
        self.ratings_path.parent.mkdir(parents=True, exist_ok=True)

        self.threads: Dict[str, Dict[str, Any]] = {}

    def load(self) -> None:
        if self.threads_path.exists():
            try:
                self.threads = json.loads(self.threads_path.read_text(encoding="utf-8"))
            except Exception:
                self.threads = {}
        else:
            self.threads = {}

    def save(self) -> None:
        self.threads_path.write_text(json.dumps(self.threads, ensure_ascii=False, indent=2), encoding="utf-8")

    def count_threads(self) -> int:
        return len(self.threads)

    def new_thread_id(self) -> str:
        return uuid.uuid4().hex

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        return self.threads.get(thread_id)

    def set_intake(self, thread_id: str, intake: Dict[str, Any]) -> None:
        th = self.threads.setdefault(thread_id, {"messages": [], "intake": {}, "created_ts": int(time.time())})
        th["intake"] = intake or {}
        th["updated_ts"] = int(time.time())

    def append_message(self, thread_id: str, role: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        th = self.threads.setdefault(thread_id, {"messages": [], "intake": {}, "created_ts": int(time.time())})
        th["messages"].append({
            "ts": int(time.time()),
            "role": role,
            "text": text,
            "meta": meta or {},
        })
        th["updated_ts"] = int(time.time())

    def thread_summary(self, thread_id: str, max_messages: int = 6) -> str:
        th = self.threads.get(thread_id)
        if not th:
            return ""
        msgs = th.get("messages") or []
        tail = msgs[-max_messages:]
        # Keep this short to avoid polluting prompt
        bits = []
        for m in tail:
            role = m.get("role")
            text = _clean(m.get("text"))
            if not text:
                continue
            if role == "user":
                bits.append(f"User: {text[:160]}")
            elif role == "atlas":
                # only keep a small slice of Atlas reply
                bits.append(f"Atlas: {text[:160]}")
        return " | ".join(bits)

    def _find_last_atlas_message(self, thread_id: str) -> Optional[Dict[str, Any]]:
        th = self.threads.get(thread_id)
        if not th:
            return None
        msgs = th.get("messages") or []
        for m in reversed(msgs):
            if m.get("role") == "atlas":
                return m
        return None

    def rate_last_atlas_answer(self, thread_id: str, rating: str, note: str = "") -> bool:
        last = self._find_last_atlas_message(thread_id)
        if not last:
            return False

        record = {
            "ts": int(time.time()),
            "thread_id": thread_id,
            "rating": rating,
            "note": note,
            "query": (last.get("meta") or {}).get("query"),
            "symptom_class": ((last.get("meta") or {}).get("meta") or {}).get("symptom_class"),
        }

        # Append JSONL
        with self.ratings_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # also store in-memory on that message for UI if needed
        last.setdefault("meta", {})
        last["meta"]["rating"] = rating
        if note:
            last["meta"]["rating_note"] = note
        return True

