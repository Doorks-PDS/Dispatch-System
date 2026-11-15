"""Rev75 customer approval: no SMTP, Stripe, or production data."""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.services import moses_estimate_acceptance as acceptance


def setup(tmp_path, platform='doorks'):
    folder=tmp_path/'business_workspaces'/platform
    folder.mkdir(parents=True)
    document={'id':'estimate-1','document_type':'estimate', 'document_number':'RE00076',
              'status':'Sent','customer':'Customer A','contact_email':'contact@example.com',
              'description':'Repair two door closers','total':'250.00','amount':250,
              'line_items':json.dumps([{'description':'Repair two door closers','quantity':1,'rate':250}]),
              'pricing_required':False,
              'requires_number_assignment':False}
    (folder/'estimates_invoices.json').write_text(json.dumps([document]))
    admin=SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'}, auth_role='office_admin'),
                          session={'active_platform':platform},
                          app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))
    public=SimpleNamespace(state=SimpleNamespace(auth_user=None,auth_role=None),
                           session={}, app=admin.app)
    return admin,public,folder


@pytest.mark.parametrize('platform',['doorks','sdc'])
def test_customer_accept_updates_document_once(tmp_path,platform):
    admin,public,folder=setup(tmp_path,platform)
    link=acceptance.issue(admin,platform,'estimate-1')
    assert link['sent'] is False
    assert len(link['token']) >= 40
    stored=(folder/'estimate_acceptance_links.json').read_text()
    assert link['token'] not in stored
    assert acceptance.inspect(public,link['token'])['status']=='Awaiting acceptance'
    outcome=acceptance.accept(public,link['token'],'Taylor Customer')
    assert outcome['accepted'] is True
    saved=json.loads((folder/'estimates_invoices.json').read_text())[0]
    assert saved['status']=='Approved' and saved['accepted_by']=='Taylor Customer'
    history=acceptance.history(admin,platform,'estimate-1')
    assert history[0]['state']=='accepted'
    with pytest.raises(HTTPException) as e:
        acceptance.accept(public,link['token'],'Another Person')
    assert e.value.status_code==410


def test_declines_stale_document_and_allows_reissue_after_revocation(tmp_path):
    admin,public,folder=setup(tmp_path)
    link=acceptance.issue(admin,'doorks','estimate-1')
    with pytest.raises(HTTPException):
        acceptance.issue(admin,'doorks','estimate-1')
    record=json.loads((folder/'estimates_invoices.json').read_text())
    record[0]['total']='450'
    (folder/'estimates_invoices.json').write_text(json.dumps(record))
    with pytest.raises(HTTPException) as e:
        acceptance.accept(public,link['token'],'Taylor Customer')
    assert e.value.status_code==409
    assert json.loads((folder/'estimates_invoices.json').read_text())[0]['status']=='Sent'
    acceptance.revoke(admin,'doorks',link['link_id'])
    with pytest.raises(HTTPException) as e:
        acceptance.inspect(public,link['token'])
    assert e.value.status_code==410
    new=acceptance.issue(admin,'doorks','estimate-1')
    assert new['token']!=link['token']


def test_workspace_and_unsent_guards(tmp_path):
    admin,public,folder=setup(tmp_path)
    admin.session['active_platform']='sdc'
    with pytest.raises(HTTPException) as e: acceptance.issue(admin,'doorks','estimate-1')
    assert e.value.status_code==403
    admin.session['active_platform']='doorks'
    record=json.loads((folder/'estimates_invoices.json').read_text())
    record[0]['status']='Draft'
    (folder/'estimates_invoices.json').write_text(json.dumps(record))
    with pytest.raises(HTTPException) as e: acceptance.issue(admin,'doorks','estimate-1')
    assert e.value.status_code==409
    with pytest.raises(HTTPException) as e: acceptance.inspect(public,'not_a_valid_token')
    assert e.value.status_code==404


def test_expiry_and_review_flags(tmp_path):
    admin,public,folder=setup(tmp_path)
    link=acceptance.issue(admin,'doorks','estimate-1')
    path=folder/'estimate_acceptance_links.json'
    links=json.loads(path.read_text())
    links[0]['expires_at']='2020-01-01T00:00:00+00:00'
    path.write_text(json.dumps(links))
    with pytest.raises(HTTPException) as e: acceptance.accept(public,link['token'],'Taylor Customer')
    assert e.value.status_code==410
    acceptance.revoke(admin,'doorks',link['link_id'])
    record=json.loads((folder/'estimates_invoices.json').read_text())
    record[0]['pricing_required']=True
    (folder/'estimates_invoices.json').write_text(json.dumps(record))
    with pytest.raises(HTTPException) as e: acceptance.issue(admin,'doorks','estimate-1')
    assert e.value.status_code==409
