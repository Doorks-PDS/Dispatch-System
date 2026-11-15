"""Release-parity checks: report only actual workspace-scoped tools, never UI parity."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_workspace_capabilities import inspect
from app.routers.doorks_assistant import workspace_capabilities, router


def request(workspace, role='office_admin', user='admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user=user, auth_role=role),
                           session={'active_platform': workspace})


def test_three_workspaces_are_explicit_and_not_misrepresented(monkeypatch):
    for key in ('DOORKS_MOSES_DOORKS_AGENT_ENABLED', 'DOORKS_MOSES_PDS_AGENT_ENABLED', 'DOORKS_SDC_AGENT_ENABLED'):
        monkeypatch.delenv(key, raising=False)
    for workspace in ('doorks', 'pds', 'sdc'):
        result = inspect(request(workspace))
        assert result['workspace'] == workspace
        assert result['agent_enabled'] is False
        assert result['full_editor_parity_verified'] is False
        assert 'same_ticket_editor_across_office_customer_vendor' in result['release_checks_outstanding']
        assert result['read_only_tools'] and result['approval_proposal_categories']


def test_accounting_and_job_capabilities_are_scoped():
    doorks = inspect(request('doorks'))
    pds = inspect(request('pds'))
    sdc = inspect(request('sdc'))
    assert 'supplier_bill' in doorks['approval_proposal_categories']
    assert 'supplier_bill' not in pds['approval_proposal_categories']
    assert 'supplier_bill' not in sdc['approval_proposal_categories']
    assert 'pds_job_detail' in pds['read_only_tools']
    assert 'pds_job_detail' not in doorks['read_only_tools']
    assert 'pds_job_detail' not in sdc['read_only_tools']


def test_rejects_other_roles_and_anonymous_users():
    for r in (request('pds', role='technician'), request('unknown'), request('sdc', user=None)):
        with pytest.raises(HTTPException) as e:
            inspect(r)
        assert e.value.status_code in (401, 403)


def test_route_is_read_only_and_registered(monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED', 'true')
    result = workspace_capabilities(request('pds'))
    assert result['agent_enabled'] is True
    assert 'live_resend_delivery' in result['release_checks_outstanding']
    assert any(getattr(route, 'path', '') == '/doorks-assistant/workspace-capabilities'
               and 'GET' in route.methods for route in router.routes)
