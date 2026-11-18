"""The van ticket reuses the PDS parts catalogue and Moses intake."""
from pathlib import Path

from app.routers import pds_van_stock as van


def test_van_ticket_uses_shared_moses_part_editor():
    js = (Path(__file__).resolve().parents[1] / 'static' / 'app.js').read_text(encoding='utf-8')
    start = js.index('  async function renderVanStockView(){')
    end = js.index('  function renderTimeOffView()', start)
    view = js[start:end]
    assert '🚐 ' in view
    assert 'Open Van Ticket' in view
    assert '✨ Add Part with Moses' in view
    assert "renderPartsListView();document.querySelector('#parts_add')?.click()" in view
    assert 'photo.append(img)' in view
    assert "'/pds-van-stock/movements'" in view
    assert "'/pds-van-stock/template'" in view
    assert "'/pds-van-stock/vans/'" in view
    assert "item.low" in view
    assert "globalThis.crypto?.randomUUID" in view


def test_van_catalog_includes_existing_parts_media_without_new_store(monkeypatch, fixture_data=None):
    from types import SimpleNamespace
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir='/unused')))
    monkeypatch.setattr(van, '_read', lambda path: {'template': {}, 'vans': {'tech1': {'employee_name': 'Tech', 'enabled': True, 'items': {'part1': {'minimum': None, 'target': None}}}}, 'events': []})
    monkeypatch.setattr(van, '_path', lambda req: None)
    monkeypatch.setattr(van, '_parts', lambda req: {'part1': {'id': 'part1', 'part_number': 'DL1', 'description': 'Lock', 'manufacturer': 'Stanley', 'image_url': '/moses/part-image/pds/demo', 'product_url': 'https://example.com/part'}})
    monkeypatch.setattr(van, '_people', lambda req: {'tech1': {'name': 'Tech'}})
    monkeypatch.setattr('app.routers.data._pds_stock_balances', lambda req: {'part1': 2})
    result = van._view(request)
    for row in (result['catalog'][0], result['vans'][0]['items'][0]):
        assert row['image_url'] == '/moses/part-image/pds/demo'
        assert row['product_url'] == 'https://example.com/part'
        assert row['manufacturer'] == 'Stanley'


def test_moses_can_read_van_stock_but_cannot_modify_it():
    import ast
    source = (Path(__file__).resolve().parents[1] / 'app/services/moses_agent.py').read_text(encoding='utf-8')
    funcs = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)]
    tool = next(node for node in funcs if node.name == 'get_pds_van_stock_overview')
    code = ast.unparse(tool)
    assert "platform != 'pds'" in code
    assert 'pds_van_stock import overview' in code
    assert 'overview(request)' in code
    assert 'set_up_van' not in code
    assert 'movement(' not in code
    assert 'warehouse_shortages_truncated' in code
    registered = source.split('tools=(', 1)[1].split('    # Apply limits', 1)[0]
    assert registered.count('get_pds_van_stock_overview') == 1
    assert 'For van stock and parts restocking questions call get_pds_van_stock_overview' in source
