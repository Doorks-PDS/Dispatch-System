from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import pds_purchase_orders as po


def _request(tmp_path, role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user='admin',auth_role=role),
                           session={'active_platform':'pds'},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path),project_root=str(tmp_path))))


def test_preview_is_read_only_and_commit_skips_existing_vendor(tmp_path):
    req=_request(tmp_path)
    path=po._supplier_path(req)
    old={'id':'old-id','name':'Acme Doors','phone':'555-1111','other_field':'preserve'}
    po._write(path,[old]); original=path.read_bytes()
    batch=po.ImportBatch(kind='vendors',rows=[{'Vendor Name':'Acme Doors','Phone':'changed'},
                                               {'Vendor Name':'New Supplier','Email':'new@example.com'},
                                               {'Vendor Name':'New Supplier'}])
    result=po.preview_import(batch,req)
    assert (result['new_count'],result['duplicate_count'],result['invalid_count'])==(1,2,0)
    assert path.read_bytes()==original
    with pytest.raises(HTTPException):po.commit_import(batch,req)
    batch.confirm_import=True
    done=po.commit_import(batch,req)
    assert done['created']==1 and done['skipped']==2
    items=po._read(path,[])
    assert items[0]==old and len(items)==2
    assert items[1]['name']=='New Supplier'
    assert po.commit_import(batch,req)['created']==0


def test_part_import_preserves_existing_prices_and_requires_valid_rows(tmp_path):
    req=_request(tmp_path)
    from app.routers.data import _parts_path
    path=_parts_path(req)
    original={'items':[{'id':'one','part_number':'311S','price':305,'supplier_rate':200,'extra':'keep'}],
              'metadata':{'v':1}}
    po._write(path,original)
    batch=po.ImportBatch(kind='parts',rows=[{'Item':'311S','Cost':'2'},
                                             {'SKU':'NEW-ABC','Description':'Door hinge','Cost':'$18.50','Preferred Vendor':'Door Supply'}],confirm_import=True)
    preview=po.preview_import(batch,req)
    assert preview['new_count']==1 and preview['duplicate_count']==1
    done=po.commit_import(batch,req)
    assert done['created']==1
    saved=po._read(path,{})
    assert saved['items'][0]==original['items'][0] and saved['metadata']=={'v':1}
    assert saved['items'][1]['supplier_rate']==18.5 and saved['items'][1]['price']==''
    invalid=po.ImportBatch(kind='parts',rows=[{'Item':'X','Cost':'invalid'}],confirm_import=True)
    assert po.preview_import(invalid,req)['invalid_count']==1
    with pytest.raises(HTTPException):po.commit_import(invalid,req)
    assert po._read(path,{})==saved


def test_import_requires_office_admin(tmp_path):
    with pytest.raises(HTTPException) as err:
        po.preview_import(po.ImportBatch(kind='vendors',rows=[{'Name':'Test'}]),_request(tmp_path,'office'))
    assert err.value.status_code==403


def test_pds_ui_has_po_and_safe_import_preview():
    js=(Path(__file__).parents[1]/'static/app.js').read_text()
    assert "poButton.textContent='Purchase Order'" in js
    assert "renderUnifiedPurchaseOrders('pds',true" in js
    assert 'qb_import_kind' in js and '/pds-purchase-orders/import/preview' in js
    assert '/pds-purchase-orders/import/commit' in js
    assert 'My Scheduled Tasks' in js
    assert 'card.append(notes, officeNotes)' in js


def test_live_agent_schema_validation_recovers_as_read_only(monkeypatch):
    from pydantic import BaseModel, ValidationError
    from app.routers import doorks_assistant as assistant
    from app.services import moses_agent
    class BadSchema(BaseModel):
        required: int
    try:
        BadSchema.model_validate({'required':'invalid'})
    except ValidationError as error:
        validation_error=error
    request=SimpleNamespace(state=SimpleNamespace(auth_user='admin',auth_role='office_admin'),
                            session={'active_platform':'pds'},
                            app=SimpleNamespace(state=SimpleNamespace(data_dir='/tmp/none')))
    monkeypatch.setattr(moses_agent,'readiness',lambda *_: {'ready_for_live_check':True})
    monkeypatch.setattr(moses_agent,'answer',lambda *_: (_ for _ in ()).throw(validation_error))
    monkeypatch.setattr(moses_agent,'read_only_recovery',lambda *_: 'This week has three scheduled visits. No records were changed.')
    result=assistant.chat(assistant.Message(message='Review my schedule'),request)
    assert result['agent_mode']=='read_only_recovery'
    assert result['action_proposals']==[]
    assert 'three scheduled visits' in result['answer']
