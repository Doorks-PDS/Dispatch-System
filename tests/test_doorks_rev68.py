"""Regression checks for account tickets and financial navigation separation."""
import json
from pathlib import Path
from types import SimpleNamespace
from app.routers import doorks_portals as portal

class Request:
    def __init__(self, root):
        self.app=SimpleNamespace(state=SimpleNamespace(data_dir=root))
        self.state=SimpleNamespace(auth_user='admin',auth_role='office_admin')
        self.session={'active_platform':'doorks'}

def test_account_edit_and_deactivation_preserve_history(tmp_path):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    p=root/'portal_access.json'
    p.write_text(json.dumps({'invites':[],'submissions':[], 'accounts':[{'id':'acct1','role':'vendor','email':'vendor@example.com','contact_name':'Old','company':'Original','status':'active','password_hash':'secret','vendor_id':'v1'}]}))
    request=Request(tmp_path)
    assert portal.edit_portal_account('acct1',portal.PortalAccountEdit(contact_name='New Contact',company='New Co'),request)['ok']
    assert portal.deactivate_portal_account('acct1',request)['ok']
    account=json.loads(p.read_text())['accounts'][0]
    assert account['status']=='deactivated'
    assert account['contact_name']=='New Contact'
    assert account['vendor_id']=='v1'
    assert account['password_hash']=='secret'
    assert 'deactivated_at' in account

def test_portal_account_response_does_not_leak_hash(tmp_path):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    (root/'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[], 'accounts':[{'id':'a','password_hash':'secret','status':'active'}]}))
    accounts=portal.list_portal_accounts(Request(tmp_path))['accounts']
    assert 'password_hash' not in accounts[0]
