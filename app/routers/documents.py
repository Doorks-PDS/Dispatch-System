from __future__ import annotations

from typing import Optional, Any, List, Dict
import re

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/documents", tags=["documents"])


def _store(request: Request):
    return request.app.state.documents_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


class DocCreate(BaseModel):
    job_id: str = ""
    customer: str = ""
    address: str = ""
    ship_to: str = ""
    work: str = ""
    labor: str = ""
    parts: str = ""
    number: str = ""
    po_number: str = ""
    invoice_number: str = ""
    job_number: str = ""
    tax_rate: float = 0.0
    completed_by: str = ""
    date: str = ""
    type: str = ""
    items: List[dict[str, Any]] = []


class AutoDescriptionPayload(BaseModel):
    job_id: str = ""
    customer: str = ""
    address: str = ""
    project: str = ""
    job_number: str = ""
    door_location: str = ""
    door_id: str = ""
    door_type: str = ""
    notes: str = ""
    recommendations: str = ""
    office_notes: str = ""
    job_notes: str = ""
    work: str = ""
    doc_type: str = "estimate"
    type: str = ""
    crew: bool = False
    trips: int = 1
    dates: List[str] = []
    completion_forms: List[dict[str, Any]] = []
    recommendation_forms: List[dict[str, Any]] = []


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return " ".join(text.split())


def _clean_multiline(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _looks_like_contact_or_address(text: str) -> bool:
    lowered = f" {_clean_text(text).lower()} "
    if not lowered.strip():
        return True
    address_tokens = [
        " ave ", " avenue ", " st ", " street ", " rd ", " road ", " dr ", " drive ",
        " blvd ", " boulevard ", " suite ", " ste ", " escondido ", " san diego ",
        " ca ", " zip ", " towne centre ", " phone ", " email ", " contact "
    ]
    if any(tok in lowered for tok in address_tokens):
        return True
    if "@" in lowered:
        return True
    if sum(ch.isdigit() for ch in lowered) >= 7:
        return True
    return False


def _as_sentence(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""
    if clean[-1] not in ".!?":
        clean += "."
    return clean


def _as_list(value: Any) -> List[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _get_any(source: dict[str, Any], keys: List[str]) -> Any:
    if not isinstance(source, dict):
        return ""
    for key in keys:
        if key in source and source.get(key) not in (None, ""):
            return source.get(key)
        for actual_key, actual_value in source.items():
            if str(actual_key).lower().replace("_", "") == key.lower().replace("_", "") and actual_value not in (None, ""):
                return actual_value
    return ""


def _job_from_store(request: Optional[Request], job_id: str) -> dict[str, Any]:
    if not request or not job_id:
        return {}
    store = getattr(request.app.state, "calendar_store", None)
    if not store:
        return {}
    try:
        job = store.get_job(job_id)
        return job if isinstance(job, dict) else {}
    except Exception:
        return {}


def _merge_payload_with_job(payload: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    merged = dict(job or {})
    merged.update({k: v for k, v in (payload or {}).items() if v not in (None, "", [], {})})

    merged.setdefault("office_notes", job.get("office_notes") or job.get("officeNotes") or "")
    merged.setdefault("job_notes", job.get("job_notes") or job.get("jobNotes") or "")
    merged.setdefault("customer", job.get("customer") or job.get("customer_name") or "")
    merged.setdefault("address", job.get("address") or job.get("job_address") or "")
    merged.setdefault("job_number", job.get("job_number") or job.get("jobNumber") or "")
    merged.setdefault("completion_forms", job.get("completion_forms") or job.get("completionForms") or [])
    merged.setdefault("recommendation_forms", job.get("recommendation_forms") or job.get("recommendationForms") or [])
    return merged


def _collect_forms(data: dict[str, Any]) -> List[dict[str, Any]]:
    forms: List[dict[str, Any]] = []
    for key in [
        "recommendation_forms",
        "recommendationForms",
        "recommendations_forms",
        "completion_forms",
        "completionForms",
        "forms",
    ]:
        forms.extend(_as_list(data.get(key)))

    nested = data.get("documents") or {}
    if isinstance(nested, dict):
        forms.extend(_as_list(nested.get("recommendation_forms")))
        forms.extend(_as_list(nested.get("completion_forms")))

    out: List[dict[str, Any]] = []
    seen = set()
    for form in forms:
        key = str(form.get("id") or form.get("created_at") or form)
        if key in seen:
            continue
        seen.add(key)
        out.append(form)
    return out


def _form_score(form: dict[str, Any]) -> int:
    text = " ".join(str(v) for v in form.values()).lower()
    score = 0
    if "recommend" in text:
        score += 6
    if "ready to quote" in text or "ready_to_quote" in text:
        score += 6
    if "parts required" in text or "parts_required" in text:
        score += 5
    if _clean_text(_get_any(form, ["recommendations", "additional_recommendations", "additionalRecommendations"])):
        score += 5
    if _clean_text(_get_any(form, ["tech_notes", "techNotes", "notes"])):
        score += 3
    if _clean_text(_get_any(form, ["door_location", "doorLocation"])):
        score += 2
    return score


def _best_form(data: dict[str, Any], doc_type: str = "estimate") -> dict[str, Any]:
    forms = _collect_forms(data)
    if not forms:
        return {}

    quote_forms = [
        f for f in forms
        if bool(f.get("ready_to_quote"))
        or _clean_text(_get_any(f, ["parts_required", "partsRequired", "time_required", "timeRequired"]))
        or str(_get_any(f, ["status_update", "statusUpdate", "status"])).strip().lower() == "quote"
    ]

    completion_forms = [
        f for f in forms
        if _clean_text(_get_any(f, ["tech_notes", "techNotes", "parts_used", "partsUsed"]))
    ]

    if str(doc_type or "").lower() == "estimate" and quote_forms:
        return sorted(quote_forms, key=_form_score, reverse=True)[0]
    if str(doc_type or "").lower() == "invoice" and completion_forms:
        return sorted(completion_forms, key=_form_score, reverse=True)[0]
    return sorted(forms, key=_form_score, reverse=True)[0]


def _extract_parts_required(value: Any) -> List[str]:
    text = _clean_multiline(value)
    if not text:
        return []
    if _clean_text(text).lower() in {"none", "n/a", "na", "no", "no parts", "none."}:
        return []
    text = re.sub(r"^parts\s+required\s*:\s*", "", text, flags=re.I)
    raw_items = re.split(r"\n+|;|,(?=\s*\(?\d|\s*\d+x|\s*1x|\s*\()", text)
    items: List[str] = []
    for raw in raw_items:
        item = _clean_text(raw)
        if not item:
            continue
        item = re.sub(r"^\-\s*", "", item)
        if item.lower() in {"none", "n/a", "na", "no", "no parts", "none."}:
            continue
        items.append(item)
    return items


def _extract_approval_scope(job_notes: str) -> List[str]:
    text = _clean_multiline(job_notes)
    if not text:
        return []
    match = re.search(r"approval\s+to\s+replace\s*:?(.*)$", text, flags=re.I | re.S)
    if not match:
        return []
    raw = match.group(1).strip()
    items: List[str] = []
    for piece in re.split(r"\n+|;|,(?=\s*\(?\d|\s*\d+x|\s*1x|\s*\()", raw):
        item = _clean_text(piece)
        if item and item.lower() not in {"none", "n/a", "na", "no"}:
            items.append(item)
    return items


def _strip_checkin_checkout(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""
    cleanup_patterns = [
        r"^arrived\s+(?:on\s+site|onsite)\s*(?:and|,)?\s*(?:met\s+with\s+contact\.?\s*)?(?:checked\s+in\s*(?:with\s+customer)?\.?\s*)?",
        r"^tech(?:nician)?\s+arrived\s+(?:on\s+site|onsite)\s*(?:and)?\s*(?:checked\s+in\s*(?:with\s+customer)?\.?\s*)?",
        r"^we\s+arrived\s+(?:on\s+site|onsite).*?(?:property\.|property)",
        r"\s*(?:cleaned\s+up|cleaned\s+up,?\s+checked\s+out|checked\s+out)\.?$",
        r"\s*sign\s*off\s*sheet\s*included\s*in\s*pictures\.?$",
    ]
    for pat in cleanup_patterns:
        clean = re.sub(pat, "", clean, flags=re.I)
    clean = re.sub(r"\bwe\b", "technicians", clean, flags=re.I)
    clean = re.sub(r"\bi\b", "technician", clean, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip(" ,.-")
    return _clean_text(clean)


def _normalize_findings(text: str, door_location: str, door_type: str) -> str:
    clean = _strip_checkin_checkout(text)
    if not clean:
        return ""
    clean = re.sub(r"^moved\s+to\s+", "", clean, flags=re.I).strip()
    clean = re.sub(r"^at\s+the\s+", "", clean, flags=re.I).strip()
    target = " ".join(x for x in [door_location, door_type] if x).strip()
    if target and target.lower() not in clean.lower():
        clean = f"At the {target}, {clean[0].lower() + clean[1:] if clean else clean}"
    else:
        if clean and not clean.lower().startswith("at the") and target:
            clean = f"At the {target}, {clean[0].lower() + clean[1:]}"
    return _as_sentence(clean)


def _proposal_title(data: dict[str, Any], form: dict[str, Any]) -> str:
    door_location = _clean_text(
        _get_any(form, ["door_location", "doorLocation"])
        or data.get("door_location")
        or data.get("doorLocation")
        or data.get("door_id")
        or data.get("doorId")
    )
    door_type = _clean_text(
        _get_any(form, ["door_type", "doorType"])
        or data.get("door_type")
        or data.get("doorType")
    )
    project = _clean_text(data.get("project"))
    if project and not _looks_like_contact_or_address(project):
        return project
    title = " ".join(x for x in [door_location, door_type] if x).strip()
    return title or "Opening"



def _field_action_sentence(sentence: str, crew: bool = False) -> str:
    s = _strip_checkin_checkout(sentence)
    if not s:
        return ""
    low = s.lower()
    actor = "Technicians" if crew else "Technician"
    plural_actor = "Technicians"
    replacements = [
        (r"^(?:technicians\s+)?took\s+(.+?)\s+down", f"{plural_actor} removed \\1"),
        (r"^(?:technicians\s+)?swapped\s+out\s+", f"{actor} replaced "),
        (r"^(?:technicians\s+)?switched\s+out\s+", f"{actor} replaced "),
        (r"^(?:technicians\s+)?ran\s+to\s+.+?\s+and\s+picked\s+.+?\s+up\s+and\s+installed\s+", f"{actor} installed "),
        (r"^(?:technicians\s+)?after\s+inspecting\s+", f"{actor} inspected the opening and "),
        (r"^(?:technicians\s+)?once\s+.+?\s+", ""),
    ]
    for pat, rep in replacements:
        s = re.sub(pat, rep, s, flags=re.I)
    if re.search(r"\b(replaced|removed|installed|adjusted|reset|serviced|repaired|lubed|secured|cut|mounted|tested)\b", s, flags=re.I):
        if not re.match(r"^(Technician|Technicians)\b", s):
            s = f"{actor} {s[0].lower() + s[1:]}"
    return _as_sentence(s)

def _invoice_summary(tech_notes: str, parts_used: str = "", crew: bool = False) -> List[str]:
    clean = _strip_checkin_checkout(tech_notes)
    if not clean:
        return []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    selected: List[str] = []
    action_words = ["replaced", "removed", "installed", "reset", "adjusted", "repaired", "serviced", "lubed", "secured", "cut", "mounted", "hung", "tested", "confirmed", "verified"]

    for s in sentences:
        low = s.lower()
        if any(word in low for word in action_words):
            action = _field_action_sentence(s, crew=crew)
            if action and action.lower() not in [x.lower() for x in selected]:
                selected.append(action)
        if len(selected) >= 3:
            break

    if not selected and sentences:
        first = _field_action_sentence(sentences[0], crew=crew)
        if first:
            selected.append(first)

    if parts_used and _clean_text(parts_used).lower() not in {"none", "n/a", "na", "no"}:
        part_text = _clean_text(parts_used)
        if not any(part_text.lower() in line.lower() for line in selected):
            selected.insert(0, f"{'Technicians' if crew else 'Technician'} installed/replaced {part_text}.")

    if not any("tested" in line.lower() or "confirmed" in line.lower() for line in selected):
        selected.append("Tested operation and confirmed proper function.")
    if not any("clean" in line.lower() for line in selected):
        selected.append("Cleaned up work area.")

    return selected[:5]


def generate_description_from_data(data: dict[str, Any]) -> str:
    doc_type = _clean_text(data.get("doc_type") or data.get("type") or "estimate").lower()
    crew = bool(data.get("crew"))
    tech = "Technicians" if crew else "Technician"

    form = _best_form(data, doc_type)
    office_notes = _clean_text(data.get("office_notes") or data.get("officeNotes"))
    job_notes = _clean_multiline(data.get("job_notes") or data.get("jobNotes"))
    payload_notes = _clean_text(data.get("notes") or data.get("work"))

    form_tech_notes = _clean_text(_get_any(form, ["tech_notes", "techNotes", "notes"]))
    form_recs = _clean_text(_get_any(form, ["recommendations", "additional_recommendations", "additionalRecommendations", "recommendation"]))
    parts_required = _get_any(form, ["parts_required", "partsRequired"])
    parts_used = _clean_text(_get_any(form, ["parts_used", "partsUsed", "parts"]))
    time_required = _clean_text(_get_any(form, ["time_required", "timeRequired", "time", "hours"]))
    door_location = _clean_text(_get_any(form, ["door_location", "doorLocation"]) or data.get("door_location") or data.get("doorLocation"))
    door_type = _clean_text(_get_any(form, ["door_type", "doorType"]) or data.get("door_type") or data.get("doorType"))

    if doc_type == "invoice":
        lines: List[str] = [f"{tech} arrived onsite and checked in with customer."]
        summary_lines = _invoice_summary(form_tech_notes or payload_notes or office_notes or job_notes, parts_used, crew=crew)
        lines.extend(summary_lines)
        lines.append("********JOB COMPLETE*********")
        return " ".join(line for line in lines if line).strip()

    # Estimates: recommendation/quote forms first; dispatch/job notes only as last fallback.
    preferred_source = form_recs or form_tech_notes or payload_notes or office_notes or job_notes

    title = _proposal_title(data, form)
    lines: List[str] = [f"Proposal Includes – {title}"]

    findings = _normalize_findings(preferred_source, door_location, door_type)
    if findings:
        lines.append(f"Per our site visit, {findings}")
    else:
        lines.append("Per our site visit, technician reviewed the condition of the opening and identified recommended repairs.")

    scope_items = _extract_parts_required(parts_required)
    if not scope_items:
        scope_items = _extract_approval_scope(job_notes)

    if scope_items:
        lines.append("")
        lines.append("Recommended scope includes:")
        for item in scope_items:
            lines.append(f"- {item}")

    if time_required:
        lines.append("")
        lines.append(f"Estimated onsite labor: {time_required} hour(s).")

    lines.append("")
    lines.append("Please allow 1–3 weeks for scheduling and material procurement.")
    lines.append("****EXCLUDES: HIDDEN CONDITIONS OR SPECIAL SCHEDULING ARRANGEMENTS****")

    return "\n".join(line for line in lines if line is not None).strip()


def generate_description(payload: AutoDescriptionPayload) -> str:
    return generate_description_from_data(payload.dict())


class SignoffCreate(BaseModel):
    job_id: str = ""
    job_number: str = ""
    customer: str = ""
    date: str = ""
    techs: str = ""
    contact_name: str = ""
    arrival_time: str = ""
    departure_time: str = ""
    additional_techs_onsite: bool = False
    signature_data: str = ""


def _doc_response(item: dict) -> dict:
    row = dict(item)
    row.pop("signature_data", None)
    row["download_url"] = f"/documents/download/{row['filename']}"
    row["open_url"] = f"/documents/download/{row['filename']}?inline=1"
    return row


@router.get("")
def list_documents(
    request: Request,
    job_id: str = Query(default=""),
    type: str = Query(default=""),
    x_api_key: Optional[str] = Header(default=None),
):
    _require(request, x_api_key)
    items = _store(request).list_documents(job_id=job_id)
    if type:
        items = [item for item in items if str(item.get("type") or "") == str(type)]
    items = [_doc_response(item) for item in items]
    return {"ok": True, "items": items}


@router.post("/estimate")
def create_estimate(request: Request, payload: DocCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    item = _store(request).create_pdf("estimate", payload.dict())
    return {"ok": True, "doc": _doc_response(item)}


@router.post("/invoice")
def create_invoice(request: Request, payload: DocCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    item = _store(request).create_pdf("invoice", payload.dict())
    return {"ok": True, "doc": _doc_response(item)}


@router.put("/{filename}")
def update_document(request: Request, filename: str, payload: DocCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).update_document(filename, payload.dict())
        return {"ok": True, "doc": _doc_response(item)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{filename}")
def delete_document(request: Request, filename: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        _store(request).delete_document(filename)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download/{filename}")
def download_document(request: Request, filename: str, x_api_key: Optional[str] = Header(default=None), inline: bool = Query(default=False)):
    _require(request, x_api_key)
    path = request.app.state.documents_store.dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    headers = {"Content-Disposition": f"inline; filename=\"{filename}\""} if inline else None
    return FileResponse(path=str(path), media_type="application/pdf", filename=None if inline else filename, headers=headers)


@router.post("/signoff")
def create_signoff(request: Request, payload: SignoffCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from datetime import datetime
    import io, base64, json

    store = _store(request)
    number = (payload.job_number or datetime.now().strftime("SIGNOFF-%Y%m%d-%H%M%S")).strip()
    safe_number = number.replace("/", "_").replace("\\", "_")
    filename = f"SIGNOFF_{safe_number}.pdf"
    path = store.dir / filename

    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    y = h - 50
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Job Sign Off")
    y -= 30
    c.setFont("Helvetica", 11)
    fields = [
        ("Job #", payload.job_number),
        ("Customer", payload.customer),
        ("Date", payload.date),
        ("Technician", payload.techs),
        ("Additional Techs Onsite", "Yes" if payload.additional_techs_onsite else "No"),
        ("Contact", payload.contact_name),
        ("Arrival", payload.arrival_time),
        ("Departure", payload.departure_time),
    ]
    for label, value in fields:
        c.drawString(40, y, f"{label}: {value or ''}")
        y -= 18
    sig_y = y - 80
    c.rect(40, sig_y, 240, 70)
    c.drawString(46, y-10, "Signature")
    sig = (payload.signature_data or "").strip()
    if sig.startswith("data:image") and "," in sig:
        try:
            raw = base64.b64decode(sig.split(",", 1)[1])
            img = ImageReader(io.BytesIO(raw))
            c.drawImage(img, 46, sig_y + 8, width=220, height=52, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.showPage()
    c.save()

    data = store._load()
    item = {
        "id": f"signoff-{safe_number}",
        "type": "signoff",
        "filename": filename,
        "number": payload.job_number or safe_number,
        "job_id": payload.job_id,
        "job_number": payload.job_number,
        "customer": payload.customer,
        "address": "",
        "po_number": "",
        "completed_by": payload.techs,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "date": payload.date,
        "contact_name": payload.contact_name,
        "arrival_time": payload.arrival_time,
        "departure_time": payload.departure_time,
        "additional_techs_onsite": payload.additional_techs_onsite,
        "signature_data": payload.signature_data,
    }
    items = data.get("items", [])
    items.append(item)
    data["items"] = items
    store._save(data)

    job_store = getattr(request.app.state, "calendar_store", None)
    if job_store and payload.job_id:
        try:
            job = job_store.get_job(payload.job_id)
            if job:
                docs = dict(job.get("documents") or {})
                signoffs = list(docs.get("signoffs") or [])
                signoffs.append(filename)
                docs["signoffs"] = signoffs
                job_store.update_job(payload.job_id, {"job_notes": job.get("job_notes") or "", "office_notes": job.get("office_notes") or "", "parts_order": job.get("parts_order") or {}, "completion_forms": job.get("completion_forms") or [],})
                data2 = job_store._load()
                for i,j in enumerate(data2.get("jobs", [])):
                    if str(j.get("id")) == str(payload.job_id):
                        data2["jobs"][i]["signoff_file"] = filename
                        data2["jobs"][i]["documents"] = docs
                        job_store._save(data2)
                        break
        except Exception:
            pass

    return {"ok": True, "doc": _doc_response(item)}


@router.post("/auto-description")
def auto_description(payload: dict[str, Any], request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)

    job_id = _clean_text(payload.get("job_id") or payload.get("id") or "")
    job = _job_from_store(request, job_id)
    data = _merge_payload_with_job(payload, job)

    return {"ok": True, "description": generate_description_from_data(data)}
