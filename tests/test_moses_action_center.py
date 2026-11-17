from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services import moses_action_center as action


class Request:
    def __init__(self, root, platform='pds', role='office_admin', logged_in=True, jobs=None):
        self.state = SimpleNamespace(auth_user={'id': 'office-1'} if logged_in else None,
                                     auth_role=role)
        self.session = {'active_platform': platform}
        store=SimpleNamespace(list_jobs=lambda: list(jobs or []))
        self.app=SimpleNamespace(state=SimpleNamespace(data_dir=root, calendar_store=store))


@pytest.fixture
def connected(monkeypatch, tmp_path):
    from app.services import moses_followthrough
    monkeypatch.setitem(sys.modules, 'app.services.moses_resend_events', ModuleType('app.services.moses_resend_events'))
    resend=sys.modules['app.services.moses_resend_events']
    resend._ledger=lambda request: Path(request.app.state.data_dir)/'moses_resend_delivery_events.json'
    resend._action_file=lambda request,p,k: Path(request.app.state.data_dir)/('actions_'+p+'_'+k+'.json')
    butler=ModuleType('app.services.moses_butler_flow')
    butler.pending_actions=lambda request: {'proposals': [{'id':'p123','state':'pending','butler_action':'schedule', 'record_id':'j1'}], 'count':1}
    monkeypatch.setitem(sys.modules,'app.services.moses_butler_flow',butler)
    workspaces=ModuleType('app.routers.workspaces')
    workspaces.load=lambda p: json.loads(Path(p).read_text())
    monkeypatch.setitem(sys.modules,'app.routers.workspaces',workspaces)
    return tmp_path


def _draft(path, state='pending_review', draft_id='d123'):
    f=path/'moses_pds'/'quote_review_drafts.json'
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps([{'id':draft_id,'job_id':'j1','job_number':'1026-73',
                              'customer':'The Irvine Company','scope':'Review top and bottom latch kit replacements',
                              'state':state,'version':2,'updated_at':'2026-11-16T12:00:00+00:00'}]))
    return f


def test_saved_draft_job_and_pending_approval_are_combined_read_only(connected):
    p=_draft(connected)
    before=hashlib.sha256(p.read_bytes()).hexdigest()
    request=Request(connected,jobs=[{'id':'j1','job_number':'1026-73','customer':'The Irvine Company','status':'Quote','date':'2026-10-30'}])
    result=action.overview(request)
    assert result['workspace']=='pds' and result['read_only']
    assert result['approvals']['count']==1
    assert result['drafts']['count']==1
    assert result['drafts']['items'][0]['draft_id']=='d123'
    assert result['work']['count']==1
    assert result['delivery']['available'] is False
    assert result['delivery']['count'] is None
    assert hashlib.sha256(p.read_bytes()).hexdigest()==before


def test_saved_draft_detail_verified_and_unpriced(connected):
    _draft(connected)
    result=action.pds_draft_detail(Request(connected),'d123')
    assert result['draft']['job_number']=='1026-73'
    assert result['no_price_assumed'] and not result['issued_estimate']
    assert result['draft']['state']=='pending_review'
    with pytest.raises(HTTPException) as e: action.pds_draft_detail(Request(connected),'other')
    assert e.value.status_code==404


@pytest.mark.parametrize('platform,role,user,status', [
    ('pds','tech',True,403),('pds','office',True,403),('sdc','office',True,403),
    ('pds','office_admin',False,401),('unknown','office_admin',True,403),
])
def test_guards(connected,platform,role,user,status):
    with pytest.raises(HTTPException) as e:
        action.overview(Request(connected,platform=platform,role=role,logged_in=user))
    assert e.value.status_code==status


def test_workspace_isolation(connected):
    _draft(connected)
    result=action.overview(Request(connected,platform='sdc'))
    assert result['drafts']['available'] is False
    assert result['drafts']['items']==[]
    with pytest.raises(HTTPException) as e:
        action.pds_draft_detail(Request(connected,platform='doorks'),'d123')
    assert e.value.status_code==403


def test_missing_saved_drafts_distinct_from_delivery_unknown(connected):
    result=action.overview(Request(connected))
    assert result['drafts']['count']==0 and result['drafts']['available']
    assert result['delivery']['count'] is None


def test_corrupt_draft_ledger_is_not_silent_zero(connected):
    f=connected/'moses_pds'/'quote_review_drafts.json';f.parent.mkdir(exist_ok=True)
    f.write_text('{broken')
    with pytest.raises(HTTPException) as e:
        action.overview(Request(connected))
    assert e.value.status_code==503


def test_cannot_guess_or_misuse_saved_draft_id(connected):
    for ident in ('', '../draft', 'x'*81, 'other/id', 'not found'):
        with pytest.raises(HTTPException) as e:
            action.pds_draft_detail(Request(connected),ident)
        assert e.value.status_code in (404,422)


def test_unavailable_delivery_not_misreported_as_success(connected):
    result=action.overview(Request(connected))
    assert 'not checked' in result['delivery']['note'].lower()


def test_action_center_rejects_wrong_workspace_return(monkeypatch,connected):
    from app.services import moses_followthrough
    monkeypatch.setattr(moses_followthrough,'desk',lambda request:{'workspace':'sdc'})
    with pytest.raises(HTTPException) as e:
        action.overview(Request(connected))
    assert e.value.status_code==503


def test_source_bridge_is_no_new_send_or_payment_action():
    agent=ROOT/'app/services/moses_agent.py'
    if agent.exists():
        code=agent.read_text()
        assert 'def get_moses_action_center' in code
        assert 'def get_verified_pds_draft' in code
        assert 'def prepare_customer_dispatch_update' in code
        portion=code[code.index('def prepare_customer_dispatch_update'):code.index('def get_business_briefing')]
    else:
        from patch_agent import TOOL
        portion=TOOL
    assert 'from app.services.moses_dispatch_send import propose' in portion
    assert 'propose(request, platform, record_id' in portion
    assert '_transmit(' not in portion
    assert 'decide(' not in portion
    assert 'write_text(' not in portion


def test_result_does_not_disclose_email_or_private_note(connected):
    draft=_draft(connected)
    stored=json.loads(draft.read_text());stored[0]['customer_email']='private@example.com';stored[0]['private_notes']='Do not expose';draft.write_text(json.dumps(stored))
    result=action.overview(Request(connected))
    assert 'private@example.com' not in json.dumps(result)
    assert 'Do not expose' not in json.dumps(result)
