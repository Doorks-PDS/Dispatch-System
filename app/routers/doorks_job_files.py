"""Doorks-only work-order attachments and visit forms; never touches PDS records."""
from __future__ import annotations
import json, os, uuid, re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.routers import workspaces

router=APIRouter(prefix='/workspaces/doorks/jobs',tags=['doorks-jobs'])
_lock=RLock()
MAX_SIZE=12*1024*1024
EXTENSIONS={'.pdf','.png','.jpg','.jpeg','.webp','.doc','.docx','.xls','.xlsx','.csv','.txt'}

class Visit(BaseModel):
    data:dict

def folder(request,job_id):
    workspaces.guard(request,'doorks','work_orders')
    if not re.fullmatch(r'[a-f0-9]{32}',job_id):raise HTTPException(400,'Invalid job identifier')
    with workspaces._lock:
        jobs=workspaces.load(workspaces.location(request,'doorks','work_orders'))
    if not any(j.get('id')==job_id for j in jobs):raise HTTPException(404,'Work order not found')
    base=Path(request.app.state.data_dir)/'business_workspaces'/'doorks'/'job_files'/job_id
    base.mkdir(parents=True,exist_ok=True)
    return base

def read_index(path):
    if not path.exists():return []
    result=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(result,list):raise HTTPException(500,'Invalid job file index')
    return result

def write_index(path,items):
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8') as f:
        json.dump(items,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

@router.get('/{job_id}/records')
def records(job_id:str,request:Request):
    base=folder(request,job_id)
    with _lock:
        forms=read_index(base/'forms.json');files=read_index(base/'attachments.json')
    # References are IDs, not free-form paths; only records belonging to this job are exposed.
    return {'forms':forms,'attachments':files}

@router.post('/{job_id}/forms')
def add_form(job_id:str,payload:Visit,request:Request):
    base=folder(request,job_id)
    allowed={'completion_date','completion_technician','completion_labor_hours','completion_labor_rate','completion_parts_total','completion_work_performed','completion_parts_used','completion_recommendations','completion_status','completion_door_type','completion_door_location','completion_time_in','completion_time_out','completion_lunch'}
    if not isinstance(payload.data,dict) or set(payload.data)-allowed:raise HTTPException(400,'Invalid completion fields')
    data={}
    for key,value in payload.data.items():
        if not isinstance(value,(str,int,float)) or len(str(value))>4000:raise HTTPException(400,'Invalid completion value')
        data[key]=str(value).strip()
    if not data.get('completion_work_performed'):raise HTTPException(400,'Work performed is required')
    actor=getattr(request.state,'auth_user',None)
    now=datetime.now(timezone.utc).isoformat()
    item={'id':uuid.uuid4().hex,'created_at':now,'updated_at':now,'created_by':str(actor.get('name') or actor.get('username') or '') if isinstance(actor,dict) else '',**data}
    with _lock:
        path=base/'forms.json';items=read_index(path);items.append(item);write_index(path,items)
    return {'item':item}

@router.patch('/{job_id}/forms/{form_id}')
def edit_form(job_id:str,form_id:str,payload:Visit,request:Request):
    base=folder(request,job_id)
    allowed={'completion_date','completion_technician','completion_labor_hours','completion_labor_rate','completion_parts_total','completion_work_performed','completion_parts_used','completion_recommendations','completion_status','completion_door_type','completion_door_location','completion_time_in','completion_time_out','completion_lunch'}
    if not isinstance(payload.data,dict) or set(payload.data)-allowed:raise HTTPException(400,'Invalid completion fields')
    with _lock:
        path=base/'forms.json';items=read_index(path)
        item=next((x for x in items if x.get('id')==form_id),None)
        if item is None:raise HTTPException(404,'Form not found')
        for key,value in payload.data.items():
            if not isinstance(value,(str,int,float)) or len(str(value))>4000:raise HTTPException(400,'Invalid completion value')
            item[key]=str(value).strip()
        item['updated_at']=datetime.now(timezone.utc).isoformat();write_index(path,items)
    return {'item':item}

@router.post('/{job_id}/attachments')
async def upload(job_id:str,request:Request,file:UploadFile=File(...),form_id:str=''):
    base=folder(request,job_id)
    original=Path(file.filename or '').name[:180]
    ext=Path(original).suffix.lower()
    if not original or ext not in EXTENSIONS:raise HTTPException(400,'Unsupported file format')
    if form_id:
        with _lock:
            if not any(x.get('id')==form_id for x in read_index(base/'forms.json')):raise HTTPException(404,'Completion form not found')
    raw=await file.read(MAX_SIZE+1)
    if not raw or len(raw)>MAX_SIZE:raise HTTPException(413,'File must be 1 byte to 12 MB')
    identifier=uuid.uuid4().hex;stored=identifier+ext
    item={'id':identifier,'name':original,'size':len(raw),'form_id':form_id,'created_at':datetime.now(timezone.utc).isoformat()}
    with _lock:
        path=base/'attachments.json';items=read_index(path)
        dest=base/stored
        with dest.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        try:write_index(path,[*items,item])
        except Exception:dest.unlink(missing_ok=True);raise
    return {'item':item}

@router.get('/{job_id}/attachments/{attachment_id}')
def download(job_id:str,attachment_id:str,request:Request):
    base=folder(request,job_id)
    with _lock:item=next((x for x in read_index(base/'attachments.json') if x.get('id')==attachment_id),None)
    if item is None:raise HTTPException(404,'File not found')
    ext=Path(item['name']).suffix.lower();path=base/(attachment_id+ext)
    if not path.is_file():raise HTTPException(404,'File missing from persistent storage')
    return FileResponse(path,filename=item['name'])
