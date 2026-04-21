from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.atlas_engine import AtlasEngine
from app.services.moses_engine import MosesEngine
from app.services.forms_library import list_forms


def handle_chat(
    q: str,
    mode: str,
    conversation_id: Optional[str] = None,
    requester_role: str = "tech",  # "tech" or "office"
    project_root: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Central router:
      - tech mode -> AtlasEngine
      - office mode -> MosesEngine
    Returns the shape your UI/API expects.
    """
    q = (q or "").strip()
    mode = (mode or "").strip() or ("office" if requester_role == "office" else "tech")

    # Instantiate per-call so engines can safely load project_root, stores, etc.
    atlas_engine = AtlasEngine(project_root=project_root)
    moses_engine = MosesEngine(project_root=project_root)

    # Include forms list for UI; tech can see forms, office can see forms
    forms = list_forms(project_root) if project_root else []

    if mode == "office":
        m = moses_engine.answer(q=q, conversation_id=conversation_id)
        return {
            "ok": True,
            "conversation_id": conversation_id or "",
            "mode": "office",
            "intent": m.get("intent", "office"),
            "answer_md": (m.get("text") or "") + ("\n" if not str(m.get("text", "")).endswith("\n") else ""),
            "moses": m,
            "forms": forms,
        }

    # default to tech/atlas
    a = atlas_engine.answer(
        q=q,
        mode="tech",
        session_id=conversation_id,
        include_sources=kwargs.get("include_sources", False),
        debug=kwargs.get("debug", False),
    )
    return {
        "ok": True,
        "conversation_id": a.get("conversation_id", conversation_id or ""),
        "mode": "tech",
        "intent": a.get("intent", "tech"),
        "answer_md": a.get("answer_md", ""),
        "atlas": a.get("answer_json", {}),
        "forms": forms,
    }
