"""Isolated Doorks/SDC workspace records. PDS stores are never read or written."""
from __future__ import annotations
import json, os, uuid, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router=APIRouter(prefix="/workspaces",tags=["workspaces"])
_lock=RLock()
KINDS={"doorks":("customers","vendors","addresses","work_orders","estimates_invoices","purchase_orders","customer_inquiries","vendor_assignments","expenses","receivables","inventory","employees","payroll","stock_adjustments"),"sdc":("customers","vendors","addresses","purchase_orders","estimates_invoices","orders","software_leads","products","expenses","receivables","inventory")}
class Record(BaseModel):
    data:dict

def guard(request:Request,platform:str,kind:str):
    if platform not in KINDS or kind not in KINDS[platform]:raise HTTPException(404,"Unknown workspace collection")
    user=getattr(request.state,"auth_user",None)
    if not user:raise HTTPException(401,"Login required")
    # Phase 2A is admin-only until employee assignments and role enforcement are deployed.
    if getattr(request.state,"auth_role",None)!="office_admin":raise HTTPException(403,"Office Admin only during setup")
    if request.session.get("active_platform")!=platform:raise HTTPException(403,"Switch to this workspace first")

def location(request:Request,platform:str,kind:str):
    base=Path(request.app.state.data_dir)/"business_workspaces"/platform
    base.mkdir(parents=True,exist_ok=True)
    return base/(kind+".json")

def load(path):
    if not path.exists():return []
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,list):raise HTTPException(500,"Invalid workspace storage")
    return data

def save(path,records):
    temp=path.with_name(path.name+".tmp")
    with temp.open("w",encoding="utf-8") as f:
        json.dump(records,f,indent=2,ensure_ascii=False)
        f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def clean(data):
    if not isinstance(data,dict) or len(data)>30:raise HTTPException(400,"Invalid record")
    out={}
    for key,value in data.items():
        if not isinstance(key,str) or not key.replace("_","").isalnum() or len(key)>40:raise HTTPException(400,"Invalid field")
        if not isinstance(value,(str,int,float,bool,type(None))):raise HTTPException(400,"Invalid field value")
        if isinstance(value,str) and len(value)>4000:raise HTTPException(400,"Field too long")
        out[key]=value
    return out

@router.get("/{platform}/{kind}")
def listing(platform:str,kind:str,request:Request):
    guard(request,platform,kind)
    with _lock:return {"items":load(location(request,platform,kind))}

@router.post("/{platform}/{kind}")
def create(platform:str,kind:str,payload:Record,request:Request):
    guard(request,platform,kind)
    if platform=='doorks' and kind=='payroll':raise HTTPException(409,'Use calculated Doorks timecard endpoint')
    with _lock:
        path=location(request,platform,kind);items=load(path)
        data=clean(payload.data)
        for k in ("authorization_status","authorized_by","authorized_at","unauthorized_by","unauthorized_at"):data.pop(k,None)
        if kind=="purchase_orders":
            # PO numbers are assigned server-side and are never reused after deletion.
            counter_path=path.parent/"purchase_order_sequence.json"
            current=0
            if counter_path.exists():
                current=int(json.loads(counter_path.read_text(encoding="utf-8")).get("last",0))
            for existing in items:
                match=re.fullmatch(r"PO-(\d+)",str(existing.get("po_number","")))
                if match:current=max(current,int(match.group(1)))
            data.pop("po_number",None)
            data["po_number"]=f"PO-{current+1:05d}"
            tmp=counter_path.with_suffix(".tmp")
            with tmp.open("w",encoding="utf-8") as f:
                json.dump({"last":current+1},f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,counter_path)
        if platform=="doorks" and kind=="work_orders":
            # Calendar-month sequence, date prefix in workspace-local time.
            # Reserve before writing the record to prevent number reuse after deletion.
            now_local=datetime.now(ZoneInfo("America/Los_Angeles"))
            month_key=now_local.strftime("%Y-%m")
            counter_path=path.parent/"work_order_monthly_sequence.json"
            state={}
            if counter_path.exists():
                state=json.loads(counter_path.read_text(encoding="utf-8"))
                if not isinstance(state,dict):raise HTTPException(500,"Invalid work order counter")
            current=int(state.get(month_key,0))
            # Account for records created with this scheme even if counter was lost.
            for existing in items:
                created=str(existing.get("created_at",""))
                if not str(existing.get("job_number", "")).startswith(now_local.strftime("%m%y")+"-"):continue
                match=re.fullmatch(r"\d{4}-(\d+)",str(existing.get("job_number", "")))
                if match:current=max(current,int(match.group(1)))
            current+=1
            data.pop("work_order_number",None)
            data.pop("job_number",None)
            data["job_number"]=f"{now_local:%m%y}-{current:02d}"
            state[month_key]=current
            tmp=counter_path.with_suffix(".tmp")
            with tmp.open("w",encoding="utf-8") as f:
                json.dump(state,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,counter_path)
        item={"id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),**data}
        
        if kind in ("work_orders","orders") and data.get("source_estimate_id"):
            existing=next((x for x in items if x.get("source_estimate_id")==data["source_estimate_id"]),None)
            if existing:raise HTTPException(409,"This estimate already has a linked fulfillment record")
        if kind=="expenses":item["authorization_status"]="Pending Authorization"
        items.append(item);save(path,items)
    return {"item":item}

@router.post("/{platform}/estimates/{record_id}/create-fulfillment")
def create_estimate_fulfillment(platform:str,record_id:str,request:Request):
    """Create one linked Doorks job or SDC product order from an approved estimate."""
    guard(request,platform,"estimates_invoices")
    target_kind="work_orders" if platform=="doorks" else "orders"
    guard(request,platform,target_kind)
    with _lock:
        estimates=load(location(request,platform,"estimates_invoices"))
        estimate=next((x for x in estimates if x.get("id")==record_id and str(x.get("document_type","")).casefold()=="estimate"),None)
        if estimate is None:raise HTTPException(404,"Estimate not found")
        if str(estimate.get("status","")).casefold()!="approved":raise HTTPException(409,"Approve estimate first")
        target_path=location(request,platform,target_kind)
        records=load(target_path)
        existing=next((x for x in records if x.get("source_estimate_id")==record_id),None)
        if existing:return {"item":existing,"already_exists":True,"collection":target_kind}
        fields={k:estimate[k] for k in ("customer","customer_name","contact","address","description","total","amount","notes") if k in estimate and isinstance(estimate[k],(str,int,float,bool,type(None)))}
        fields.update(source_estimate_id=record_id,source_estimate_number=str(estimate.get("document_number","")),status="Pending",fulfillment_status="Pending")
        if platform=="doorks":
            now_local=datetime.now(ZoneInfo("America/Los_Angeles"))
            month_key=now_local.strftime("%Y-%m")
            counter_path=target_path.parent/"work_order_monthly_sequence.json"
            state=json.loads(counter_path.read_text(encoding="utf-8")) if counter_path.exists() else {}
            if not isinstance(state,dict):raise HTTPException(500,"Invalid work order counter")
            current=int(state.get(month_key,0))
            for row in records:
                if str(row.get("job_number","")).startswith(now_local.strftime("%m%y")+"-"):
                    m=re.fullmatch(r"\d{4}-(\d+)",str(row.get("job_number","")))
                    if m:current=max(current,int(m.group(1)))
            current+=1
            fields["job_number"]=f"{now_local:%m%y}-{current:02d}"
            state[month_key]=current
            tmp=counter_path.with_suffix(".tmp")
            with tmp.open("w",encoding="utf-8") as f:
                json.dump(state,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,counter_path)
        item={"id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),**fields}
        records.append(item)
        save(target_path,records)
        return {"item":item,"already_exists":False,"collection":target_kind}

@router.post("/{platform}/estimates/{record_id}/fulfillment")
def set_estimate_fulfillment(platform:str,record_id:str,payload:dict,request:Request):
    """Record an approval-linked service or product milestone without creating an invoice."""
    guard(request,platform,"estimates_invoices")
    stage=payload.get("stage")
    track=payload.get("track")
    if track not in ("Service","Product") or stage not in ("Pending","In Progress","Completed"):
        raise HTTPException(400,"Choose Service/Product and Pending/In Progress/Completed")
    with _lock:
        path=location(request,platform,"estimates_invoices");items=load(path)
        item=next((x for x in items if x.get("id")==record_id and str(x.get("document_type","")).casefold()=="estimate"),None)
        if item is None:raise HTTPException(404,"Estimate not found")
        if str(item.get("status","")).casefold()!="approved":raise HTTPException(409,"Approve the estimate first")
        item["fulfillment_track"]=track
        item["fulfillment_status"]=stage
        item["fulfillment_updated_at"]=datetime.now(timezone.utc).isoformat()
        save(path,items)
        return {"item":item}

@router.post("/{platform}/estimates/{record_id}/convert-to-invoice")
def convert_estimate_to_invoice(platform:str,record_id:str,request:Request):
    """Atomically create one draft invoice linked to a saved approved estimate."""
    guard(request,platform,"estimates_invoices")
    with _lock:
        path=location(request,platform,"estimates_invoices")
        items=load(path)
        source=next((x for x in items if x.get("id")==record_id),None)
        if source is None or str(source.get("document_type","")).casefold()!="estimate":
            raise HTTPException(404,"Estimate not found")
        if str(source.get("status","")).casefold()!="approved":
            raise HTTPException(409,"Approve the estimate before converting it")
        existing=next((x for x in items if x.get("document_type","").casefold()=="invoice" and x.get("source_estimate_id")==record_id),None)
        if existing:return {"item":existing,"already_exists":True}
        # Use existing invoice numbers when deriving next sequence; never reuse a deleted
        # number because the monotonic sequence file persists separately.
        counter=path.parent/"invoice_sequence.json"
        current=0
        if counter.exists():current=int(json.loads(counter.read_text(encoding="utf-8")).get("last",0))
        for row in items:
            match=re.fullmatch(r"INV-(\d+)",str(row.get("document_number", "")))
            if match:current=max(current,int(match.group(1)))
        number=f"INV-{current+1:05d}"
        tmp=counter.with_suffix(".tmp")
        with tmp.open("w",encoding="utf-8") as f:
            json.dump({"last":current+1},f);f.flush();os.fsync(f.fileno())
        os.replace(tmp,counter)
        now=datetime.now(timezone.utc).isoformat()
        excluded={"id","created_at","updated_at","document_number","status","paid","source_estimate_id","source_estimate_number"}
        invoice={k:v for k,v in source.items() if k not in excluded}
        invoice.update(id=uuid.uuid4().hex,created_at=now,document_type="Invoice",document_number=number,status="Draft",paid=0,source_estimate_id=record_id,source_estimate_number=source.get("document_number", ""),fulfillment_track=source.get("fulfillment_track",""),fulfillment_status=source.get("fulfillment_status","Pending"))
        items.append(invoice)
        save(path,items)
    return {"item":invoice,"already_exists":False}

@router.patch("/{platform}/{kind}/{record_id}")
def update(platform:str,kind:str,record_id:str,payload:Record,request:Request):
    guard(request,platform,kind)
    if platform=='doorks' and kind=='payroll':raise HTTPException(409,'Calculated timecards are immutable; approval has a separate endpoint')
    with _lock:
        path=location(request,platform,kind);items=load(path)
        for item in items:
            if item.get("id")==record_id:
                data=clean(payload.data)
                for k in ("authorization_status","authorized_by","authorized_at","unauthorized_by","unauthorized_at"):data.pop(k,None)
                if platform=='doorks' and kind=='employees':
                    # Employment records stay on disk. Disabling a linked employee
                    # immediately revokes login access at the authentication store.
                    data.pop('auth_user_id',None)
                    data.pop('access_active',None)
                    linked=item.get('auth_user_id')
                    if linked and str(data.get('status',item.get('status','Active'))).lower()!='active':
                        if linked==request.state.auth_user.get('id'):
                            raise HTTPException(409,'Cannot deactivate your own login')
                        try:request.app.state.users_store.set_active(linked,False)
                        except ValueError as exc:raise HTTPException(409,str(exc))
                        item['access_active']=False
                if kind=="purchase_orders":data.pop("po_number",None)
                if kind in ("work_orders","orders"):
                    data.pop("source_estimate_id",None)
                    data.pop("source_estimate_number",None)
                if platform=="doorks" and kind=="work_orders":
                    data.pop("job_number",None)
                    data.pop("work_order_number",None)
                    data.pop("id",None)
                    data.pop("created_at",None)
                item.update(data);
                if kind=="expenses":
                    item["authorization_status"]="Pending Authorization"
                    item.pop("authorized_by",None);item.pop("authorized_at",None)
                item["updated_at"]=datetime.now(timezone.utc).isoformat()
                save(path,items);return {"item":item}
    raise HTTPException(404,"Record not found")

@router.post("/{platform}/expenses/{record_id}/authorization")
def authorize_expense(platform:str,record_id:str,payload:dict,request:Request):
    guard(request,platform,"expenses")
    if not isinstance(payload.get("authorized"),bool):raise HTTPException(400,"authorized must be boolean")
    with _lock:
        path=location(request,platform,"expenses");items=load(path)
        for item in items:
            if item.get("id")==record_id:
                user=getattr(request.state,"auth_user",None)
                actor=str(user.get("name") or user.get("username") or user.get("id") or "office_admin") if isinstance(user,dict) else "office_admin"
                item["authorization_status"]="Authorized" if payload["authorized"] else "Pending Authorization"
                if payload["authorized"]:
                    item["authorized_by"]=actor
                    item["authorized_at"]=datetime.now(timezone.utc).isoformat()
                else:
                    item.pop("authorized_by",None);item.pop("authorized_at",None)
                    item["unauthorized_by"]=actor
                    item["unauthorized_at"]=datetime.now(timezone.utc).isoformat()
                save(path,items);return {"item":item}
    raise HTTPException(404,"Record not found")

@router.patch("/{platform}/{kind}/{record_id}/status")
def set_status(platform:str,kind:str,record_id:str,payload:dict,request:Request):
    guard(request,platform,kind)
    if kind not in ("customers","vendors"):raise HTTPException(400,"Status applies to customers and vendors")
    if not isinstance(payload.get("active"),bool):raise HTTPException(400,"active must be boolean")
    with _lock:
        path=location(request,platform,kind);items=load(path)
        for item in items:
            if item.get("id")==record_id:
                if payload["active"]:item.pop("deactivated_at",None)
                else:item["deactivated_at"]=datetime.now(timezone.utc).isoformat()
                item["updated_at"]=datetime.now(timezone.utc).isoformat()
                save(path,items);return {"item":item}
    raise HTTPException(404,"Record not found")

@router.delete("/{platform}/{kind}/{record_id}")
def delete(platform:str,kind:str,record_id:str,request:Request):
    guard(request,platform,kind)
    if platform=='doorks' and kind in ('payroll','employees'):
        raise HTTPException(409,'Retain employee and payroll history; deactivate employee access instead')
    with _lock:
        path=location(request,platform,kind);items=load(path)
        if kind in ("customers","vendors"):
            target=next((x for x in items if x.get("id")==record_id),None)
            if target:
                name=str(target.get("name") or "").strip().casefold()
                # Conservative link check: do not delete if referenced by another collection.
                for other_kind in KINDS[platform]:
                    if other_kind==kind:continue
                    for linked in load(location(request,platform,other_kind)):
                        for key in (("customer","customer_name") if kind=="customers" else ("vendor","supplier")):
                            if name and str(linked.get(key) or "").strip().casefold()==name:
                                raise HTTPException(409,"Record is linked to existing work. Deactivate it instead.")
        remaining=[item for item in items if item.get("id")!=record_id]
        if len(items)==len(remaining):raise HTTPException(404,"Record not found")
        save(path,remaining)
    return {"ok":True}

@router.delete('/{platform}/{kind}/{record_id}/contact')
def delete_contact_record(platform:str,kind:str,record_id:str,request:Request):
    """Remove only one contact row, preserving company and linked business history."""
    guard(request,platform,kind)
    if kind not in ('customers','vendors'):
        raise HTTPException(400,'Contact deletion is available for customer and supplier directories')
    with _lock:
        path=location(request,platform,kind)
        items=load(path)
        target=next((x for x in items if x.get('id')==record_id),None)
        if not target:raise HTTPException(404,'Contact not found')
        company=str(target.get('name') or '').strip().casefold()
        if not any(x.get('id')!=record_id and str(x.get('name') or '').strip().casefold()==company for x in items):
            raise HTTPException(409,'This is the last record for the company. Deactivate instead to preserve the company profile.')
        person=str(target.get('contact') or '').strip().casefold()
        email=str(target.get('email') or '').strip().casefold()
        for other_kind in KINDS[platform]:
            if other_kind==kind:continue
            for linked in load(location(request,platform,other_kind)):
                if person and str(linked.get('contact') or '').strip().casefold()==person and str(linked.get('customer') or linked.get('vendor') or linked.get('supplier') or '').strip().casefold()==company:
                    raise HTTPException(409,'Contact is referenced by existing records. Deactivate instead.')
                if email and str(linked.get('email') or linked.get('contact_email') or '').strip().casefold()==email:
                    raise HTTPException(409,'Contact email is referenced by existing records. Deactivate instead.')
        save(path,[x for x in items if x.get('id')!=record_id])
    return {'ok':True}
