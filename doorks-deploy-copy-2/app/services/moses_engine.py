from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.storage import first_existing_data_path

from app.services.calendar_store import CalendarStore
from app.services.crm_store import CRMStore
from app.services.legacy_store import LegacyStore
from app.services.moses_assist import moses_generate

JOB_RE = re.compile(r"\b\d{4}-\d+\b", re.I)
DOC_RE = re.compile(r"\b(?:RE|JS)\s*[- ]?\d+\b", re.I)
NUM_RE = re.compile(r"\d+")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
APPROVED_STATUSES = {"dispatch", "parts on order", "complete/quote", "complete", "done"}
STATUS_ALIASES = [
    ("sales lead", "Sales Lead", "sales leads"),
    ("quote sent", "Quote Sent", "quotes sent"),
    ("parts on order", "Parts on Order", "parts on order"),
    ("dispatch", "Dispatch", "dispatch jobs"),
    ("complete/quote", "Complete/Quote", "complete/quote jobs"),
    ("complete", "Complete", "complete jobs"),
    ("done", "Done", "done jobs"),
]
STOPWORDS = {
    "for", "the", "a", "an", "at", "of", "and", "to", "on", "this", "that",
    "show", "find", "get", "lookup", "look", "up", "please", "me", "all",
    "sales", "lead", "leads"
}


class MosesEngine:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or ".")
        self.calendar = CalendarStore(self.project_root)
        self.crm = CRMStore(self.project_root)
        self.legacy = LegacyStore(self.project_root)
        self.parts_csv = first_existing_data_path(self.project_root, "parts_list.csv")
        self.documents_index_path = first_existing_data_path(self.project_root, "documents_index.json")
        self.timecards_path = first_existing_data_path(self.project_root, "time_cards.json")
        self.timecards_legacy_path = first_existing_data_path(self.project_root, "timecards.json")
        self.timeoff_path = first_existing_data_path(self.project_root, "timeoff_requests.json")

    def _normalize(self, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip()
        if s.endswith(".0"):
            s = s[:-2]
        if s in {"â€”", "â€“", "—", "–", "None", "null", "NULL"}:
            return ""
        return s

    def _lower(self, value: Any) -> str:
        return self._normalize(value).lower()

    def _digits(self, value: Any) -> str:
        return "".join(NUM_RE.findall(self._normalize(value)))

    def _field(self, item: Dict[str, Any], *names: str) -> str:
        for name in names:
            if name in item and self._normalize(item.get(name)):
                return self._normalize(item.get(name))
        return ""

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _parse_date(self, value: Any):
        s = self._normalize(value)
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except Exception:
            return None

    def _source_label(self, item: Dict[str, Any]) -> str:
        return self._normalize(item.get("source") or item.get("_source") or "CURRENT").upper() or "CURRENT"

    def _all_jobs(self) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        try:
            current = self.calendar.all() if hasattr(self.calendar, "all") else self.calendar.list_jobs()
            for item in current or []:
                row = dict(item)
                row["source"] = "CURRENT"
                jobs.append(row)
        except Exception:
            pass
        try:
            legacy = self.legacy.all() if hasattr(self.legacy, "all") else self.legacy.list_jobs()
            for item in legacy or []:
                row = dict(item)
                row["source"] = self._source_label(row) or "LEGACY"
                jobs.append(row)
        except Exception:
            pass
        return self._dedupe_prefer_current(jobs)

    def _job_key(self, item: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
        return (
            self._field(item, "id"),
            self._field(item, "job_number", "lead_number"),
            self._field(item, "estimate_number", "estimate_no"),
            self._field(item, "invoice_number", "invoice_no"),
            self._field(item, "customer", "customer_name").lower(),
        )

    def _dedupe_prefer_current(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best: Dict[Tuple[str, str, str, str, str], Dict[str, Any]] = {}
        for item in jobs:
            key = self._job_key(item)
            if key not in best:
                best[key] = item
                continue
            existing = best[key]
            if self._source_label(existing) != "CURRENT" and self._source_label(item) == "CURRENT":
                best[key] = item
        return list(best.values())

    def _sorted(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sort_key(item: Dict[str, Any]):
            d = self._parse_date(self._field(item, "date", "date_display", "created_at"))
            return (
                0 if self._source_label(item) == "CURRENT" else 1,
                -(d.toordinal() if d else -1),
                self._field(item, "customer", "customer_name").lower(),
                self._field(item, "job_number", "lead_number"),
            )
        return sorted(jobs, key=sort_key)

    def _bubble(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": self._field(item, "id"),
            "customer": self._field(item, "customer", "customer_name"),
            "job_number": self._field(item, "job_number", "lead_number"),
            "estimate_number": self._field(item, "estimate_number", "estimate_no"),
            "invoice_number": self._field(item, "invoice_number", "invoice_no"),
            "po_number": self._field(item, "po_number", "po_no"),
            "address": self._field(item, "address"),
            "date": self._field(item, "date", "date_display"),
            "status": self._field(item, "status") or "History",
            "source": self._source_label(item),
            "contact": self._field(item, "contact", "contact_name"),
            "job_notes": self._field(item, "job_notes", "tech_notes", "description", "office_notes"),
            "work_performed": self._field(item, "work_performed"),
            "additional_recommendations": self._field(item, "additional_recommendations", "recommendations"),
            "parts_used": self._field(item, "parts_used", "parts_required"),
        }

    def _response(self, jobs: List[Dict[str, Any]], text: str = "", intent: str = "office", records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        ordered = self._sorted(jobs)
        bubbles = [self._bubble(j) for j in ordered[:12]]
        payload: Dict[str, Any] = {
            "intent": intent,
            "text": text,
            "jobs": bubbles,
            "bubbles": bubbles,
            "total": len(ordered),
            "show_more": len(ordered) > 6,
            "all_jobs": [self._bubble(j) for j in ordered[:200]],
        }
        if len(bubbles) == 1:
            payload["job"] = bubbles[0]
        if records:
            payload["records"] = records[:50]
        return payload

    def _history_has(self, item: Dict[str, Any], status: str) -> bool:
        want = status.lower()
        for row in (item.get("status_history") or []):
            if isinstance(row, dict) and self._lower(row.get("status")) == want:
                return True
            if isinstance(row, str) and self._lower(row) == want:
                return True
        return False

    def _filter_time(self, jobs: List[Dict[str, Any]], q_lower: str) -> List[Dict[str, Any]]:
        today = date.today()
        target_year = None
        if "last year" in q_lower:
            target_year = today.year - 1
        elif "this year" in q_lower:
            target_year = today.year
        else:
            m = YEAR_RE.search(q_lower)
            if m:
                target_year = int(m.group(1))

        filtered = jobs
        if "today" in q_lower:
            filtered = [j for j in filtered if (d := self._parse_date(self._field(j, "date", "date_display", "created_at"))) and d == today]
        elif "this month" in q_lower:
            filtered = [j for j in filtered if (d := self._parse_date(self._field(j, "date", "date_display", "created_at"))) and d.year == today.year and d.month == today.month]
        elif "last month" in q_lower:
            month = 12 if today.month == 1 else today.month - 1
            year = today.year - 1 if today.month == 1 else today.year
            filtered = [j for j in filtered if (d := self._parse_date(self._field(j, "date", "date_display", "created_at"))) and d.year == year and d.month == month]
        elif target_year is not None:
            filtered = [j for j in filtered if (d := self._parse_date(self._field(j, "date", "date_display", "created_at"))) and d.year == target_year]
        return self._sorted(filtered)

    def _search_identifier(self, raw: str, *fields: str) -> List[Dict[str, Any]]:
        target = self._normalize(raw).upper().replace(" ", "")
        target_digits = self._digits(target)
        hits: List[Dict[str, Any]] = []
        for item in self._all_jobs():
            for field in fields:
                value = self._field(item, field)
                if not value:
                    continue
                check = value.upper().replace(" ", "")
                if check == target or (target_digits and self._digits(check) == target_digits):
                    hits.append(item)
                    break
        return self._sorted(hits)

    def _tokenize_subject(self, q: str) -> List[str]:
        words = re.findall(r"[A-Za-z0-9#]+", self._lower(q))
        return [w for w in words if w not in STOPWORDS and len(w) > 1]

    def _search_contains(self, q: str) -> List[Dict[str, Any]]:
        qn = self._lower(q)
        if not qn:
            return []
        tokens = self._tokenize_subject(q)
        hits: List[Dict[str, Any]] = []
        for item in self._all_jobs():
            hay_parts = [
                self._field(item, "customer", "customer_name"),
                self._field(item, "contact", "contact_name"),
                self._field(item, "job_number", "lead_number"),
                self._field(item, "estimate_number", "estimate_no"),
                self._field(item, "invoice_number", "invoice_no"),
                self._field(item, "po_number", "po_no"),
                self._field(item, "address"),
                self._field(item, "job_notes", "tech_notes", "description", "office_notes"),
                self._field(item, "work_performed"),
                self._field(item, "additional_recommendations"),
                self._field(item, "parts_used"),
            ]
            for form in (item.get("completion_forms") or []):
                hay_parts.extend([
                    self._normalize(form.get("technician_name")),
                    self._normalize(form.get("tech_notes")),
                    self._normalize(form.get("recommendations") or form.get("additional_recommendations")),
                    self._normalize(form.get("parts_required") or form.get("parts_used")),
                ])
            hay = " | ".join([x.lower() for x in hay_parts if x])
            if qn in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                hits.append(item)
        return self._sorted(hits)

    def _status_current(self, status: str) -> List[Dict[str, Any]]:
        want = status.lower()
        return self._sorted([
            j for j in self._all_jobs()
            if self._source_label(j) == "CURRENT" and self._lower(j.get("status")) == want
        ])

    def _quote_sent_jobs(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in self._all_jobs():
            if self._source_label(item) != "CURRENT":
                continue
            estimate = self._field(item, "estimate_number", "estimate_no")
            if not estimate or not estimate.upper().startswith("RE"):
                continue
            if self._field(item, "status") == "Quote Sent" or self._history_has(item, "Quote Sent"):
                out.append(item)
        return self._sorted(out)

    def _approved_quotes(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in self._all_jobs():
            if self._source_label(item) != "CURRENT":
                continue
            estimate = self._field(item, "estimate_number", "estimate_no")
            if not estimate or not estimate.upper().startswith("RE"):
                continue
            status = self._lower(item.get("status"))
            approved = bool(item.get("approved")) or status in APPROVED_STATUSES
            came_from_quote = self._history_has(item, "Quote Sent") or self._history_has(item, "Quote") or self._lower(item.get("kind")) == "sales_lead"
            if approved and came_from_quote:
                out.append(item)
        return self._sorted(out)

    def _documents(self) -> List[Dict[str, Any]]:
        data = self._read_json(self.documents_index_path, {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        docs: List[Dict[str, Any]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            docs.append(dict(row))
        return docs

    def _link_docs_to_jobs(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_jobs = self._all_jobs()
        by_id = {self._field(j, "id"): j for j in all_jobs if self._field(j, "id")}
        out: List[Dict[str, Any]] = []
        for doc in docs:
            linked = None
            job_id = self._field(doc, "job_id")
            if job_id and job_id in by_id:
                linked = dict(by_id[job_id])
            else:
                num = self._field(doc, "job_number")
                est = self._field(doc, "number", "estimate_number") if self._lower(doc.get("type")) == "estimate" else self._field(doc, "estimate_number")
                inv = self._field(doc, "number", "invoice_number") if self._lower(doc.get("type")) == "invoice" else self._field(doc, "invoice_number")
                for j in all_jobs:
                    if num and self._field(j, "job_number", "lead_number") == num:
                        linked = dict(j); break
                    if est and self._field(j, "estimate_number", "estimate_no") == est:
                        linked = dict(j); break
                    if inv and self._field(j, "invoice_number", "invoice_no") == inv:
                        linked = dict(j); break
            if linked is None:
                linked = {
                    "id": self._field(doc, "job_id"),
                    "customer": self._field(doc, "customer"),
                    "job_number": self._field(doc, "job_number"),
                    "estimate_number": self._field(doc, "number") if self._lower(doc.get("type")) == "estimate" else self._field(doc, "estimate_number"),
                    "invoice_number": self._field(doc, "number") if self._lower(doc.get("type")) == "invoice" else self._field(doc, "invoice_number"),
                    "po_number": self._field(doc, "po_number"),
                    "address": self._field(doc, "address"),
                    "date": self._field(doc, "date", "created_at"),
                    "status": "Document",
                    "source": "CURRENT",
                }
            linked["document_type"] = self._field(doc, "type")
            linked["document_number"] = self._field(doc, "number")
            linked["document_path"] = self._field(doc, "path")
            out.append(linked)
        return self._sorted(out)

    def _search_documents(self, q: str, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        qn = self._lower(q)
        tokens = self._tokenize_subject(q)
        docs = []
        for row in self._documents():
            if doc_type and self._lower(row.get("type")) != doc_type.lower():
                continue
            hay = " | ".join([
                self._normalize(row.get("number")), self._normalize(row.get("customer")), self._normalize(row.get("address")),
                self._normalize(row.get("job_number")), self._normalize(row.get("invoice_number")), self._normalize(row.get("po_number")),
                self._normalize(row.get("work")), self._normalize(row.get("parts")), self._normalize(row.get("labor")),
            ]).lower()
            if qn in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                docs.append(row)
        return self._link_docs_to_jobs(docs)

    def _extract_subject(self, q: str) -> str:
        s = self._normalize(q)
        lower = s.lower()
        patterns = [
            r"^(?:show|find|get|lookup)?\s*contacts?\s+(?:for|at|from)\s+",
            r"^(?:show|find|get|lookup)?\s*customers?\s+(?:for|at|from)\s+",
            r"^(?:show|find|get|lookup)?\s*(?:phone|email)\s+(?:for|at|from)\s+",
            r"^(?:parts?|vendor|price|cost|source)\s+(?:for|on)\s+",
            r"^(?:show|find|get|lookup)?\s*time\s*cards?\s+(?:for)?\s*",
            r"^(?:show|find|get|lookup)?\s*time\s*off\s+(?:for)?\s*",
        ]
        for pat in patterns:
            stripped = re.sub(pat, "", lower, flags=re.I)
            if stripped != lower:
                return stripped.strip()
        return lower.strip()

    def _query_customers(self, q: str) -> List[Dict[str, Any]]:
        subject = self._extract_subject(q)
        items = self.crm.list_customers()
        if not subject:
            return items[:25]
        tokens = self._tokenize_subject(subject)
        out = []
        for item in items:
            hay = self._lower(item.get("company_name"))
            if subject in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                out.append(item)
        return out[:25]

    def _query_contacts(self, q: str) -> List[Dict[str, Any]]:
        subject = self._extract_subject(q)
        items = self.crm.list_contacts()
        if not subject:
            return items[:25]
        matched_customers = self._query_customers(subject)
        out: List[Dict[str, Any]] = []
        seen = set()
        for customer in matched_customers[:10]:
            cname = self._normalize(customer.get("company_name"))
            for item in self.crm.list_contacts(cname):
                key = self._field(item, "id") or f"{self._field(item,'name')}|{cname}"
                if key not in seen:
                    seen.add(key)
                    out.append(item)
        if out:
            return out[:25]
        tokens = self._tokenize_subject(subject)
        for item in items:
            hay = " | ".join([
                self._normalize(item.get("name")), self._normalize(item.get("company_name")),
                self._normalize(item.get("phone_number")), self._normalize(item.get("cell_phone")),
                self._normalize(item.get("email")),
            ]).lower()
            if subject in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                out.append(item)
        return out[:25]

    def _customer_response(self, customers: List[Dict[str, Any]], contacts: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
        lines = [text]
        if customers:
            lines.append("Customers:")
            for item in customers[:10]:
                lines.append(f"- {self._normalize(item.get('company_name'))}")
        if contacts:
            lines.append("Contacts:")
            for item in contacts[:12]:
                bits = [self._normalize(item.get("name"))]
                company = self._normalize(item.get("company_name"))
                phone = self._normalize(item.get("cell_phone") or item.get("phone_number"))
                email = self._normalize(item.get("email"))
                if company:
                    bits.append(company)
                if phone:
                    bits.append(phone)
                if email:
                    bits.append(email)
                lines.append("- " + " | ".join([b for b in bits if b]))
        return self._response([], "\n".join(lines), intent="office_crm")

    def _parts_lookup(self, q: str) -> List[Dict[str, str]]:
        if not self.parts_csv.exists():
            return []
        subject = self._extract_subject(q)
        subject_lower = subject.lower()
        subject_digits = self._digits(subject)
        terms = [t for t in re.split(r"\s+", subject_lower) if t and t not in STOPWORDS]
        out: List[Dict[str, str]] = []
        with self.parts_csv.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = {
                    "item": self._normalize(row.get("Item") or row.get("item") or row.get("Part") or row.get("part") or row.get("Code") or row.get("code")),
                    "description": self._normalize(row.get("Description") or row.get("description")),
                    "vendor": self._normalize(row.get("Preferred Vendor") or row.get("Vendor") or row.get("vendor")),
                    "cost": self._normalize(row.get("Cost") or row.get("cost")),
                    "price": self._normalize(row.get("Price") or row.get("price") or row.get("Sell") or row.get("sell")),
                }
                hay = " | ".join([v for v in item.values() if v]).lower()
                if subject_lower:
                    if subject_digits and subject_digits in self._digits(hay):
                        out.append(item)
                    elif terms and all(term in hay for term in terms[:2]):
                        out.append(item)
                    elif terms and any(term in hay for term in terms[:4]):
                        out.append(item)
                else:
                    out.append(item)
                if len(out) >= 12:
                    break
        return out

    def _parts_response(self, items: List[Dict[str, str]], text: str) -> Dict[str, Any]:
        lines = [text]
        for item in items[:10]:
            bits = [item.get("item") or "Part"]
            if item.get("description"):
                bits.append(item["description"])
            if item.get("vendor"):
                bits.append(f"Vendor: {item['vendor']}")
            if item.get("price") or item.get("cost"):
                bits.append(f"Price: {item.get('price') or item.get('cost')}")
            lines.append("- " + " | ".join([b for b in bits if b]))
        return self._response([], "\n".join(lines), intent="office_parts")

    def _timecards(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        modern = self._read_json(self.timecards_path, {"items": []})
        if isinstance(modern, dict):
            items.extend(modern.get("items", []))
        legacy = self._read_json(self.timecards_legacy_path, [])
        if isinstance(legacy, list):
            items.extend(legacy)
        return [x for x in items if isinstance(x, dict)]

    def _timeoff(self) -> List[Dict[str, Any]]:
        data = self._read_json(self.timeoff_path, {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        return [x for x in items if isinstance(x, dict)]

    def _timecard_search(self, q: str) -> List[Dict[str, Any]]:
        subject = self._extract_subject(q)
        tokens = self._tokenize_subject(subject)
        rows = []
        for item in self._timecards():
            hay = " | ".join([
                self._normalize(item.get("user") or item.get("technician_name") or item.get("employee_name")),
                self._normalize(item.get("date")), self._normalize(item.get("notes")),
                self._normalize(item.get("hours")), self._normalize(item.get("billed_hours")),
            ]).lower()
            if not subject or subject in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                rows.append(item)
        return rows

    def _timeoff_search(self, q: str) -> List[Dict[str, Any]]:
        subject = self._extract_subject(q)
        tokens = self._tokenize_subject(subject)
        rows = []
        for item in self._timeoff():
            hay = " | ".join([
                self._normalize(item.get("employee_name") or item.get("user")),
                self._normalize(item.get("start_date")), self._normalize(item.get("end_date")),
                self._normalize(item.get("status")), self._normalize(item.get("notes")),
            ]).lower()
            if not subject or subject in hay or (tokens and all(tok in hay for tok in tokens[:2])) or any(tok in hay for tok in tokens[:3]):
                rows.append(item)
        return rows

    def _timecard_response(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not items:
            return self._response([], "No timecards found.", intent="office_timecards")
        lines = [f"Found {len(items)} timecards."]
        records = []
        for item in items[:20]:
            name = self._normalize(item.get("user") or item.get("technician_name") or item.get("employee_name"))
            day = self._normalize(item.get("date"))
            hours = self._normalize(item.get("hours") or item.get("billed_hours"))
            notes = self._normalize(item.get("notes"))
            line = " | ".join([x for x in [name, day, f"Hours: {hours}" if hours else "", notes] if x])
            lines.append(f"- {line}")
            records.append({"type": "timecard", "employee": name, "date": day, "hours": hours, "notes": notes})
        return self._response([], "\n".join(lines), intent="office_timecards", records=records)

    def _timeoff_response(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not items:
            return self._response([], "No time off requests found.", intent="office_timeoff")
        lines = [f"Found {len(items)} time off requests."]
        records = []
        for item in items[:20]:
            name = self._normalize(item.get("employee_name") or item.get("user"))
            start = self._normalize(item.get("start_date"))
            end = self._normalize(item.get("end_date"))
            status = self._normalize(item.get("status"))
            notes = self._normalize(item.get("notes"))
            line = " | ".join([x for x in [name, f"{start} to {end}" if start or end else "", status, notes] if x])
            lines.append(f"- {line}")
            records.append({"type": "timeoff", "employee": name, "start_date": start, "end_date": end, "status": status, "notes": notes})
        return self._response([], "\n".join(lines), intent="office_timeoff", records=records)


    def _job_search_parts(self, item: Dict[str, Any]) -> Dict[str, str]:
        notes_bits: List[str] = [
            self._field(item, "job_notes", "tech_notes", "description", "office_notes"),
            self._field(item, "work_performed"),
            self._field(item, "additional_recommendations", "recommendations"),
            self._field(item, "parts_used", "parts_required"),
        ]
        for form in (item.get("completion_forms") or []):
            if not isinstance(form, dict):
                continue
            notes_bits.extend([
                self._field(form, "technician_name"),
                self._field(form, "tech_notes"),
                self._field(form, "recommendations", "additional_recommendations"),
                self._field(form, "parts_required", "parts_used"),
            ])

        return {
            "customer": self._field(item, "customer", "customer_name"),
            "contact": self._field(item, "contact", "contact_name"),
            "job_number": self._field(item, "job_number", "lead_number"),
            "estimate_number": self._field(item, "estimate_number", "estimate_no"),
            "invoice_number": self._field(item, "invoice_number", "invoice_no"),
            "po_number": self._field(item, "po_number", "po_no"),
            "address": self._field(item, "address"),
            "status": self._field(item, "status"),
            "notes": " | ".join([x for x in notes_bits if x]),
        }

    def _score_job_match(self, item: Dict[str, Any], q: str) -> int:
        qn = self._lower(q)
        if not qn:
            return 0
        tokens = self._tokenize_subject(q)
        digits = self._digits(qn)
        parts = self._job_search_parts(item)

        customer = self._lower(parts["customer"])
        contact = self._lower(parts["contact"])
        job_number = self._lower(parts["job_number"])
        estimate_number = self._lower(parts["estimate_number"])
        invoice_number = self._lower(parts["invoice_number"])
        po_number = self._lower(parts["po_number"])
        address = self._lower(parts["address"])
        status = self._lower(parts["status"])
        notes = self._lower(parts["notes"])
        hay = " | ".join([customer, contact, job_number, estimate_number, invoice_number, po_number, address, status, notes])

        score = 0
        for ident in [job_number, estimate_number, invoice_number, po_number]:
            if ident and qn.replace(" ", "") == ident.replace(" ", ""):
                score += 220
            if ident and qn in ident:
                score += 130
            if digits and ident and self._digits(ident) == digits:
                score += 90

        for field in [customer, contact, address]:
            if field and qn == field:
                score += 150
            elif field and qn in field:
                score += 95
            elif field and field in qn:
                score += 60

        if status and status in qn:
            score += 25

        for tok in tokens:
            if len(tok) < 2:
                continue
            if tok in job_number or tok in estimate_number or tok in invoice_number or tok in po_number:
                score += 42
            elif tok in customer:
                score += 30
            elif tok in contact:
                score += 24
            elif tok in address:
                score += 22
            elif tok in notes:
                score += 13
            elif tok in hay:
                score += 6

        if qn and qn in notes:
            score += 55

        return score

    def _search_all_jobs(self, q: str, limit: int = 50) -> List[Dict[str, Any]]:
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for item in self._all_jobs():
            score = self._score_job_match(item, q)
            if score > 0:
                scored.append((score, item))
        scored.sort(
            key=lambda pair: (
                -pair[0],
                0 if self._source_label(pair[1]) == "CURRENT" else 1,
                -(self._parse_date(self._field(pair[1], "date", "date_display", "created_at")).toordinal()
                  if self._parse_date(self._field(pair[1], "date", "date_display", "created_at")) else -1),
                self._field(pair[1], "customer", "customer_name").lower(),
            )
        )
        out: List[Dict[str, Any]] = []
        seen = set()
        for _, item in scored:
            key = self._job_key(item)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _single_line_job(self, item: Dict[str, Any]) -> str:
        bits = []
        customer = self._field(item, "customer", "customer_name")
        if customer:
            bits.append(customer)
        job = self._field(item, "job_number", "lead_number")
        if job:
            bits.append(f"Job #{job}")
        estimate = self._field(item, "estimate_number", "estimate_no")
        if estimate:
            bits.append(f"Estimate {estimate}")
        invoice = self._field(item, "invoice_number", "invoice_no")
        if invoice:
            bits.append(f"Invoice {invoice}")
        status = self._field(item, "status")
        if status:
            bits.append(status)
        address = self._field(item, "address")
        if address and len(bits) < 6:
            bits.append(address)
        return " | ".join([b for b in bits if b])

    def _count_response(self, label: str, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._response(jobs, f"{len(jobs)} {label}.", intent="office_count")

    def _hours_response(self, employee: str, items: List[Dict[str, Any]], q_lower: str) -> Dict[str, Any]:
        if not items:
            return self._response([], f"No timecards found for {employee}.", intent="office_timecards")
        total = 0.0
        for item in items:
            for field in ("hours", "billed_hours"):
                raw = str(item.get(field) or "").strip()
                try:
                    if raw:
                        total += float(raw)
                        break
                except Exception:
                    continue
        name = employee.strip() or "that employee"
        if "this month" in q_lower:
            return self._response([], f"{name} has {total:.2f} hours this month.", intent="office_timecards")
        return self._response([], f"{name} has {total:.2f} hours.", intent="office_timecards")

    def _last_visit_response(self, jobs: List[Dict[str, Any]], label: str = "visit") -> Dict[str, Any]:
        if not jobs:
            return self._response([], f"No {label} found.", intent="office_last_visit")
        item = self._sorted(jobs)[0]
        day = self._field(item, "date", "date_display", "created_at")
        customer = self._field(item, "customer", "customer_name")
        address = self._field(item, "address")
        status = self._field(item, "status")
        text = " | ".join([x for x in [customer, day, status, address] if x])
        return self._response([item], text or "Found latest visit.", intent="office_last_visit")
    def _summary(self, label: str, jobs: List[Dict[str, Any]]) -> str:
        if not jobs:
            return f"No {label} found."
        if len(jobs) == 1:
            item = jobs[0]
            parts = self._job_search_parts(item)
            line = self._single_line_job(item)
            notes = parts.get("notes", "").strip()
            if notes:
                short = re.sub(r"\s+", " ", notes).strip()
                if len(short) > 140:
                    short = short[:137].rstrip(" ,.;") + "..."
                line = f"{line} | {short}" if line else short
            return line or f"Found 1 {label}."
        return f"Found {len(jobs)} {label}. Showing best matches first."

    def answer(self, q: str, conversation_id=None):
        q_clean = self._normalize(q)
        q_lower = q_clean.lower()
        try:
            if not q_clean:
                return self._response([], "Ask Moses about jobs, estimates, invoices, customers, contacts, parts, timecards, or time off.")

            if q_lower in {"forms", "show forms", "form", "takeoff", "takeoffs"}:
                gen = moses_generate(q_clean)
                return self._response([], self._normalize(gen.get("text")), intent="office_forms")

            if q_lower.startswith("proposal") or q_lower.startswith("invoice:") or q_lower.startswith("proposal:"):
                gen = moses_generate(q_clean)
                return self._response([], self._normalize(gen.get("text")), intent="office_write")

            if any(term in q_lower for term in ["timecard", "time card"]):
                subject = self._extract_subject(q_clean)
                items = self._timecard_search(q_clean)
                items = self._filter_time(items, q_lower)
                if "how many hours" in q_lower or "hours does" in q_lower:
                    return self._hours_response(subject or "that employee", items, q_lower)
                return self._timecard_response(items)

            if "time off" in q_lower or "pto" in q_lower:
                items = self._timeoff_search(q_clean)
                return self._timeoff_response(items)

            if "how many estimates have been sent" in q_lower:
                jobs = self._filter_time(self._quote_sent_jobs(), q_lower)
                jobs = [j for j in jobs if self._field(j, "estimate_number", "estimate_no")]
                return self._count_response("estimates sent", jobs)

            if "how many estimates" in q_lower and any(t in q_lower for t in ["this month", "last month", "this year"]):
                jobs = self._filter_time(self._search_documents("estimate", doc_type="estimate"), q_lower)
                return self._count_response("estimates found", jobs)

            if "how many invoices" in q_lower and any(t in q_lower for t in ["this month", "last month", "this year"]):
                jobs = self._filter_time(self._search_documents("invoice", doc_type="invoice"), q_lower)
                return self._count_response("invoices found", jobs)

            match = JOB_RE.search(q_clean)
            if match:
                jobs = self._filter_time(self._search_identifier(match.group(0), "job_number", "lead_number"), q_lower)
                if jobs:
                    return self._response(jobs, self._summary("job", jobs))

            match = DOC_RE.search(q_clean)
            if match:
                token = match.group(0).upper().replace(" ", "")
                if token.startswith("RE"):
                    jobs = self._search_identifier(token, "estimate_number", "estimate_no")
                    if not jobs:
                        jobs = self._search_documents(token, doc_type="estimate")
                    jobs = self._filter_time(jobs, q_lower)
                    return self._response(jobs, self._summary("estimate", jobs))
                if token.startswith("JS"):
                    jobs = self._search_identifier(token, "invoice_number", "invoice_no")
                    if not jobs:
                        jobs = self._search_documents(token, doc_type="invoice")
                    jobs = self._filter_time(jobs, q_lower)
                    return self._response(jobs, self._summary("invoice", jobs))

            if re.search(r"\bpo\b", q_lower):
                nums = NUM_RE.findall(q_clean)
                if nums:
                    jobs = self._filter_time(self._search_identifier(nums[0], "po_number", "po_no"), q_lower)
                    return self._response(jobs, self._summary("PO matches", jobs))

            if any(term in q_lower for term in ["contact", "customer", "phone", "email"]):
                contacts = self._query_contacts(q_clean)
                customers = self._query_customers(q_clean)
                if contacts or customers:
                    return self._customer_response(customers, contacts, "Matched CRM records:")

            if any(term in q_lower for term in ["part", "vendor", "price", "cost", "source"]):
                parts = self._parts_lookup(q_clean)
                if parts:
                    return self._parts_response(parts, "Matched parts:")

            if any(term in q_lower for term in ["last time", "when was the last time", "last visit", "last time we were at"]):
                subject = self._extract_subject(q_clean)
                jobs = self._filter_time(self._search_all_jobs(subject or q_clean), q_lower)
                return self._last_visit_response(jobs)

            q_tokens = self._tokenize_subject(q_clean)
            for needle, status, label in STATUS_ALIASES:
                if needle in q_lower and needle != "quote sent":
                    other_subject = [tok for tok in q_tokens if tok not in needle.lower().split() and tok not in {"this", "month", "last", "year", "today", "we", "have"}]
                    if other_subject:
                        break
                    jobs = self._filter_time(self._status_current(status), q_lower)
                    return self._response(jobs, self._summary(label, jobs))

            if "approved" in q_lower and "quote" in q_lower:
                jobs = self._filter_time(self._approved_quotes(), q_lower)
                return self._response(jobs, self._summary("approved quotes", jobs))

            if "quote sent" in q_lower:
                jobs = self._filter_time(self._quote_sent_jobs(), q_lower)
                return self._response(jobs, self._summary("quotes sent", jobs))

            if any(term in q_lower for term in ["recent jobs", "recent dispatch", "recent sales leads", "show recent", "latest jobs"]):
                jobs = self._filter_time(self._all_jobs(), q_lower)[:25]
                return self._response(jobs, "Showing recent jobs newest first.")

            jobs = self._filter_time(self._search_all_jobs(q_clean), q_lower)
            if jobs:
                return self._response(jobs, self._summary("matching jobs", jobs))

            if re.search(r"\bestimate\b", q_lower):
                jobs = self._filter_time(self._search_documents(q_clean, doc_type="estimate"), q_lower)
                return self._response(jobs, self._summary("estimates", jobs))

            if re.search(r"\binvoice\b", q_lower):
                jobs = self._filter_time(self._search_documents(q_clean, doc_type="invoice"), q_lower)
                return self._response(jobs, self._summary("invoices", jobs))

            docs = self._filter_time(self._search_documents(q_clean), q_lower)
            if docs:
                return self._response(docs, self._summary("documents", docs))

            gen = moses_generate(q_clean, context={
                "recent_jobs": [self._bubble(j) for j in self._sorted(self._all_jobs())[:10]],
                "documents": self._documents()[:12],
                "customers": self.crm.list_customers()[:10],
                "contacts": self.crm.list_contacts()[:12],
            })
            text = self._normalize(gen.get("text"))
            if text:
                return self._response([], text, intent="office_chat")
            return self._response([], "No exact matches found.")
        except Exception as exc:
            return self._response([], f"Moses hit an error while searching: {exc}", intent="office_error")
