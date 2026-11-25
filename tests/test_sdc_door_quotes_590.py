"""Moses 5.90 SDC custom doors: public intake, private queue, durable attachments."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import sdc_door_quotes as doors

ROOT = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


def make_client(tmp_path):
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.state.project_root = ROOT

    @app.middleware("http")
    async def set_test_session(request, call_next):
        role = request.headers.get("x-test-role")
        request.state.auth_user = {"id": "sdc-test-user"} if role else None
        request.state.auth_role = role
        request.scope["session"] = {"active_platform": request.headers.get("x-test-platform", "sdc")}
        return await call_next(request)

    app.include_router(doors.router)
    return TestClient(app)


def payload():
    return {
        "full_name": "Alex Customer", "email": "alex@example.com", "phone": "555-100-2000",
        "door_style": "Bi-fold", "door_count": "2", "opening_width": "72",
        "opening_height": "84", "measurement_unit": "in", "wood_finish": "Warm oak",
        "material": "Wood + woven cane", "notes": "Two sets by the patio",
        "fulfillment": "Shipping", "postal_code": "92001", "timeline": "Two months",
        "utm_source": "facebook", "utm_medium": "paid_social", "utm_campaign": "sdc_custom_doors_intro",
    }


def test_public_form_and_private_sdc_queue(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/saddleback/doors").status_code == 200
    out = client.post("/api/saddleback/door-quotes", data=payload(),
                      files=[("photos", ("example.png", PNG, "image/png"))])
    assert out.status_code == 201, out.text
    reference = out.json()["reference"]
    data_file = tmp_path / "business_workspaces" / "sdc" / "door_quote_requests.json"
    assert data_file.exists()
    assert not (tmp_path / "business_workspaces" / "pds").exists()

    # Public cannot read customer names, notes, or photos.
    assert client.get("/api/saddleback/door-quotes").status_code == 401
    assert client.get("/sdc/door-quote-requests").status_code == 401
    staff = {"x-test-role": "office_admin", "x-test-platform": "sdc"}
    records = client.get("/api/saddleback/door-quotes", headers=staff)
    assert records.status_code == 200
    item = records.json()["items"][0]
    assert item["id"].startswith(reference) and item["door_count"] == 2
    assert item["utm_campaign"] == "sdc_custom_doors_intro"
    assert len(item["photos"]) == 1
    photo_url = f"/api/saddleback/door-quotes/{item['id']}/photos/0"
    assert client.get(photo_url).status_code == 401
    photo = client.get(photo_url, headers=staff)
    assert photo.status_code == 200 and photo.content == PNG
    assert photo.headers["cache-control"] == "private, no-store"
    assert client.get(photo_url, headers={"x-test-role": "office_admin", "x-test-platform": "pds"}).status_code == 403
    assert client.get(photo_url, headers={"x-test-role": "tech"}).status_code == 403

    change = client.patch(f"/api/saddleback/door-quotes/{item['id']}", headers=staff,
                          json={"status": "Reviewing", "staff_notes": "Review cane options"})
    assert change.status_code == 200
    assert change.json()["item"]["status"] == "Reviewing"
    assert client.get("/api/saddleback/door-quotes", headers=staff).json()["items"][0]["staff_notes"] == "Review cane options"


def test_validation_deduplication_and_photo_type(tmp_path):
    client = make_client(tmp_path)
    form = payload()
    assert client.post("/api/saddleback/door-quotes", data={**form, "opening_width": "-3"}).status_code == 422
    assert client.post("/api/saddleback/door-quotes", data={**form, "fulfillment": "Shipping", "postal_code": ""}).status_code == 422
    assert client.post("/api/saddleback/door-quotes", data=form,
                       files=[("photos", ("bad.png", b"<script>alert(1)</script>", "image/png"))]).status_code == 422
    assert not (tmp_path / "business_workspaces" / "sdc" / "door_quote_requests.json").exists()
    first = client.post("/api/saddleback/door-quotes", data=form)
    assert first.status_code == 201
    second = client.post("/api/saddleback/door-quotes", data=form)
    assert second.status_code == 201 and second.json().get("duplicate") is True
    assert len(client.get("/api/saddleback/door-quotes", headers={"x-test-role": "office_admin"}).json()["items"]) == 1


def test_bad_status_cannot_modify_and_links_visible(tmp_path):
    client = make_client(tmp_path)
    result = client.post("/api/saddleback/door-quotes", data=payload())
    assert result.status_code == 201
    admin = {"x-test-role": "office_admin"}
    item = client.get("/api/saddleback/door-quotes", headers=admin).json()["items"][0]
    assert client.patch(f"/api/saddleback/door-quotes/{item['id']}", headers=admin,
                        json={"status": "Published", "staff_notes": ""}).status_code == 422
    assert client.patch(f"/api/saddleback/door-quotes/{item['id']}",
                        json={"status": "Closed"}).status_code == 401
    assert client.get(f"/api/saddleback/door-quotes/{item['id']}/photos/0",headers=admin).status_code == 404
    dash = (ROOT / "static/app.js").read_text(encoding="utf-8")
    assert "'SDC Sales & Reports'" in dash
    assert "'Door Storefront'" in dash
    assert "'Atlas Storefront'" in dash
    assert "'SDC Marketing'" in dash
    marketing = (ROOT / "static/sdc_atlas_marketing.html").read_text(encoding="utf-8")
    assert 'href="/saddleback/doors"' in marketing
    assert "Copy door quote campaign link" in marketing
    assert "sdc_custom_doors_intro" in marketing
    assert "/static/sdc_project_hero.webp" in (ROOT / "static/sdc_doors.html").read_text()
