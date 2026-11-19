"""PRIO Coin remains a protected, explicitly labeled prototype."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_prio_preview_admin_navigation_is_explicit():
    frontend = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    backend = (ROOT / 'main.py').read_text(encoding='utf-8')
    assert "navPrioCoinPreview" in frontend
    assert "Admin Trials" in frontend
    assert "renderPrioCoinWorkspace();" in frontend
    assert "window.open('/pds/prio-coin-preview'" not in frontend
    assert 'currentUser?.role !== \'office_admin\'' in frontend
    assert 'role === "office_admin" && activePlatform === "pds"' in frontend
    assert "@app.get('/pds/prio-coin-preview'" in backend
    assert "'office_admin'" in backend
    assert "prio_coin_admin_preview.html" in backend
    assert "pds_prio_trials_router" in backend
    assert "Simulated total" in frontend
