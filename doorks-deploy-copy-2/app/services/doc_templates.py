from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

TRIP_RATE = 175.0
FUEL_RATE = 15.0
SINGLE_LABOR_RATE = 175.0
CREW_LABOR_RATE = 235.0


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _sentence(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if text[-1] not in ".!?":
        text += "."
    return text


def _split_lines(value: Any) -> List[str]:
    text = _clean(value)
    if not text:
        return []
    parts = re.split(r"[\n;,]+", text)
    return [p.strip(" -") for p in parts if p and p.strip(" -")]


def _unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _tech_context(job: Dict[str, Any]) -> Tuple[bool, List[str]]:
    forms = job.get("completion_forms") or []
    names = _unique_keep_order([_clean(f.get("technician_name")) for f in forms if isinstance(f, dict)])
    return (len(names) > 1, names)


def _parts_from_job(job: Dict[str, Any]) -> List[str]:
    found: List[str] = []
    for form in job.get("completion_forms") or []:
        if not isinstance(form, dict):
            continue
        found.extend(_split_lines(form.get("parts_required")))
        found.extend(_split_lines(form.get("parts_used")))
    found.extend(_split_lines(job.get("parts_used")))
    found.extend(_split_lines(job.get("parts_required")))
    return _unique_keep_order(found)


def _recommendations(job: Dict[str, Any]) -> List[str]:
    found: List[str] = []
    for form in job.get("completion_forms") or []:
        if not isinstance(form, dict):
            continue
        found.extend(_split_lines(form.get("recommendations")))
        found.extend(_split_lines(form.get("additional_recommendations")))
    found.extend(_split_lines(job.get("office_notes")))
    return _unique_keep_order(found)


def _work_notes(job: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    for form in job.get("completion_forms") or []:
        if not isinstance(form, dict):
            continue
        for key in ("tech_notes", "status_update"):
            val = _sentence(form.get(key))
            if val:
                notes.append(val)
    for key in ("job_notes", "office_notes"):
        val = _sentence(job.get(key))
        if val:
            notes.append(val)
    return _unique_keep_order(notes)


def _door_label(job: Dict[str, Any]) -> str:
    forms = [f for f in (job.get("completion_forms") or []) if isinstance(f, dict)]
    for form in forms:
        location = _clean(form.get("door_location"))
        door_type = _clean(form.get("door_type"))
        if location and door_type:
            return f"{location} - {door_type}"
        if location:
            return location
    return _clean(job.get("job_number")) or "Specified Opening"


def _group_forms_by_date(job: Dict[str, Any]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for form in job.get("completion_forms") or []:
        if not isinstance(form, dict):
            continue
        created = _clean(form.get("created_at")) or _clean(job.get("date"))
        day = created[:10] if len(created) >= 10 else (_clean(job.get("date")) or "")
        groups[day].append(form)
    return sorted(groups.items(), key=lambda kv: kv[0] or "")


def _default_labor_hours(job: Dict[str, Any]) -> float:
    total = 0.0
    for form in job.get("completion_forms") or []:
        if not isinstance(form, dict):
            continue
        try:
            total += float(form.get("time_onsite_hours") or 0)
        except Exception:
            pass
    return round(total, 2)


def _default_items(job: Dict[str, Any], multiple_techs: bool, include_parts: bool = True) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {"code": "TRIP", "description": "Trip Charge", "qty": 1, "rate": TRIP_RATE, "kind": "trip", "taxable": False},
        {"code": "FUEL", "description": "Fuel Surcharge", "qty": 1, "rate": FUEL_RATE, "kind": "fuel", "taxable": False},
    ]
    hours = _default_labor_hours(job)
    if hours > 0:
        items.append({
            "code": "CREW" if multiple_techs else "LABOR",
            "description": "Crew Tech Labor" if multiple_techs else "Single Tech Labor",
            "qty": hours,
            "rate": CREW_LABOR_RATE if multiple_techs else SINGLE_LABOR_RATE,
            "kind": "labor",
            "taxable": False,
        })
    if include_parts:
        for part in _parts_from_job(job):
            items.append({"code": "PART", "description": part, "qty": 1, "rate": 0, "kind": "part", "taxable": True})
    return items


def build_doc_suggestion(job: Dict[str, Any], doc_type: str, extra_notes: str = "", scope_hint: str = "") -> Dict[str, Any]:
    job = dict(job or {})
    doc_type = (doc_type or "estimate").strip().lower()
    multiple_techs, tech_names = _tech_context(job)
    actor = "Technicians" if multiple_techs else "Technician"
    door_label = _door_label(job)
    customer = _clean(job.get("customer"))
    address = _clean(job.get("address"))
    job_number = _clean(job.get("job_number"))
    work_notes = _work_notes(job)
    recommendations = _recommendations(job)
    parts = _parts_from_job(job)
    extra = _sentence(extra_notes)
    scope_hint = _sentence(scope_hint)

    if doc_type == "invoice":
        groups = _group_forms_by_date(job)
        lines: List[str] = []
        if groups:
            for idx, (day, forms) in enumerate(groups, start=1):
                lines.append(f"Trip #{idx} ({day})")
                lines.append(f"{actor} arrived onsite and checked in with customer.")
                for form in forms:
                    location = _clean(form.get("door_location"))
                    if location:
                        lines.append(f"{actor} moved to {location} and evaluated reported issues.")
                    note = _sentence(form.get("tech_notes"))
                    if note:
                        lines.append(note)
                    used = _split_lines(form.get("parts_used"))
                    if used:
                        lines.append("Parts used: " + ", ".join(used) + ".")
                    rec = _split_lines(form.get("additional_recommendations"))
                    if rec:
                        lines.append("Additional recommendations: " + "; ".join(rec) + ".")
                lines.append("")
        else:
            lines.append(f"{actor} arrived onsite and checked in with customer.")
            if door_label:
                lines.append(f"{actor} moved to {door_label} and evaluated reported issues.")
            lines.extend(work_notes[:4])
        if extra:
            lines.append(extra)
        lines.append("********JOB COMPLETE*********")
        work = "\n".join([line for line in lines if line is not None]).strip()
    else:
        lines = [f"Proposal Includes - {door_label}"]
        lines.append(f"{actor} arrived onsite and checked in with customer. {actor} moved to {door_label} and evaluated reported issues.")
        if work_notes:
            lines.extend(work_notes[:4])
        scope_bits: List[str] = []
        if scope_hint:
            scope_bits.append(scope_hint)
        if recommendations:
            scope_bits.append("Recommended scope: " + "; ".join(recommendations[:4]) + ".")
        if parts:
            scope_bits.append("Parts anticipated: " + ", ".join(parts[:6]) + ".")
        if not scope_bits:
            scope_bits.append("Proposal includes labor and material required to complete the described repairs.")
        lines.extend(scope_bits)
        lines.append("Schedule work to be completed during normal business hours upon approval.")
        lines.append("****EXCLUDES: HIDDEN CONDITIONS OR SPECIAL SCHEDULING ARRANGEMENTS****")
        if extra:
            lines.append(extra)
        work = "\n".join(lines).strip()

    return {
        "work": work,
        "items": _default_items(job, multiple_techs, include_parts=True),
        "prompt_summary": {
            "customer": customer,
            "address": address,
            "job_number": job_number,
            "door_label": door_label,
            "tech_names": tech_names,
            "parts_found": parts,
            "recommendations": recommendations,
        },
    }
