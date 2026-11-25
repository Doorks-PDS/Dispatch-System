"""Atlas customization-first storefront and SDC-only marketing draft review."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.routers import doorks_storefront as storefront

ROOT = Path(__file__).resolve().parents[1]


def req(tmp_path, role='office_admin', platform='sdc'):
    state = SimpleNamespace(auth_user={'id':'admin-1'} if role else None, auth_role=role)
    return SimpleNamespace(state=state, session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, project_root=ROOT)))


def draft(**overrides):
    data={'channel':'both','title':'Your way','caption':'Atlas is customized for your team.',
          'asset':'atlas_real_dashboard.webp','planned_at':'2026-12-01T18:00:00+00:00','campaign':'custom_software'}
    data.update(overrides)
    return storefront.AtlasMarketingDraft(**data)


def test_public_storefront_is_custom_first_and_keeps_real_screens_and_leads():
    html=(ROOT/'static'/'sdc_software.html').read_text()
    assert 'Run the work.' in html and 'Your way.' in html
    assert 'software built around' in html
    assert 'id="atlas-real-stage"' in html
    assert html.count('data-real-slide=')==5
    assert 'atlas_preview_1.webp' not in html and '<video' not in html
    assert 'id="lead"' in html and '/api/software/inquiries' in html
    assert 'id="atlas-moses-chat-widget"' in html
    assert 'meta name="keywords"' not in html


def test_sdc_marketing_drafts_approval_and_edit_reset(tmp_path):
    request=req(tmp_path)
    post=storefront.atlas_marketing_create(draft(),request)['post']
    assert post['status']=='draft'
    view=storefront.atlas_marketing_posts(request)
    assert len(view['posts'])==1 and view['meta_connected'] is False
    assert view['auto_publishing_enabled'] is False
    approved=storefront.atlas_marketing_decide(post['id'], storefront.AtlasMarketingDecision(approve=True,confirm=True),request)
    assert approved['post']['status']=='approved' and approved['published'] is False
    edited=storefront.atlas_marketing_edit(post['id'],draft(title='Refined caption'),request)
    assert edited['post']['status']=='draft' and edited['post']['approved_by'] is None
    assert edited['post']['revision']==2
    again=storefront.atlas_marketing_posts(request)
    assert again['posts'][0]['title']=='Refined caption'


def test_marketing_no_unauthorized_access_or_unapproved_asset(tmp_path):
    for role,platform in [('tech','sdc'),('office','sdc'),('office_admin','pds'),(None,'sdc')]:
        with pytest.raises(HTTPException):
            storefront.atlas_marketing_posts(req(tmp_path,role,platform))
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_create(draft(asset='../../data/users.json'),req(tmp_path))
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_create(draft(planned_at='2026-12-01T10:00'),req(tmp_path))


def test_marketing_approval_requires_confirm_and_does_not_publish(tmp_path):
    request=req(tmp_path)
    post=storefront.atlas_marketing_create(draft(),request)['post']
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_decide(post['id'],storefront.AtlasMarketingDecision(approve=True,confirm=False),request)
    one=storefront.atlas_marketing_decide(post['id'],storefront.AtlasMarketingDecision(approve=False,confirm=True),request)
    assert one['post']['status']=='archived' and one['published'] is False
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_edit(post['id'],draft(),request)


def test_sdc_navigation_and_marketing_page_present():
    assert "'SDC Marketing'" in (ROOT/'static'/'app.js').read_text()
    html=(ROOT/'static'/'sdc_atlas_marketing.html').read_text()
    assert 'no automatic posts' in html
    assert '/api/software/marketing/posts' in html
    assert 'Atlas Marketing Desk' in html
