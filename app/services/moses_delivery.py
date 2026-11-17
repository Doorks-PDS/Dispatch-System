"""Read-only, platform-scoped outgoing document email previews.

No external transport, Stripe session creation, or record mutation occurs here.
Actual sending must be a separately approved and audited operation.
"""
from __future__ import annotations

import os
from email.utils import parseaddr
from fastapi import HTTPException


def _email(value):
    address = parseaddr(str(value or '').strip())[1]
    if not address or '@' not in address or any(c.isspace() for c in address):
        return ''
    local, domain = address.rsplit('@', 1)
    return address if local and '.' in domain and not address.endswith('.') else ''


def _email_from_record(record, kind):
    keys = ('vendor_email', 'supplier_email', 'email', 'contact_email') if kind == 'purchase_order' else (
        'customer_email', 'contact_email', 'email')
    for key in keys:
        value = _email(record.get(key))
        if value:
            return value
    return ''


def _invoice_recipient(request, platform, item):
    """Use the linked customer AP mailbox; otherwise the invoice's job contact.

    Customer profiles are looked up ONLY in the authenticated active workspace.
    Ambiguous company names fail closed rather than selecting another company.
    """
    if platform not in ('doorks', 'sdc'):
        return _email_from_record(item, 'invoice'), 'document_contact'
    from app.routers.workspaces import guard, location, load
    guard(request, platform, 'customers')
    customer_id = str(item.get('customer_id') or '').strip()
    customer_name = str(item.get('customer') or item.get('customer_name') or '').strip().casefold()
    profiles = load(location(request, platform, 'customers'))
    if customer_id:
        matches = [p for p in profiles if str(p.get('id')) == customer_id]
    elif customer_name:
        matches = [p for p in profiles if str(p.get('name') or '').strip().casefold() == customer_name]
    else:
        matches = []
    if len(matches) == 1:
        raw = str(matches[0].get('invoice_email') or '').strip()
        if raw:
            email = _email(raw)
            if not email:
                raise HTTPException(409, 'Customer invoice email is invalid; correct it before sending')
            return email, 'customer_ap'
    elif len(matches) > 1:
        # Multiple customer rows can represent contacts; only pick a common AP address.
        ap_values = {str(p.get('invoice_email') or '').strip().casefold()
                     for p in matches if str(p.get('invoice_email') or '').strip()}
        if len(ap_values) == 1:
            email = _email(next(iter(ap_values)))
            if not email:
                raise HTTPException(409, 'Customer invoice email is invalid; correct it before sending')
            return email, 'customer_ap'
        if len(ap_values) > 1:
            raise HTTPException(409, 'Customer has conflicting invoice email addresses; review recipient')
    # The document's contact is intentionally preferred to a generic profile email.
    for key in ('contact_email', 'customer_email', 'email'):
        email = _email(item.get(key))
        if email:
            return email, 'job_contact'
    return '', 'missing'


def _find_record(request, platform, kind, record_id):
    if platform in ('doorks', 'sdc'):
        from app.routers.workspaces import guard, location, load
        collection = 'purchase_orders' if kind == 'purchase_order' else 'estimates_invoices'
        guard(request, platform, collection)
        records = load(location(request, platform, collection))
        matches = [r for r in records if str(r.get('id')) == record_id and
                   (kind == 'purchase_order' or str(r.get('document_type', '')).lower() == kind)]
    elif platform == 'pds' and kind == 'purchase_order':
        from app.routers.pds_purchase_orders import _guard, _paths, _read
        _guard(request)
        records_path, _ = _paths(request)
        matches = [r for r in _read(records_path, []) if str(r.get('id')) == record_id]
    else:
        raise HTTPException(409, 'This platform/document workflow is not connected yet')
    if len(matches) != 1:
        raise HTTPException(404, 'Document was not uniquely found in the active workspace')
    return matches[0]


def preview(request, platform: str, kind: str, record_id: str):
    """Build a truthful read-only email proposal; never fabricate attachments or URLs."""
    if platform not in ('pds', 'doorks', 'sdc') or kind not in ('estimate', 'invoice', 'purchase_order'):
        raise HTTPException(400, 'Invalid platform or document type')
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != platform:
        raise HTTPException(403, 'Switch to the matching workspace')
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office Admin access required for document delivery')
    item = _find_record(request, platform, kind, record_id)
    number = str(item.get('document_number') or item.get('po_number') or '').strip()
    label = {'estimate': 'Estimate', 'invoice': 'Invoice', 'purchase_order': 'Purchase Order'}[kind]
    recipient, recipient_source = (_invoice_recipient(request, platform, item)
                                   if kind == 'invoice' else (_email_from_record(item, kind), 'document_contact'))
    # Sender & reply-to must be configured; never guess an organization's domain.
    from app.services.moses_mail_identity import identity, general_inquiry_footer
    mail = identity(platform, kind)
    sender, reply_to, cc = mail['from'], mail['reply_to'], mail['cc']
    subject = f'{label} {number}' if number else f'{label} (number pending)'
    opening = ({'estimate': 'Please review the attached estimate.',
                'invoice': 'Please review the attached invoice.',
                'purchase_order': 'Please review the attached purchase order.'})[kind]
    # Portal/payment URLs must come from a separately verified, published document.
    # Do not reuse arbitrary URLs from user-editable records as payment links.
    issues = []
    if not number: issues.append('Official document number missing')
    if not recipient: issues.append('Verified recipient email missing; review customer/vendor contact')
    issues.extend(mail['issues'])
    issues.append('Generated PDF attachment and customer/vendor portal link not verified')
    if kind == 'invoice':
        issues.append('Stripe payment link and webhook verification not configured')
    return {
        'platform': platform, 'document_type': kind, 'record_id': record_id,
        'document_number': number, 'from': sender, 'to': recipient, 'recipient_source': recipient_source, 'reply_to': reply_to,
        'cc': cc, 'subject': subject, 'text': opening + '\n\n' +
            'The finalized document and secure link will be included after verification.',
        'ready_to_send': False, 'sent': False, 'payment_created': False,
        'issues': issues,
    }


# Dispatch notifications share the document-delivery sender/reply settings, but
# never mutate a job, queue an email, or infer a travel time.
def preview_dispatch_eta(request, platform: str, record_id: str, mode: str,
                         eta_time: str = '', note: str = ''):
    from datetime import datetime
    if platform not in ('doorks', 'pds'):
        raise HTTPException(400, 'Dispatch email is only available for Doorks and PDS')
    if mode not in ('scheduled', 'en_route', 'delay', 'general'):
        raise HTTPException(400, 'Unknown dispatch update type')
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != platform:
        raise HTTPException(403, 'Switch to the matching workspace')
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office Admin required')
    if not record_id or len(record_id) > 80:
        raise HTTPException(400, 'Invalid work order identifier')
    if platform == 'doorks':
        from app.routers.workspaces import guard, location, load
        guard(request, 'doorks', 'work_orders')
        matches = [r for r in load(location(request, 'doorks', 'work_orders'))
                   if str(r.get('id', '')) == record_id]
    else:
        store = getattr(request.app.state, 'calendar_store', None)
        if store is None:
            raise HTTPException(503, 'PDS dispatch store unavailable')
        job = store.get_job(record_id)
        matches = [job] if job else []
    if len(matches) != 1:
        raise HTTPException(404, 'Work order not uniquely found')
    job = matches[0]
    customer = str(job.get('customer') or '').strip()
    job_number = str(job.get('job_number') or job.get('work_order_number') or '').strip()
    visit_date = str(job.get('scheduled_date') or job.get('date') or '').strip()
    visit_time = str(job.get('scheduled_time') or '').strip()
    recipient = _email(job.get('customer_email') or job.get('email') or job.get('contact_email'))
    from app.services.moses_mail_identity import identity, general_inquiry_footer
    mail = identity(platform, 'dispatch')
    sender, reply_to, cc = mail['from'], mail['reply_to'], mail['cc']
    note = (note or '').strip()
    eta_time = (eta_time or '').strip()
    if len(note) > 1000:
        raise HTTPException(400, 'Update note is too long')
    if eta_time:
        try:
            datetime.strptime(eta_time, '%H:%M')
        except ValueError:
            raise HTTPException(400, 'ETA must be entered as 24-hour HH:MM')
    issues = []
    if not recipient: issues.append('Verified customer email missing')
    issues.extend(mail['issues'])
    if not customer: issues.append('Customer name missing')
    if not job_number: issues.append('Job number missing')
    if mode == 'scheduled' and not visit_date:
        issues.append('No scheduled visit date recorded')
    if mode in ('en_route', 'delay') and not eta_time:
        issues.append('A confirmed ETA time is required; Moses cannot invent travel times')
    if mode == 'general' and not note:
        issues.append('Enter the update message')
    if str(job.get('status') or '').lower() in ('cancelled', 'canceled'):
        issues.append('Job is cancelled; review before contacting customer')
    subjects = {
        'scheduled': 'Scheduled service reminder', 'en_route': 'Technician on the way',
        'delay': 'Updated arrival time', 'general': 'Service update',
    }
    lines = [f'Hello {customer or "customer"},', '',
             f'This is an update regarding service job {job_number or "(number pending)"}.']
    if mode == 'scheduled':
        lines.append('Your service visit is scheduled for '+
                     (visit_date or '(date not confirmed)')+
                     ((' at '+visit_time) if visit_time else '')+'.')
        if eta_time: lines.append('Our estimated arrival time is '+eta_time+'.')
    elif mode == 'en_route':
        lines.append('Our technician is on the way.'+
                     ((' The estimated arrival time is '+eta_time+'.') if eta_time else ''))
    elif mode == 'delay':
        lines.append('Your expected arrival time has changed.'+
                     ((' The updated ETA is '+eta_time+'.') if eta_time else ''))
    if note:
        lines.extend(['', note])
    lines.extend(['', 'Please reply to this email if you have any questions.', 'Thank you.'])
    if platform == 'pds':
        lines.append(general_inquiry_footer(platform, mail).strip())
    # Always preview-only. Outbound transport and send history require a
    # separate approval + idempotent delivery action, not implemented here.
    return {
        'platform': platform, 'record_id': record_id, 'job_number': job_number,
        'customer': customer, 'mode': mode, 'scheduled_date': visit_date,
        'eta_time': eta_time, 'to': recipient, 'from': sender,
        'reply_to': reply_to, 'cc': cc,
        'subject': subjects[mode]+(' — Job '+job_number if job_number else ''),
        'text': '\n'.join(lines), 'ready_to_send': False, 'sent': False,
        'issues': issues + ['Approved outbound email transport not enabled'],
    }
