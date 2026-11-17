from __future__ import annotations
import importlib.util
import json
import tempfile
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

PATH = Path(__file__).resolve().parents[1] / 'app/services/moses_followthrough.py'
spec = importlib.util.spec_from_file_location('moses_followthrough_under_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def stub_workspace_reader(monkeypatch):
    """Minimal source adapter for tests run against a lightweight source checkout."""
    app = types.ModuleType('app'); app.__path__ = []
    routers = types.ModuleType('app.routers'); routers.__path__ = []
    workspaces = types.ModuleType('app.routers.workspaces')
    workspaces.load = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    monkeypatch.setitem(sys.modules, 'app', app)
    monkeypatch.setitem(sys.modules, 'app.routers', routers)
    monkeypatch.setitem(sys.modules, 'app.routers.workspaces', workspaces)


def request(base):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=base)))


def save(base, rows):
    path = Path(base) / 'moses_pds' / 'quote_review_drafts.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))


def row(state='pending_review', number='1126-01'):
    return {'id': 'a'*32,'job_id':'b'*32, 'job_number': number, 'customer':'Example PDS',
            'state':state,'scope':'SECRET FIELD NOT FOR CARD', 'review_note':'private',
            'updated_at':'2026-11-16T13:00:00+00:00'}


def test_absent_queue_is_new_not_prepared():
    with tempfile.TemporaryDirectory() as temp:
        out = module._pds_drafts(request(temp))
        assert out['available'] and out['count'] == 0
        assert not (Path(temp) / 'moses_pds').exists()


def test_pending_draft_is_a_compact_card():
    with tempfile.TemporaryDirectory() as temp:
        save(temp, [row()])
        out = module._pds_drafts(request(temp))
        assert out['count'] == 1 and out['items'][0]['draft_id'] == 'a'*32
        assert 'scope' not in out['items'][0] and 'review_note' not in out['items'][0]
        assert out['items'][0]['job_number'] == '1126-01'


def test_approved_drafts_are_visible_but_not_marked_issued():
    with tempfile.TemporaryDirectory() as temp:
        save(temp, [row('ready_for_estimator')])
        out=module._pds_drafts(request(temp))
        assert out['count']==1 and 'estimator' in out['items'][0]['title'].lower()
        assert 'sent' not in out['items'][0]


def test_declined_drafts_not_in_actionable_queue():
    with tempfile.TemporaryDirectory() as temp:
        save(temp, [row('declined')])
        assert module._pds_drafts(request(temp))['count']==0


def test_malformed_existing_file_is_not_empty_queue():
    with tempfile.TemporaryDirectory() as temp:
        save(temp, [])
        target=Path(temp)/'moses_pds'/'quote_review_drafts.json'
        target.write_text('not json')
        with pytest.raises(HTTPException): module._pds_drafts(request(temp))


def test_invalid_identifiers_are_not_exposed():
    with tempfile.TemporaryDirectory() as temp:
        invalid=row(); invalid['id']=''
        save(temp,[invalid])
        with pytest.raises(HTTPException): module._pds_drafts(request(temp))


def test_workspace_isolation_from_desk():
    # Non-PDS workspaces never call _pds_drafts or reveal the PDS queue.
    assert "if workspace == 'pds' else" in Path(__file__).resolve().parents[1].joinpath('app/services/moses_followthrough.py').read_text()


def test_frontend_uses_real_drafts_launch():
    content=Path(__file__).resolve().parents[1].joinpath('static/app.js').read_text()
    assert "['Moses saved drafts',drafts]" in content
    assert "getElementById('mosesDraftsLaunch')" in content
    assert "launch.click()" in content


def test_results_bounded():
    with tempfile.TemporaryDirectory() as temp:
        save(temp,[{**row(), 'id':f'{i:032x}', 'job_id':f'{i+100:032x}'} for i in range(50)])
        out=module._pds_drafts(request(temp))
        assert out['count']==50 and len(out['items'])==30


def test_desk_includes_saved_drafts_pds_only(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        save(temp, [row()])
        req = request(temp)
        monkeypatch.setattr(module, '_guard', lambda _request: 'pds')
        monkeypatch.setattr(module, '_approvals', lambda _request: {'available': True, 'items': []})
        monkeypatch.setattr(module, '_pds_work', lambda _request: {'available': True, 'items': []})
        monkeypatch.setattr(module, '_delivery', lambda _request, _platform: {'available': False, 'items': []})
        assert module.desk(req)['drafts']['count'] == 1
        monkeypatch.setattr(module, '_guard', lambda _request: 'sdc')
        report = module.desk(req)
        assert report['drafts']['available'] is False and report['drafts']['items'] == []


def test_invalid_saved_record_format_is_not_silent_success():
    with tempfile.TemporaryDirectory() as temp:
        save(temp, ['wrong schema'])
        with pytest.raises(HTTPException):
            module._pds_drafts(request(temp))
