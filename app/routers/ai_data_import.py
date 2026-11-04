"""Review-first CSV import for Doorks and SDC workspace records.

Never touches PDS legacy files or any existing record. Imports append only after
explicit confirmation and reject duplicates using a chosen identifying column.
"""
from __future__ import annotations
import csv, io, json, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from app.routers import workspaces

router=APIRouter(prefix="/ai-data-import",tags=["ai-data-import"])
lock=RLock()
ALLOWED={
    "doorks": {"customers","vendors","work_orders","estimates_invoices","purchase_orders","inventory"},
    "sdc": {"customers","vendors","orders","products","purchase_orders","inventory"}
}
# Only collections supported by the installed workspaces backend may be committed.
IDENTITY={"customers":"name","vendors":"name","products":"sku","inventory":"part_number",
          "work_orders":"work_order_number","orders":"order_id",
          "estimates_invoices":"document_number","purchase_orders":"po_number"}

def guard(request,platform,kind):
    if platform not in ALLOWED or kind not in ALLOWED[platform]:
        raise HTTPException(400,"Unsupported import destination")
    if not getattr(request.state,"auth_user",None):
        raise HTTPException(401,"Login required")
    if getattr(request.state,"auth_role",None)!="office_admin":
        raise HTTPException(403,"Office Admin only")
    if request.session.get("active_platform")!=platform:
        raise HTTPException(403,"Switch to the destination workspace first")

def base_dir(request,platform):
    path=Path(request.app.state.data_dir)/"business_workspaces"/platform/"import_staging"
    path.mkdir(parents=True,exist_ok=True)
    return path

# CSV migration: accept UTF-8 BOM, Excel-style Windows exports and one-column lists.
# Keep the upload bounded while supporting real customer and job exports.
MAX_CSV_BYTES = 32 * 1024 * 1024
MAX_CSV_ROWS = 50000

def csv_rows(blob):
    import re
    try:
        try:
            text = blob.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Older Excel/Quickbase exports can use Windows-1252.
            text = blob.decode("cp1252")
        if not text.strip():
            raise ValueError("CSV is empty")
        sample = text[:16384]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            # One-column customer lists are valid; otherwise prefer the most
            # common separator in the first nonempty physical header line.
            first = next((line for line in sample.splitlines() if line.strip()), "")
            delimiter = max((",", ";", "\t", "|"), key=lambda c: first.count(c))
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        original = next(reader, None)
        if not original or not any(str(h).strip() for h in original):
            raise ValueError("Missing CSV headers")
        # Do not reject real-world headings such as 'Customer - Company Name'.
        # Disambiguate colliding normalized names rather than dropping data.
        headers = []
        used = set()
        for index, heading in enumerate(original, 1):
            name = re.sub(r"[^a-z0-9]+", "_", str(heading).strip().casefold()).strip("_")[:70]
            name = name or "column_" + str(index)
            unique = name
            suffix = 2
            while unique in used:
                unique = name[:65] + "_" + str(suffix)
                suffix += 1
            headers.append(unique)
            used.add(unique)
        protected = {"id", "created_at", "updated_at", "authorization_status", "authorized_by", "authorized_at", "unauthorized_by", "unauthorized_at"}
        rows = []
        for row in reader:
            if not any(str(v).strip() for v in row):
                continue
            if len(row) > len(headers):
                raise ValueError("Row " + str(reader.line_num) + " has more fields than the header. Check the file delimiter or quotation marks")
            mapped = {key: str(row[i]).strip()[:4000] if i < len(row) else "" for i, key in enumerate(headers) if key not in protected}
            if any(mapped.values()):
                rows.append(workspaces.clean(mapped))
            if len(rows) > MAX_CSV_ROWS:
                raise ValueError("More than 50,000 records; split into batches of 50,000 rows")
        if not rows:
            raise ValueError("No nonempty data rows found")
        return [h for h in headers if h not in protected], rows
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(400, str(exc))

@router.post("/{platform}/{kind}/preview")
async def preview(platform:str,kind:str,request:Request,file:UploadFile=File(...)):
    guard(request,platform,kind)
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400,"This first import phase accepts CSV files only")
    blob=await file.read(MAX_CSV_BYTES + 1)
    if len(blob)>MAX_CSV_BYTES:raise HTTPException(413,"CSV exceeds 32 MB. Split the file into smaller batches")
    headers,rows=csv_rows(blob)
    token=uuid.uuid4().hex
    stage={"platform":platform,"kind":kind,"filename":Path(file.filename or "").name,
           "created_at":datetime.now(timezone.utc).isoformat(),
           "user":str((getattr(request.state,"auth_user",None) or {}).get("id","")),
           "headers":headers,"rows":rows}
    path=base_dir(request,platform)/(token+".json")
    workspaces.save(path,[stage])
    return {"token":token,"filename":stage["filename"],"columns":headers,"count":len(rows),"sample":rows[:8],
            "note":"Preview only. No records have been changed."}

@router.post("/{platform}/{kind}/ai-preview")
async def ai_preview(platform:str,kind:str,request:Request,file:UploadFile=File(...)):
    guard(request,platform,kind)
    from app.routers import workspace_ai
    if (platform,kind) not in workspace_ai.FIELDS:
        raise HTTPException(400,"AI extraction is not available for this destination")
    if not (file.filename or "").lower().endswith((".pdf",".png",".jpg",".jpeg",".webp")):
        raise HTTPException(400,"AI preview supports PDF, JPG, PNG and WEBP in this release")
    extracted=await workspace_ai.extract(platform,kind,request,file=file,email_text="")
    row={k:v for k,v in extracted["fields"].items() if v}
    if not row:raise HTTPException(422,"No usable fields found in document")
    token=uuid.uuid4().hex
    stage={"platform":platform,"kind":kind,"filename":Path(file.filename or "document").name,
           "created_at":datetime.now(timezone.utc).isoformat(),
           "user":str((getattr(request.state,"auth_user",None) or {}).get("id","")),
           "headers":list(extracted["fields"]),"rows":[row]}
    workspaces.save(base_dir(request,platform)/(token+".json"),[stage])
    return {"token":token,"filename":stage["filename"],"columns":stage["headers"],
            "count":1,"sample":[row],"note":"AI proposed one record. Review carefully before approving; no data has changed."}

class ColumnMapping(BaseModel):
    token: str
    mapping: dict[str, str]

@router.post("/{platform}/{kind}/map-preview")
def map_preview(platform: str, kind: str, request: Request, payload: ColumnMapping):
    guard(request, platform, kind)
    if len(payload.token)!=32 or any(c not in '0123456789abcdef' for c in payload.token):
        raise HTTPException(400,'Invalid preview token')
    with lock, workspaces._lock:
        path=base_dir(request,platform)/(payload.token+'.json')
        if not path.exists():raise HTTPException(404,'Preview not found')
        stage=workspaces.load(path)[0]
        user=str((getattr(request.state,'auth_user',None) or {}).get('id',''))
        if stage.get('platform')!=platform or stage.get('kind')!=kind or stage.get('user')!=user:
            raise HTTPException(403,'Preview ownership mismatch')
        from datetime import timedelta
        if datetime.now(timezone.utc)-datetime.fromisoformat(stage['created_at'])>timedelta(hours=12):
            path.unlink(missing_ok=True);raise HTTPException(410,'Preview expired')
        sources=set(stage.get('headers',[])); forbidden={'id','created_at','updated_at','authorization_status','authorized_by','authorized_at','unauthorized_by','unauthorized_at'}
        mapping={s:t for s,t in payload.mapping.items() if t}
        if not mapping or set(mapping)-sources or len(set(mapping.values()))!=len(mapping):
            raise HTTPException(400,'Invalid or duplicate column mapping')
        permitted={
            'customers':{'name','contact','email','phone','address','customer_type','preferred_visit_type','notes'},
            'vendors':{'name','contact','email','phone','address','service_area','trade','vendor_type','onboarding_status','license_number','license_expiration','insurance_expiration','payment_terms','tax_form_status','notes'},
            'inventory':{'supplier','part_number','description','quantity','unit_cost','notes'},
            'products':{'name','sku','price','description'},
            'work_orders':{'customer','contact','phone','email','address','service_type','scheduled_date','scheduled_time','description','status','priority','notes'},
            'estimates_invoices':{'customer','work_order_number','document_type','document_number','date','amount','status','description','notes'},
            'purchase_orders':{'po_number','vendor','vendor_id','customer','work_order_number','date','expected_date','description','quantity','unit_cost','amount','status','notes'},
            'orders':{'customer','item','order_date','status','total','shipping','tax','notes'}
        }.get(kind,set())
        if set(mapping.values())-permitted or set(mapping.values())&forbidden:
            raise HTTPException(400,'Unsupported or protected destination fields')
        identity=IDENTITY.get(kind)
        if identity and identity not in mapping.values():
            raise HTTPException(400,'Map required identity field: '+identity)
        rows=[{dest:str(row.get(source,'')).strip() for source,dest in mapping.items()} for row in stage['rows']]
        stage['headers']=list(mapping.values());stage['rows']=rows
        workspaces.save(path,[stage])
        return {'token':payload.token,'columns':stage['headers'],'count':len(rows),'sample':rows[:8],'note':'Mapped preview saved; no records imported'}

class PreviewEdit(BaseModel):
    token: str
    rows: list[dict[str, str]]

@router.post("/{platform}/{kind}/edit-preview")
def edit_preview(platform: str, kind: str, request: Request, payload: PreviewEdit):
    guard(request, platform, kind)
    if len(payload.token) != 32 or not all(c in "0123456789abcdef" for c in payload.token):
        raise HTTPException(400, "Invalid preview token")
    with lock, workspaces._lock:
        stage_path = base_dir(request, platform) / (payload.token + ".json")
        if not stage_path.exists():
            raise HTTPException(404, "Preview not found or already processed")
        stage = workspaces.load(stage_path)[0]
        user_id = str((getattr(request.state, "auth_user", None) or {}).get("id", ""))
        if stage.get("platform") != platform or stage.get("kind") != kind or stage.get("user") != user_id:
            raise HTTPException(403, "Preview ownership mismatch")
        from datetime import timedelta
        if datetime.now(timezone.utc) - datetime.fromisoformat(stage["created_at"]) > timedelta(hours=12):
            stage_path.unlink(missing_ok=True)
            raise HTTPException(410, "Preview expired; upload again")
        original_rows = stage.get("rows", [])
        columns = stage.get("headers", [])
        if not isinstance(original_rows, list) or not isinstance(columns, list):
            raise HTTPException(400, "Invalid preview")
        if len(payload.rows) != min(8, len(original_rows)):
            raise HTTPException(400, "Edited row count does not match the preview")
        forbidden = {"id", "created_at", "updated_at", "authorization_status", "authorized_by", "authorized_at", "unauthorized_by", "unauthorized_at"}
        allowed_columns = set(columns) - forbidden
        for i, row in enumerate(payload.rows):
            if set(row) - allowed_columns:
                raise HTTPException(400, "Unrecognized or protected column")
            if any(not isinstance(value, str) or len(value) > 4000 for value in row.values()):
                raise HTTPException(400, "Invalid field value")
            original_rows[i] = {key: str(row.get(key, "")).strip() for key in columns if key in allowed_columns}
        stage["rows"] = original_rows
        workspaces.save(stage_path, [stage])
        return {"ok": True, "updated_rows": len(payload.rows), "message": "Preview corrected; no records imported"}


# Revision 50: read-only duplicate preflight and durable import batch history.
def _identity_value(row, key):
    return str(row.get(key, "") or "").strip().casefold()

def _preview_status(stage, existing, kind):
    key = IDENTITY.get(kind)
    seen = {_identity_value(r, key) for r in existing} if key else set()
    seen.discard("")
    valid, duplicates, missing = 0, [], []
    for index, row in enumerate(stage.get("rows", []), 1):
        value = _identity_value(row, key) if key else ""
        if key and not value:
            missing.append(index)
        elif value and value in seen:
            duplicates.append(index)
        else:
            valid += 1
            if value: seen.add(value)
    return {"count": len(stage.get("rows", [])), "eligible": valid,
            "duplicate_count": len(duplicates), "duplicate_rows": duplicates[:100],
            "missing_identity_count": len(missing), "missing_identity_rows": missing[:100],
            "identity_field": key, "numbered_preview_only": kind in {"work_orders","purchase_orders","estimates_invoices","orders"}}

def _history_path(request, platform):
    return base_dir(request, platform) / "import_history.json"

@router.get("/{platform}/history")
def import_history(platform: str, request: Request):
    if platform not in ALLOWED: raise HTTPException(400, "Invalid workspace")
    guard(request, platform, next(iter(ALLOWED[platform])))
    with lock, workspaces._lock:
        items = workspaces.load(_history_path(request, platform))
        return {"items": list(reversed(items[-100:]))}

class Preflight(BaseModel):
    token: str

@router.post("/{platform}/{kind}/preflight")
def import_preflight(platform: str, kind: str, request: Request, payload: Preflight):
    guard(request, platform, kind)
    if len(payload.token) != 32 or any(c not in "0123456789abcdef" for c in payload.token):
        raise HTTPException(400, "Invalid preview token")
    with lock, workspaces._lock:
        path = base_dir(request, platform) / (payload.token + ".json")
        if not path.exists(): raise HTTPException(404, "Preview not found")
        stage = workspaces.load(path)[0]
        user = str((getattr(request.state, "auth_user", None) or {}).get("id", ""))
        if stage.get("platform") != platform or stage.get("kind") != kind or stage.get("user") != user:
            raise HTTPException(403, "Preview ownership mismatch")
        from datetime import timedelta
        if datetime.now(timezone.utc) - datetime.fromisoformat(stage["created_at"]) > timedelta(hours=12):
            path.unlink(missing_ok=True)
            raise HTTPException(410, "Preview expired")
        return _preview_status(stage, workspaces.load(workspaces.location(request, platform, kind)), kind)

class Approval(BaseModel):
    token:str
    confirm:bool=False

@router.post("/{platform}/{kind}/approve")
def approve(platform:str,kind:str,request:Request,payload:Approval):
    guard(request,platform,kind)
    if not payload.confirm:raise HTTPException(400,"Explicit confirmation required")
    if len(payload.token)!=32 or not all(c in "0123456789abcdef" for c in payload.token):
        raise HTTPException(400,"Invalid preview token")
    with lock,workspaces._lock:
        stage_path=base_dir(request,platform)/(payload.token+".json")
        if not stage_path.exists():raise HTTPException(404,"Preview not found or already processed")
        stage=workspaces.load(stage_path)[0]
        if stage["platform"]!=platform or stage["kind"]!=kind or stage["user"]!=str((getattr(request.state,"auth_user",None) or {}).get("id","")):
            raise HTTPException(403,"Preview ownership mismatch")
        from datetime import timedelta
        if datetime.now(timezone.utc)-datetime.fromisoformat(stage["created_at"])>timedelta(hours=12):
            stage_path.unlink(missing_ok=True)
            raise HTTPException(410,"Preview expired; upload again")
        # Preserve existing numbering and business logic: generated identifiers
        # are not imported into active numbered collections.
        if kind in {"work_orders","purchase_orders","estimates_invoices","orders"}:
            raise HTTPException(400,"Numbered business records require a dedicated mapping workflow; preview is available but direct import is disabled")
        dest=workspaces.location(request,platform,kind)
        existing=workspaces.load(dest)
        key=IDENTITY.get(kind)
        seen={str(r.get(key,"")).strip().casefold() for r in existing if r.get(key)} if key else set()
        added=0;duplicates=0;added_ids=[]
        for row in stage["rows"]:
            value=str(row.get(key,"")).strip().casefold() if key else ""
            if key and not value:
                duplicates+=1;continue
            if value and value in seen:
                duplicates+=1;continue
            if value:seen.add(value)
            new_id=uuid.uuid4().hex
            existing.append({"id":new_id,"created_at":datetime.now(timezone.utc).isoformat(),**row})
            added_ids.append(new_id)
            added+=1
        # Save the destination first. If history cannot be written, do not claim
        # that the import failed (and invite a second submission); return a warning.
        batch_id = uuid.uuid4().hex
        
        workspaces.save(dest, existing)
        history_warning = None
        try:
            history_path = _history_path(request, platform)
            history = workspaces.load(history_path)
            history.append({"batch_id": batch_id, "platform": platform, "kind": kind,
                            "filename": stage.get("filename", ""),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "user": stage.get("user", ""), "added": added,
                            "duplicates_skipped": duplicates,
                            "created_record_ids": added_ids,
                            "recovery_note": "Review IDs before any manual recovery. No automatic destructive rollback."})
            workspaces.save(history_path, history)
        except Exception:
            history_warning = "Records were saved, but import history could not be written. Do not retry without checking the destination."
        stage_path.unlink(missing_ok=True)
        return {"added": added, "duplicates_skipped": duplicates,
                "destination": kind, "batch_id": batch_id, "warning": history_warning}
