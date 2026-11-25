"""Offline QBO line-approval controls (no Intuit or business-data writes)."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.services import pds_qbo_line_mappings as lines


def req(tmp_path, role='office_admin', platform='pds'):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))),
        session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id': 'office-1'}, auth_role=role))


def doc(kind='invoice', fingerprint='a'*64):
    record = {
        'kind': kind, 'pds_number': 'JS00031' if kind == 'invoice' else 'PO-00031',
        'source_fingerprint': fingerprint,
        'lines': [dict(position=1, description='Field labor', quantity='2', amount='350.00',
                       **({'unit_price': '175.00', 'taxable_in_pds': False} if kind == 'invoice' else {'unit_cost': '175.00'})),
                  dict(position=2, description='Weather seal', quantity='1', amount='45.00',
                       **({'unit_price': '45.00', 'taxable_in_pds': True} if kind == 'invoice' else {'unit_cost': '45.00'}))]}
    return record


class Response:
    def __init__(self, provider):
        self.body = json.dumps({'QueryResponse': {'Item': [provider]}}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _):
        return self.body


def provider(kind='invoice', **changes):
    row = {'Id': '1001', 'Active': True, 'Name': 'Labor service',
           'Type': 'Service', 'IncomeAccountRef': {'value':'101'},
           'ExpenseAccountRef': {'value':'201'}}
    row.update(changes)
    return row


def configured(monkeypatch, current, kind='invoice', account='200', env='sandbox', item=None):
    from app.services import pds_qbo_master_links as master
    monkeypatch.setattr(lines, '_document', lambda request, the_kind, number: current)
    monkeypatch.setattr(master, '_company', lambda request: (account, env, 'fake-token'))
    calls = []
    def fake_open(request, timeout=12):
        calls.append(request)
        return Response(item if item is not None else provider(kind))
    monkeypatch.setattr(lines, 'urlopen', fake_open)
    return calls


def test_read_only_review_does_not_create_files(tmp_path, monkeypatch):
    current=doc();configured(monkeypatch,current)
    result=lines.status(req(tmp_path),'invoice','JS00031')
    assert (result['total_lines'],result['mapped_lines'])==(2,0)
    assert result['can_post'] is False and result['automatic_sync_enabled'] is False
    assert not list(tmp_path.iterdir())


def test_unauthorized_role_and_platform_blocked_before_provider(tmp_path,monkeypatch):
    current=doc();calls=configured(monkeypatch,current)
    for r in (req(tmp_path,'lead'),req(tmp_path,'tech'),req(tmp_path,'office'),req(tmp_path,'office_admin','doorks')):
        with pytest.raises(HTTPException) as denied:
            lines.approve(r,'invoice','JS00031',1,'1001',confirm=True)
        assert denied.value.status_code==403
        with pytest.raises(HTTPException):
            lines.status(r,'invoice','JS00031')
    assert not calls and not list(tmp_path.iterdir())


@pytest.mark.parametrize('id_',('abc','1 OR 1=1','-1','١٢٣','', '1'*33))
def test_bad_qbo_id_rejected_without_network(tmp_path,monkeypatch,id_):
    calls=configured(monkeypatch,doc())
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',1,id_,confirm=True)
    assert error.value.status_code==422
    assert not calls


def test_confirmation_required_before_lookup(tmp_path, monkeypatch):
    calls=configured(monkeypatch,doc())
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=False)
    assert error.value.status_code==422 and not calls


@pytest.mark.parametrize('bad',[
    {'Active':False}, {'Type':'Group'}, {'IncomeAccountRef':{}},
    {'IncomeAccountRef':None}, {'Id':'wrong'}, {'Name':''},
])
def test_provider_item_must_be_active_supported_and_accounted(tmp_path,monkeypatch,bad):
    configured(monkeypatch,doc(),item=provider(**bad))
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=True)
    assert error.value.status_code==409
    assert not (tmp_path/'pds_qbo_line_approvals.json').exists()


def test_invoice_lines_are_saved_only_as_local_reviews(tmp_path,monkeypatch):
    current=doc();calls=configured(monkeypatch,current)
    result=lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=True)
    assert result['status']=='reviewed' and result['can_post'] is False
    assert len(calls)==1 and calls[0].get_method()=='GET'
    assert '/v3/company/200/query?' in calls[0].full_url
    assert 'SELECT+%2A+FROM+Item' in calls[0].full_url
    review=lines.status(req(tmp_path),'invoice','JS00031')
    assert review['mapped_lines']==1 and review['lines'][0]['account_ref']=='101'
    assert review['lines'][1]['provider_id'] is None
    assert review['all_lines_reviewed'] is False
    assert {x.name for x in tmp_path.iterdir() if x.is_file()} == {'pds_qbo_line_approvals.json.lock','pds_qbo_line_approvals.json'}
    saved=json.loads((tmp_path/'pds_qbo_line_approvals.json').read_text())['items']['invoice:JS00031']
    assert saved['fingerprint']=='a'*64 and saved['company_id']=='200'
    assert 'token' not in str(saved).lower()
    again=lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=True)
    assert again['status']=='already_reviewed'
    configured(monkeypatch,current,item=provider(Id='1002'))
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',1,'1002',confirm=True)
    assert error.value.status_code==409 # verified but different ID must not replace approved line


def test_po_checks_expense_account_not_income(tmp_path,monkeypatch):
    current=doc('supplier_po')
    configured(monkeypatch,current,item=provider('supplier_po', IncomeAccountRef=None))
    saved=lines.approve(req(tmp_path),'supplier_po','PO-00031',1,'1001',confirm=True)
    assert saved['mapped_item']['account_ref']=='201'
    assert saved['mapped_item']['account_role']=='expense'
    assert lines.status(req(tmp_path),'supplier_po','PO-00031')['mapped_lines']==1


def test_po_without_expense_account_rejected(tmp_path,monkeypatch):
    configured(monkeypatch,doc('supplier_po'),item=provider('supplier_po',ExpenseAccountRef=None))
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'supplier_po','PO-00031',1,'1001',confirm=True)
    assert error.value.status_code==409


def test_stale_fingerprint_or_company_does_not_reuse_ids(tmp_path,monkeypatch):
    current=doc();configured(monkeypatch,current)
    lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=True)
    modified=doc(fingerprint='b'*64)
    configured(monkeypatch,modified)
    status=lines.status(req(tmp_path),'invoice','JS00031')
    assert status['mapped_lines']==0 and status['lines'][0]['provider_id'] is None
    assert status['lines'][0]['status']=='stale'
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',2,'1001',confirm=True)
    assert error.value.status_code==409
    configured(monkeypatch,current,account='201')
    assert lines.status(req(tmp_path),'invoice','JS00031')['mapped_lines']==0


def test_source_changes_during_verification_block_save(tmp_path,monkeypatch):
    current=doc();different=doc(fingerprint='f'*64)
    counter=[0]
    def changed(*args):
        counter[0]+=1
        return current if counter[0]==1 else different
    from app.services import pds_qbo_master_links as master
    monkeypatch.setattr(lines,'_document',changed)
    monkeypatch.setattr(master,'_company',lambda request: ('200','sandbox','fake-token'))
    monkeypatch.setattr(lines,'urlopen',lambda *args,**kwargs: Response(provider()))
    with pytest.raises(HTTPException) as error:
        lines.approve(req(tmp_path),'invoice','JS00031',1,'1001',confirm=True)
    assert error.value.status_code==409
    assert not (tmp_path/'pds_qbo_line_approvals.json').exists()


def test_stale_line_signature_and_invalid_saved_mapping_not_trusted():
    current=doc()
    saved={'kind':'invoice','number':'JS00031','fingerprint':current['source_fingerprint'],
           'company_id':'200','environment':'sandbox','lines':{'1':{
               'source_line':{'position':1,'description':'CHANGED'},'provider_id':'1001',
               'item_type':'Service','account_ref':'101'}}}
    summary=lines.line_summary(current,saved,company='200',environment='sandbox')
    assert summary['mapped_lines']==0 and summary['lines'][0]['provider_id'] is None


def test_status_rejects_non_prepared_documents(tmp_path,monkeypatch):
    from app.services import pds_qbo_master_links as master
    with patch.object(lines.preview,'preview_invoice',side_effect=HTTPException(409,'Not prepared')):
        with pytest.raises(HTTPException) as error:
            lines.status(req(tmp_path),'invoice','JS00031')
    assert error.value.status_code==409


def test_line_position_bounds(tmp_path,monkeypatch):
    configured(monkeypatch,doc())
    for position in (0,3,101):
        with pytest.raises(HTTPException) as error:
            lines.approve(req(tmp_path),'invoice','JS00031',position,'1001',confirm=True)
        assert error.value.status_code==422


def test_readiness_includes_line_approval_coverage(tmp_path,monkeypatch):
    from app.services import pds_qbo_sync_readiness as ready
    from app.services import pds_qbo_master_links as master
    current=doc()
    configured(monkeypatch,current)
    monkeypatch.setattr(ready.preview,'preview_invoice',lambda request,number:current)
    monkeypatch.setattr(master,'_sources',lambda request,kind:[{'pds_id':'customer-1','name':'Customer','active':True}])
    current['pds_customer']='Customer'
    r=req(tmp_path)
    before=ready.readiness(r,'invoice','JS00031')
    assert before['item_mapping']=={'reviewed':0,'total':2,'all_lines_reviewed':False}
    assert before['can_post'] is False
    lines.approve(r,'invoice','JS00031',1,'1001',confirm=True)
    after=ready.readiness(r,'invoice','JS00031')
    assert after['item_mapping']['reviewed']==1
    assert 'Individual income/expense item mappings' in after['unresolved']
    lines.approve(r,'invoice','JS00031',2,'1001',confirm=True)
    done=ready.readiness(r,'invoice','JS00031')
    assert done['item_mapping']['all_lines_reviewed'] is True
    assert done['can_post'] is False and done['automatic_sync_enabled'] is False
    assert 'Tax treatment' in done['unresolved']


def test_po_readiness_still_never_posts_when_items_approved(tmp_path,monkeypatch):
    current=doc('supplier_po')
    configured(monkeypatch,current)
    from app.services import pds_qbo_sync_readiness as ready
    from app.services import pds_qbo_master_links as master
    from app.services import pds_quickbooks_purchase_orders as po
    monkeypatch.setattr(ready.preview,'preview_supplier_po',lambda request,number:current)
    monkeypatch.setattr(master,'_sources',lambda request,kind:[])
    current['pds_supplier']='Vendor'
    monkeypatch.setattr(po,'_rows',lambda request:{'PO-00031':{'number':'PO-00031','supplier_id':'supplier-1'}})
    r=req(tmp_path)
    lines.approve(r,'supplier_po','PO-00031',1,'1001',confirm=True)
    report=ready.readiness(r,'supplier_po','PO-00031')
    assert report['item_mapping']['reviewed']==1
    assert report['source_supplier_id']=='supplier-1'
    assert report['can_post'] is False
