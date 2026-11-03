"""Regression tests for Doorks parts stock. Run: python -m pytest tests/test_doorks_stock_integration.py"""
from types import SimpleNamespace
from app.routers import doorks_operations as op


def test_zero_stock_part_is_retained(tmp_path, monkeypatch):
    from app.routers import workspaces as ws
    root = tmp_path / 'business_workspaces' / 'doorks'
    root.mkdir(parents=True)
    ws.save(root / 'inventory.json', [dict(id='a', part_number='CM-1', description='Camden part', quantity='0')])
    monkeypatch.setattr('app.routers.pds_purchase_orders._receive_events', lambda req, platform: [])
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))
    rows = op.stock_snapshot(req)['items']
    assert len(rows) == 1 and rows[0]['sku'] == 'CM-1' and rows[0]['on_hand'] == 0


def test_opening_receiving_and_adjustment(tmp_path, monkeypatch):
    from app.routers import workspaces as ws
    root = tmp_path / 'business_workspaces' / 'doorks'
    root.mkdir(parents=True)
    ws.save(root / 'inventory.json', [dict(id='a', part_number='SKU-9', description='Door part', quantity='2')])
    ws.save(root / 'stock_adjustments.json', [dict(sku='SKU-9', quantity_delta=-1)])
    monkeypatch.setattr('app.routers.pds_purchase_orders._receive_events', lambda req, platform: [dict(sku='sku-9', quantity=3, to_inventory=True)])
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))
    rows = op.stock_snapshot(req)['items']
    assert len(rows) == 1 and rows[0]['on_hand'] == 4
