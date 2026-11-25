"""5.88: compact marketing review, public tour navigation, safe brand-scoped assets."""
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException
import pytest
from app.routers import doorks_storefront as storefront

ROOT=Path(__file__).resolve().parents[1]


def req(tmp, role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'office-1'}, auth_role=role),
        session={'active_platform':'sdc'},app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp,project_root=ROOT)))


def test_compact_tour_and_accessibility():
    html=(ROOT/'static/sdc_software.html').read_text()
    assert 'id="atlas-real-stage"' in html
    assert html.count('data-real-slide=')==5
    assert html.count('id="atlas-real-prev"')==1
    assert html.count('id="atlas-real-next"')==1
    assert 'id="atlas-real-features"' in html
    assert 'function showPoints()' in html
    assert 'max-height:308px' in html
    assert 'aria-pressed' in html
    assert '/api/software/inquiries' in html
    assert '/static/atlas_hero_mountains.webp' in html


def test_sdc_marketing_navigation_and_simple_review_ui():
    app=(ROOT/'static/app.js').read_text()
    assert "addSdc('sdcDevelopmentNav','SDC Marketing'," in app
    assert "'SDC Sales & Reports'" in app
    desk=(ROOT/'static/sdc_atlas_marketing.html').read_text()
    assert '<h1>SDC Marketing</h1>' in desk
    assert 'Review & approve' in desk
    assert 'id="editorBody" hidden' in desk
    assert 'id="toggleEditor"' in desk
    assert 'Add launch drafts' in desk
    assert 'drafts' in desk.lower() and 'metricool' in desk.lower()
    assert '<form id="compose">' in desk
    assert '/api/software/marketing/posts' in desk
    assert 'Atlas Marketing Desk' in desk  # existing tests rely on legacy title


def test_approved_public_launch_images_are_brand_isolated(tmp_path):
    assert 'atlas_launch_workflow.webp' in storefront.MARKETING_ASSETS_BY_BRAND['atlas']
    assert 'history_launch_diary.webp' in storefront.MARKETING_ASSETS_BY_BRAND['history']
    assert 'history_launch_diary.webp' not in storefront.MARKETING_ASSETS_BY_BRAND['atlas']
    assert 'atlas_launch_workflow.webp' not in storefront.MARKETING_ASSETS_BY_BRAND['history']
    assert 'sdc_project_hero.webp' in storefront.MARKETING_ASSETS_BY_BRAND['saddleback']
    r=req(tmp_path)
    atlas=storefront.AtlasMarketingDraft(brand='atlas', channel='both', title='Intro', caption='Text', asset='atlas_launch_workflow.webp')
    history=storefront.AtlasMarketingDraft(brand='history', channel='both', title='Intro', caption='Text', asset='history_launch_diary.webp')
    assert storefront.atlas_marketing_create(atlas,r)['published'] is False
    assert storefront.atlas_marketing_create(history,r)['published'] is False
    with pytest.raises(HTTPException):
        storefront.atlas_marketing_create(history.model_copy(update={'asset':'atlas_launch_workflow.webp'}),r)


def test_no_auto_publication_from_sdc():
    desk=(ROOT/'static/sdc_atlas_marketing.html').read_text()
    assert 'approve' in desk.lower()
    assert 'nothing will be published' in desk.lower()
    assert 'auto_publishing_enabled' in (ROOT/'app/routers/doorks_storefront.py').read_text()
