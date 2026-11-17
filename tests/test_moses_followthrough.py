from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.services import moses_followthrough as desk

class FakeStore:
    def __init__(self, jobs): self.jobs=jobs
    def list_jobs(self): return self.jobs

def req(tmp_path, workspace='pds', role='office_admin', jobs=None):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'},auth_role=role),
        session={'active_platform':workspace},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,
            calendar_store=FakeStore(jobs if jobs is not None else []))))

def write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(rows),encoding='utf-8')

def test_office_admin_only(tmp_path):
    with pytest.raises(HTTPException) as exc: desk.desk(req(tmp_path,role='technician'))
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc: desk.desk(req(tmp_path,workspace='invalid'))
    assert exc.value.status_code==403

def test_pds_queue_uses_saved_statuses_and_filters(tmp_path):
    jobs=[{'id':'a','job_number':'0126-01','customer':'Acme','status':'Quote'},
          {'id':'b','job_number':'0126-02','customer':'Beta','status':'To Be Invoiced'},
          {'id':'c','job_number':'0126-03','status':'Parts on Order'},
          {'id':'d','status':'Complete'}, {'id':'e','status':'Cancelled'}]
    out=desk._pds_work(req(tmp_path,jobs=jobs))
    assert out['count']==3
    assert [r['kind'] for r in out['items']]==['needs_quote','needs_invoice','parts_on_order']
    assert 'email' not in out['items'][0]

def test_missing_calendar_is_unavailable(tmp_path):
    r=req(tmp_path);r.app.state.calendar_store=None
    assert desk._pds_work(r)['available'] is False

def test_invalid_calendar_does_not_fake_zero(tmp_path):
    with pytest.raises(HTTPException) as exc:desk._pds_work(req(tmp_path,jobs=[None]))
    assert exc.value.status_code==503

def test_delivery_requires_signed_event_and_saved_send(tmp_path):
    r=req(tmp_path,workspace='doorks')
    from app.services import moses_resend_events as resend
    write(resend._ledger(r),[{'event_id':'ev1','provider_message_id':'email_A','occurred_at':'2026-11-15T15:00:00+00:00','delivery_status':'bounced'},
                             {'event_id':'ev2','provider_message_id':'email_B','occurred_at':'2026-11-15T16:00:00+00:00','delivery_status':'failed'}])
    write(resend._action_file(r,'doorks','estimate'),[{'record_id':'estimate-a','provider_message_id':'email_A','state':'executed'}])
    out=desk._delivery(r,'doorks')
    assert out['available'] and out['count']==1
    assert out['items'][0]['record_id']=='estimate-a'
    assert 'email_A' not in str(out)

def test_delivery_latest_event_wins(tmp_path):
    r=req(tmp_path,workspace='sdc')
    from app.services import moses_resend_events as resend
    write(resend._ledger(r),[{'event_id':'ev1','provider_message_id':'emailA','occurred_at':'2026-11-15T14:00:00+00:00','delivery_status':'bounced'},
                             {'event_id':'ev2','provider_message_id':'emailA','occurred_at':'2026-11-15T17:00:00+00:00','delivery_status':'delivered_to_recipient_server'}])
    write(resend._action_file(r,'sdc','invoice'),[{'record_id':'invoice1','provider_message_id':'emailA','state':'executed'}])
    assert desk._delivery(r,'sdc')['count']==0

def test_pds_estimate_email_unsupported_in_current_main(tmp_path):
    r=req(tmp_path,workspace='pds')
    from app.services import moses_resend_events as resend
    write(resend._ledger(r),[{'event_id':'x','provider_message_id':'pds_est','occurred_at':'2026-11-15T17:00:00+00:00','delivery_status':'bounced'}])
    write(resend._action_file(r,'pds','estimate'),[{'record_id':'e','provider_message_id':'pds_est','state':'executed'}])
    result=desk._delivery(r,'pds')
    assert result['available'] is False and result['count'] is None

def test_delivery_missing_ledger_not_no_issues(tmp_path):
    out=desk._delivery(req(tmp_path),'pds')
    assert out['available'] is False and out['count'] is None

def test_corrupt_delivery_source_is_error(tmp_path):
    r=req(tmp_path,workspace='doorks')
    from app.services import moses_resend_events as resend
    write(resend._ledger(r),[{'provider_message_id':None,'occurred_at':'a','delivery_status':'failed'}])
    with pytest.raises(HTTPException) as exc:desk._delivery(r,'doorks')
    assert exc.value.status_code==503

def test_approvals_missing_feature_flag_is_unavailable(tmp_path,monkeypatch):
    from app.services import moses_butler_flow
    def disabled(r): raise HTTPException(503,'disabled')
    monkeypatch.setattr(moses_butler_flow,'pending_actions',disabled)
    result=desk._approvals(req(tmp_path))
    assert result['available'] is False and result['count'] is None

def test_combined_is_read_only_and_workspace_scoped(tmp_path,monkeypatch):
    from app.services import moses_butler_flow
    monkeypatch.setattr(moses_butler_flow,'pending_actions',lambda r:{'count':0,'proposals':[]})
    before=list(tmp_path.rglob('*'))
    out=desk.desk(req(tmp_path,workspace='pds'))
    assert out['workspace']=='pds' and out['records_changed'] is False
    assert out['delivery']['count'] is None
    assert list(tmp_path.rglob('*'))==before
