"""The PDS UI and public Twilio policies are wired to actual app endpoints."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.pds_sms import router as sms_router


def test_public_twilio_pages_readable_without_live_provider_configuration(monkeypatch):
    monkeypatch.delenv('PDS_SMS_PUBLIC_BASE_URL', raising=False)
    app=FastAPI();app.include_router(sms_router)
    with TestClient(app) as client:
        for route,title in [('/pds/sms','SMS Service Updates'),('/pds/sms/privacy','Privacy Policy'),('/pds/sms/terms','Terms & Conditions')]:
            response=client.get(route)
            assert response.status_code==200
            assert title.replace('&','&amp;') in response.text
        assert client.post('/pds/sms/twilio/inbound').status_code==503


def test_interactive_van_pds_business_and_door_record_layout_is_real_source():
    js=(Path(__file__).resolve().parents[1]/'static/app.js').read_text()
    start=js.index('  async function renderVanStockView(){')
    end=js.index('  function renderTimeOffView()',start)
    van=js[start:end]
    for anchor in ("input.addEventListener('focus',draw)", 'setPart(id)',
                   '🚐 Vehicle Information', "'/pds-van-stock/reconciliation'",
                   "'/pds-van-stock/template/'", "'/pds-van-stock/vans/'",'Warehouse and van stock are quantity records only'):
        assert anchor in van,anchor
    assert 'document.createElement("details")' in js
    assert '🚪 Door Records (optional)' in js
    assert "const entries=platform==='pds'&&pdsStock" in js
    assert "activePlatform==='pds' && tracked.has(String(p.id))" in js
