from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.openai_assist import call_openai_json

def classify_intent(q: str) -> str:
    t = (q or "").lower()
    if any(k in t for k in ["wire", "wiring", "terminal", "land on", "connect"]):
        return "wiring"
    if any(k in t for k in ["fis", "learn cycle", "learn", "program", "programming", "set limits", "setup", "configure"]):
        return "programming"
    if any(k in t for k in ["install", "commission", "teach in"]):
        return "setup"
    return "troubleshooting"


SAFETY_PATTERNS = [
    ("rolling steel", "Safety: Rolling steel springs store serious energy—use proper winding bars, keep your body out of the winding path, and clamp/secure the curtain before adjusting tension."),
    ("rsd", "Safety: Rolling steel springs store serious energy—use proper winding bars, keep your body out of the winding path, and clamp/secure the curtain before adjusting tension."),
    ("spring", "Safety: Springs store serious energy—use proper tools and secure the door before adjusting."),
    ("herculite", "Safety: Support the door before loosening pivots/patch hardware—glass can shift and crack."),
    ("glass", "Safety: Support the door before loosening pivots/patch hardware—glass can shift and crack."),
    ("wiring", "Safety: De-energize and verify power is off before touching wiring. Use lockout/tagout where required."),
    ("120v", "Safety: De-energize and verify power is off before touching wiring. Use lockout/tagout where required."),
    ("240v", "Safety: De-energize and verify power is off before touching wiring. Use lockout/tagout where required."),
]

def _auto_safety(q: str) -> Optional[str]:
    t = (q or "").lower()
    for key, msg in SAFETY_PATTERNS:
        if key in t:
            return msg
    return None

def _is_bad_reference(url: str) -> bool:
    u = (url or "").lower()
    return any(x in u for x in ["google.com/search", "bing.com/search", "duckduckgo.com/html", "duckduckgo.com/?q="])

def _normalize_steps(steps: List[str]) -> List[str]:
    cleaned: List[str] = []
    for s in steps or []:
        s = re.sub(r"^\s*(step\s*\d+:\s*)", "", s, flags=re.I).strip()
        s = re.sub(r"^\s*\d+\.\s*", "", s).strip()
        if s:
            cleaned.append(s)
    return cleaned


def generate_structured_answer(
    q: str,
    mode: str = "tech",
    intent: str = "troubleshooting",
    tech_matches: Optional[List[Dict[str, Any]]] = None,
    references: Optional[List[Dict[str, str]]] = None,
    **_ignored: Any,
) -> Dict[str, Any]:
    """
    Clean Doorks 3.0-ish output:
      - short answer (1–2 lines)
      - steps (numbered)
      - safety only if relevant
      - manuals/videos only if useful
      - at most ONE 'need' question (only if required)
    """
    references = references or []

    system = (
        "You are Atlas, a commercial door tech support assistant.\n"
        "Be direct. No section headers like Snapshot/Quick checks.\n"
        "No bold. No markdown.\n"
        "Output JSON only with:\n"
        "{answer, steps[], safety?, manuals[], videos[], need?, confidence_pct}\n"
        "Rules:\n"
        "- Do not invent manuals, terminal numbers, or button names.\n"
        "- Use provided references as manuals/videos.\n"
        "- Only ask ONE question if absolutely required for safe/accurate wiring/programming.\n"
    )

    user = {
        "q": q,
        "intent": intent,
        "references_found": references,
        "schema": {
            "answer": "string",
            "steps": ["string"],
            "safety": "optional",
            "manuals": [{"title": "string", "url": "string"}],
            "videos": [{"title": "string", "url": "string"}],
            "need": "optional single question",
            "confidence_pct": 0,
        },
    }

    out = call_openai_json(system_prompt=system, user_prompt=str(user))

    out.setdefault("answer", "")
    out.setdefault("steps", [])
    out.setdefault("safety", "")
    out.setdefault("manuals", [])
    out.setdefault("videos", [])
    out.setdefault("need", "")
    out.setdefault("confidence_pct", 75)

    out["steps"] = _normalize_steps(out.get("steps", []))

    # safety auto-fill if relevant
    if not (out.get("safety") or "").strip():
        s = _auto_safety(q)
        if s:
            out["safety"] = s

    # bucket refs into manuals/videos
    manuals: List[Dict[str, str]] = []
    videos: List[Dict[str, str]] = []
    for r in references[:10]:
        title = (r.get("title") or "").strip() or "Reference"
        url = (r.get("url") or "").strip()
        if not url or _is_bad_reference(url):
            continue
        if "youtube.com/results" in url or "youtu.be" in url:
            videos.append({"title": title, "url": url})
        else:
            manuals.append({"title": title, "url": url})

    out["manuals"] = manuals[:4]
    out["videos"] = videos[:2]

    # If programming/wiring and no manual found: keep shallow steps and ask one detail
    if intent in {"programming", "wiring", "setup"} and not out["manuals"]:
        out["steps"] = out["steps"][:3]
        if not (out.get("need") or "").strip():
            out["need"] = "What is the exact model/variant (label) and any add-on boards? That determines the correct diagram/menu."
        out["confidence_pct"] = min(int(out.get("confidence_pct", 65)), 60)

    # reduce over-questioning
    need = (out.get("need") or "").strip()
    if need:
        out["need"] = need.split("\n")[0].strip()

    return out


def render_answer_text(out: Dict[str, Any]) -> str:
    lines: List[str] = []

    ans = (out.get("answer") or "").strip()
    if ans:
        lines.append(ans)

    steps = out.get("steps") or []
    if steps:
        if lines:
            lines.append("")
        for i, s in enumerate(steps, 1):
            lines.append(f"{i}) {str(s).strip()}")

    safety = (out.get("safety") or "").strip()
    if safety:
        lines.append("")
        lines.append(safety)

    manuals = out.get("manuals") or []
    if manuals:
        lines.append("")
        lines.append("Manuals/Docs:")
        for m in manuals:
            lines.append(f"- {m.get('title','Manual')}: {m.get('url','')}")

    videos = out.get("videos") or []
    if videos:
        lines.append("")
        lines.append("Videos:")
        for v in videos:
            lines.append(f"- {v.get('title','Video')}: {v.get('url','')}")

    need = (out.get("need") or "").strip()
    if need:
        lines.append("")
        lines.append(f"Need: {need}")

    return "\n".join(lines).strip() + "\n"
