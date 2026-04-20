from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.storage import bootstrap_data_dir, bootstrap_data_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> List[str]:
    text = str(text or "").replace("\r", "")
    if not text:
        return [""]
    out: List[str] = []
    for raw_line in text.splitlines() or [""]:
        words = raw_line.split()
        if not words:
            out.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if stringWidth(trial, font_name, font_size) <= max_width:
                current = trial
            else:
                out.append(current)
                current = word
        out.append(current)
    return out or [""]


class DocumentsStore:
    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.dir = bootstrap_data_dir(self.project_root, "documents")
        self.index_path = bootstrap_data_file(self.project_root, "documents_index.json")
        self.dir.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _ensure(self):
        base = {
            "version": 4,
            "estimate_next": 1,
            "invoice_next": 1,
            "items": [],
        }
        cur = _read_json(self.index_path, base)
        if not isinstance(cur, dict):
            cur = base
        for k, v in base.items():
            cur.setdefault(k, v)
        if not isinstance(cur.get("items"), list):
            cur["items"] = []
        _write_json(self.index_path, cur)

    def _load(self) -> Dict[str, Any]:
        self._ensure()
        data = _read_json(self.index_path, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("estimate_next", 1)
        data.setdefault("invoice_next", 1)
        data.setdefault("items", [])
        if not isinstance(data["items"], list):
            data["items"] = []
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        _write_json(self.index_path, data)

    def _next_number(self, doc_type: str) -> str:
        data = self._load()
        if doc_type == "estimate":
            n = int(data.get("estimate_next", 1))
            data["estimate_next"] = n + 1
            self._save(data)
            return f"RE{n:05d}"
        if doc_type == "invoice":
            n = int(data.get("invoice_next", 1))
            data["invoice_next"] = n + 1
            self._save(data)
            return f"JS{n:05d}"
        raise ValueError("Unknown doc_type")

    def list_documents(self, job_id: str = "") -> List[Dict[str, Any]]:
        data = self._load()
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if job_id and str(item.get("job_id") or "") != str(job_id):
                continue
            out.append(item)
        out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return out

    def get_document(self, filename: str) -> Optional[Dict[str, Any]]:
        for item in self._load().get("items", []):
            if str(item.get("filename") or "") == str(filename):
                return item
        return None

    def _write_box(self, c: canvas.Canvas, x: float, y_top: float, w: float, h: float, title: str) -> None:
        c.setStrokeColor(colors.HexColor("#d1d5db"))
        c.setLineWidth(1)
        c.roundRect(x, y_top - h, w, h, 8, stroke=1, fill=0)
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 10, y_top - 15, title)

    def _write_pdf(self, path: Path, doc_type: str, payload: Dict[str, Any], number: str) -> None:
        c = canvas.Canvas(str(path), pagesize=letter)
        page_w, page_h = letter
        left = 42
        right = page_w - 42
        content_w = right - left
        y = page_h - 44

        brand = "PRIORITY DOOR SYSTEMS"
        subbrand = "836 W. Washington Ave. - Escondido, CA 92025 - 760-233-5037 - www.prioritydoors.com"
        title = "INVOICE" if doc_type == "invoice" else "ESTIMATE"

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(left, y, brand)
        y -= 16
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#4b5563"))
        c.drawString(left, y, subbrand)

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(right, page_h - 44, title)

        top_box_y = page_h - 96
        left_box_w = 300
        right_box_w = 220
        box_h = 86

        self._write_box(c, left, top_box_y, left_box_w, box_h, "Customer")
        self._write_box(c, right - right_box_w, top_box_y, right_box_w, box_h, "Document Info")

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#111827"))
        customer_lines = _wrap_text(f"{payload.get('customer') or ''}\n{payload.get('address') or ''}", "Helvetica", 10, left_box_w - 20)
        cy = top_box_y - 30
        for line in customer_lines[:4]:
            c.drawString(left + 10, cy, line[:80])
            cy -= 12

        info_lines = [
            ("Date", str(payload.get("date") or "")),
            ("Number", number),
            ("Prepared By", str(payload.get("completed_by") or "")),
            ("PO #", str(payload.get("po_number") or "")),
            ("Job #", str(payload.get("job_number") or "")),
        ]
        iy = top_box_y - 30
        c.setFont("Helvetica", 9)
        for label, value in info_lines:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(right - right_box_w + 10, iy, f"{label}:")
            c.setFont("Helvetica", 9)
            c.drawString(right - right_box_w + 74, iy, value[:26])
            iy -= 11
            if iy < top_box_y - box_h + 14:
                break

        y = top_box_y - box_h - 16

        work_title = "Work Scope" if doc_type == "estimate" else "Work Performed"
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(page_w / 2, y, work_title)
        y -= 18
        c.setFont("Helvetica", 10)
        work_lines = _wrap_text(str(payload.get("work") or ""), "Helvetica", 10, content_w - 12)
        if not work_lines:
            work_lines = [""]
        line_h = 12
        for idx, line in enumerate(work_lines):
            if y < 84:
                c.showPage()
                y = page_h - 50
                c.setFillColor(colors.HexColor("#111827"))
                c.setFont("Helvetica-Bold", 11)
                cont_title = f"{work_title} (continued)" if idx < len(work_lines) else work_title
                c.drawCentredString(page_w / 2, y, cont_title)
                y -= 18
                c.setFont("Helvetica", 10)
            c.drawString(left, y, line[:180])
            y -= line_h

        y -= 12

        items = payload.get("items") or []
        normalized_items: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            qty = _safe_float(item.get("qty"))
            rate = _safe_float(item.get("rate"))
            total = qty * rate
            kind = str(item.get("kind") or "other").lower()
            normalized_items.append({
                "code": str(item.get("code") or ""),
                "description": str(item.get("description") or ""),
                "qty": qty,
                "rate": rate,
                "total": total,
                "kind": kind,
                "taxable": bool(item.get("taxable", True)),
            })

        headers = [("Item", 46), ("Description", 118), ("Qty", 385), ("Price", 437), ("Amount", 520)]
        row_h = 18

        def draw_items_header(draw_y: float) -> float:
            c.setFillColor(colors.HexColor("#f3f4f6"))
            c.roundRect(left, draw_y - row_h, content_w, row_h, 6, stroke=0, fill=1)
            c.setFillColor(colors.HexColor("#111827"))
            c.setFont("Helvetica-Bold", 9)
            for label, x in headers:
                c.drawString(x, draw_y - 12, label)
            return draw_y - row_h - 4

        y = draw_items_header(y)

        c.setFont("Helvetica", 9)
        for item in normalized_items:
            desc_lines = _wrap_text(item["description"], "Helvetica", 9, 250)
            needed_h = max(1, len(desc_lines)) * 11 + 6
            if y - needed_h < 150:
                c.showPage()
                y = page_h - 60
                y = draw_items_header(y)
                c.setFont("Helvetica", 9)

            c.setStrokeColor(colors.HexColor("#e5e7eb"))
            c.line(left, y - needed_h, right, y - needed_h)
            c.drawString(46, y - 12, item["code"][:18])
            line_y = y - 12
            for line in desc_lines[:6]:
                c.drawString(118, line_y, line[:72])
                line_y -= 11
            c.drawRightString(416, y - 12, f"{item['qty']:g}")
            c.drawRightString(492, y - 12, f"${item['rate']:,.2f}")
            c.drawRightString(right - 6, y - 12, f"${item['total']:,.2f}")
            y -= needed_h

        subtotal = sum(item["total"] for item in normalized_items)
        taxable = sum(item["total"] for item in normalized_items if item["taxable"])
        tax_rate = _safe_float(payload.get("tax_rate"))
        tax = taxable * (tax_rate / 100.0)
        total = subtotal + tax

        if y < 140:
            c.showPage()
            y = page_h - 60

        y -= 16
        summary_w = 250
        summary_h = 78
        self._write_box(c, right - summary_w, y, summary_w, summary_h, "Totals")

        ty = y - 30
        total_rows = [
            ("Subtotal", subtotal),
            (f"Sales Tax ({tax_rate:.2f}%)", tax),
            ("Total", total),
        ]
        for idx, (label, value) in enumerate(total_rows):
            c.setFont("Helvetica-Bold" if idx == len(total_rows) - 1 else "Helvetica", 9 if idx < 2 else 10)
            c.drawString(right - summary_w + 10, ty, label)
            c.drawRightString(right - 10, ty, f"${value:,.2f}")
            ty -= 16 if idx == 1 else 14
        c.showPage()
        c.save()

    def _build_item(self, doc_type: str, number: str, filename: str, path: Path, payload: Dict[str, Any], created_at: Optional[str] = None) -> Dict[str, Any]:
        return {
            "type": doc_type,
            "number": number,
            "filename": filename,
            "path": str(path),
            "job_id": str(payload.get("job_id") or ""),
            "customer": str(payload.get("customer") or ""),
            "address": str(payload.get("address") or ""),
            "ship_to": str(payload.get("ship_to") or ""),
            "po_number": str(payload.get("po_number") or ""),
            "job_number": str(payload.get("job_number") or ""),
            "invoice_number": str(payload.get("invoice_number") or ""),
            "completed_by": str(payload.get("completed_by") or ""),
            "tax_rate": float(payload.get("tax_rate") or 0.0),
            "items": payload.get("items") or [],
            "work": str(payload.get("work") or ""),
            "labor": str(payload.get("labor") or ""),
            "parts": str(payload.get("parts") or ""),
            "date": str(payload.get("date") or ""),
            "created_at": created_at or _now_iso(),
            "updated_at": _now_iso(),
        }

    def create_pdf(self, doc_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        requested_number = str(payload.get("number") or "").strip()
        number = requested_number or self._next_number(doc_type)
        filename = f"{number}.pdf"
        path = self.dir / filename
        self._write_pdf(path, doc_type, payload, number)
        item = self._build_item(doc_type, number, filename, path, payload)
        data = self._load()
        items = [x for x in data.get("items", []) if str(x.get("filename") or "") != filename]
        items.append(item)
        data["items"] = items
        self._save(data)
        return item

    def update_document(self, filename: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_document(filename)
        if not existing:
            raise KeyError("Document not found")
        doc_type = str(payload.get("type") or existing.get("type") or "estimate")
        number = str(payload.get("number") or existing.get("number") or "").strip()
        if not number:
            number = self._next_number(doc_type)
        new_filename = f"{number}.pdf"
        new_path = self.dir / new_filename
        merged = dict(existing)
        merged.update(payload)
        merged["type"] = doc_type
        merged["number"] = number
        self._write_pdf(new_path, doc_type, merged, number)
        item = self._build_item(doc_type, number, new_filename, new_path, merged, created_at=str(existing.get("created_at") or _now_iso()))

        data = self._load()
        items = []
        for row in data.get("items", []):
            if str(row.get("filename") or "") == str(filename):
                continue
            items.append(row)
        items.append(item)
        data["items"] = items
        self._save(data)
        old_path = self.dir / filename
        if old_path.exists() and old_path.name != new_filename:
            try:
                old_path.unlink()
            except Exception:
                pass
        return item

    def delete_document(self, filename: str) -> None:
        data = self._load()
        items = data.get("items", [])
        kept = [x for x in items if str(x.get("filename") or "") != str(filename)]
        if len(kept) == len(items):
            raise KeyError("Document not found")
        data["items"] = kept
        self._save(data)
        path = self.dir / filename
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
