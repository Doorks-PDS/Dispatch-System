from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

NON_ALNUM_RE = re.compile(r"[^a-z0-9]+", re.I)
JOB_RE = re.compile(r"^\d{4}-\d{1,4}$", re.I)


def _text(v: Any) -> str:
    return str(v or "").strip()


def _norm(v: Any) -> str:
    return NON_ALNUM_RE.sub(" ", _text(v).lower()).strip()


def _compact(v: Any) -> str:
    return NON_ALNUM_RE.sub("", _text(v).lower())


def _digits(v: Any) -> str:
    return re.sub(r"\D", "", _text(v))


def _clean_num(v: Any) -> str:
    s = _text(v).replace("â€”", "").replace("—", "").replace("â€“", "").replace("–", "").strip()
    if not s:
        return ""
    if re.fullmatch(r"\d+\.0", s):
        return s[:-2]
    return s


def _parse_date(v: Any) -> str:
    s = _text(v)
    if not s:
        return ""
    s = s.replace("\r", " ").replace("\n", " ").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%m-%d-%Y", "%m-%d-%y"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return s[:10]


class LegacyStore:
    """Read-only historical jobs from legacy JSON + CSV files."""

    def __init__(self, project_root: Optional[str] = None) -> None:
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.project_root = root
        self.data_dir = root / "data"
        self.records: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        rows: List[Dict[str, Any]] = []
        rows.extend(self._load_legacy_json())
        rows.extend(self._load_csv(self.data_dir / "Billable_Time.csv", "BILLABLE_UPGRADED"))
        rows.extend(self._load_csv(self.data_dir / "billable_time.csv", "BILLABLE"))
        rows.extend(self._load_csv(self.data_dir / "tech_notes.csv", "TECH_NOTES"))
        self.records = self._merge_rows(rows)

    def all(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.records]

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        target = _text(record_id)
        if not target:
            return None
        for row in self.records:
            if _text(row.get("id")) == target:
                return dict(row)
        return None

    def query_jobs(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        rows = self.records
        if date:
            rows = [r for r in rows if _text(r.get("date")).startswith(_text(date))]
        if status:
            want = _norm(status)
            rows = [r for r in rows if _norm(r.get("status")) == want]

        query = _text(q)
        if query:
            scored: List[Tuple[int, Dict[str, Any]]] = []
            for row in rows:
                score = self._score(query, row)
                if score > 0:
                    scored.append((score, row))
            scored.sort(key=lambda pair: (-pair[0], self._sort_key(pair[1])))
            rows = [r for _, r in scored]
        else:
            rows = self._sort_rows(rows)

        return [dict(r) for r in rows[: max(1, min(int(limit), 5000))]]

    def search(self, query: str, limit: int = 10, records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        pool = records if records is not None else self.records
        if not query:
            return [dict(r) for r in pool[:limit]]
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for row in pool:
            score = self._score(query, row)
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda pair: (-pair[0], self._sort_key(pair[1])))
        return [dict(r) for _, r in scored[:limit]]

    def _load_legacy_json(self) -> List[Dict[str, Any]]:
        path = self.data_dir / "legacy_jobs.json"
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = raw if isinstance(raw, list) else raw.get("jobs", []) if isinstance(raw, dict) else []
        out: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            out.append(self._normalize_record(item, "JSON"))
        return out

    def _load_csv(self, path: Path, source_kind: str) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if not isinstance(row, dict):
                        continue
                    out.append(self._normalize_record(row, source_kind))
        except Exception:
            return []
        return out

    def _normalize_record(self, raw: Dict[str, Any], source_kind: str) -> Dict[str, Any]:
        rec = dict(raw)

        customer = (
            rec.get("customer")
            or rec.get("customer_name")
            or rec.get("Company Name")
            or rec.get("Contact - Customer - Company Name")
            or rec.get("Job - Customer")
            or ""
        )
        contact = (
            rec.get("contact")
            or rec.get("contact_name")
            or rec.get("Contact Name")
            or rec.get("Contact - Name")
            or rec.get("Contact")
            or ""
        )
        address = (
            rec.get("address")
            or rec.get("Job Site Address")
            or rec.get("site")
            or rec.get("location")
            or rec.get("Job - Location")
            or ""
        )
        job_number = (
            rec.get("job_number")
            or rec.get("Job Number")
            or rec.get("Job - Job Number")
            or ""
        )
        estimate_no = (
            rec.get("estimate_no")
            or rec.get("estimate_number")
            or rec.get("Proposal Number")
            or rec.get("Estimate Number")
            or ""
        )
        invoice_no = (
            rec.get("invoice_no")
            or rec.get("invoice_number")
            or rec.get("Invoice Number")
            or ""
        )
        po_no = (
            rec.get("po_no")
            or rec.get("po_number")
            or rec.get("P.O Number")
            or rec.get("PO Number")
            or ""
        )
        date = (
            rec.get("date")
            or rec.get("scheduled_date")
            or rec.get("Date")
            or rec.get("Date Job Performed")
            or rec.get("Job - Date")
            or ""
        )

        job_notes = (
            rec.get("job_notes")
            or rec.get("tech_notes")
            or rec.get("description")
            or rec.get("Description of Problem")
            or rec.get("Description Of Problem")
            or rec.get("problem")
            or ""
        )
        work_performed = (
            rec.get("work_performed")
            or rec.get("Work Performed")
            or rec.get("completion_summary")
            or rec.get("office_notes")
            or ""
        )
        recommendations = (
            rec.get("additional_recommendations")
            or rec.get("Additional Repairs Needed/Recommended")
            or rec.get("recommended")
            or ""
        )
        parts_used = (
            rec.get("parts_used")
            or rec.get("Material Used")
            or rec.get("materials")
            or ""
        )
        status = rec.get("status") or "History"
        tech = rec.get("tech_name") or rec.get("Technician") or ""

        customer = _text(customer)
        contact = _text(contact)
        address = _text(address).replace("\r", "\n")
        job_number = _clean_num(job_number)
        estimate_no = _clean_num(estimate_no)
        invoice_no = _clean_num(invoice_no)
        po_no = _clean_num(po_no)
        date = _parse_date(date)
        job_notes = _text(job_notes)
        work_performed = _text(work_performed)
        recommendations = _text(recommendations)
        parts_used = _text(parts_used)
        status = _text(status) or "History"
        tech = _text(tech)

        richness = sum(
            1 for v in [customer, contact, address, job_number, estimate_no, invoice_no, po_no, job_notes, work_performed, recommendations, parts_used]
            if v
        )
        source_priority = {
            "BILLABLE_UPGRADED": 40,
            "BILLABLE": 30,
            "TECH_NOTES": 20,
            "JSON": 10,
        }.get(source_kind, 0)

        base = {
            "customer": customer,
            "customer_name": customer,
            "contact": contact,
            "contact_name": contact,
            "address": address,
            "job_number": job_number,
            "estimate_no": estimate_no,
            "estimate_number": estimate_no,
            "invoice_no": invoice_no,
            "invoice_number": invoice_no,
            "po_no": po_no,
            "po_number": po_no,
            "date": date,
            "status": status,
            "job_notes": job_notes,
            "description": job_notes,
            "work_performed": work_performed,
            "additional_recommendations": recommendations,
            "recommended": recommendations,
            "parts_used": parts_used,
            "materials": parts_used,
            "tech_name": tech,
            "source": "LEGACY",
            "source_detail": source_kind,
            "readonly": True,
            "kind": "legacy",
            "source_priority": source_priority,
            "richness": richness,
            "raw": dict(rec),
        }
        ident = "|".join([_compact(job_number), date, _compact(customer), _compact(contact), _compact(address), source_kind])
        base["id"] = hashlib.md5(ident.encode("utf-8")).hexdigest()[:16]
        return base

    def _merge_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for row in rows:
            job_key = _compact(row.get("job_number"))
            date_key = _text(row.get("date"))
            customer_key = _compact(row.get("customer"))
            if job_key:
                key = (job_key, date_key, customer_key)
            else:
                key = ("", date_key, customer_key + "|" + _compact(row.get("address")))

            existing = best.get(key)
            if existing is None:
                best[key] = dict(row)
                continue

            merged = dict(existing)
            for field in [
                "customer", "customer_name", "contact", "contact_name", "address",
                "job_number", "estimate_no", "estimate_number", "invoice_no", "invoice_number",
                "po_no", "po_number", "date", "status", "tech_name",
            ]:
                if not _text(merged.get(field)) and _text(row.get(field)):
                    merged[field] = row.get(field)

            for field in ["job_notes", "work_performed", "additional_recommendations", "parts_used"]:
                old = _text(merged.get(field))
                new = _text(row.get(field))
                if new and new.lower() not in old.lower():
                    merged[field] = (old + ("\n\n" if old and new else "") + new).strip()

            # richer source metadata wins
            if int(row.get("source_priority") or 0) >= int(existing.get("source_priority") or 0):
                merged["source_detail"] = row.get("source_detail") or merged.get("source_detail")
            merged["source"] = "LEGACY"
            merged["readonly"] = True
            merged["kind"] = "legacy"
            merged["richness"] = max(int(existing.get("richness") or 0), int(row.get("richness") or 0))
            best[key] = merged

        merged_rows = list(best.values())
        for r in merged_rows:
            ident = "|".join([
                _compact(r.get("job_number")),
                _text(r.get("date")),
                _compact(r.get("customer")),
                _compact(r.get("address")),
                _compact(r.get("estimate_no")),
                _compact(r.get("invoice_no")),
                _compact(r.get("po_no")),
            ])
            r["id"] = hashlib.md5(ident.encode("utf-8")).hexdigest()[:16]
        return self._sort_rows(merged_rows)

    def _score(self, query: str, rec: Dict[str, Any]) -> int:
        q = _text(query)
        if not q:
            return 0

        qnorm = _norm(q)
        qcompact = _compact(q)
        qdigits = _digits(q)

        customer = _norm(rec.get("customer"))
        contact = _norm(rec.get("contact"))
        job_number = _text(rec.get("job_number"))
        estimate = _text(rec.get("estimate_no"))
        invoice = _text(rec.get("invoice_no"))
        po_no = _text(rec.get("po_no"))

        c_job = _compact(job_number)
        c_est = _compact(estimate)
        c_inv = _compact(invoice)
        c_po = _compact(po_no)

        score = 0

        if qcompact:
            if qcompact == c_job:
                score += 1000
            elif c_job.startswith(qcompact) and len(qcompact) >= 4:
                score += 820

            if qcompact == c_est:
                score += 980
            if qcompact == c_inv:
                score += 980
            if qcompact == c_po:
                score += 980

        if qdigits:
            if qdigits and qdigits == _digits(estimate):
                score += 920
            if qdigits and qdigits == _digits(invoice):
                score += 920
            if qdigits and qdigits == _digits(po_no):
                score += 920

        if qnorm:
            if qnorm == customer:
                score += 700
            elif qnorm in customer:
                score += 540
            if qnorm == contact:
                score += 620
            elif qnorm in contact:
                score += 460

        tokens = [t for t in qnorm.split() if len(t) > 1]
        if tokens:
            cust_hits = sum(1 for t in tokens if t in customer)
            contact_hits = sum(1 for t in tokens if t in contact)
            score += cust_hits * 90 + contact_hits * 80

        return score

    def _sort_key(self, row: Dict[str, Any]) -> Tuple[int, str, str, str]:
        has_job = 0 if _text(row.get("job_number")) else 1
        date_key = _text(row.get("date"))
        cust = _norm(row.get("customer"))
        job = _text(row.get("job_number"))
        return (has_job, date_key, cust, job)

    def _sort_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        with_job = [r for r in rows if _text(r.get("job_number"))]
        no_job = [r for r in rows if not _text(r.get("job_number"))]
        with_job = sorted(with_job, key=lambda r: (_text(r.get("date")), _text(r.get("job_number"))), reverse=True)
        no_job = sorted(no_job, key=lambda r: (_norm(r.get("customer")), _text(r.get("date"))), reverse=False)
        return with_job + no_job


# patched helpers
