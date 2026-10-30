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

def csv_rows(blob):
    try:
        text=blob.decode("utf-8-sig")
        dialect=csv.Sniffer().sniff(text[:8192],delimiters=",;\\t")
        reader=csv.DictReader(io.StringIO(text),dialect=dialect)
        if not reader.fieldnames:raise ValueError("Missing headers")
        headers=[str(h or "").strip().lower().replace(" ","_") for h in reader.fieldnames]
        if len(headers)!=len(set(headers)) or any(not h.replace("_","").isalnum() or len(h)>40 for h in headers):
            raise ValueError("Invalid or repeated column names")
        rows=[]
        for row in reader:
            if None in row:raise ValueError("Unexpected extra columns")
            mapped={headers[i]:str(row.get(h) or "").strip()[:4000] for i,h in enumerate(reader.fieldnames) if headers[i] not in {"id","created_at","updated_at","authorization_status","authorized_by","authorized_at","unauthorized_by","unauthorized_at"}}
            if any(mapped.values()):rows.append(workspaces.clean(mapped))
            if len(rows)>1000:raise ValueError("Maximum 1000 rows per upload")
        if not rows:raise ValueError("No data rows found")
        return headers,rows
    except (UnicodeDecodeError,csv.Error,ValueError) as exc:
        raise HTTPException(400,str(exc))

@router.post("/{platform}/{kind}/preview")
async def preview(platform:str,kind:str,request:Request,file:UploadFile=File(...)):
    guard(request,platform,kind)
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400,"This first import phase accepts CSV files only")
    blob=await file.read(2_000_001)
    if len(blob)>2_000_000:raise HTTPException(413,"File exceeds 2 MB")
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
        added=0;duplicates=0
        for row in stage["rows"]:
            value=str(row.get(key,"")).strip().casefold() if key else ""
            if key and not value:
                duplicates+=1;continue
            if value and value in seen:
                duplicates+=1;continue
            if value:seen.add(value)
            existing.append({"id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),**row})
            added+=1
        workspaces.save(dest,existing)
        stage_path.unlink()
        return {"added":added,"duplicates_skipped":duplicates,"destination":kind}
