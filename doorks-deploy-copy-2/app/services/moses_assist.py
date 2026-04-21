from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

from app.services.forms_library import list_forms
from app.services.calendar_store import CalendarStore

MOSES_MODEL = os.getenv("MOSES_MODEL", os.getenv("ATLAS_MODEL", "gpt-4o-mini"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EXCLUDES_LINE = "****EXCLUDES: HIDDEN CONDITIONS OR SPECIAL SCHEDULING ARRANGEMENTS****"
DEFAULT_LEAD = "Please allow 1–3 weeks for scheduling and delivery."


def _client():
    if not OpenAI or not OPENAI_API_KEY:
        return None
    return OpenAI(api_key=OPENAI_API_KEY)


def _project_root() -> str:
    return os.getenv("DOORKS_PROJECT_ROOT", ".")


def _calendar() -> CalendarStore:
    return CalendarStore(project_root=_project_root())


def _is_forms(q: str) -> bool:
    t = (q or "").strip().lower()
    return t in {"forms", "show forms", "form", "takeoff", "takeoffs"}


def _mode(q: str) -> str:
    t = (q or "").strip().lower()
    if t.startswith("proposal"):
        return "proposal"
    if t.startswith("invoice"):
        return "invoice"
    return "chat"


def _strip_prefix(q: str) -> str:
    s = (q or "").strip()
    low = s.lower()
    for p in ["proposal", "proposal -", "proposal:", "invoice", "invoice -", "invoice:"]:
        if low.startswith(p):
            if ":" in s[:20]:
                return s.split(":", 1)[1].strip()
            if "-" in s[:20]:
                return s.split("-", 1)[1].strip()
            return s[len(p):].strip(" :-")
    return s


def _guess_location_reference(notes: str) -> str:
    n = (notes or "").strip()
    patterns = [
        r"\b(main entrance|rear exit|front entrance|side entrance|side patio|shipping door|receiving door|lobby|er|icu|pharmacy)\b",
        r"\b(door)\b.*?\b(\d+)\b",
    ]
    for pat in patterns:
        m = re.search(pat, n, re.I)
        if m:
            return m.group(0).strip().title()
    return "Door / Opening"


def _service_label(notes: str) -> str:
    t = (notes or "").lower()
    if any(w in t for w in ["install", "furnish and install", "f&i", "replace", "retrofit"]):
        return "Install / Replace"
    if any(w in t for w in ["repair", "fix", "adjust", "troubleshoot"]):
        return "Repair / Service"
    if any(w in t for w in ["pm", "preventative", "preventive maintenance", "inspect", "tune"]):
        return "Service / PM"
    return "Repairs / Services"


def _search_jobs_text(q: str) -> Optional[str]:
    jobs = _calendar().query_jobs(q=q, limit=10)
    if not jobs:
        return None
    lines = ["Matched jobs:"]
    for j in jobs:
        lines.append(
            f"- {j.get('job_number','')} | {j.get('status','')} | {j.get('customer','')} | {j.get('address','')} | {j.get('date_display') or j.get('date') or ''}"
        )
    return "\n".join(lines)


def _deterministic_office_draft(mode: str, notes: str) -> str:
    location = _guess_location_reference(notes)
    label = _service_label(notes)
    header = "Proposal Includes" if mode == "proposal" else "Invoice Includes"
    body_bits = []
    lower = notes.lower()
    if "overhead concealed closer" in lower or "ohc" in lower:
        body_bits.append("This proposal covers replacement of the existing overhead concealed closer at the referenced opening.")
    elif "closer" in lower:
        body_bits.append("This proposal covers replacement of the existing door closer at the referenced opening.")
    elif any(w in lower for w in ["replace", "installation", "install"]):
        body_bits.append("This proposal covers furnishing and installing the required material at the referenced opening.")
    else:
        body_bits.append("This proposal covers the required repair work at the referenced opening.")
    if any(w in lower for w in ["remove", "cut", "trim"]):
        body_bits.append("A crew will be required to complete the scope of work.")
    if mode == "proposal":
        return f"{header} – {location} {label}\n\n{' '.join(body_bits)}\n\n{DEFAULT_LEAD}\n{EXCLUDES_LINE}"
    return f"{header} – {location} {label}\n\n{' '.join(body_bits)}\n\n********JOB COMPLETE*********"


def moses_generate(q: str, attachments: Optional[List[Dict[str, Any]]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    attachments = attachments or []
    context = context or {}
    client = _client()

    if _is_forms(q):
        forms = list_forms(_project_root())
        msg = "Forms (download):\n" + "\n".join([f"- {f['title']}: {f['download_url']}" for f in forms])
        return {"mode": "forms", "text": msg}

    mode = _mode(q)
    notes = _strip_prefix(q)

    if mode == "chat":
        found = _search_jobs_text(q)
        if found:
            return {"mode": "chat", "text": found}
        if not client:
            return {"mode": "chat", "text": "Moses is not configured. Set OPENAI_API_KEY and restart."}
        system = (
            "You are Moses, the office assistant for a commercial door company.\n"
            "Behave like an office manager/search analyst, not a generic chatbot.\n"
            "Prefer concise, factual answers grounded in the provided company context.\n"
            "When context includes jobs, estimates, invoices, CRM, timecards, or time off, use that first.\n"
            "Do not invent job numbers, estimate numbers, invoice numbers, parts, vendors, or contacts.\n"
            "If context is thin, answer briefly and say what was not found.\n"
        )
        user = {"q": q, "attachments": attachments[:6], "context": context}
        resp = client.chat.completions.create(
            model=MOSES_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        return {"mode": "chat", "text": (resp.choices[0].message.content or "").strip()}

    deterministic = _deterministic_office_draft(mode, notes)
    if not client:
        return {"mode": mode, "text": deterministic}

    system = (
        "You are Moses, writing QuickBooks-ready proposal/invoice text for a commercial door company.\n"
        "Follow the house format closely.\n"
        "Keep the wording concise and field-usable.\n"
        "Do not add markdown bullets.\n"
        "Preserve the final lead-time / excludes line for proposals and job complete line for invoices.\n"
        "Use the provided draft as the base and improve it without drifting from the format.\n"
    )
    user = {"q": q, "draft": deterministic, "attachments": attachments[:6], "context": context}
    resp = client.chat.completions.create(
        model=MOSES_MODEL,
        temperature=0.15,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    )
    text = (resp.choices[0].message.content or "").strip() or deterministic
    if mode == "proposal":
        if DEFAULT_LEAD not in text:
            text = text.rstrip() + "\n\n" + DEFAULT_LEAD
        if EXCLUDES_LINE not in text:
            text = text.rstrip() + "\n" + EXCLUDES_LINE
    else:
        if "********JOB COMPLETE*********" not in text:
            text = text.rstrip() + "\n\n********JOB COMPLETE*********"
    return {"mode": mode, "text": text}
