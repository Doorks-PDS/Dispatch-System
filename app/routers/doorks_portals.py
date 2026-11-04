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
    subject: str=Field(min_length=1,max_length=160)
    message: str=Field(min_length=1,max_length=2000)
    reference: str=Field(default='',max_length=100)

@router.post('/submit')
def submit(payload:Submission,request:Request):
    with _lock:
        p=store(request);obj=read(p)
        i=access(request,payload.token)
        # Never trust user-supplied company or entity IDs; derive identity from the invitation.
        item={'id':str(uuid.uuid4()),'invite_id':i['id'],'kind':i['kind'],'company':i['company'],
              'record_id':i['record_id'],'contact_name':i['contact_name'],'contact_email':i['contact_email'],
              'subject':payload.subject.strip(),'message':payload.message.strip(),
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
            filename='vendor-upload-'+submission_id+'.'+ext,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.get('/access',response_class=HTMLResponse)
def portal_page(response: HTMLResponse):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Doorks Portal</title><style>body{font:16px system-ui;background:#f5f7fa;color:#17212f;margin:0;padding:30px}main{max-width:620px;margin:40px auto;background:white;padding:28px;border-radius:14px;box-shadow:0 4px 25px #0001}label{display:block;margin:15px 0 6px}input,textarea{box-sizing:border-box;width:100%;padding:12px;border:1px solid #bbc4ce;border-radius:7px;font:inherit}textarea{min-height:140px}button{padding:12px 20px;background:#183c62;color:white;border:0;border-radius:7px;margin-top:18px;cursor:pointer}#status{margin-top:18px;white-space:pre-wrap}</style></head><body><main><h1>Doorks Portal</h1><p id="identity">Checking access…</p><form id="form" hidden><label for="subject">Subject</label><input id="subject" maxlength="160" required><label for="reference">Reference / work order (optional)</label><input id="reference" maxlength="100"><label for="message">Details</label><textarea id="message" maxlength="2000" required></textarea><button type="submit">Submit for review</button></form><p id="status" role="status"></p><section id="docs" hidden><h2>My estimates & invoices</h2><p id="docHint"></p><div id="docList"></div></section></main><script>const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);const identity=document.getElementById('identity'),form=document.getElementById('form'),status=document.getElementById('status');async function run(){try{if(!token)throw Error('Missing invitation token');const r=await fetch('/doorks-portals/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token}),cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.detail||'Access denied');identity.textContent=(d.kind==='customer'?'Customer':'Vendor')+' portal — '+d.company+' ('+d.contact_name+')';form.hidden=false;if(d.kind==='customer'){
 const section=document.getElementById('docs'),list=document.getElementById('docList'),hint=document.getElementById('docHint');section.hidden=false;
 try{const rr=await fetch('/doorks-portals/customer/documents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token}),cache:'no-store'});const data=await rr.json();if(!rr.ok)throw Error(data.detail||'Unable to load documents');
 hint.textContent=data.documents.length?'Only published documents linked to your customer account are shown.':'No published documents available. Ask the office to link your customer record if needed.';
 for(const doc of data.documents){const box=document.createElement('div');box.style.cssText='border:1px solid #d4dce5;border-radius:9px;padding:14px;margin:12px 0';
 const title=document.createElement('h3');title.textContent=doc.document_type+' '+doc.document_number;box.append(title);
 const detail=document.createElement('p');detail.textContent='Date: '+doc.date+' | Status: '+doc.status+' | Total: $'+Number(doc.amount).toFixed(2)+(doc.document_type==='Invoice'?' | Balance: $'+Number(doc.balance_due).toFixed(2):'');box.append(detail);
 if(doc.line_items&&doc.line_items.length){const ul=document.createElement('ul');for(const line of doc.line_items){const li=document.createElement('li');li.textContent=(line.description||line.item||'Item')+' × '+(line.quantity||1);ul.append(li)}box.append(ul)}
 if(doc.document_type==='Invoice'&&Number(doc.balance_due)>0){if(doc.checkout_url){const pay=document.createElement('a');pay.href=doc.checkout_url;pay.target='_blank';pay.rel='noopener noreferrer';pay.textContent='Pay securely with external provider';pay.style.cssText='display:inline-block;margin:8px 12px 8px 0';box.append(pay)}const ask=document.createElement('button');ask.type='button';ask.textContent='Ask about payment';ask.onclick=async()=>{const note=prompt('Question for the office (optional):') ;if(note===null)return;ask.disabled=true;try{const r=await fetch('/doorks-portals/customer/payment-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,document_id:doc.id,note,request_id:crypto.randomUUID()})});const d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');alert('Sent to office for review. No payment was recorded.')}catch(e){alert(e.message)}finally{ask.disabled=false}};box.append(ask)}
 if(doc.document_type==='Estimate'&&['sent','quote sent','pending approval'].includes(doc.status.toLowerCase())){const note=document.createElement('input');note.placeholder='Optional note';note.maxLength=1000;box.append(note);for(const decision of ['approve','decline','question']){const b=document.createElement('button');b.type='button';b.textContent=decision==='approve'?'Request Approval':decision==='decline'?'Decline':'Ask a Question';b.style.marginRight='8px';b.onclick=async()=>{b.disabled=true;try{const res=await fetch('/doorks-portals/customer/document-response',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,document_id:doc.id,decision,note:note.value})});const out=await res.json();if(!res.ok)throw Error(out.detail||'Request failed');b.parentElement.querySelector('p').textContent='Response received for office review. No document status changed automatically.';}catch(e){alert(e.message)}finally{b.disabled=false}};box.append(b)}}list.append(box)}
 }catch(err){hint.textContent=err.message}
 }else if(d.kind==='vendor'){
 const section=document.createElement('section');const heading=document.createElement('h2');heading.textContent='My assignments & purchase orders';section.append(heading);form.before(section);
 try{const rr=await fetch('/doorks-portals/vendor/records',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token}),cache:'no-store'});const data=await rr.json();if(!rr.ok)throw Error(data.detail||'Unable to load vendor records');
 if(!data.linked){const p=document.createElement('p');p.textContent='This invitation is not linked to a saved vendor record. Contact the office.';section.append(p)}
 for(const [type,records] of [['assignment',data.assignments],['purchase_order',data.purchase_orders]]){
 const h=document.createElement('h3');h.textContent=type==='assignment'?'Assignments':'Purchase orders';section.append(h);
 if(!records.length){const p=document.createElement('p');p.textContent='No available records.';section.append(p)}
 for(const record of records){const box=document.createElement('div');box.style.cssText='border:1px solid #d4dce5;border-radius:9px;padding:14px;margin:12px 0';
 const title=document.createElement('strong');title.textContent=(record.po_number||record.work_order_number||'Record')+' — '+record.status;box.append(title);
 const detail=document.createElement('p');detail.textContent=type==='assignment'?[record.scope,record.scheduled_date,record.scheduled_time,record.address].filter(Boolean).join(' | '):[record.description,record.quantity?'Qty: '+record.quantity:'',record.received_quantity?'Received: '+record.received_quantity:''].filter(Boolean).join(' | ');box.append(detail);
 const sel=document.createElement('select');for(const value of (type==='assignment'?['accepted','declined','in_progress','completed','delayed','question']:['shipped','received','delayed','question'])){const o=document.createElement('option');o.value=value;o.textContent=value.replaceAll('_',' ');sel.append(o)}box.append(sel);
 const note=document.createElement('textarea');note.placeholder='Optional update details';note.maxLength=2000;note.style.minHeight='70px';box.append(note);
 const send=document.createElement('button');send.type='button';send.textContent='Submit update for office review';send.onclick=async()=>{send.disabled=true;try{const id=crypto.randomUUID();const res=await fetch('/doorks-portals/vendor/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,record_type:type,record_id:record.id,update_status:sel.value,note:note.value,request_id:id})});const out=await res.json();if(!res.ok)throw Error(out.detail||'Update failed');alert('Update submitted for office review.');note.value=''}catch(e){alert(e.message)}finally{send.disabled=false}};box.append(send);
 const upload=document.createElement('input');upload.type='file';upload.accept='.pdf,.png,.jpg,.jpeg,.webp';upload.style.marginTop='12px';box.append(upload);
 const up=document.createElement('button');up.type='button';up.textContent='Upload supporting document';up.onclick=async()=>{if(!upload.files.length){alert('Choose a file first');return}up.disabled=true;try{const fd=new FormData();fd.append('token',token);fd.append('record_type',type);fd.append('record_id',record.id);fd.append('note',note.value);fd.append('file',upload.files[0]);const res=await fetch('/doorks-portals/vendor/upload',{method:'POST',body:fd});const out=await res.json();if(!res.ok)throw Error(out.detail||'Upload failed');alert('Document submitted for office review.');upload.value=''}catch(e){alert(e.message)}finally{up.disabled=false}};box.append(up);section.append(box)}
 }
 }catch(err){const p=document.createElement('p');p.textContent=err.message;section.append(p)}
 }form.onsubmit=async e=>{e.preventDefault();status.textContent='Submitting…';try{const res=await fetch('/doorks-portals/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,subject:document.getElementById('subject').value,reference:document.getElementById('reference').value,message:document.getElementById('message').value})});const out=await res.json();if(!res.ok)throw Error(out.detail||'Submission failed');status.textContent='Received for office review. Reference: '+out.submission_id;form.reset()}catch(err){status.textContent=err.message}}}catch(e){identity.textContent=e.message}}run();</script></body></html>'''
