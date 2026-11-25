"""5.87: Separate SDC brand marketing drafts; no unauthorized social publishing."""
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException
import pytest

from app.routers import doorks_storefront as storefront

ROOT = Path(__file__).resolve().parents[1]


def req(tmp_path, role='office_admin', platform='sdc'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin-1'}, auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, project_root=ROOT)))


def draft(brand, asset=''):
    return storefront.AtlasMarketingDraft(brand=brand, channel='both', title='Brand introduction',
                                         caption='A distinct opening post for this brand.',
                                         asset=asset, planned_at='', campaign='brand_introduction')


def test_first_three_launch_drafts_is_idempotent_and_unpublished(tmp_path):
    request=req(tmp_path)
    created=storefront.sdc_marketing_seed_launch(request)
    assert set(created['created']) == {'atlas','history','saddleback'}
    again=storefront.sdc_marketing_seed_launch(request)
    assert not again['created']
    posts=storefront.atlas_marketing_posts(request)
    assert len(posts['posts']) == 3
    assert {x['brand'] for x in posts['posts']} == {'atlas','history','saddleback'}
    assert all(x['status'] == 'draft' for x in posts['posts'])
    assert posts['publish_enabled'] is False
    assert posts['auto_publishing_enabled'] is False
    assert posts['brands']['history']['instagram'] == 'beyond_historybooks'
    assert posts['brands']['saddleback']['metricool_id'] == '8365706'


def test_assets_are_brand_scoped(tmp_path):
    request=req(tmp_path)
    created=storefront.atlas_marketing_create(draft('history','beyond_history_profile.webp'),request)
    assert created['post']['brand']=='history'
    assert created['published'] is False
    with pytest.raises(HTTPException) as exc:
        storefront.atlas_marketing_create(draft('saddleback','atlas_real_dashboard.webp'),request)
    assert exc.value.status_code==422
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_create(draft('history','../../data/users.json'),request)


def test_cannot_change_post_brand_or_reuse_old_approval(tmp_path):
    request=req(tmp_path)
    created=storefront.atlas_marketing_create(draft('history'),request)['post']
    result=storefront.atlas_marketing_decide(created['id'],storefront.AtlasMarketingDecision(approve=True,confirm=True),request)
    assert result['post']['status']=='approved' and result['published'] is False
    with pytest.raises(HTTPException) as exc:
        storefront.atlas_marketing_edit(created['id'],draft('atlas'),request)
    assert exc.value.status_code == 409
    updated=storefront.atlas_marketing_edit(created['id'],draft('history'),request)['post']
    assert updated['status']=='draft'
    assert updated['approved_by'] is None


def test_legacy_atlas_defaults_to_atlas_and_no_read_side_effects(tmp_path):
    from app.routers import workspaces
    request=req(tmp_path)
    path=storefront._atlas_marketing_path(request)
    workspaces.save(path,[{'id':'legacy','title':'Old Atlas post','status':'draft','caption':'copy'}])
    result=storefront.atlas_marketing_posts(request)
    assert result['posts'][0]['brand']=='atlas'
    assert 'brand' not in workspaces.load(path)[0]


def test_only_sdc_office_admin_seeds_launch_drafts(tmp_path):
    for role,platform in [('tech','sdc'),('office','sdc'),('office_admin','pds')]:
        with pytest.raises(HTTPException):
            storefront.sdc_marketing_seed_launch(req(tmp_path,role,platform))


def test_storefront_uses_approved_mountain_art_and_real_screens_remain():
    html=(ROOT/'static'/'sdc_software.html').read_text()
    assert 'src="/static/atlas_hero_mountains.webp"' in html
    assert '/static/atlas_real_extra_2.webp' not in html.split('</section>',1)[0]
    assert html.count('data-real-slide=')==5
    assert '/api/software/inquiries' in html and 'atlas-moses-chat-widget' in html
    desk=(ROOT/'static'/'sdc_atlas_marketing.html').read_text()
    assert 'Atlas Marketing Desk' in desk  # Preserve 5.85 HTML compatibility test.
    assert 'Add launch drafts' in desk
    for brand in ('atlas','saddleback','history'):
        assert f'data-brand="{brand}"' in desk
    assert 'is NOT auto-published' not in desk  # no false claim of direct publication
