from __future__ import annotations

from typing import Optional, Any, List
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
    customer: str = ""
    address: str = ""
    project: str = ""
    job_number: str = ""
    door_location: str = ""
    door_id: str = ""
    notes: str = ""
    recommendations: str = ""
    office_notes: str = ""
    job_notes: str = ""
    work: str = ""
    doc_type: str = "estimate"
    crew: bool = False
    trips: int = 1
    dates: List[str] = []


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return " ".join(text.split())


def _looks_like_contact_or_address(text: str) -> bool:
    lowered = f" {_clean_text(text).lower()} "
    if not lowered.strip():
        return True
    address_tokens = [" ave ", " avenue ", " st ", " street ", " rd ", " road ", " dr ", " drive ", " blvd ", " boulevard ", " suite ", " ste ", " escondido ", " ca ", " zip "]
    if any(tok in lowered for tok in address_tokens):
        return True
    if "@" in lowered:
        return True
    if sum(ch.isdigit() for ch in lowered) >= 4:
        return True
    return False


def _split_note_parts(*values: Any) -> List[str]:
    parts: List[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        for piece in re.split(r"(?<=[.!?])\s+|\n+", text):
            chunk = _clean_text(piece)
            if not chunk or _looks_like_contact_or_address(chunk):
                continue
            parts.append(chunk)
    deduped: List[str] = []
    seen = set()
    for part in parts:
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(part)
    return deduped


def _as_sentence(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""
    if clean[-1] not in ".!?":
        clean += "."
    return clean


def _proposal_title(payload: AutoDescriptionPayload) -> str:
    for value in [payload.project, payload.door_location, payload.door_id]:
        clean = _clean_text(value)
        if clean and not _looks_like_contact_or_address(clean):
            return clean
    return "Opening"


def generate_description(payload: AutoDescriptionPayload) -> str:
    tech = "Technicians" if payload.crew else "Technician"
    doc_type = (_clean_text(payload.doc_type) or "estimate").lower()
    notes = _split_note_parts(payload.office_notes, payload.job_notes, payload.notes, payload.work)
    recs = _split_note_parts(payload.recommendations)

    if doc_type == "invoice":
        lines: List[str] = [f"{tech} arrived onsite and checked in with customer."]
        for part in notes:
            lowered = part.lower()
            if lowered.startswith("arrived on site") or lowered.startswith("arrived onsite"):
                continue
            lines.append(_as_sentence(part))
        for rec in recs:
            lines.append(f"Recommended repairs: {_clean_text(rec)}.")
        lines.append("********JOB COMPLETE*********")
        return " ".join(line for line in lines if line).strip()

    title = _proposal_title(payload)
    lines = [f"Proposal Includes – {title}"]
    lines.append(f"{tech} arrived onsite and checked in with customer to review the condition of the opening.")
    if notes:
        lines.extend(_as_sentence(part) for part in notes)
    elif payload.job_notes:
        lines.append(_as_sentence(payload.job_notes))
    for rec in recs:
        lines.append(_as_sentence(rec))
    lines.append("Scheduling to be coordinated with customer upon approval.")
    lines.append("****EXCLUDES: HIDDEN CONDITIONS OR SPECIAL SCHEDULING ARRANGEMENTS****")
    return " ".join(line for line in lines if line).strip()

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
                # direct mutate persisted record
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
def auto_description(payload: AutoDescriptionPayload, request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "description": generate_description(payload)}
