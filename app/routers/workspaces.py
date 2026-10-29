"""Isolated Doorks/SDC workspace records. PDS stores are never read or written."""
from __future__ import annotations
import json, os, uuid, re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router=APIRouter(prefix="/workspaces",tags=["workspaces"])
_lock=RLock()
KINDS={"doorks":("customers","vendors","work_orders","expenses","receivables","inventory"),"sdc":("customers","orders","products","expenses","receivables","inventory")}
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
    with _lock:
        path=location(request,platform,kind);items=load(path)
        data=clean(payload.data)
        if platform=="doorks" and kind=="work_orders":
            # Monotonic counter on persistent storage, never derived from list length.
            # Keep the counter even if work orders are deleted.
            counter_path=path.parent/"work_order_sequence.json"
            current=0
            if counter_path.exists():
                current=int(json.loads(counter_path.read_text(encoding="utf-8")).get("last",0))
            for existing in items:
                match=re.fullmatch(r"WO-(\d+)",str(existing.get("work_order_number", "")))
                if match:current=max(current,int(match.group(1)))
            data.pop("work_order_number",None)
            data["work_order_number"]=f"WO-{current+1:04d}"
            # Write the reservation before saving the work order; skipped numbers
            # are preferable to reusing a number after a failed write.
            save_counter=counter_path.with_suffix(".tmp")
            with save_counter.open("w",encoding="utf-8") as f:
                json.dump({"last":current+1},f);f.flush();os.fsync(f.fileno())
            os.replace(save_counter,counter_path)
        item={"id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),**data}
        items.append(item);save(path,items)
    return {"item":item}

@router.patch("/{platform}/{kind}/{record_id}")
def update(platform:str,kind:str,record_id:str,payload:Record,request:Request):
    guard(request,platform,kind)
    with _lock:
        path=location(request,platform,kind);items=load(path)
        for item in items:
            if item.get("id")==record_id:
                data=clean(payload.data)
                if platform=="doorks" and kind=="work_orders":
                    data.pop("work_order_number",None)
                    data.pop("id",None)
                    data.pop("created_at",None)
                item.update(data);item["updated_at"]=datetime.now(timezone.utc).isoformat()
                save(path,items);return {"item":item}
    raise HTTPException(404,"Record not found")

@router.delete("/{platform}/{kind}/{record_id}")
def delete(platform:str,kind:str,record_id:str,request:Request):
    guard(request,platform,kind)
    with _lock:
        path=location(request,platform,kind);items=load(path)
        remaining=[item for item in items if item.get("id")!=record_id]
        if len(items)==len(remaining):raise HTTPException(404,"Record not found")
        save(path,remaining)
    return {"ok":True}
