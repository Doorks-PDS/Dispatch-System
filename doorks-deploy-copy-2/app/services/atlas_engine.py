from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

from app.services.atlas_search import search_tech_notes
from app.services.llm_assist import (
    classify_intent,
    generate_structured_answer,
    render_answer_text,
)
from app.services.web_refs import find_references_for_query


def _short_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


class AtlasEngine:
    def __init__(self, project_root: Optional[str] = None, **_ignored: Any) -> None:
        self.started_at = time.time()
        self.project_root = project_root

    def answer(
        self,
        q: str,
        mode: str = "tech",
        session_id: Optional[str] = None,
        top_k: int = 6,
        web_results: int = 6,
        include_sources: bool = False,
        debug: bool = False,
        **_ignored: Any,
    ) -> Dict[str, Any]:
        q = (q or "").strip()
        conversation_id = _short_id((session_id or "session:none") + "|c|" + q + "|" + str(time.time())[:8])
        message_id = _short_id(q + "|" + str(time.time()))

        intent = classify_intent(q)

        matches = search_tech_notes(q, top_k=top_k)
        refs = find_references_for_query(q, limit=web_results)

        out_json = generate_structured_answer(
            q=q,
            mode=mode,
            intent=intent,
            tech_matches=matches,
            references=refs,
        )

        answer_text = render_answer_text(out_json)

        resp: Dict[str, Any] = {
            "ok": True,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "query": q,
            "mode": mode,
            "intent": intent,
            "answer_md": answer_text,
            "answer_json": out_json,
        }

        if include_sources:
            resp["sources"] = (out_json.get("manuals") or []) + (out_json.get("videos") or [])

        if debug:
            resp["debug"] = {
                "matches_count": len(matches),
                "refs_count": len(refs),
                "intent": intent,
                "confidence_pct": out_json.get("confidence_pct"),
            }

        return resp
