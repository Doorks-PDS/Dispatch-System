"""Regression checks for PDS session initialization and hub notification layout."""
from pathlib import Path
from types import SimpleNamespace
from app.routers import platforms

ROOT=Path(__file__).resolve().parents[1]


def request(platform=None, role='office_admin'):
    session={} if platform is None else {'active_platform':platform}
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'u1'},auth_role=role),session=session)


def test_default_visible_pds_sets_real_session_workspace():
    req=request()
    result=platforms.current(req)
    assert result['platform']=='pds'
    assert req.session['active_platform']=='pds'


def test_existing_admin_other_workspace_is_preserved():
    req=request('sdc')
    assert platforms.current(req)['platform']=='sdc'
    assert req.session['active_platform']=='sdc'


def test_non_admin_session_never_remains_in_foreign_workspace():
    req=request('doorks',role='office')
    assert platforms.current(req)['platform']=='pds'
    assert req.session['active_platform']=='pds'


def test_login_and_pin_both_select_pds_session():
    source=(ROOT/'app/routers/auth.py').read_text()
    assert source.count('request.session["active_platform"] = "pds"')>=2


def test_page_waits_for_server_workspace_before_rendering_calendar():
    js=(ROOT/'static/app.js').read_text()
    assert "await initializePlatform();\n    if(activePlatform!=='pds')return;\n    renderCalendarView()" in js
    assert "await initializePlatform();\n      if(activePlatform==='pds'){renderCalendarView();refreshBadges();}" in js


def test_nav_notification_badge_is_separate_from_title_and_subtitle():
    css=(ROOT/'static/style.css').read_text()
    assert '.navbtn:has(>small)' in css
    assert '.navbtn:has(>small)>small' in css
    assert '.navbtn>.badge{position:absolute' in css
    assert 'text-overflow:ellipsis' in css
