from pathlib import Path
import ast
import os
import re

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')
DRAFT=(ROOT/'static/moses_drafts.js').read_text(encoding='utf-8')
OPERATIONS=(ROOT/'static/moses_part_dispatch.js').read_text(encoding='utf-8')
API=(ROOT/'app/routers/moses_drafts.py').read_text(encoding='utf-8')
UI=(ROOT/'templates/ui.html').read_text(encoding='utf-8')
DELIVERY=(ROOT/'app/services/moses_delivery.py').read_text(encoding='utf-8')


def test_source_python_parses():ast.parse(API)
def test_dispatch_button_on_real_moses_job_cards():
    assert 'moses-open-dispatch-email' in APP
    assert 'Customer ETA / Update' in APP
    assert 'row.id' in APP

def test_dispatch_only_uses_existing_endpoints():
    assert '/dispatch/' in OPERATIONS
    assert '/eta/preview' in OPERATIONS
    assert '/eta/send-proposal' in OPERATIONS
    assert "'/decision'" in OPERATIONS
    assert '/eta/delivery-history' in OPERATIONS

def test_dispatch_requires_two_confirmations():
    assert 'Request send approval' in OPERATIONS
    assert 'FINAL EMAIL APPROVAL' in OPERATIONS
    assert 'window.confirm' in OPERATIONS
    assert "mode:mode.value" in OPERATIONS
    assert "eta_time:eta.value" in OPERATIONS

def test_no_auto_retry_or_fake_delivery():
    assert 'Do not retry' in OPERATIONS
    assert 'Final delivery must be checked separately' in OPERATIONS
    assert 'No safe retry' in OPERATIONS

def test_new_part_visible_in_moses_draft():
    assert 'Research / Add a new PDS part' in DRAFT
    assert 'moses-open-part-intake' in DRAFT
    assert 'item.parts_required' in DRAFT

def test_research_does_not_auto_populate_prices():
    assert 'https://www.google.com/search?q=' in OPERATIONS
    assert 'opens search' in OPERATIONS
    assert 'verified catalog price' in OPERATIONS.lower()
    assert 'confirm_create:true' in OPERATIONS

def test_missing_price_holds_instead_of_creating():
    assert "if(price.value==='')" in OPERATIONS
    assert 'part was NOT added' in OPERATIONS

def test_backend_explicit_confirmation_price_and_duplicates():
    assert 'payload.confirm_create is not True' in API
    assert 'decimal.Decimal(payload.price.strip())' in API
    assert 'not price.is_finite()' in API
    assert 'already in the catalog' in API
    assert 'number.casefold()' in API
    assert 'with _lock(path):' in API

def test_no_automatic_estimate_or_mail_sent_from_part_intake():
    assert "'email_sent': False" in API
    assert "'estimate_created': False" in API
    assert "'ordered': False" in API

def test_workspace_isolated():
    assert 'def moses_create_catalog_part(' in API
    assert '    _guard(request)' in API
    assert "document.body.dataset.platform!=='pds'" in OPERATIONS

def test_ui_script_installed():
    assert '/static/moses_part_dispatch.js?v=1' in UI


def _intake(tmp_path, monkeypatch):
    import importlib.util
    import json
    import sys
    from types import SimpleNamespace
    from fastapi import HTTPException
    file=ROOT/'app/routers/moses_drafts.py'
    spec=importlib.util.spec_from_file_location('moses_drafts_intake_test',file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    part_path=tmp_path/'parts_catalog.json'
    module_data=SimpleNamespace(_parts_path=lambda request:part_path,
                               _part_https_url=lambda value:value)
    monkeypatch.setitem(sys.modules,'app.routers.data',module_data)
    req=SimpleNamespace(state=SimpleNamespace(auth_user={'id':'office'},auth_role='office_admin'),
                        session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(calendar_store=object())))
    return module,req,part_path


def test_real_backend_creates_and_blocks_duplicate(tmp_path,monkeypatch):
    import json
    from fastapi import HTTPException
    m,req,path=_intake(tmp_path,monkeypatch)
    data=m.MosesNewPart(part_number=' AA-42 ',description='Replacement hinge',price='47.50',confirm_create=True)
    r=m.moses_create_catalog_part(data,req)
    assert r['ok'] and r['ordered'] is False and r['email_sent'] is False
    rows=json.loads(path.read_text())['items']
    assert len(rows)==1 and rows[0]['part_number']=='AA-42' and rows[0]['price']=='47.50'
    try:
        m.moses_create_catalog_part(m.MosesNewPart(part_number='aa-42',description='Duplicate',price='5.00',confirm_create=True),req)
        assert False, 'duplicate must fail'
    except HTTPException as e:
        assert e.status_code==409
    assert len(json.loads(path.read_text())['items'])==1


def test_real_backend_confirmation_role_and_price_fail_closed(tmp_path,monkeypatch):
    from fastapi import HTTPException
    m,req,path=_intake(tmp_path,monkeypatch)
    base=dict(part_number='P-100',description='Motor',price='39.00')
    for kwargs,code in [({'confirm_create':False},422),({'price':'NaN','confirm_create':True},422),
                         ({'price':'-1','confirm_create':True},422),({'price':'40.123','confirm_create':True},422)]:
        try:m.moses_create_catalog_part(m.MosesNewPart(**{**base,**kwargs}),req);assert False
        except HTTPException as e:assert e.status_code==code
    req.state.auth_role='technician'
    try:m.moses_create_catalog_part(m.MosesNewPart(**base,confirm_create=True),req);assert False
    except HTTPException as e:assert e.status_code==403
    assert not path.exists()


def test_corrupt_parts_catalog_never_overwritten(tmp_path,monkeypatch):
    from fastapi import HTTPException
    m,req,path=_intake(tmp_path,monkeypatch)
    path.write_text('not-json')
    try:m.moses_create_catalog_part(m.MosesNewPart(part_number='P1',description='Test',price='4',confirm_create=True),req);assert False
    except HTTPException as e:assert e.status_code==503
    assert path.read_text()=='not-json'


def test_dispatch_email_template_describes_actual_office_approved_status():
    assert "Our technician is on the way." in DELIVERY
    assert "Our estimated arrival time is " in DELIVERY
    assert "Our technician is preparing to head your way." not in DELIVERY
