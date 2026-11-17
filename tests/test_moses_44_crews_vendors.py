"""Regression checks for Moses 4.4 staff crews and PDS vendor isolation."""
from pathlib import Path
import importlib.util
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]

def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_multi_technician_schedule_uses_existing_employee_id_list(monkeypatch):
    mod = _load('app/routers/pds_scheduling.py', 'moses44_scheduling')
    class Store:
        def __init__(self):
            self.job={'id':'job123', 'date':'2026-11-17','status':'Dispatch'}
        def get_job(self, id):return dict(self.job)
        def update_job(self,id,update):self.job.update(update);return dict(self.job)
    store=Store()
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(calendar_store=store)))
    monkeypatch.setattr(mod,'_dispatcher',lambda _request:None)
    monkeypatch.setattr(mod,'_person',lambda _request,id: {'id':id} if id in ('tech1','tech2') else (_ for _ in ()).throw(HTTPException(404,'Unknown technician')))
    result=mod.visit_plan('job123',mod.VisitPlan(employee_ids=['tech1','tech2'],scheduled_date='2026-11-20',scheduled_time='09:00'),request)
    assert result['planned_employee_ids']==['tech1','tech2']
    assert store.job['date']=='2026-11-17' and store.job['status']=='Dispatch'
    result=mod.visit_plan('job123',mod.VisitPlan(employee_ids=['tech1','tech2'],scheduled_date='2026-11-20',scheduled_time='09:00',update_to_schedule=True),request)
    assert result['assignment_confirmed'] is True
    assert store.job['assigned_employee_ids']==['tech1','tech2']
    assert store.job['date']=='2026-11-20' and store.job['status']=='Scheduled'
    with pytest.raises(HTTPException) as exc:
        mod.visit_plan('job123',mod.VisitPlan(employee_ids=['tech1','tech1'],scheduled_date='2026-11-20',scheduled_time='09:00',update_to_schedule=True),request)
    assert exc.value.status_code==422
    assert store.job['assigned_employee_ids']==['tech1','tech2']


def test_service_vendor_directory_is_separate_from_supplier_records(tmp_path):
    mod = _load('app/routers/pds_purchase_orders.py', 'moses44_pds_po')
    state=SimpleNamespace(data_dir=tmp_path)
    request=SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(auth_user={'id':'tester'},auth_role='office'), session={'active_platform':'pds'})
    created=mod.add_service_vendor(mod.POInput(data={'name':'Example Door Service','trade':'Automatic door repair','license_number':'TEST'}), request)['item']
    assert created['name']=='Example Door Service' and created['active']
    assert mod.service_vendors(request)['items'][0]['id']==created['id']
    assert mod.list_suppliers(request)['items']==[]
    updated=mod.edit_service_vendor(created['id'],mod.POInput(data={'name':'Example Door Service','trade':'Door maintenance'}),request)['item']
    assert updated['trade']=='Door maintenance'
    assert not mod.status_service_vendor(created['id'],{'active':False},request)['item']['active']
    assert len(mod.service_vendors(request)['items'])==1
    with pytest.raises(HTTPException) as exc:mod.add_service_vendor(mod.POInput(data={'name':'Example Door Service'}),request)
    assert exc.value.status_code==409


def test_moses_launcher_draft_drawer_and_vendor_ui():
    app=(ROOT/'static/app.js').read_text()
    drafts=(ROOT/'static/moses_drafts.js').read_text()
    assert "batchBtn.textContent='✦ Moses'" in app
    assert "document.getElementById('workspaceMosesBubble')" in app
    assert "async function openPdsJobFlowWorkQueue()" in app
    assert "const selectedIds=()=>[...employeeRows.querySelectorAll('select')]" in app
    assert "renderPdsServiceVendors()" in app
    assert "document.dispatchEvent(new CustomEvent('moses-open-pds-job'" in drafts
    assert "topDrawer.style.zIndex='11250'" in app
    store=(ROOT/'app/services/calendar_store.py').read_text()
    assert '"planned_employee_ids"' in store
    assert '("assigned_employee_ids", "assigned_technician_ids", "planned_employee_ids")' in store
