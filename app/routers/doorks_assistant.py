"""Permission-gated Moses chat. Internal office search is scoped to active workspace."""
from __future__ import annotations
import json, os
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router=APIRouter(prefix='/doorks-assistant',tags=['doorks-assistant'])
class Message(BaseModel):
    message: str=Field(min_length=1,max_length=1500)

def allowed(request):
    if not getattr(request.state,'auth_user',None):raise HTTPException(401,'Sign in to use Moses')
    platform=request.session.get('active_platform')
    if platform not in ('doorks','pds','sdc'):raise HTTPException(403,'Select a workspace')
    return platform

@router.post('/chat')
def chat(payload:Message,request:Request):
    platform=allowed(request)
    text=payload.message.strip()
    # Record lookup is restricted to office admins; technicians receive generic help.
    role=str(getattr(request.state,'auth_role',''))
    can_search=role=='office_admin'
    collections={'doorks':['work_orders','customers','vendors','customer_inquiries','vendor_assignments'],
                 'sdc':['orders','customers','vendors'],'pds':[]}[platform] if can_search else []
    matches=[]
    if can_search:
        root=Path(request.app.state.data_dir)/'business_workspaces'/platform
        for kind in collections:
            path=root/(kind+'.json')
            if not path.exists():continue
            try:
                data=json.loads(path.read_text())
                items=data if isinstance(data,list) else data.get('items',[])
                for item in items:
                    if not isinstance(item,dict):continue
                    fields=('name','customer','job_number','work_order_number','address','description','status','vendor','email')
                    if any(text.lower() in str(item.get(k,'')).lower() for k in fields):
                        matches.append({'type':kind,'id':str(item.get('id','')),
                            'name':str(item.get('name') or item.get('customer') or item.get('job_number') or '')[:140],
                            'status':str(item.get('status') or '')[:60]})
                    if len(matches)>=15:break
            except (OSError,ValueError,TypeError):continue
            if len(matches)>=15:break
    key=os.getenv('OPENAI_API_KEY','')
    if not key:
        answer=('I found '+str(len(matches))+' matching records in '+platform+'.' if matches else
                'I can help navigate '+platform+'. Try asking for a specific customer, job number, or vendor. Record searches require office administrator access.')
        return {'answer':answer,'matches':matches,'workspace':platform}
    prompt='You are Moses, a concise office assistant for '+platform+'. Only use the authorized records supplied. Never invent data or imply actions were performed. Do not reveal credentials. If the data is insufficient say so.'
    data={'model':os.getenv('DOORKS_MOSES_MODEL','gpt-4.1-mini'),'input':[
        {'role':'system','content':prompt},{'role':'user','content':'Authorized matches: '+json.dumps(matches)+'\nQuestion: '+text}],
        'max_output_tokens':350}
    try:
        req=UrlRequest('https://api.openai.com/v1/responses',data=json.dumps(data).encode(),
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=20) as response:out=json.loads(response.read())
        answer=' '.join(c.get('text','') for o in out.get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
        if not answer:answer='I could not complete that request. Please try a more specific question.'
    except Exception:
        answer='Moses is temporarily unavailable. Your records were not changed.'
    return {'answer':answer,'matches':matches,'workspace':platform}
