"""Public Atlas software catalog and inquiry intake on the existing Doorks service."""
from __future__ import annotations
import csv, io, json, os, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response, HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=['sdc-storefront'])
def _shared_workspace_lock():
    """Use the same lock as workspace CRUD for software leads and customers.

    Public intake and admin edits write to the same JSON files; independent
    locks can otherwise lose updates during concurrent submissions/edits.
    """
    from app.routers import workspaces as ws
    return ws._lock

PACKAGES = (
    {'name':'Basic','description':'Dispatch, work orders, scheduling, customers, forms and team management.'},
    {'name':'Platinum','description':'Basic plus customer and vendor portals, assignment tracking and document collaboration.'},
    {'name':'Premium','description':'Platinum plus accounting, purchasing, receiving, AI intake and connected workflows.'},
    {'name':'Personalized','description':'Custom integrations, branding, onboarding and tailored workflows.'},
)

class SoftwareInquiry(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    contact: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(default='', max_length=40)
    package: str = Field(min_length=1, max_length=40)
    notes: str = Field(default='', max_length=2000)
    website: str = Field(default='', max_length=200)  # hidden honeypot; never reuse for company URL
    company_website: str = Field(default='', max_length=300)
    utm_source: str = Field(default='', max_length=100)
    utm_medium: str = Field(default='', max_length=100)
    utm_campaign: str = Field(default='', max_length=100)
    landing_page: str = Field(default='', max_length=300)

@router.get('/software')
def software_storefront(request: Request):
    path = Path(request.app.state.project_root if hasattr(request.app.state,'project_root') else Path(__file__).resolve().parents[2]) / 'static' / 'sdc_software.html'
    return FileResponse(path, media_type='text/html')

@router.get('/api/software/packages')
def software_packages():
    return {'packages': PACKAGES, 'pricing':'Contact us for a quote'}

def _recent_matching_inquiry(rows, company, email, package, now):
    """Prevent accidental double-submission without merging different inquiries."""
    cutoff = now - timedelta(minutes=2)
    for row in reversed(rows):
        if not isinstance(row, dict):
            continue
        if (str(row.get('company', '')).strip().casefold() != company.casefold()
                or str(row.get('email', '')).strip().casefold() != email.casefold()
                or row.get('package') != package):
            continue
        try:
            created = datetime.fromisoformat(str(row.get('created_at', '')).replace('Z', '+00:00'))
            if created.tzinfo is not None and cutoff <= created.astimezone(timezone.utc) <= now:
                return row
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def _recent_inquiry_count(rows, email, now, window=timedelta(hours=1)):
    """Count accepted submissions by an email address in the existing lead store.

    This is a lightweight per-email abuse safeguard, not an IP-based rate limiter.
    """
    cutoff = now - window
    count = 0
    for row in rows:
        if not isinstance(row, dict) or str(row.get('email', '')).strip().casefold() != email.casefold():
            continue
        try:
            created = datetime.fromisoformat(str(row.get('created_at', '')).replace('Z', '+00:00'))
            if created.tzinfo is not None and cutoff <= created.astimezone(timezone.utc) <= now:
                count += 1
        except (TypeError, ValueError, OverflowError):
            continue
    return count


@router.post('/api/software/inquiries', status_code=201)
def submit_software_inquiry(payload: SoftwareInquiry, request: Request):
    if payload.website:  # do not disclose honeypot
        return {'ok':True,'message':'Inquiry received'}
    if payload.company_website.strip():
        from urllib.parse import urlsplit
        try:
            parsed = urlsplit(payload.company_website.strip())
            if parsed.scheme.lower() not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or any(ch.isspace() for ch in payload.company_website):
                raise ValueError('Invalid company website')
        except ValueError as exc:
            raise HTTPException(400, 'Enter a valid website URL beginning with https:// or http://') from exc
    if not payload.company.strip() or not payload.contact.strip():
        raise HTTPException(400,'Business name and contact are required')
    if any(ord(ch) < 32 and ch not in '\t\n\r' for ch in payload.notes):
        raise HTTPException(400,'Invalid inquiry text')
    if payload.package not in {p['name'] for p in PACKAGES}:
        raise HTTPException(400,'Select an available package')
    if ('@' not in payload.email or '.' not in payload.email.rsplit('@',1)[-1]
            or any(ch.isspace() for ch in payload.email.strip())):
        raise HTTPException(400,'Enter a valid email address')
    base = Path(request.app.state.data_dir) / 'business_workspaces' / 'sdc'
    path = base / 'software_leads.json'
    record = {'id':uuid.uuid4().hex, 'company':payload.company.strip(), 'contact':payload.contact.strip(),
              'email':payload.email.strip(), 'phone':payload.phone.strip(), 'company_website':payload.company_website.strip(), 'package':payload.package,
              'notes':payload.notes.strip(), 'setup_assistance':'Discuss during consultation',
              'status':'New', 'source':'public_software_storefront',
              'utm_source':payload.utm_source.strip(), 'utm_medium':payload.utm_medium.strip(),
              'utm_campaign':payload.utm_campaign.strip(), 'landing_page':payload.landing_page.strip(),
              'created_at':datetime.now(timezone.utc).isoformat()}
    with _shared_workspace_lock():
        base.mkdir(parents=True,exist_ok=True)
        try:
            existing=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        except (ValueError,OSError) as exc:
            raise HTTPException(500,'Inquiry storage unavailable') from exc
        if not isinstance(existing,list):
            raise HTTPException(500,'Inquiry storage unavailable')
        duplicate = _recent_matching_inquiry(existing, record['company'], record['email'], record['package'], datetime.now(timezone.utc))
        if duplicate:
            return {'ok': True, 'message': 'Inquiry received', 'reference': str(duplicate['id'])[:8], 'duplicate': True}
        # Duplicate retries return their existing reference before the hourly limit.
        # Never erase or mutate older inquiries when the limit is reached.
        if _recent_inquiry_count(existing, record['email'], datetime.now(timezone.utc)) >= 5:
            raise HTTPException(429, 'Too many inquiries from this email. Please try again later.')
        existing.append(record)
        temp=path.with_suffix('.json.tmp')
        with temp.open('w',encoding='utf-8') as f:
            json.dump(existing,f,indent=2,ensure_ascii=False)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    return {'ok':True,'message':'Inquiry received','reference':record['id'][:8]}


@router.get('/api/software/inquiries')
def list_software_inquiries(request: Request):
    """Admin-only view of public software leads; never exposed to storefront visitors."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    path = ws.location(request, 'sdc', 'software_leads')
    with _shared_workspace_lock():
        leads = ws.load(path)
    return {'items': sorted(leads, key=lambda row: str(row.get('created_at', '')), reverse=True)}


def _software_lead_summary(leads, today=None):
    """Read-only lead pipeline summary; invalid legacy dates never crash reporting."""
    from datetime import date
    today = today or date.today()
    statuses = {name: 0 for name in LEAD_STATUSES}
    due = overdue = demos_scheduled = 0
    for row in leads:
        if not isinstance(row, dict):
            continue
        status = row.get('status') or 'New'
        if status in statuses:
            statuses[status] += 1
        if status == 'Demo Scheduled':
            demos_scheduled += 1
        if status in ('Won', 'Lost'):
            continue
        raw = row.get('follow_up_date') or ''
        try:
            day = date.fromisoformat(raw) if raw else None
        except (TypeError, ValueError):
            continue
        if day and day <= today:
            due += 1
            overdue += day < today
    return {'total': sum(isinstance(row, dict) for row in leads),
            'by_status': statuses, 'followups_due': due, 'followups_overdue': overdue, 'demos_scheduled': demos_scheduled}


@router.get('/api/software/inquiries/summary')
def software_inquiry_summary(request: Request):
    """Admin-only overview; no personal lead details exposed in summary."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    with _shared_workspace_lock():
        rows = ws.load(ws.location(request, 'sdc', 'software_leads'))
    return _software_lead_summary(rows)


@router.get('/api/software/inquiries/export.csv')
def export_software_inquiries(request: Request):
    """Admin-only CSV export. Prefix formula-like cells to prevent spreadsheet execution."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    with _shared_workspace_lock():
        rows = ws.load(ws.location(request, 'sdc', 'software_leads'))
    headers = ('company', 'contact', 'email', 'phone', 'company_website', 'package', 'status',
               'created_at', 'follow_up_date', 'demo_date', 'proposal_date', 'proposal_amount', 'proposal_terms', 'notes', 'internal_notes',
               'utm_source', 'utm_medium', 'utm_campaign', 'landing_page')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(headers)
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = []
        for field in headers:
            value = str(row.get(field) or '')
            if value.lstrip().startswith(('=', '+', '-', '@')):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return Response(content='\ufeff' + stream.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="sdc-software-inquiries.csv"',
                             'Cache-Control': 'no-store'})


class LeadStatusUpdate(BaseModel):
    status: str | None = Field(default=None, min_length=1, max_length=30)
    internal_notes: str | None = Field(default=None, max_length=4000)
    follow_up_date: str | None = Field(default=None, max_length=10)
    demo_date: str | None = Field(default=None, max_length=10)
    proposal_date: str | None = Field(default=None, max_length=10)
    proposal_amount: str | None = Field(default=None, max_length=20)
    proposal_terms: str | None = Field(default=None, max_length=2000)
    onboarding_completed: list[str] | None = None

LEAD_STATUSES = ('New', 'Contacted', 'Demo Scheduled', 'Demo Completed', 'Proposal Sent', 'Won', 'Lost')
ONBOARDING_STEPS = ('requirements_confirmed', 'package_confirmed', 'agreement_signed', 'payment_arranged', 'configuration_planned', 'training_scheduled', 'launch_verified')

@router.get('/sdc/software-leads')
def software_leads_dashboard(request: Request):
    """Protected SDC lead dashboard; uses existing app and storage."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    root = Path(getattr(request.app.state, 'project_root', Path(__file__).resolve().parents[2]))
    return FileResponse(root / 'static' / 'sdc_software_leads.html', media_type='text/html')

@router.patch('/api/software/inquiries/{lead_id}')
def update_software_inquiry(lead_id: str, payload: LeadStatusUpdate, request: Request):
    """Admin-only status change; preserve all original inquiry fields."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    if payload.status is not None and payload.status not in LEAD_STATUSES:
        raise HTTPException(400, 'Invalid lead status')
    from datetime import date
    for field_name in ('follow_up_date', 'demo_date', 'proposal_date'):
        value = getattr(payload, field_name)
        if value is not None:
            try:
                if value and date.fromisoformat(value).isoformat() != value:
                    raise ValueError('Non-ISO date')
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, field_name.replace('_', ' ').capitalize() + ' must be YYYY-MM-DD') from exc
    # Store proposal prices as a normalized decimal string rather than a
    # floating-point number. Blank means no price has been agreed.
    from decimal import Decimal, InvalidOperation
    normalized_amount = None
    if payload.proposal_amount is not None:
        raw_amount = payload.proposal_amount.strip()
        if raw_amount:
            try:
                amount = Decimal(raw_amount)
            except InvalidOperation as exc:
                raise HTTPException(400, 'Proposal amount must be a valid dollar amount') from exc
            if not amount.is_finite() or amount < 0 or amount > Decimal('99999999.99') or amount.as_tuple().exponent < -2:
                raise HTTPException(400, 'Proposal amount must be between $0 and $99,999,999.99 with at most two decimals')
            normalized_amount = format(amount.quantize(Decimal('0.01')), 'f')
        else:
            normalized_amount = ''
    if payload.onboarding_completed is not None:
        if len(payload.onboarding_completed) != len(set(payload.onboarding_completed)) or any(step not in ONBOARDING_STEPS for step in payload.onboarding_completed):
            raise HTTPException(400, 'Invalid onboarding checklist')
    if payload.status is None and payload.internal_notes is None and payload.follow_up_date is None and payload.demo_date is None and payload.proposal_date is None and payload.proposal_amount is None and payload.proposal_terms is None and payload.onboarding_completed is None:
        raise HTTPException(400, 'No changes supplied')
    if len(lead_id) != 32 or any(ch not in '0123456789abcdef' for ch in lead_id):
        raise HTTPException(400, 'Invalid lead identifier')
    with _shared_workspace_lock():
        path = ws.location(request, 'sdc', 'software_leads')
        rows = ws.load(path)
        target = next((row for row in rows if isinstance(row, dict) and row.get('id') == lead_id), None)
        if target is None:
            raise HTTPException(404, 'Inquiry not found')
        now = datetime.now(timezone.utc).isoformat()
        if payload.status is not None and target.get('status', 'New') != payload.status:
            history = target.get('status_history')
            if not isinstance(history, list):
                history = []
            history.append({'from': target.get('status', 'New'), 'to': payload.status, 'at': now})
            target['status_history'] = history[-100:]
            target['status'] = payload.status
        if payload.internal_notes is not None:
            target['internal_notes'] = payload.internal_notes.strip()
        if payload.follow_up_date is not None:
            target['follow_up_date'] = payload.follow_up_date
        if payload.demo_date is not None:
            target['demo_date'] = payload.demo_date
        if payload.proposal_date is not None:
            target['proposal_date'] = payload.proposal_date
        if normalized_amount is not None:
            target['proposal_amount'] = normalized_amount
        if payload.proposal_terms is not None:
            target['proposal_terms'] = payload.proposal_terms.strip()
        if payload.onboarding_completed is not None:
            target['onboarding_completed'] = [step for step in ONBOARDING_STEPS if step in payload.onboarding_completed]
        target['updated_at'] = now
        ws.save(path, rows)
    return {'ok': True, 'id': lead_id, 'status': target.get('status', 'New'),
            'follow_up_date': target.get('follow_up_date', ''),
            'demo_date': target.get('demo_date', ''),
            'proposal_date': target.get('proposal_date', ''),
            'proposal_amount': target.get('proposal_amount', ''),
            'proposal_terms': target.get('proposal_terms', ''),
            'onboarding_completed': target.get('onboarding_completed', [])}


@router.delete('/api/software/inquiries/{lead_id}')
def delete_software_inquiry(lead_id: str, request: Request):
    """Explicit admin-only lead deletion; does not touch linked customer records."""
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    if len(lead_id) != 32 or any(ch not in '0123456789abcdef' for ch in lead_id):
        raise HTTPException(400, 'Invalid lead identifier')
    with _shared_workspace_lock():
        path = ws.location(request, 'sdc', 'software_leads')
        rows = ws.load(path)
        if not any(isinstance(row, dict) and row.get('id') == lead_id for row in rows):
            raise HTTPException(404, 'Inquiry not found')
        ws.save(path, [row for row in rows if not (isinstance(row, dict) and row.get('id') == lead_id)])
    return {'ok': True, 'deleted_id': lead_id}


@router.get('/api/software/inquiries/{lead_id}/proposal')
def printable_software_proposal(lead_id: str, request: Request):
    """Admin-only printable proposal; browser Print > Save as PDF.

    Read-only: viewing a draft never marks a lead as Proposal Sent.
    """
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    if len(lead_id) != 32 or any(ch not in '0123456789abcdef' for ch in lead_id):
        raise HTTPException(400, 'Invalid lead identifier')
    with _shared_workspace_lock():
        rows = ws.load(ws.location(request, 'sdc', 'software_leads'))
        lead = next((row.copy() for row in rows if isinstance(row, dict) and row.get('id') == lead_id), None)
    if lead is None:
        raise HTTPException(404, 'Inquiry not found')
    from html import escape
    def safe(value):
        return escape(str(value or ''), quote=True)
    def multiline(value):
        return safe(value).replace('\n', '<br>')
    package = str(lead.get('package') or 'Custom')
    description = next((p['description'] for p in PACKAGES if p['name'] == package), 'Custom software configuration, subject to agreed scope.')
    amount = lead.get('proposal_amount')
    from decimal import Decimal, InvalidOperation
    try:
        formatted_amount = '${:,.2f}'.format(Decimal(str(amount))) if amount not in (None, '') else 'To be confirmed'
    except (InvalidOperation, ValueError):
        formatted_amount = 'To be confirmed'
    terms = lead.get('proposal_terms') or 'Implementation scope, pricing, billing cadence, and delivery dates are subject to written agreement.'
    proposal_date = lead.get('proposal_date') or datetime.now(timezone.utc).date().isoformat()
    content = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SDC Proposal — {safe(lead.get('company'))}</title>
<style>
:root{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1c3024;background:#f1f5f1}}
*{{box-sizing:border-box}}body{{margin:0;padding:34px 18px}}.sheet{{max-width:850px;margin:auto;background:white;border-radius:22px;padding:58px;box-shadow:0 16px 55px #18352114}}
header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;border-bottom:2px solid #e3ebe3;padding-bottom:28px}}.brand{{font-size:18px;font-weight:800;letter-spacing:-.03em}}.brand small{{display:block;color:#66806c;font-size:11px;font-weight:600;letter-spacing:.13em;margin-top:5px}}.date{{font-size:13px;color:#58705e;text-align:right}}
h1{{font-size:42px;letter-spacing:-.055em;line-height:1.1;margin:40px 0 12px}}.subtitle{{color:#627768;font-size:16px;line-height:1.5}}.eyebrow{{font-size:11px;text-transform:uppercase;letter-spacing:.13em;color:#477455;font-weight:800;margin-bottom:10px}}.section{{margin-top:40px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.tile{{background:#f5f8f5;border:1px solid #e5ece5;border-radius:14px;padding:20px}}.tile strong{{display:block;font-size:17px;margin-top:6px}}.tile span{{color:#637568;font-size:12px}}h2{{font-size:19px;letter-spacing:-.035em}}p{{line-height:1.65}}.price{{font-size:30px;font-weight:800;letter-spacing:-.05em;color:#245137}}.terms{{white-space:normal;overflow-wrap:anywhere}}.footer{{margin-top:50px;padding-top:22px;border-top:1px solid #e1e9e2;color:#738277;font-size:12px}}.toolbar{{max-width:850px;margin:0 auto 20px;display:flex;justify-content:space-between;align-items:center;gap:16px}}button{{background:#245137;border:0;color:white;padding:12px 20px;border-radius:10px;font-weight:700;cursor:pointer}}.hint{{font-size:13px;color:#536a59}}
@media(max-width:600px){{.sheet{{padding:27px 22px}}h1{{font-size:32px}}.grid{{grid-template-columns:1fr}}.toolbar{{flex-direction:column;align-items:flex-start}}}}
@media print{{@page{{size:letter;margin:16mm}}body{{background:white;padding:0}}.toolbar{{display:none}}.sheet{{padding:0;box-shadow:none;border-radius:0;max-width:none}}.tile{{break-inside:avoid}}}}
</style></head><body><div class="toolbar"><span class="hint">Internal preview · Print or save as PDF · Not automatically sent</span><button type="button" onclick="window.print()">Print / Save PDF</button></div><main class="sheet"><header><div class="brand">SADDLEBACK DESIGN CO.<small>SOFTWARE SOLUTIONS</small></div><div class="date">Proposal date<br><strong>{safe(proposal_date)}</strong><br>Reference {safe(lead_id[:8].upper())}</div></header><h1>Software proposal</h1><p class="subtitle">A tailored operations platform designed to simplify how your team works.</p><section class="section"><div class="eyebrow">Prepared for</div><h2>{safe(lead.get('company'))}</h2><p>{safe(lead.get('contact'))}<br>{safe(lead.get('email'))}<br>{safe(lead.get('phone'))}</p></section><section class="section grid"><div class="tile"><span>Recommended package</span><strong>{safe(package)}</strong><p>{safe(description)}</p></div><div class="tile"><span>Proposed investment (USD)</span><div class="price">{safe(formatted_amount)}</div><p>Billing frequency and any applicable taxes must be specified in the final agreement.</p></div></section><section class="section"><div class="eyebrow">Scope and commercial terms</div><div class="terms">{multiline(terms)}</div></section><section class="section"><div class="eyebrow">Next steps</div><p>Review the proposed scope, confirm implementation requirements and payment terms, and execute a separate written agreement before work begins.</p></section><div class="footer">Saddleback Design Co. · Proposal for discussion only; not an invoice, contract, or payment request.</div></main></body></html>"""
    return HTMLResponse(content, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'X-Robots-Tag': 'noindex, nofollow'})


@router.post('/api/software/inquiries/{lead_id}/convert-customer')
def convert_software_inquiry_to_customer(lead_id: str, request: Request):
    """Create or retrieve one SDC customer linked to a software inquiry.

    Explicit admin action only. Never delete the original inquiry, and never
    merge a lead with an unrelated customer based on company name alone.
    """
    from app.routers import workspaces as ws
    ws.guard(request, 'sdc', 'software_leads')
    ws.guard(request, 'sdc', 'customers')
    if len(lead_id) != 32 or any(ch not in '0123456789abcdef' for ch in lead_id):
        raise HTTPException(400, 'Invalid lead identifier')
    # Share the workspace lock with the existing customer create/update APIs.
    with ws._lock:
        leads_path = ws.location(request, 'sdc', 'software_leads')
        customers_path = ws.location(request, 'sdc', 'customers')
        leads = ws.load(leads_path)
        lead = next((r for r in leads if isinstance(r, dict) and r.get('id') == lead_id), None)
        if lead is None:
            raise HTTPException(404, 'Software inquiry not found')
        customers = ws.load(customers_path)
        existing = next((r for r in customers if isinstance(r, dict)
                         and r.get('source_software_inquiry_id') == lead_id), None)
        if existing:
            return {'ok': True, 'already_exists': True, 'customer': existing}
        company = str(lead.get('company') or '').strip()
        contact = str(lead.get('contact') or '').strip()
        if not company or not contact:
            raise HTTPException(409, 'Inquiry needs a business name and contact')
        customer = {
            'id': uuid.uuid4().hex,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'name': company, 'company': company, 'contact': contact,
            'email': str(lead.get('email') or '').strip(),
            'phone': str(lead.get('phone') or '').strip(),
            'source': 'sdc_software_storefront',
            'source_software_inquiry_id': lead_id,
            'software_package_interest': str(lead.get('package') or ''),
        }
        customers.append(customer)
        ws.save(customers_path, customers)
        # Do not mutate the lead: conversion is traceable via customer linkage.
        return {'ok': True, 'already_exists': False, 'customer': customer}
