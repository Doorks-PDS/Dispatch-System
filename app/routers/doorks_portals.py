"""Doorks-only limited external portal, invitation-based, no access to internal workspace APIs."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from threading import RLock
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
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
        if not invite or invite['revoked'] or datetime.fromisoformat(invite['expires_at'])<=now():
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
    days: int=Field(default=14,ge=1,le=30)

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
               'created_at':iso(now()),'expires_at':iso(now()+timedelta(days=payload.days)),
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
        if invite.get('revoked') or datetime.fromisoformat(invite['expires_at']) <= now():
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
    return {'active_invitations': sum(not x.get('revoked') and datetime.fromisoformat(x['expires_at']) > now() for x in obj['invites']),
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

@router.post('/submit')
def submit(payload:Submission,request:Request):
    if not (payload.subject.strip() or payload.message.strip() or payload.reference.strip()):
        raise HTTPException(400,'Enter a subject, details or reference before submitting')
    with _lock:
        p=store(request);obj=read(p)
        i=access(request,payload.token)
        # Never trust user-supplied company or entity IDs; derive identity from the invitation.
        item={'id':str(uuid.uuid4()),'invite_id':i['id'],'kind':i['kind'],'company':i['company'],
              'record_id':i['record_id'],'contact_name':i['contact_name'],'contact_email':i['contact_email'],
              'subject':payload.subject.strip() or 'Customer inquiry / update','message':payload.message.strip(),
              'reference':payload.reference.strip(),'status':'pending_review','created_at':iso(now())}
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
