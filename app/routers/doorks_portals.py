"""Doorks-only limited external portal, invitation-based, no access to internal workspace APIs."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from threading import RLock
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix='/doorks-portals', tags=['doorks-portals'])
_lock = RLock()

def now(): return datetime.now(timezone.utc)
def iso(t): return t.isoformat()
def store(request):
    p = Path(request.app.state.data_dir) / 'business_workspaces' / 'doorks' / 'portal_access.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def read(p):
    if not p.exists(): return {'invites': [], 'submissions': [], 'payment_links': [], 'notifications': []}
    obj = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or not isinstance(obj.get('invites'), list) or not isinstance(obj.get('submissions'), list):
        raise HTTPException(500, 'Portal storage invalid')
    obj.setdefault('payment_links', [])
    obj.setdefault('notifications', [])
    obj.setdefault('accounts', [])
    obj.setdefault('checkout_sessions', [])
    obj.setdefault('stripe_events', [])
    return obj

def write(p, obj):
    tmp=p.with_name(p.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,p)

def admin(request):
    if not getattr(request.state,'auth_user',None) or getattr(request.state,'auth_role',None)!='office_admin':
        raise HTTPException(403,'Office Admin required')
    if request.session.get('active_platform')!='doorks':
        raise HTTPException(403,'Switch to Doorks first')

def workspace_items(request, kind):
    """Read only the Doorks collection; never authorize by a display name."""
    path = Path(request.app.state.data_dir) / 'business_workspaces' / 'doorks' / (kind + '.json')
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding='utf-8'))
    items = data if isinstance(data, list) else data.get('items') if isinstance(data, dict) else None
    if not isinstance(items, list): raise HTTPException(500, 'Invalid workspace collection')
    return [item for item in items if isinstance(item, dict)]

def vendor_is_suspended(request, record_id):
    if not record_id:
        return False
    return any(str(v.get('id') or '') == record_id and
               str(v.get('onboarding_status') or '').strip().lower() == 'suspended'
               for v in workspace_items(request, 'vendors'))

def verify_invitation_link(request, kind, record_id):
    """Fail closed for nonexistent customer/vendor IDs; blank ID allows requests only."""
    if not record_id: return
    collection = 'customers' if kind == 'customer' else 'vendors'
    if not any(str(x.get('id') or '') == record_id for x in workspace_items(request, collection)):
        raise HTTPException(400, 'Record ID not found in Doorks ' + collection)
    if kind == 'vendor' and vendor_is_suspended(request, record_id):
        raise HTTPException(409, 'Vendor is suspended; portal access cannot be issued')

def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def access(request, token):
    if not isinstance(token,str) or len(token)!=64: raise HTTPException(401,'Invalid portal access')
    with _lock:
        obj=read(store(request))
        invite=next((i for i in obj['invites'] if hmac.compare_digest(i['token_hash'],digest(token))),None)
        if not invite or invite['revoked'] or (invite.get('expires_at') and datetime.fromisoformat(invite['expires_at'])<=now()):
            raise HTTPException(401,'Portal link expired or revoked')
        # Rev 48: fail closed when a linked vendor is suspended or a linked
        # customer/vendor has been removed. Unlinked links remain message-only.
        rid = str(invite.get('record_id') or '').strip()
        if rid:
            kind = invite.get('kind')
            collection = 'vendors' if kind == 'vendor' else 'customers'
            if not any(str(x.get('id') or '') == rid for x in workspace_items(request, collection)):
                raise HTTPException(403, 'Linked portal account is no longer active')
            if kind == 'vendor' and vendor_is_suspended(request, rid):
                raise HTTPException(403, 'Vendor portal access is suspended')
        return invite

class Invite(BaseModel):
    kind: str
    contact_name: str=Field(min_length=1,max_length=120)
    contact_email: str=Field(min_length=3,max_length=250)
    company: str=Field(min_length=1,max_length=160)
    record_id: str=Field(default='',max_length=100)
    days: int=Field(default=14,ge=0,le=365)

@router.post('/admin/invitations')
def create_invite(payload:Invite, request:Request):
    admin(request)
    if payload.kind not in ('customer','vendor'): raise HTTPException(400,'Invalid portal type')
    if '@' not in payload.contact_email: raise HTTPException(400,'Valid email required')
    verify_invitation_link(request, payload.kind, payload.record_id.strip())
    token=secrets.token_urlsafe(48)  # 64 characters
    with _lock:
        p=store(request); obj=read(p)
        entry={'id':str(uuid.uuid4()),'kind':payload.kind,'contact_name':payload.contact_name.strip(),
               'contact_email':payload.contact_email.strip(),'company':payload.company.strip(),
               'record_id':payload.record_id.strip(),'token_hash':digest(token),
               'created_at':iso(now()),'expires_at':iso(now()+timedelta(days=payload.days)) if payload.days else None,
               'revoked':False}
        obj['invites'].append(entry);write(p,obj)
    # Fragment prevents the bearer token being sent to the server in HTTP GET or referrer.
    return {'invitation':{k:v for k,v in entry.items() if k!='token_hash'},'link':str(request.base_url).rstrip('/')+'/doorks-portals/access#'+token}

@router.get('/admin/overview')
def overview(request:Request):
    admin(request)
    with _lock:
        obj=read(store(request))
        return {'invitations':[{k:v for k,v in i.items() if k!='token_hash'} for i in obj['invites']],
                'submissions':obj['submissions'], 'payment_links':obj['payment_links'], 'notifications':obj['notifications']}

@router.get('/admin/link-options')
def portal_link_options(request: Request):
    """Limited contact details for the invitation picker, office admin only."""
    admin(request)
    output = {}
    for kind, collection in (('customer', 'customers'), ('vendor', 'vendors')):
        output[kind] = [{
            'id': str(x.get('id') or ''),
            'name': str(x.get('name') or x.get('company') or x.get('customer') or x.get('vendor') or '')[:160],
            'contact': str(x.get('contact') or x.get('contact_name') or '')[:120],
            'email': str(x.get('email') or '')[:250],
            'status': str(x.get('onboarding_status') or '')[:40] if kind == 'vendor' else '',
        } for x in workspace_items(request, collection) if str(x.get('id') or '').strip()]
    return output

@router.post('/admin/invitations/{invite_id}/revoke')
def revoke(invite_id:str,request:Request):
    admin(request)
    with _lock:
        p=store(request);obj=read(p)
        i=next((i for i in obj['invites'] if i['id']==invite_id),None)
        if not i: raise HTTPException(404,'Invitation not found')
        i['revoked']=True;write(p,obj)
    return {'ok':True}

class SessionToken(BaseModel):
    token: str

@router.post('/session')
def session(payload:SessionToken,request:Request):
    i=access(request,payload.token)
    return {'kind':i['kind'],'company':i['company'],'contact_name':i['contact_name'],
            'expires_at':i['expires_at'],'capabilities':['submit_request'] if i['kind']=='customer' else ['submit_update']}

# Rev 41: read-only customer document visibility with server-side invitation scoping.
# No client-supplied customer ID, document ID, or company name grants access.
def customer_documents(request, invite):
    if invite['kind'] != 'customer':
        raise HTTPException(403, 'Customer invitation required')
    customer_id = str(invite.get('record_id') or '').strip()
    if not customer_id:
        return []  # Fail closed: unlinked invitations cannot see financial documents.
    root = Path(request.app.state.data_dir) / 'business_workspaces' / 'doorks'
    cp = root / 'customers.json'
    dp = root / 'estimates_invoices.json'
    if not cp.exists() or not dp.exists():
        return []
    def items(path):
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list): return data
        if isinstance(data, dict) and isinstance(data.get('items'), list): return data['items']
        return []
    customers = items(cp)
    customer = next((c for c in customers if str(c.get('id','')) == customer_id), None)
    if not customer:
        return []
    # A verified customer record ID is required. Documents linked by customer_id
    # are accepted; older documents with only a customer name must be linked by
    # an office admin before external publication to avoid name collisions.
    output=[]
    for d in items(dp):
        if not isinstance(d,dict) or str(d.get('customer_id') or '') != customer_id:
            continue
        kind=str(d.get('document_type') or '')
        status=str(d.get('status') or '')
        if kind not in ('Estimate','Invoice') or status.lower() in ('draft','voided'):
            continue
        total=round(float(d.get('amount') or 0),2)
        paid=round(float(d.get('paid') or 0),2) if kind=='Invoice' else 0
        output.append({'id':str(d.get('id') or ''),'document_type':kind,
            'document_number':str(d.get('document_number') or ''),
            'date':str(d.get('date') or ''),'status':status,
            'amount':total,'paid':paid,'balance_due':round(max(0,total-paid),2),
            'terms':str(d.get('terms') or ''),
            'line_items':d.get('line_items') if isinstance(d.get('line_items'),list) else [],
            'notes':str(d.get('notes') or '')[:2000]})
    return output

# Rev 43: Admin-configured external checkout links; Doorks never collects card data.
# A link is visible only to an invitation matching the invoice's saved customer ID.
from urllib.parse import urlsplit

class PaymentLinkRequest(BaseModel):
    document_id: str=Field(min_length=1,max_length=100)
    checkout_url: str=Field(default='',max_length=2000)

def verified_checkout_url(url):
    if not url: return ''
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(400,'Checkout link must be an HTTPS URL without credentials or fragments')
    if parsed.hostname in ('localhost','127.0.0.1','0.0.0.0','::1') or parsed.hostname.endswith(('.local','.internal')):
        raise HTTPException(400,'Invalid checkout domain')
    return url

def invoice_record(request, document_id):
    root=Path(request.app.state.data_dir)/'business_workspaces'/'doorks'
    p=root/'estimates_invoices.json'
    if not p.exists(): raise HTTPException(404,'Invoice not found')
    data=json.loads(p.read_text(encoding='utf-8'))
    items=data if isinstance(data,list) else data.get('items',[]) if isinstance(data,dict) else []
    doc=next((x for x in items if isinstance(x,dict) and str(x.get('id') or '')==document_id and x.get('document_type')=='Invoice'),None)
    if not doc or not str(doc.get('customer_id') or '').strip():
        raise HTTPException(404,'Linked invoice not found')
    return doc

@router.post('/admin/payment-link')
def set_payment_link(payload:PaymentLinkRequest,request:Request):
    admin(request)
    url=verified_checkout_url(payload.checkout_url.strip())
    doc=invoice_record(request,payload.document_id)
    with _lock:
        p=store(request);obj=read(p)
        obj['payment_links']=[x for x in obj['payment_links'] if x.get('document_id')!=payload.document_id]
        if url:
            obj['payment_links'].append({'document_id':payload.document_id,'customer_id':str(doc['customer_id']),
                'checkout_url':url,'updated_at':iso(now())})
            obj['notifications'].append({'id':str(uuid.uuid4()),'kind':'payment_link_ready',
                'document_id':payload.document_id,'customer_id':str(doc['customer_id']),
                'created_at':iso(now()),'delivery':'office_only',
                'message':'Checkout link configured; share the portal invitation privately. No email was sent.'})
        write(p,obj)
    return {'ok':True,'enabled':bool(url)}

class PaymentQuestion(BaseModel):
    token: str
    document_id: str=Field(min_length=1,max_length=100)
    note: str=Field(default='',max_length=1000)
    request_id: str=Field(min_length=8,max_length=100)

@router.post('/customer/payment-question')
def payment_question(payload:PaymentQuestion,request:Request):
    with _lock:
        invite=access(request,payload.token)
        docs=customer_documents(request,invite)
        doc=next((d for d in docs if d['id']==payload.document_id and d['document_type']=='Invoice'),None)
        if not doc: raise HTTPException(404,'Invoice unavailable')
        p=store(request);obj=read(p)
        old=next((x for x in obj['submissions'] if x.get('invite_id')==invite['id'] and x.get('request_id')==payload.request_id),None)
        if old: return {'ok':True,'submission_id':old['id'],'duplicate':True}
        item={'id':str(uuid.uuid4()),'invite_id':invite['id'],'kind':'customer',
            'company':invite['company'],'record_id':invite['record_id'],
            'contact_name':invite['contact_name'],'contact_email':invite['contact_email'],
            'subject':'Payment question — '+doc['document_number'],
            'message':payload.note.strip() or 'Customer requests payment assistance',
            'reference':doc['document_number'],'document_id':doc['id'],
            'request_id':payload.request_id,'status':'pending_review','created_at':iso(now())}
        obj['submissions'].append(item)
        obj['notifications'].append({'id':str(uuid.uuid4()),'kind':'payment_question',
            'submission_id':item['id'],'created_at':iso(now()),'delivery':'office_only',
            'message':'Customer payment question received for '+doc['document_number']})
        write(p,obj)
    return {'ok':True,'submission_id':item['id'],'duplicate':False}

@router.post('/customer/documents')
def list_customer_documents(payload:SessionToken, request:Request):
    invite=access(request,payload.token)
    docs=customer_documents(request,invite)
    with _lock:
        obj=read(store(request))
        links={x['document_id']:x for x in obj['payment_links'] if x.get('customer_id')==str(invite.get('record_id') or '')}
    for doc in docs:
        if doc['document_type']=='Invoice' and doc['balance_due']>0 and doc['id'] in links and str(links[doc['id']].get('customer_id') or '') == str(invite.get('record_id') or ''):
            doc['checkout_url']=links[doc['id']]['checkout_url']
    return {'documents':docs, 'linked':bool(invite.get('record_id'))}

class DocumentResponse(BaseModel):
    token: str
    document_id: str=Field(min_length=1,max_length=100)
    decision: str
    note: str=Field(default='',max_length=1000)

class SubmissionReview(BaseModel):
    status: Literal['pending_review', 'reviewed', 'resolved', 'rejected']
    note: str = Field(default='', max_length=1000)

@router.post('/admin/submissions/{submission_id}/review')
def review_submission(submission_id: str, payload: SubmissionReview, request: Request):
    """Office-only review metadata; never posts to source financial or operational records."""
    admin(request)
    with _lock:
        p = store(request); obj = read(p)
        item = next((x for x in obj['submissions'] if x.get('id') == submission_id), None)
        if item is None: raise HTTPException(404, 'Submission not found')
        previous = item.get('status', 'pending_review')
        item['status'] = payload.status
        item['review_note'] = payload.note.strip()
        item['reviewed_at'] = iso(now())
        item['reviewed_by'] = str(getattr(request.state, 'auth_user', '') or '')[:120]
        obj.setdefault('review_history', []).append({
            'submission_id': submission_id, 'from_status': previous, 'to_status': payload.status,
            'note': payload.note.strip(), 'at': item['reviewed_at'], 'by': item['reviewed_by']})
        write(p, obj)
    return {'ok': True, 'status': payload.status}

@router.get('/admin/security-check')
def portal_security_check(request: Request):
    """Read-only invitation and record-link checks for the office administrator."""
    admin(request)
    with _lock:
        obj = read(store(request))
    issues = []
    for invite in obj['invites']:
        if invite.get('revoked') or (invite.get('expires_at') and datetime.fromisoformat(invite['expires_at']) <= now()):
            continue
        rid = str(invite.get('record_id') or '').strip()
        if not rid:
            issues.append({'invitation_id': invite['id'], 'issue': 'Unlinked invitation: submissions only'})
        else:
            try:
                verify_invitation_link(request, invite['kind'], rid)
            except HTTPException as exc:
                issue = 'Suspended vendor with active invitation' if exc.status_code == 409 else 'Linked customer/vendor record no longer exists'
                issues.append({'invitation_id': invite['id'], 'issue': issue})
    return {'active_invitations': sum(not x.get('revoked') and (not x.get('expires_at') or datetime.fromisoformat(x['expires_at']) > now()) for x in obj['invites']),
            'pending_submissions': sum(x.get('status') == 'pending_review' for x in obj['submissions']),
            'issues': issues, 'ok': not issues}

@router.post('/customer/document-response')
def customer_document_response(payload:DocumentResponse,request:Request):
    if payload.decision not in ('approve','decline','question'):
        raise HTTPException(400,'Invalid decision')
    with _lock:
        p=store(request);obj=read(p)
        invite=access(request,payload.token)
        docs=customer_documents(request,invite)
        doc=next((d for d in docs if d['id']==payload.document_id),None)
        if not doc or doc['document_type']!='Estimate':
            raise HTTPException(404,'Estimate unavailable')
        if doc['status'].lower() not in ('sent','quote sent','pending approval'):
            raise HTTPException(409,'Estimate is not awaiting customer response')
        # Capture a review request; do not mutate the financial source document.
        item={'id':str(uuid.uuid4()),'invite_id':invite['id'],'kind':'customer',
            'company':invite['company'],'record_id':invite['record_id'],
            'contact_name':invite['contact_name'],'contact_email':invite['contact_email'],
            'subject':'Estimate '+doc['document_number']+' — '+payload.decision,
            'message':payload.note.strip() or 'No additional note',
            'reference':doc['document_number'],'document_id':doc['id'],
            'decision':payload.decision,'status':'pending_review','created_at':iso(now())}
        obj['submissions'].append(item);write(p,obj)
    return {'ok':True,'status':'pending_review','submission_id':item['id']}

class Submission(BaseModel):
    token: str
    subject: str=Field(default='',max_length=160)
    message: str=Field(default='',max_length=2000)
    reference: str=Field(default='',max_length=100)
    request_id: str=Field(default='',max_length=100)

@router.post('/submit')
def submit(payload:Submission,request:Request):
    if not (payload.subject.strip() or payload.message.strip() or payload.reference.strip()):
        raise HTTPException(400,'Enter a subject, details or reference before submitting')
    with _lock:
        p=store(request);obj=read(p)
        i=access(request,payload.token)
        if payload.request_id:
            previous=next((x for x in obj['submissions'] if x.get('invite_id')==i['id'] and x.get('request_id')==payload.request_id),None)
            if previous:return {'ok':True,'submission_id':previous['id'],'status':previous['status'],'duplicate':True}
        # Never trust user-supplied company or entity IDs; derive identity from the invitation.
        item={'id':str(uuid.uuid4()),'invite_id':i['id'],'kind':i['kind'],'company':i['company'],
              'record_id':i['record_id'],'contact_name':i['contact_name'],'contact_email':i['contact_email'],
              'subject':payload.subject.strip() or 'Customer inquiry / update','message':payload.message.strip(),
              'reference':payload.reference.strip(),'request_id':payload.request_id,'status':'pending_review','created_at':iso(now())}
        obj['submissions'].append(item);write(p,obj)
    return {'ok':True,'submission_id':item['id'],'status':'pending_review'}

# Rev 42: strictly ID-scoped vendor records. No company-name matching or
# untrusted reference values may authorize viewing a record.
def vendor_records(request, invite):
    if invite['kind'] != 'vendor':
        raise HTTPException(403, 'Vendor invitation required')
    vendor_id = str(invite.get('record_id') or '').strip()
    if not vendor_id:
        return {'assignments': [], 'purchase_orders': [], 'linked': False}
    root = Path(request.app.state.data_dir) / 'business_workspaces' / 'doorks'
    def items(kind):
        p = root / (kind + '.json')
        if not p.exists(): return []
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, list): return data
        if isinstance(data, dict) and isinstance(data.get('items'), list): return data['items']
        raise HTTPException(500, 'Invalid workspace data')
    if not any(isinstance(v, dict) and str(v.get('id') or '') == vendor_id for v in items('vendors')):
        return {'assignments': [], 'purchase_orders': [], 'linked': False}
    assignments=[]
    for a in items('vendor_assignments'):
        if not isinstance(a,dict) or str(a.get('vendor_id') or '') != vendor_id: continue
        if str(a.get('status') or '').lower() in ('draft','cancelled'): continue
        assignments.append({k:str(a.get(k) or '')[:1000] for k in
            ('id','work_order_number','scheduled_date','scheduled_time','status','scope','address','notes')})
    orders=[]
    for po in items('purchase_orders'):
        if not isinstance(po,dict) or str(po.get('vendor_id') or '') != vendor_id: continue
        if str(po.get('status') or '').lower() in ('draft','cancelled'): continue
        orders.append({k:str(po.get(k) or '')[:1000] for k in
            ('id','po_number','date','expected_date','status','description','quantity','received_quantity','work_order_number')})
    return {'assignments': assignments, 'purchase_orders': orders, 'linked': True}

@router.post('/vendor/records')
def list_vendor_records(payload:SessionToken,request:Request):
    return vendor_records(request, access(request,payload.token))

class VendorUpdate(BaseModel):
    token: str
    record_type: Literal['assignment','purchase_order']
    record_id: str=Field(min_length=1,max_length=100)
    update_status: Literal['accepted','declined','in_progress','completed','delayed','shipped','received','question']
    note: str=Field(default='',max_length=2000)
    request_id: str=Field(min_length=8,max_length=100)

@router.post('/vendor/update')
def vendor_update(payload:VendorUpdate,request:Request):
    with _lock:
        p=store(request);obj=read(p)
        invite=access(request,payload.token)
        records=vendor_records(request,invite)
        collection=records['assignments' if payload.record_type=='assignment' else 'purchase_orders']
        record=next((r for r in collection if r['id']==payload.record_id),None)
        if not record: raise HTTPException(404,'Record not available')
        if payload.record_type=='purchase_order' and payload.update_status in ('accepted','declined','in_progress','completed'):
            raise HTTPException(400,'Invalid purchase order update')
        if payload.record_type=='assignment' and payload.update_status in ('shipped','received'):
            raise HTTPException(400,'Invalid assignment update')
        existing=next((x for x in obj['submissions'] if x.get('invite_id')==invite['id'] and
            x.get('request_id')==payload.request_id),None)
        if existing: return {'ok':True,'submission_id':existing['id'],'status':'pending_review','duplicate':True}
        item={'id':str(uuid.uuid4()),'invite_id':invite['id'],'kind':'vendor',
              'company':invite['company'],'record_id':invite['record_id'],
              'contact_name':invite['contact_name'],'contact_email':invite['contact_email'],
              'subject':payload.record_type+' '+(record.get('po_number') or record.get('work_order_number') or record['id'])+' — '+payload.update_status,
              'message':payload.note.strip() or 'Status update submitted for review',
              'reference':record.get('po_number') or record.get('work_order_number') or '',
              'source_record_id':record['id'],'source_record_type':payload.record_type,
              'requested_status':payload.update_status,'request_id':payload.request_id,
              'status':'pending_review','created_at':iso(now())}
        obj['submissions'].append(item);write(p,obj)
    return {'ok':True,'submission_id':item['id'],'status':'pending_review','duplicate':False}

@router.post('/vendor/upload')
async def vendor_upload(request:Request,token:str=Form(...),record_type:str=Form(...),
                        record_id:str=Form(...),note:str=Form(''),file:UploadFile=File(...)):
    # Reject arbitrary record IDs before reading or storing the upload.
    invite=access(request,token)
    if record_type not in ('assignment','purchase_order'): raise HTTPException(400,'Invalid record type')
    records=vendor_records(request,invite)
    collection=records['assignments' if record_type=='assignment' else 'purchase_orders']
    record=next((r for r in collection if r['id']==record_id),None)
    if not record: raise HTTPException(404,'Record not available')
    if len(note)>1000: raise HTTPException(400,'Note too long')
    # Magic bytes are checked, not just the user-controlled extension/content-type.
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024: raise HTTPException(413,'File must be 1 byte to 5 MB')
    if content.startswith(b'%PDF-'): ext='pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'): ext='png'
    elif content.startswith(b'\xff\xd8\xff'): ext='jpg'
    elif content.startswith(b'RIFF') and content[8:12]==b'WEBP': ext='webp'
    else: raise HTTPException(415,'Only PDF, JPG, PNG or WEBP supported')
    with _lock:
        # Recheck access and source linkage while committing metadata.
        invite=access(request,token)
        records=vendor_records(request,invite)
        collection=records['assignments' if record_type=='assignment' else 'purchase_orders']
        if not any(r['id']==record_id for r in collection): raise HTTPException(404,'Record not available')
        p=store(request);obj=read(p)
        file_id=uuid.uuid4().hex
        folder=p.parent/'portal_private_uploads';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(file_id+'.'+ext)
        with dest.open('xb') as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        item={'id':str(uuid.uuid4()),'invite_id':invite['id'],'kind':'vendor',
              'company':invite['company'],'record_id':invite['record_id'],
              'contact_name':invite['contact_name'],'contact_email':invite['contact_email'],
              'subject':'Vendor document — '+record_type,
              'message':note.strip() or 'Supporting document uploaded',
              'reference':record.get('po_number') or record.get('work_order_number') or '',
              'source_record_id':record_id,'source_record_type':record_type,
              'upload_id':file_id,'upload_extension':ext,
              'original_filename':Path(file.filename or 'upload').name[:160],
              'file_size':len(content),'status':'pending_review','created_at':iso(now())}
        try:
            obj['submissions'].append(item);write(p,obj)
        except Exception:
            dest.unlink(missing_ok=True)
            raise
    return {'ok':True,'submission_id':item['id'],'status':'pending_review'}

@router.post('/customer/upload')
async def customer_upload(request:Request,token:str=Form(...),subject:str=Form(''),
                          reference:str=Form(''),note:str=Form(''),file:UploadFile=File(...)):
    invite=access(request,token)
    if invite['kind']!='customer': raise HTTPException(403,'Customer invitation required')
    if len(subject)>160 or len(reference)>100 or len(note)>2000:
        raise HTTPException(400,'Field too long')
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024: raise HTTPException(413,'File must be 1 byte to 5 MB')
    if content.startswith(b'%PDF-'): ext='pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'): ext='png'
    elif content.startswith(b'\xff\xd8\xff'): ext='jpg'
    elif content.startswith(b'RIFF') and content[8:12]==b'WEBP': ext='webp'
    else: raise HTTPException(415,'Only PDF, JPG, PNG or WEBP supported')
    with _lock:
        invite=access(request,token)
        if invite['kind']!='customer': raise HTTPException(403,'Customer invitation required')
        p=store(request);obj=read(p);file_id=uuid.uuid4().hex
        folder=p.parent/'portal_private_uploads';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(file_id+'.'+ext)
        with dest.open('xb') as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        item={'id':str(uuid.uuid4()),'invite_id':invite['id'],'kind':'customer',
              'company':invite['company'],'record_id':invite['record_id'],
              'contact_name':invite['contact_name'],'contact_email':invite['contact_email'],
              'subject':subject.strip() or 'Customer attachment',
              'message':note.strip() or 'Supporting document uploaded',
              'reference':reference.strip(),'upload_id':file_id,'upload_extension':ext,
              'original_filename':Path(file.filename or 'upload').name[:160],
              'file_size':len(content),'status':'pending_review','created_at':iso(now())}
        try:
            obj['submissions'].append(item);write(p,obj)
        except Exception:
            dest.unlink(missing_ok=True);raise
    return {'ok':True,'submission_id':item['id'],'status':'pending_review'}

@router.get('/admin/uploads/{submission_id}')
def admin_vendor_upload(submission_id:str,request:Request):
    from fastapi.responses import FileResponse
    admin(request)
    with _lock:
        obj=read(store(request))
        item=next((x for x in obj['submissions'] if x.get('id')==submission_id and x.get('upload_id')),None)
        if not item: raise HTTPException(404,'Upload not found')
        ext=item.get('upload_extension')
        if ext not in ('pdf','png','jpg','webp'): raise HTTPException(404,'Upload not found')
        path=store(request).parent/'portal_private_uploads'/(item['upload_id']+'.'+ext)
        if not path.is_file(): raise HTTPException(404,'Upload unavailable')
        return FileResponse(path,media_type={'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[ext],
            filename='portal-upload-'+submission_id+'.'+ext,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

class CustomerDocumentLink(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    document_id: str = Field(min_length=1, max_length=100)

@router.get('/admin/document-links')
def document_links(request: Request):
    """Read-only link review; display-name matches are suggestions, never authorization."""
    admin(request)
    customers = workspace_items(request, 'customers')
    documents = workspace_items(request, 'estimates_invoices')
    return {'customers': [{'id': str(c.get('id') or ''), 'name': str(c.get('name') or c.get('company') or '')}
                          for c in customers if c.get('id')],
            'documents': [{'id': str(d.get('id') or ''), 'number': str(d.get('document_number') or ''),
                           'type': str(d.get('document_type') or ''), 'customer': str(d.get('customer') or ''),
                           'customer_id': str(d.get('customer_id') or ''), 'status': str(d.get('status') or '')}
                          for d in documents if d.get('id') and d.get('document_type') in ('Estimate', 'Invoice')]}

@router.post('/admin/document-links')
def link_customer_document(payload: CustomerDocumentLink, request: Request):
    """Explicit office-admin linking; never auto-match or silently reassign."""
    admin(request)
    if not any(str(c.get('id') or '') == payload.customer_id for c in workspace_items(request, 'customers')):
        raise HTTPException(404, 'Customer not found')
    path = Path(request.app.state.data_dir) / 'business_workspaces' / 'doorks' / 'estimates_invoices.json'
    with _lock:
        if not path.exists(): raise HTTPException(404, 'Documents not found')
        raw = json.loads(path.read_text(encoding='utf-8'))
        docs = raw if isinstance(raw, list) else raw.get('items') if isinstance(raw, dict) else None
        if not isinstance(docs, list): raise HTTPException(500, 'Invalid document collection')
        doc = next((d for d in docs if isinstance(d, dict) and str(d.get('id') or '') == payload.document_id), None)
        if not doc or doc.get('document_type') not in ('Estimate', 'Invoice'):
            raise HTTPException(404, 'Estimate or invoice not found')
        existing = str(doc.get('customer_id') or '').strip()
        if existing and existing != payload.customer_id:
            raise HTTPException(409, 'Document is already linked to another customer; no reassignment performed')
        if existing == payload.customer_id: return {'ok': True, 'already_linked': True}
        doc['customer_id'] = payload.customer_id
        tmp = path.with_name(path.name + '.portal-link-tmp')
        try:
            with tmp.open('w', encoding='utf-8') as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
                f.flush(); os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
    return {'ok': True, 'already_linked': False}

@router.post('/my-submissions')
def my_submissions(payload: SessionToken, request: Request):
    """Invitation-scoped request history, never exposing other companies' messages."""
    invite = access(request, payload.token)
    with _lock:
        obj = read(store(request))
        rows = [x for x in obj['submissions'] if x.get('invite_id') == invite['id']]
    return {'submissions': [{k: x.get(k) for k in ('id','subject','message','reference','status','created_at','kind')}
                            for x in rows[-200:]]}

@router.get('/access',response_class=HTMLResponse)
def portal_page(response: HTMLResponse):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    template = Path(__file__).resolve().parents[2] / 'static' / 'doorks_portal.html'
    return template.read_text(encoding='utf-8')


@router.post('/customer/work-orders')
def customer_work_orders(payload: SessionToken, request: Request):
    invite=access(request,payload.token)
    if invite['kind']!='customer': raise HTTPException(403,'Customer portal required')
    customer_id=str(invite.get('record_id') or '').strip()
    if not customer_id: return {'work_orders': []}
    allowed=('id','job_number','work_order_number','status','customer','address','service_type','scheduled_date','scheduled_time','description')
    rows=[{k:r.get(k) for k in allowed} for r in workspace_items(request,'work_orders')
          if str(r.get('customer_id') or '').strip()==customer_id and not r.get('deactivated_at')]
    return {'work_orders': rows[:500]}


def _vendor_file_record(request, vendor_id):
    if not any(str(v.get('id'))==vendor_id for v in workspace_items(request,'vendors')):
        raise HTTPException(404,'Vendor not found')

@router.get('/admin/vendor-files/{vendor_id}')
def list_vendor_profile_files(vendor_id:str,request:Request):
    admin(request);_vendor_file_record(request,vendor_id)
    with _lock:
        obj=read(store(request))
        return {'files':[{'id':f['id'],'filename':f['filename'],'size':f['size'],'created_at':f['created_at']}
                         for f in obj.get('vendor_profile_files',[]) if f.get('vendor_id')==vendor_id]}

@router.post('/admin/vendor-files/{vendor_id}')
async def upload_vendor_profile_file(vendor_id:str,request:Request,file:UploadFile=File(...)):
    admin(request);_vendor_file_record(request,vendor_id)
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024: raise HTTPException(413,'File must be 1 byte to 5 MB')
    if content.startswith(b'%PDF-'): ext='pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'): ext='png'
    elif content.startswith(b'\xff\xd8\xff'): ext='jpg'
    elif content.startswith(b'RIFF') and content[8:12]==b'WEBP': ext='webp'
    else: raise HTTPException(415,'Only PDF, JPG, PNG and WEBP supported')
    with _lock:
        _vendor_file_record(request,vendor_id)
        path=store(request);obj=read(path)
        uid=uuid.uuid4().hex;folder=path.parent/'portal_private_uploads';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(uid+'.'+ext)
        with dest.open('xb') as out:out.write(content);out.flush();os.fsync(out.fileno())
        obj.setdefault('vendor_profile_files',[]).append({'id':uid,'vendor_id':vendor_id,'filename':Path(file.filename or 'upload').name[:160],'size':len(content),'extension':ext,'created_at':iso(now())})
        try:write(path,obj)
        except Exception:dest.unlink(missing_ok=True);raise
    return {'ok':True,'id':uid}

@router.get('/admin/vendor-files/{vendor_id}/{file_id}')
def download_vendor_profile_file(vendor_id:str,file_id:str,request:Request):
    from fastapi.responses import FileResponse
    admin(request);_vendor_file_record(request,vendor_id)
    with _lock:
        obj=read(store(request));record=next((f for f in obj.get('vendor_profile_files',[]) if f.get('vendor_id')==vendor_id and f.get('id')==file_id),None)
    if not record:raise HTTPException(404,'File not found')
    path=store(request).parent/'portal_private_uploads'/(record['id']+'.'+record['extension'])
    if not path.is_file():raise HTTPException(404,'File missing')
    return FileResponse(path,filename=record['filename'],headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


# Rev 63: Public, unauthenticated lead intake. Leads are review-only, never auto-dispatched.
class PublicServiceRequest(BaseModel):
    company: str = Field(default='', max_length=160)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_email: str = Field(min_length=5, max_length=250)
    contact_phone: str = Field(min_length=7, max_length=50)
    address: str = Field(default='', max_length=300)
    service_type: str = Field(default='', max_length=100)
    urgency: str = Field(default='Normal', max_length=40)
    preferred_date: str = Field(default='', max_length=40)
    preferred_time: str = Field(default='', max_length=80)
    nte: str = Field(default='', max_length=40)
    description: str = Field(min_length=5, max_length=5000)
    website: str = Field(default='', max_length=300)  # honeypot

_public_hits = {}

@router.get('/request-service', response_class=HTMLResponse)
def public_service_page():
    return HTMLResponse((Path(__file__).resolve().parents[2] / 'static' / 'doorks_request_service.html').read_text(encoding='utf-8'), headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.post('/public/service-request')
def public_service_request(payload: PublicServiceRequest, request: Request):
    if payload.website.strip():
        return {'received':True}
    if '@' not in payload.contact_email or '.' not in payload.contact_email.split('@')[-1]:
        raise HTTPException(422, 'Valid email required')
    if not payload.description.strip():
        raise HTTPException(422, 'Describe the requested service')
    # Bounded in-process rate limit. For multi-instance production, add shared Redis/WAF throttling.
    ip = request.client.host if request.client else 'unknown'
    slot = int(now().timestamp() // 3600)
    with _lock:
        for k in list(_public_hits):
            if k[1] < slot - 1: _public_hits.pop(k, None)
        key = (ip, slot)
        if _public_hits.get(key, 0) >= 8:
            raise HTTPException(429, 'Too many requests. Please try again later.')
        _public_hits[key] = _public_hits.get(key, 0) + 1
        path = store(request)
        data = read(path)
        entry = {'id':str(uuid.uuid4()), 'kind':'public_service_request', 'status':'pending_review',
                 'company':payload.company.strip() or payload.contact_name.strip(),
                 'contact_name':payload.contact_name.strip(), 'contact_email':payload.contact_email.strip(),
                 'contact_phone':payload.contact_phone.strip(), 'address':payload.address.strip(),
                 'service_type':payload.service_type.strip(), 'urgency':payload.urgency.strip(),
                 'preferred_date':payload.preferred_date.strip(), 'preferred_time':payload.preferred_time.strip(),
                 'nte':payload.nte.strip(), 'subject':payload.service_type.strip() or 'New service inquiry',
                 'message':payload.description.strip(), 'reference':'', 'created_at':iso(now()),
                 'source':'public_marketing_form', 'upload_ids':[]}
        data['submissions'].append(entry)
        write(path, data)
    return {'received':True,'reference':entry['id'][:8].upper(),'id':entry['id']}

@router.post('/public/service-request/{submission_id}/attachment')
async def public_service_attachment(submission_id: str, request: Request, file: UploadFile = File(...), reference: str = Form(...)):
    # A short-lived upload reference is intentionally required; uploads must be linked to a fresh public lead.
    if submission_id[:8].upper() != reference.strip().upper():
        raise HTTPException(403, 'Invalid upload reference')
    extension = Path(file.filename or '').suffix.lower()
    if extension not in ('.png','.jpg','.jpeg','.webp','.pdf'):
        raise HTTPException(400, 'Supported files: JPG, PNG, WEBP, PDF')
    contents = await file.read(5*1024*1024+1)
    if len(contents)>5*1024*1024 or not contents:
        raise HTTPException(413, 'File must be 1 byte to 5 MB')
    signatures = {'.pdf':contents.startswith(b'%PDF-'),'.png':contents.startswith(b'\x89PNG\r\n\x1a\n'),
                  '.jpg':contents.startswith(b'\xff\xd8\xff'),'.jpeg':contents.startswith(b'\xff\xd8\xff'),
                  '.webp':contents.startswith(b'RIFF') and contents[8:12]==b'WEBP'}
    if not signatures[extension]: raise HTTPException(400, 'File content does not match extension')
    with _lock:
        path=store(request);data=read(path)
        item=next((x for x in data['submissions'] if x.get('id')==submission_id and x.get('source')=='public_marketing_form'),None)
        if not item or (now()-datetime.fromisoformat(item['created_at'])).total_seconds()>1800:
            raise HTTPException(404, 'Upload window expired')
        if len(item.get('upload_ids',[]))>=5: raise HTTPException(400, 'Maximum five attachments')
        uid=uuid.uuid4().hex
        folder=path.parent/'portal_private_uploads';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(uid+extension)
        with dest.open('xb') as handle: handle.write(contents)
        item.setdefault('upload_ids',[]).append({'id':uid,'extension':extension,'filename':Path(file.filename or 'attachment').name[:160]})
        write(path,data)
    return {'uploaded':True}

@router.get('/admin/public-attachment/{submission_id}/{upload_id}')
def public_service_download(submission_id:str,upload_id:str,request:Request):
    admin(request)
    data=read(store(request))
    item=next((x for x in data['submissions'] if x.get('id')==submission_id and x.get('source')=='public_marketing_form'),None)
    attachment=next((a for a in item.get('upload_ids',[]) if a.get('id')==upload_id),None) if item else None
    if not attachment: raise HTTPException(404, 'Attachment not found')
    target=store(request).parent/'portal_private_uploads'/(attachment['id']+attachment['extension'])
    if not target.is_file(): raise HTTPException(404, 'Attachment unavailable')
    return FileResponse(target,filename=attachment['filename'],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


# Rev 65: customer identity is bound to a verified Doorks customer record ID.
# Public registration never grants invoice access until an office admin approves it.
from fastapi.responses import RedirectResponse
import base64
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import HTTPError

class PortalRegistration(BaseModel):
    email: str=Field(min_length=5,max_length=250)
    contact_name: str=Field(min_length=2,max_length=120)
    company: str=Field(min_length=1,max_length=160)
    password: str=Field(min_length=12,max_length=128)
    role: Literal['customer','vendor']
    password_confirm: str=Field(min_length=12,max_length=128)
    role_confirm: Literal['customer','vendor']

class PortalLogin(BaseModel):
    email: str
    password: str

class PortalApproval(BaseModel):
    customer_id: str=Field(default='',max_length=100)
    vendor_id: str=Field(default='',max_length=100)

def _password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    derived=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000)
    return salt+'$'+derived.hex()

def _password_valid(password, stored):
    try:
        salt,expected=stored.split('$',1)
        return hmac.compare_digest(_password_hash(password,salt),stored)
    except (ValueError,TypeError): return False

def _portal_origin(request):
    origin=request.headers.get('origin')
    if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Invalid request origin')

def _portal_user(request):
    aid=str(request.session.get('doorks_portal_account') or '')
    if not aid: raise HTTPException(401,'Customer login required')
    with _lock:
        obj=read(store(request))
        account=next((x for x in obj['accounts'] if x['id']==aid and x.get('status')=='active'),None)
    if not account: raise HTTPException(401,'Customer account inactive')
    if account.get('role','customer')!='customer': raise HTTPException(403,'Customer portal only')
    cid=str(account.get('customer_id') or '')
    if not cid or not any(str(c.get('id'))==cid for c in workspace_items(request,'customers')):
        raise HTTPException(403,'Customer record not available')
    return account

def _vendor_user(request):
    aid=str(request.session.get('doorks_portal_account') or '')
    with _lock:
        account=next((x for x in read(store(request))['accounts'] if x.get('id')==aid and x.get('status')=='active' and x.get('role')=='vendor'),None)
    if not account: raise HTTPException(401,'Vendor login required')
    vid=str(account.get('vendor_id') or '')
    if not vid or not any(str(v.get('id'))==vid for v in workspace_items(request,'vendors')) or vendor_is_suspended(request,vid):
        raise HTTPException(403,'Vendor account unavailable')
    return account

@router.get('/vendor-account/me')
def vendor_account_me(request:Request):
    a=_vendor_user(request)
    return {'name':a['contact_name'],'company':a['company'],'role':'vendor'}

@router.get('/vendor-account/records')
def vendor_account_records(request:Request):
    a=_vendor_user(request)
    # Reuse the same vendor-scoped, allowlisted projection as invitation access.
    return vendor_records(request,{'kind':'vendor','record_id':a['vendor_id']})

@router.post('/vendor-account/upload')
async def vendor_account_upload(request:Request,record_type:str=Form(...),record_id:str=Form(...),
                                note:str=Form(''),file:UploadFile=File(...)):
    _portal_origin(request)
    account=_vendor_user(request)
    if record_type not in ('assignment','purchase_order'):raise HTTPException(400,'Invalid record type')
    if len(note)>1000:raise HTTPException(400,'Note too long')
    scope={'kind':'vendor','record_id':account['vendor_id']}
    collection=vendor_records(request,scope)['assignments' if record_type=='assignment' else 'purchase_orders']
    record=next((x for x in collection if str(x['id'])==record_id),None)
    if not record:raise HTTPException(404,'Record not available')
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024:raise HTTPException(413,'File must be 1 byte to 5 MB')
    if content.startswith(b'%PDF-'):ext='pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):ext='png'
    elif content.startswith(b'\xff\xd8\xff'):ext='jpg'
    elif content.startswith(b'RIFF') and content[8:12]==b'WEBP':ext='webp'
    else:raise HTTPException(415,'Only PDF, JPG, PNG or WEBP supported')
    with _lock:
        account=_vendor_user(request)
        scope={'kind':'vendor','record_id':account['vendor_id']}
        collection=vendor_records(request,scope)['assignments' if record_type=='assignment' else 'purchase_orders']
        if not any(str(x['id'])==record_id for x in collection):raise HTTPException(404,'Record not available')
        p=store(request);obj=read(p);file_id=uuid.uuid4().hex
        folder=p.parent/'portal_private_uploads';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(file_id+'.'+ext)
        with dest.open('xb') as output:
            output.write(content);output.flush();os.fsync(output.fileno())
        entry={'id':uuid.uuid4().hex,'kind':'vendor','company':account['company'],
               'record_id':account['vendor_id'],'contact_name':account['contact_name'],
               'contact_email':account['email'],'source_record_id':record_id,
               'source_record_type':record_type,'subject':'Vendor document — '+record_type,
               'message':note.strip() or 'Supporting document uploaded',
               'reference':record.get('po_number') or record.get('work_order_number') or '',
               'upload_id':file_id,'upload_extension':ext,
               'original_filename':Path(file.filename or 'upload').name[:160],
               'file_size':len(content),'status':'pending_review','created_at':iso(now())}
        try:obj['submissions'].append(entry);write(p,obj)
        except Exception:
            dest.unlink(missing_ok=True);raise
    return {'ok':True,'submission_id':entry['id'],'status':'pending_review'}

@router.post('/accounts/register')
def portal_register(payload:PortalRegistration,request:Request):
    _portal_origin(request)
    if payload.password != payload.password_confirm: raise HTTPException(422,'Passwords do not match')
    if payload.role != payload.role_confirm: raise HTTPException(422,'Account type confirmation does not match')
    email=payload.email.strip().lower()
    if '@' not in email or len(email.split('@')[-1])<3: raise HTTPException(422,'Valid email required')
    with _lock:
        p=store(request);obj=read(p)
        if any(a['email']==email for a in obj['accounts']): raise HTTPException(409,'Account already registered; contact the office')
        account={'id':uuid.uuid4().hex,'email':email,'contact_name':payload.contact_name.strip(),
                 'company':payload.company.strip(),'password_hash':_password_hash(payload.password),
                 'customer_id':'','vendor_id':'','role':payload.role,'status':'pending','created_at':iso(now())}
        obj['accounts'].append(account)
        obj['notifications'].append({'id':uuid.uuid4().hex,'kind':'account_registration','created_at':iso(now()),
                                     'delivery':'office_only','message':payload.role.title()+' account awaiting verification: '+email})
        write(p,obj)
    return {'ok':True,'message':'Registration received. Office verification is required before login.'}

@router.get('/admin/accounts')
def list_portal_accounts(request:Request):
    admin(request)
    with _lock: obj=read(store(request))
    return {'accounts':[{k:v for k,v in a.items() if k not in ('password_hash','password_reset_hash','password_reset_expires')} for a in obj['accounts']]}

class PortalAccountEdit(BaseModel):
    contact_name: str=Field(min_length=1,max_length=150)
    company: str=Field(min_length=1,max_length=180)

@router.patch('/admin/accounts/{account_id}')
def edit_portal_account(account_id:str,payload:PortalAccountEdit,request:Request):
    admin(request)
    with _lock:
        path=store(request);obj=read(path)
        account=next((a for a in obj['accounts'] if a['id']==account_id),None)
        if not account: raise HTTPException(404,'Account not found')
        account['contact_name']=payload.contact_name.strip()
        account['company']=payload.company.strip()
        account['updated_at']=iso(now())
        write(path,obj)
    return {'ok':True}

@router.delete('/admin/accounts/{account_id}')
def deactivate_portal_account(account_id:str,request:Request):
    admin(request)
    with _lock:
        path=store(request);obj=read(path)
        account=next((a for a in obj['accounts'] if a['id']==account_id),None)
        if not account: raise HTTPException(404,'Account not found')
        account['status']='deactivated'
        account['deactivated_at']=iso(now())
        write(path,obj)
    return {'ok':True,'message':'Portal access deactivated; history preserved'}

@router.post('/admin/accounts/{account_id}/approve')
def approve_portal_account(account_id:str,payload:PortalApproval,request:Request):
    admin(request)
    with _lock:
        p=store(request);obj=read(p)
        a=next((x for x in obj['accounts'] if x['id']==account_id),None)
        if not a: raise HTTPException(404,'Account not found')
        if a['status']!='pending': raise HTTPException(409,'Account already processed')
        role=a.get('role','customer')
        rid=payload.vendor_id if role=='vendor' else payload.customer_id
        if not rid: raise HTTPException(422,'Select a verified '+role+' record')
        verify_invitation_link(request,role,rid)
        a[role+'_id']=rid;a['status']='active';a['verified_at']=iso(now())
        write(p,obj)
    return {'ok':True,'message':role.title()+' account approved. Notify the contact through a verified channel.'}

class PortalPasswordRequest(BaseModel):
    email: str=Field(min_length=3,max_length=250)

class PortalPasswordReset(BaseModel):
    token: str=Field(min_length=32,max_length=200)
    password: str=Field(min_length=12,max_length=128)
    password_confirm: str=Field(min_length=12,max_length=128)

@router.post('/accounts/forgot-password')
def portal_forgot_password(payload:PortalPasswordRequest,request:Request):
    """Privacy-safe request; office must verify identity before issuing a link."""
    _portal_origin(request)
    email=payload.email.strip().lower()
    with _lock:
        path=store(request); obj=read(path)
        account=next((a for a in obj['accounts'] if a.get('email')==email and a.get('status')=='active'),None)
        if account:
            # Avoid unbounded duplicate office notifications from repeat requests.
            recent=any(n.get('kind')=='password_reset_requested' and n.get('account_id')==account['id']
                       and (now()-datetime.fromisoformat(n['created_at'])).total_seconds()<3600
                       for n in obj['notifications'] if n.get('created_at'))
            if not recent:
                obj['notifications'].append({'id':uuid.uuid4().hex,'kind':'password_reset_requested',
                    'account_id':account['id'],'created_at':iso(now()),'delivery':'office_only',
                    'message':'Password reset requested for portal account '+email})
                write(path,obj)
    return {'ok':True,'message':'If an active account exists, the office will review the password reset request.'}

@router.post('/admin/accounts/{account_id}/password-reset-link')
def portal_admin_password_reset_link(account_id:str,request:Request):
    """Issue a one-time, 30-minute reset URL for delivery through a VERIFIED channel."""
    admin(request)
    with _lock:
        path=store(request);obj=read(path)
        account=next((a for a in obj['accounts'] if a['id']==account_id),None)
        if not account or account.get('status')!='active': raise HTTPException(404,'Active account not found')
        token=secrets.token_urlsafe(40)
        account['password_reset_hash']=hashlib.sha256(token.encode()).hexdigest()
        account['password_reset_expires']=iso(now()+timedelta(minutes=30))
        write(path,obj)
    return {'ok':True,'reset_url':str(request.base_url).rstrip('/')+'/doorks-portals/home#reset='+token,
            'expires_in_minutes':30,'delivery':'manual_verified_channel',
            'message':'Copy and deliver only after independently verifying the account holder.'}

@router.post('/accounts/reset-password')
def portal_reset_password(payload:PortalPasswordReset,request:Request):
    _portal_origin(request)
    if payload.password!=payload.password_confirm: raise HTTPException(422,'Passwords do not match')
    digest=hashlib.sha256(payload.token.encode()).hexdigest()
    with _lock:
        path=store(request);obj=read(path)
        account=next((a for a in obj['accounts'] if a.get('password_reset_hash') and
                      hmac.compare_digest(a['password_reset_hash'],digest)),None)
        if not account or account.get('status')!='active': raise HTTPException(400,'Invalid or expired reset link')
        try: expires=datetime.fromisoformat(account.get('password_reset_expires',''))
        except ValueError: raise HTTPException(400,'Invalid or expired reset link')
        if expires<=now(): raise HTTPException(400,'Invalid or expired reset link')
        account['password_hash']=_password_hash(payload.password)
        account.pop('password_reset_hash',None);account.pop('password_reset_expires',None)
        account['password_changed_at']=iso(now())
        write(path,obj)
    request.session.pop('doorks_portal_account',None)
    return {'ok':True,'message':'Password updated. Sign in with your new password.'}

@router.post('/accounts/login')
def portal_login(payload:PortalLogin,request:Request):
    _portal_origin(request)
    with _lock:
        obj=read(store(request))
        a=next((x for x in obj['accounts'] if x['email']==payload.email.strip().lower()),None)
    # Avoid leaking whether an email exists; constant-work check for nonexistent accounts.
    if not a:
        _password_valid(payload.password,_password_hash('dummy-password-for-timing'))
        raise HTTPException(401,'Invalid credentials or account awaiting approval')
    if not _password_valid(payload.password,a.get('password_hash','')) or a['status']!='active':
        raise HTTPException(401,'Invalid credentials or account awaiting approval')
    request.session['doorks_portal_account']=a['id']
    return {'ok':True,'name':a['contact_name'],'role':a.get('role','customer')}

@router.post('/accounts/logout')
def portal_logout(request:Request):
    _portal_origin(request)
    request.session.pop('doorks_portal_account',None)
    return {'ok':True}

@router.get('/accounts/me')
def portal_me(request:Request):
    a=_portal_user(request)
    return {'name':a['contact_name'],'email':a['email'],'company':a['company']}

@router.get('/accounts/documents')
def portal_account_documents(request:Request):
    a=_portal_user(request)
    return {'documents':customer_documents(request,{'kind':'customer','record_id':a['customer_id']})}

@router.get('/accounts/payments')
def portal_account_payments(request:Request):
    a=_portal_user(request)
    with _lock: obj=read(store(request))
    return {'payments':[{'invoice_id':x['invoice_id'],'amount':round(x['amount_cents']/100,2),
            'status':x['status'],'paid_at':x.get('paid_at','')} for x in obj['checkout_sessions']
            if x['customer_id']==a['customer_id'] and x['status']=='paid']}

@router.get('/accounts/work-orders')
def portal_account_work_orders(request:Request):
    a=_portal_user(request)
    allowed=('id','job_number','work_order_number','status','customer','address','service_type','scheduled_date','scheduled_time','description')
    return {'work_orders':[{k:r.get(k) for k in allowed} for r in workspace_items(request,'work_orders')
            if str(r.get('customer_id') or '')==a['customer_id'] and not r.get('deactivated_at')][:500]}

# Stripe Checkout uses the server-side invoice amount. Never accept an amount or
# customer ID from the browser. Checkout session IDs are stored for reconciliation.
class CheckoutRequest(BaseModel):
    document_id: str=Field(min_length=1,max_length=100)

def _stripe_api(endpoint,fields):
    key=os.environ.get('STRIPE_SECRET_KEY','')
    if not key.startswith('sk_test_') and not key.startswith('sk_live_'):
        raise HTTPException(503,'Stripe is not configured')
    req=UrlRequest('https://api.stripe.com/v1/'+endpoint,
        data=urlencode(fields).encode(),headers={'Authorization':'Bearer '+key,
        'Content-Type':'application/x-www-form-urlencoded'},method='POST')
    try:
        with urlopen(req,timeout=15) as response: return json.loads(response.read())
    except HTTPError as exc:
        raise HTTPException(502,'Stripe Checkout request failed') from exc
    except Exception as exc:
        raise HTTPException(502,'Stripe Checkout unavailable') from exc

@router.post('/accounts/checkout')
def portal_checkout(payload:CheckoutRequest,request:Request):
    _portal_origin(request)
    a=_portal_user(request)
    doc=invoice_record(request,payload.document_id)
    if str(doc.get('customer_id'))!=a['customer_id']: raise HTTPException(404,'Invoice not found')
    if str(doc.get('status','')).lower() in ('draft','voided','cancelled'):
        raise HTTPException(409,'Invoice is not payable')
    amount=round((float(doc.get('amount') or 0)-float(doc.get('paid') or 0))*100)
    if amount<50 or amount>99999999: raise HTTPException(409,'Invoice has no payable balance or exceeds limit')
    base=str(request.base_url).rstrip('/')
    session=_stripe_api('checkout/sessions',{
        'mode':'payment','success_url':base+'/doorks-portals/home?payment=return',
        'cancel_url':base+'/doorks-portals/home?payment=cancel',
        'line_items[0][price_data][currency]':'usd',
        'line_items[0][price_data][unit_amount]':str(amount),
        'line_items[0][price_data][product_data][name]':'Invoice '+str(doc.get('document_number') or doc['id'])[:80],
        'line_items[0][quantity]':'1',
        'client_reference_id':doc['id'],
        'metadata[doorks_invoice_id]':doc['id'],
        'metadata[doorks_customer_id]':a['customer_id'],
        'customer_email':a['email'],
    })
    if not str(session.get('id','')).startswith('cs_') or not str(session.get('url','')).startswith('https://checkout.stripe.com/'):
        raise HTTPException(502,'Stripe did not return a valid Checkout session')
    with _lock:
        p=store(request);obj=read(p)
        obj['checkout_sessions'].append({'id':session['id'],'invoice_id':doc['id'],'customer_id':a['customer_id'],
            'amount_cents':amount,'status':'created','created_at':iso(now())})
        write(p,obj)
    return {'url':session['url']}

@router.post('/stripe/webhook')
async def stripe_webhook(request:Request):
    secret=os.environ.get('STRIPE_WEBHOOK_SECRET','')
    if not secret.startswith('whsec_'): raise HTTPException(503,'Stripe webhook not configured')
    raw=await request.body()
    if len(raw)>1024*1024: raise HTTPException(413,'Event too large')
    header=request.headers.get('stripe-signature','')
    parts=dict(x.split('=',1) for x in header.split(',') if '=' in x)
    try: timestamp=int(parts.get('t','0'))
    except ValueError: raise HTTPException(400,'Invalid signature timestamp')
    if abs(now().timestamp()-timestamp)>300: raise HTTPException(400,'Expired signature')
    expected=hmac.new(secret.encode(),str(timestamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    signatures=[x[3:] for x in header.split(',') if x.startswith('v1=')]
    if not any(hmac.compare_digest(expected,sig) for sig in signatures): raise HTTPException(400,'Invalid Stripe signature')
    event=json.loads(raw)
    eid=str(event.get('id') or '')
    if not eid.startswith('evt_'): raise HTTPException(400,'Invalid event')
    typ=event.get('type')
    objdata=event.get('data',{}).get('object',{})
    with _lock:
        p=store(request);obj=read(p)
        if eid in obj['stripe_events']: return {'received':True,'duplicate':True}
        # Never credit an invoice until Stripe reports a paid session.
        if typ in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
            sid=str(objdata.get('id') or '')
            entry=next((x for x in obj['checkout_sessions'] if x['id']==sid),None)
            if entry and objdata.get('payment_status')=='paid' and entry['status']!='paid':
                if str(objdata.get('currency','')).lower()!='usd' or int(objdata.get('amount_total') or 0)!=entry['amount_cents']:
                    raise HTTPException(409,'Checkout amount mismatch')
                path=p.parent/'estimates_invoices.json'
                original=json.loads(path.read_text())
                rows=original if isinstance(original,list) else original.get('items',[])
                invoice=next((x for x in rows if str(x.get('id'))==entry['invoice_id'] and
                    str(x.get('customer_id'))==entry['customer_id'] and x.get('document_type')=='Invoice'),None)
                if not invoice: raise HTTPException(409,'Linked invoice missing')
                applied=invoice.setdefault('stripe_checkout_session_ids',[])
                if sid not in applied:
                    old_paid=round(float(invoice.get('paid') or 0)*100)
                    total=round(float(invoice.get('amount') or 0)*100)
                    if old_paid+entry['amount_cents']>total: raise HTTPException(409,'Invoice balance changed; manual reconciliation required')
                    invoice['paid']=round((old_paid+entry['amount_cents'])/100,2)
                    applied.append(sid)
                entry['status']='paid';entry['paid_at']=iso(now());entry['payment_intent']=objdata.get('payment_intent')
                # Persist invoice before acknowledging the webhook. Repeated delivery
                # uses the session status to avoid crediting it twice.
                write(path,original)
        elif typ=='checkout.session.async_payment_failed':
            entry=next((x for x in obj['checkout_sessions'] if x['id']==objdata.get('id')),None)
            if entry and entry['status']!='paid':entry['status']='failed'
        elif typ=='charge.refunded':
            # Refunds require review; never silently adjust books without a
            # verified charge-to-invoice reconciliation.
            obj['notifications'].append({'id':uuid.uuid4().hex,'kind':'stripe_refund_review',
                'created_at':iso(now()),'delivery':'office_only','message':'Stripe refund requires accounting reconciliation: '+str(objdata.get('id',''))})
        obj['stripe_events'].append(eid)
        write(p,obj)
    return {'received':True}

@router.get('/home',response_class=HTMLResponse)
def public_home(request:Request):
    return (Path(__file__).resolve().parents[2]/'static'/'doorks_home.html').read_text(encoding='utf-8')


class VendorInquiryLink(BaseModel):
    submission_id: str=Field(min_length=1,max_length=100)
    work_order_id: str=Field(default="",max_length=100)
    vendor_id: str=Field(min_length=1,max_length=100)

@router.post('/admin/inquiry-vendor-link')
def link_inquiry_vendor(payload:VendorInquiryLink,request:Request):
    admin(request)
    vendor=next((v for v in workspace_items(request,'vendors') if str(v.get('id'))==payload.vendor_id),None)
    if not vendor or vendor_is_suspended(request,payload.vendor_id):raise HTTPException(404,'Active vendor not found')
    from app.routers import workspaces as ws
    with _lock:
        p=store(request);obj=read(p)
        sub=next((x for x in obj['submissions'] if x['id']==payload.submission_id),None)
        if not sub or sub.get('kind') not in ('customer','public_service_request'):
            raise HTTPException(404,'Customer inquiry not found')
        # The submission's original customer record ID is authoritative.
        # Never associate financial records based only on a company name.
        jobs=workspace_items(request,'work_orders')
        job=next((j for j in jobs if str(j.get('id'))==str(sub.get('work_order_id') or '')),None)
        if payload.work_order_id:
            requested=next((j for j in jobs if str(j.get('id'))==payload.work_order_id),None)
            if not requested:raise HTTPException(404,'Work order not found')
            if sub.get('record_id') and str(requested.get('customer_id') or '')!=str(sub['record_id']):
                raise HTTPException(409,'Inquiry customer does not match work order customer')
            if job and job['id']!=requested['id']:raise HTTPException(409,'Inquiry already linked to another work order')
            job=requested
        if not job:
            if sub.get('record_id') and not any(str(c.get('id'))==str(sub['record_id']) for c in workspace_items(request,'customers')):
                raise HTTPException(409,'Linked customer record no longer exists')
            fields={
                'customer':str(sub.get('company') or sub.get('contact_name') or 'New inquiry')[:160],
                'customer_id':str(sub.get('record_id') or ''),
                'contact':str(sub.get('contact_name') or '')[:120],
                'email':str(sub.get('contact_email') or '')[:250],
                'phone':str(sub.get('contact_phone') or '')[:50],
                'address':str(sub.get('address') or '')[:300],
                'description':str(sub.get('message') or sub.get('description') or sub.get('subject') or '')[:3000],
                'service_type':str(sub.get('service_type') or '')[:100],
                'priority':str(sub.get('urgency') or 'Normal')[:40],
                'scheduled_date':str(sub.get('preferred_date') or '')[:10],
                'date':str(sub.get('preferred_date') or now().date().isoformat())[:10],
                'schedule_confirmation':'Requested — office confirmation pending',
                'scheduled_time':str(sub.get('preferred_time') or '')[:80],
                'status':'Dispatch', 'source_submission_id':sub['id'],
            }
            # Use the existing workspace creation function to reserve the
            # monthly work-order number under its own sequence lock.
            created=ws.create('doorks','work_orders',ws.Record(data=fields),request)
            job=created['item']
        # Create a DRAFT assignment in the actual Doorks workspace collection.
        # The vendor portal excludes Draft until an office user reviews/activates it.
        from app.routers import workspaces as ws
        assignment_path=ws.location(request,'doorks','vendor_assignments')
        with ws._lock:
            assignments=ws.load(assignment_path)
            assignment=next((a for a in assignments if a.get('source_submission_id')==sub['id']),None)
            if assignment and (str(assignment.get('work_order_id'))!=str(job['id']) or str(assignment.get('vendor_id'))!=payload.vendor_id):
                raise HTTPException(409,'Inquiry already linked to another assignment')
            if not assignment:
                assignment={'id':uuid.uuid4().hex,'source_submission_id':sub['id'],
                    'work_order_id':job['id'],'work_order_number':str(job.get('job_number') or job.get('work_order_number') or ''),
                    'vendor_id':payload.vendor_id,'vendor':str(vendor.get('name') or ''),
                    'customer':str(job.get('customer') or ''),'customer_id':str(job.get('customer_id') or ''),
                    'address':str(job.get('address') or ''),'scheduled_date':str(job.get('scheduled_date') or ''),
                    'scheduled_time':str(job.get('scheduled_time') or ''),'scope':str(job.get('description') or '')[:2000],
                    'status':'Draft','created_at':iso(now())}
                assignments.append(assignment)
                ws.save(assignment_path,assignments)
        sub['work_order_id']=job['id']
        sub['vendor_id']=payload.vendor_id
        sub['vendor_assignment_id']=assignment['id']
        sub['linked_at']=iso(now())
        obj['notifications'].append({'id':uuid.uuid4().hex,'kind':'vendor_assignment_link',
            'delivery':'office_only','created_at':iso(now()),
            'message':'Inquiry linked to work order and vendor; create/approve assignment before sharing'})
        write(p,obj)
    return {'ok':True,'work_order_id':job['id'],'work_order_number':job.get('job_number',''),'vendor_id':payload.vendor_id,
            'message':'Draft vendor assignment created and linked to inquiry and work order. Approve its status in Vendor Assignments to make it visible to the vendor.'}


@router.get('/',include_in_schema=False)
def portal_marketing_redirect():
    return RedirectResponse('/doorks-portals/home',status_code=302)

# Rev 70: explicit office release and vendor response. Drafts remain private.
class VendorAssignmentRelease(BaseModel):
    assignment_id: str

class VendorAssignmentDecision(BaseModel):
    assignment_id: str
    decision: Literal['accepted','declined']

@router.get('/admin/vendor-onboarding')
def vendor_onboarding_queue(request:Request):
    admin(request)
    with _lock:
        obj=read(store(request))
        accounts=[{k:v for k,v in a.items() if k not in ('password_hash','password_reset_hash','password_reset_expires')} for a in obj['accounts'] if a.get('role')=='vendor']
    return {'accounts':accounts,'vendors':[{'id':v.get('id'),'name':v.get('name'),'onboarding_status':v.get('onboarding_status','')} for v in workspace_items(request,'vendors')],
            'instructions':'Approve a pending vendor account against a verified vendor record using POST /admin/accounts/{id}/approve with vendor_id. Draft assignments require separate office release.'}

@router.post('/admin/vendor-assignments/release')
def release_vendor_assignment(payload:VendorAssignmentRelease,request:Request):
    admin(request)
    from app.routers import workspaces as ws
    with _lock:
        path=ws.location(request,'doorks','vendor_assignments');rows=ws.load(path)
        row=next((r for r in rows if str(r.get('id'))==payload.assignment_id),None)
        if not row:raise HTTPException(404,'Vendor assignment not found')
        if str(row.get('status','')).lower()!='draft':raise HTTPException(409,'Only draft assignments may be released')
        vid=str(row.get('vendor_id') or '')
        verify_invitation_link(request,'vendor',vid)
        if not vid:raise HTTPException(409,'Assignment must have a verified vendor ID')
        row['status']='Offered';row['released_at']=iso(now());row['released_by']=str(request.state.auth_user.get('id',''))
        ws.save(path,rows)
        return {'item':row,'message':'Assignment is now visible to the linked vendor account'}

@router.post('/vendor-account/assignments/decision')
def vendor_assignment_decision(payload:VendorAssignmentDecision,request:Request):
    _portal_origin(request)
    account=_vendor_user(request)
    from app.routers import workspaces as ws
    with _lock:
        path=ws.location(request,'doorks','vendor_assignments');rows=ws.load(path)
        row=next((r for r in rows if str(r.get('id'))==payload.assignment_id and str(r.get('vendor_id'))==str(account['vendor_id'])),None)
        if not row:raise HTTPException(404,'Assignment not found for this vendor')
        if str(row.get('status','')).lower()!='offered':raise HTTPException(409,'Only offered assignments can be accepted or declined')
        row['status']='Accepted' if payload.decision=='accepted' else 'Declined'
        row['vendor_responded_at']=iso(now());row['vendor_responded_by']=account['id']
        ws.save(path,rows)
        return {'item':{k:row.get(k) for k in ('id','status','work_order_number','scheduled_date')},'ok':True}
