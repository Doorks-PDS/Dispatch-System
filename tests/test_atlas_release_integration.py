"""Atlas storefront deployment checks using synthetic, isolated lead data."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

import main


def test_atlas_redesign_video_and_inquiry_are_connected(tmp_path):
    original_data_dir = main.app.state.data_dir
    main.app.state.data_dir = tmp_path
    try:
        with TestClient(main.app) as client:
            page = client.get('/software')
            assert page.status_code == 200
            assert 'Less busywork.' in page.text
            assert 'id="atlas-product-tour"' in page.text
            assert 'id="atlas-gallery-slides"' in page.text
            assert '/static/atlas_preview_6.webp' in page.text
            assert 'id="atlas-moses-workflows"' in page.text
            assert 'id="atlas-butler-briefing"' in page.text
            assert "'/api/software/inquiries'" in page.text

            inquiry = {
                'company': 'Synthetic Atlas Company',
                'contact': 'Synthetic Demo Requester',
                'email': 'synthetic@example.test',
                'package': 'Basic',
                'notes': 'Release integration test only',
                'utm_source': 'google',
                'utm_medium': 'paid',
                'utm_campaign': 'release_smoke',
                'landing_page': '/software?utm_source=google',
            }
            result = client.post('/api/software/inquiries', json=inquiry)
            assert result.status_code == 201, result.text
            assert result.json()['reference']
            path = tmp_path / 'business_workspaces' / 'sdc' / 'software_leads.json'
            rows = json.loads(path.read_text(encoding='utf-8'))
            assert len(rows) == 1
            assert rows[0]['company'] == inquiry['company']
            assert rows[0]['utm_source'] == 'google'
            assert rows[0]['package'] == 'Basic'
            assert rows[0]['status'] == 'New'

            duplicate = client.post('/api/software/inquiries', json=inquiry)
            assert duplicate.status_code == 201
            assert duplicate.json().get('duplicate') is True
            assert len(json.loads(path.read_text(encoding='utf-8'))) == 1
    finally:
        main.app.state.data_dir = original_data_dir
