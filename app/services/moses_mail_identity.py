"""Platform-scoped outgoing mail identity policy.

Company sender is ALWAYS explicit and must match authenticated SMTP sender.
PDS reply routing defaults reflect approved company mailboxes; these are reply
addresses, not assertions that mailboxes exist or that SMTP is configured.
No mail is sent from this module.
"""
from __future__ import annotations
import os
from app.services.moses_delivery import _email

PDS_DEFAULTS = {
    'estimate': 'Estimates@prioritydoors.com',
    'invoice': 'Invoice@prioritydoors.com',
    'purchase_order': 'reception@prioritydoors.com',
    'dispatch': 'reception@prioritydoors.com',
}

def identity(platform: str, kind: str) -> dict:
    if platform not in ('pds', 'doorks', 'sdc'):
        raise ValueError('Unsupported workspace')
    if kind not in ('estimate', 'invoice', 'purchase_order', 'dispatch'):
        raise ValueError('Unsupported email category')
    # PDS uses an independent verified sender; Atlas/SDC retain their own sender.
    # One Resend sender identity across PDS, Doorks and Atlas/SDC.
    # Reply-To remains department- and workspace-specific.
    sender = _email(os.getenv('MOSES_DOCUMENTS_FROM'))
    if platform == 'pds':
        key = {
            'estimate': 'MOSES_PDS_ESTIMATES_REPLY_TO',
            'invoice': 'MOSES_PDS_INVOICES_REPLY_TO',
            'purchase_order': 'MOSES_PDS_PURCHASING_REPLY_TO',
            'dispatch': 'MOSES_PDS_DISPATCH_REPLY_TO',
        }[kind]
        # Explicitly configured overrides must validate; no silent fallback for bad input.
        value = os.getenv(key, '').strip() or PDS_DEFAULTS[kind]
        reply = _email(value)
        general = _email(os.getenv('MOSES_PDS_GENERAL_EMAIL', '').strip() or 'reception@prioritydoors.com')
        cc_key = {
            'estimate': 'MOSES_PDS_ESTIMATES_CC', 'invoice': 'MOSES_PDS_INVOICES_CC',
            'purchase_order': 'MOSES_PDS_PURCHASING_CC', 'dispatch': 'MOSES_PDS_DISPATCH_CC',
        }[kind]
    else:
        key = {
            'estimate': 'MOSES_ESTIMATES_REPLY_TO', 'invoice': 'MOSES_INVOICES_REPLY_TO',
            'purchase_order': 'MOSES_PURCHASING_REPLY_TO', 'dispatch': 'MOSES_DISPATCH_REPLY_TO',
        }[kind]
        reply = _email(os.getenv(key))
        general = ''
        cc_key = {
            'estimate': 'MOSES_ESTIMATES_CC', 'invoice': 'MOSES_INVOICES_CC',
            'purchase_order': 'MOSES_PURCHASING_CC', 'dispatch': 'MOSES_DISPATCH_CC',
        }[kind]
    raw_cc = os.getenv(cc_key, '').strip()
    cc = _email(raw_cc) if raw_cc else ''
    issues = []
    if not sender: issues.append('Company sender address not configured')
    if not reply: issues.append('Department Reply-To address invalid or missing')
    if platform == 'pds' and not general: issues.append('PDS general inquiries email invalid')
    if raw_cc and not cc: issues.append('CC address invalid')
    return {'from': sender, 'reply_to': reply, 'cc': cc,
            'general_inquiries_email': general, 'issues': issues}


def general_inquiry_footer(platform: str, identity_info: dict) -> str:
    if platform != 'pds' or not identity_info.get('general_inquiries_email'):
        return ''
    return '\n\nFor general inquiries, contact ' + identity_info['general_inquiries_email'] + '.'
