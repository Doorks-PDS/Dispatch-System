"""Moses 5.91: 30-second SDC contact form, authentic media, shared sales overview."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import sdc_door_quotes as doors

ROOT = Path(__file__).resolve().parents[1]


def client_for(tmp_path):
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.state.project_root = ROOT

    @app.middleware("http")
    async def test_session(request, call_next):
        role = request.headers.get("x-test-role")
        request.state.auth_user = {"id": "office"} if role else None
        request.state.auth_role = role
        request.scope["session"] = {"active_platform": request.headers.get("x-test-platform", "sdc")}
        return await call_next(request)

    app.include_router(doors.router)
    return TestClient(app)


def test_quick_request_no_measurements_or_shipping_needed(tmp_path):
    client = client_for(tmp_path)
    response = client.post("/api/saddleback/door-quotes", data={
        "full_name": "Jo Customer", "email": "jo@example.com", "phone": "555-0000",
        "notes": "Looking for new wood and cane doors"
    })
    assert response.status_code == 201, response.text
    headers = {"x-test-role": "office_admin"}
    records = client.get("/api/saddleback/door-quotes", headers=headers)
    assert records.status_code == 200
    lead = records.json()["items"][0]
    assert lead["full_name"] == "Jo Customer"
    assert lead["door_style"] == "Not sure"
    assert lead["opening_width"] == "" and lead["opening_height"] == ""
    assert lead["fulfillment"] == "Not sure"
    assert lead["notes"] == "Looking for new wood and cane doors"
    assert not (tmp_path / "business_workspaces" / "pds").exists()


def test_optional_fields_still_validated(tmp_path):
    client = client_for(tmp_path)
    basic = {"full_name": "Jo Customer", "email": "jo@example.com"}
    assert client.post("/api/saddleback/door-quotes", data={**basic, "opening_width": "-4", "opening_height": "80"}).status_code == 422
    assert client.post("/api/saddleback/door-quotes", data={**basic, "opening_width": "40"}).status_code == 422
    assert client.post("/api/saddleback/door-quotes", data={**basic, "door_style": "Random"}).status_code == 422
    assert client.post("/api/saddleback/door-quotes", data={**basic, "fulfillment": "Shipping"}).status_code == 422


def test_private_sales_overview_and_export(tmp_path):
    client = client_for(tmp_path)
    assert client.get("/sdc/sales-reports").status_code == 401
    assert client.get("/api/saddleback/door-quotes/export.csv").status_code == 401
    user = {"x-test-role": "office_admin", "x-test-platform": "sdc"}
    assert client.get("/sdc/sales-reports", headers=user).status_code == 200
    assert client.get("/sdc/sales-reports", headers={"x-test-role": "tech"}).status_code == 403
    assert client.get("/sdc/sales-reports", headers={**user, "x-test-platform": "pds"}).status_code == 403
    client.post("/api/saddleback/door-quotes", data={
        "full_name": "=HYPERLINK(\"http://example.com\")", "email": "safe@example.com"
    })
    exported = client.get("/api/saddleback/door-quotes/export.csv", headers=user)
    assert exported.status_code == 200
    assert "full_name,email,phone,status" in exported.text
    assert "'=HYPERLINK" in exported.text
    assert 'attachment;' in exported.headers.get('content-disposition', '')


def test_navigation_form_and_photo_paths():
    app = (ROOT / 'static' / 'app.js').read_text()
    for item in ('Sales & Reports', 'Atlas Storefront', 'SDC Storefront', 'PDS Parts Storefront'):
        assert f"addSdc('sdcDevelopmentNav','{item}'" in app
    assert "addSdc('sdcDevelopmentNav','Door Quote Requests'" not in app
    assert "addSdc('sdcDevelopmentNav','Atlas Software Sales'" not in app
    report = (ROOT / 'static' / 'sdc_sales_reports.html').read_text()
    assert '/api/software/inquiries' in report
    assert '/api/saddleback/door-quotes' in report
    assert 'data-type="atlas"' in report
    assert 'data-type="doors"' in report
    assert 'data-type="parts"' in report
    assert '/pds-parts/api/sdc/orders' in report
    form = (ROOT / 'static' / 'sdc_doors.html').read_text()
    assert 'name="full_name"' in form and 'name="email"' in form
    assert 'name="opening_width"' not in form
    assert 'name="postal_code"' not in form
    assert '30 seconds' in form
    assert '/static/sdc_real_doors_cover.jpg' not in form
    for f in ('sdc_project_hero.webp', 'sdc_project_collection.webp', 'sdc_project_cane.webp', 'sdc_project_sliding.webp', 'sdc_project_detail.webp'):
        image = ROOT / 'static' / f
        assert image.is_file(), f
        assert image.stat().st_size > 15000
        data = image.read_bytes()[:12]
        assert data[:4] == b'RIFF' and data[8:12] == b'WEBP'
