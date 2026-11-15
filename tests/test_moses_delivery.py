"""No external email or payment gateway calls in delivery preview tests."""
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.services.moses_delivery import preview


def req(tmp_path, platform='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user='admin', auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path, platform='doorks', collection='estimates_invoices', **fields):
    dest = tmp_path / 'business_workspaces' / platform
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (collection+'.json')).write_text(json.dumps([{'id': 'record1', **fields}]))


def test_estimate_preview_without_sending(tmp_path, monkeypatch):
    seed(tmp_path, document_type='estimate', document_number='RE00076', contact_email='client@example.com')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'documents@example.com')
    monkeypatch.setenv('MOSES_ESTIMATES_REPLY_TO', 'estimates@example.com')
    monkeypatch.setenv('MOSES_ESTIMATES_CC', 'estimates@example.com')
    result = preview(req(tmp_path), 'doorks', 'estimate', 'record1')
    assert result['to']=='client@example.com'
    assert result['cc']=='estimates@example.com'
    assert result['reply_to']=='estimates@example.com'
    assert result['document_number']=='RE00076'
    assert result['ready_to_send'] is False and result['sent'] is False
    assert result['payment_created'] is False


def test_workspace_isolation(tmp_path):
    seed(tmp_path, document_type='estimate', document_number='RE00076')
    with pytest.raises(HTTPException) as exc:
        preview(req(tmp_path, 'sdc'), 'sdc', 'estimate', 'record1')
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        preview(req(tmp_path, 'doorks'), 'sdc', 'estimate', 'record1')
    assert exc.value.status_code == 403


def test_pds_purchase_order_and_no_fake_recipient(tmp_path):
    folder = tmp_path / 'pds_purchase_orders'
    folder.mkdir()
    (folder/'records.json').write_text(json.dumps([{'id':'record1','po_number':'PO-100','vendor':'Vendor'}]))
    result = preview(req(tmp_path, 'pds'), 'pds', 'purchase_order', 'record1')
    assert not result['to'] and not result['ready_to_send']
    assert any('recipient' in issue for issue in result['issues'])


def test_pds_invoice_not_wrongly_connected(tmp_path):
    with pytest.raises(HTTPException) as exc:
        preview(req(tmp_path,'pds'), 'pds', 'invoice', 'record1')
    assert exc.value.status_code == 409


def test_non_admin_cannot_preview(tmp_path):
    with pytest.raises(HTTPException) as exc:
        preview(req(tmp_path,role='office'), 'doorks','estimate','record1')
    assert exc.value.status_code == 403


def test_invoice_no_fake_stripe_url(tmp_path):
    seed(tmp_path,document_type='invoice',document_number='JS00021',customer_email='customer@example.com')
    result=preview(req(tmp_path),'doorks','invoice','record1')
    assert not result['payment_created']
    assert any('Stripe' in issue for issue in result['issues'])
    assert 'http' not in result['text']
