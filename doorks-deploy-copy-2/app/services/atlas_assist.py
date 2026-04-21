from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.learning_store import load_cases, load_rules

# ------------------------
# BASE (built-in) symptom rules
# ------------------------

BASE_SYMPTOM_RULES: List[Tuple[str, List[str]]] = [
    ("no power", ["no power", "dead", "blank", "nothing on", "no display", "not powering"]),
    ("won't open", ["will not open", "won't open", "not opening", "doesn't open", "stuck closed"]),
    ("stuck open", ["stuck open", "won't close", "not closing", "stays open"]),
    ("opening/closing repeatedly", ["opening and closing", "ghosting", "cycling", "opens by itself", "keeps opening"]),
    ("dragging/binding", ["dragging", "binding", "rubbing", "hitting threshold", "scraping"]),
    ("leaking oil", ["leaking", "oil", "hydraulic fluid", "closer leaking"]),
    ("no latch / not latching", ["won't latch", "not latching", "doesn't latch", "won't lock"]),
    ("sensor not working", ["sensor not working", "sensor", "motion", "presence", "beam", "photo eye", "ixio", "optex"]),
    ("maglock power/alignment", ["maglock", "armature", "bond", "lock every time", "no power"]),
    ("roll-up balance/tension", ["roll up", "roll-up", "rsd", "not staying up", "drops", "tension", "spring"]),
]

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def _keyword_hit(q: str, keywords: List[str]) -> bool:
    qn = _normalize(q)
    return any(k in qn for k in keywords)

def _load_learned_rules() -> List[Tuple[str, List[str]]]:
    """
    rules.jsonl entries can be:
      {"label":"obstruction code likely","keywords":["obstruction","rollers","guides","rough","bind"]}
    """
    out: List[Tuple[str, List[str]]] = []
    for r in load_rules(limit=300):
        label = (r.get("label") or "").strip()
        keywords = r.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords = [str(k).strip().lower() for k in keywords if str(k).strip()]
        if label and keywords:
            out.append((label, keywords))
    return out

def classify_equipment(query: str, intake: Dict[str, Any]) -> str:
    q = _normalize(query)
    # crude brand/model hints (extend with learning later)
    if "mc521" in q or "stanley" in q:
        return "Stanley / MC521"
    if "record 8100" in q or ("record" in q and "8100" in q):
        return "Record / 8100"
    if "bea" in q and "ixio" in q:
        return "BEA / IXIO"
    if "liftmaster" in q:
        return "LiftMaster (operator)"
    return (intake.get("equipment") or "").strip()

def classify_symptom(query: str, intake: Dict[str, Any]) -> str:
    q = (query or "").strip()
    if intake.get("symptom"):
        return str(intake["symptom"]).strip()

    # 1) learned rules first (so tech teaching wins)
    learned = _load_learned_rules()
    for label, keywords in learned:
        if _keyword_hit(q, keywords):
            return label

    # 2) built-in fallback
    for label, keywords in BASE_SYMPTOM_RULES:
        if _keyword_hit(q, keywords):
            return label

    return q.strip() or "unknown"

# ------------------------
# Recommendation builder
# ------------------------

def _dedupe_lines(lines: List[str], max_items: int) -> List[str]:
    seen = set()
    out = []
    for x in lines:
        x = (x or "").strip()
        if not x:
            continue
        k = _normalize(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
        if len(out) >= max_items:
            break
    return out

def _cases_memory_snippets(query: str, k: int = 4) -> List[str]:
    """
    Pull recent taught cases that are relevant by simple keyword overlap.
    case format:
      {"title":"MC521 ghosting solved by rollers", "keywords":["mc521","ghosting","rollers"], "answer":"..."}
    """
    qn = set(_normalize(query).split())
    snippets: List[str] = []
    for c in reversed(load_cases(limit=400)):
        kws = c.get("keywords") or []
        if isinstance(kws, str):
            kws = [kws]
        kws_set = set(_normalize(" ".join([str(x) for x in kws])).split())
        if not kws_set:
            continue
        if len(qn.intersection(kws_set)) == 0:
            continue
        title = (c.get("title") or "").strip()
        answer = (c.get("answer") or "").strip()
        if title and answer:
            snippets.append(f"{title}: {answer}")
        if len(snippets) >= k:
            break
    return snippets

def build_recommendation_markdown(
    query: str,
    intake: Dict[str, Any],
    local_matches: List[Dict[str, Any]],
    web_hits: List[Dict[str, Any]],
    include_sources: bool = False,
    memory_k: int = 0,
) -> str:
    equipment = classify_equipment(query, intake)
    symptom = classify_symptom(query, intake)

    # pull short examples from local historical matches
    examples = []
    for m in local_matches[:6]:
        rec = (m.get("record") or {})
        note = (rec.get("Additional Repairs Needed/Recommended") or rec.get("notes") or "").strip()
        work = (rec.get("Job - Work Performed") or "").strip()
        snippet = note or work
        if snippet:
            examples.append(snippet)

    examples = _dedupe_lines(examples, 5)

    # memory snippets from taught cases
    memory_snips: List[str] = _cases_memory_snippets(query, k=max(0, int(memory_k))) if memory_k else []

    # lightweight “default” structure
    md = []
    md.append("# Atlas Recommendation")
    md.append("")
    md.append(f"**Query:** {query.strip()}")
    if equipment:
        md.append(f"**Equipment:** {equipment}")
    md.append(f"**Symptom:** {symptom}")
    md.append("")

    # If symptom looks unknown, ask for one narrowing detail
    if symptom in ("unknown",) or len(symptom) > 80:
        md.append("## Likely causes")
        md.append("- Need one more detail to narrow root cause (power vs sensor vs mechanical).")
        md.append("")
        md.append("## Quick diagnostics")
        md.append("- Confirm exact symptom (won’t open / won’t close / intermittent / no power).")
        md.append("- Identify manufacturer/model and door type (slider/swing/roll-up/maglock/gate).")
        md.append("- Check mechanical binding first, then safety inputs, then controller/power.")
        md.append("")
    else:
        md.append("## Start here")
        md.append("- Verify the symptom at the door (repeatable? intermittent?).")
        md.append("- Check the *simple* causes first (mode switch, obstruction, loose wiring, dirty sensor lens).")
        md.append("- If you can share model + photos of labels/terminal legend, Atlas can pull exact wiring/docs.")
        md.append("")

    # recommended fix path (generic but better than “wig out”)
    md.append("## Recommended fix path")
    md.append("- Isolate **mechanical vs sensors vs power/controller** before ordering parts.")
    md.append("- If you replaced electronics and it persists, suspect **mechanical bind / obstruction**.")
    md.append("- After any fix: cycle-test 10–15 times and confirm safe operation.")
    md.append("")

    # Show memory taught cases if present
    if memory_snips:
        md.append("## Learned notes from your techs (memory)")
        for s in memory_snips:
            md.append(f"- {s}")
        md.append("")

    # Show examples from notes (short)
    if examples:
        md.append("## Examples from your past jobs (short)")
        for e in examples:
            md.append(f"- {e}")
        md.append("")

    # web hits - keep clean and relevant
    if web_hits:
        md.append("## Docs & diagrams (web)")
        # show up to 4
        for h in web_hits[:4]:
            title = (h.get("title") or "Reference").strip()
            url = (h.get("url") or "").strip()
            if url:
                md.append(f"- {title} — {url}")
        md.append("")

    if include_sources:
        md.append("## Evidence trail")
        ids = []
        for m in local_matches[:6]:
            rec = m.get("record") or {}
            jn = rec.get("Job - Job Number") or ""
            if jn:
                ids.append(str(jn))
        if ids:
            md.append(f"**Historical notes used:** {', '.join(ids[:12])}")
        else:
            md.append("**Historical notes used:** (none)")
        md.append("")

    md.append("---")
    md.append("To teach Atlas: use **Teach** (or type `Make this a trick of trade:` + your rule).")

    return "\n".join(md)

