"""Moses 5.94: SDC unified sales view understands PDS checkout stages and shipments.

The SDC page is an internal front end; existing PDS order access, paid-only
fulfillment and Stripe signature tests remain in test_pds_parts_store_592.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unified_sales_reports_checkout_and_shipping_statuses():
    html = (ROOT / 'static/sdc_sales_reports.html').read_text(encoding='utf-8')
    assert '<h1>Sales &amp; Reports</h1>' in html
    assert '<iframe' not in html.lower()  # preserve the single unified table
    for item in ('/api/software/inquiries', '/api/saddleback/door-quotes',
                 '/pds-parts/api/sdc/orders', 'editTracking', 'editCarrier', 'editEta',
                 'partsSummary', 'partsPayment', 'partsFulfill', 'partsShipping',
                 'partsCompleted', 'checkout_pending', 'checkout_uncertain',
                 'supplier_ordered', 'paid_at', 'test_mode', 'tracking', 'shipping_address',
                 'total_cents', 'paymentLabel', 'nextAction'):
        assert item in html, item
    assert 'PAYMENT UNCONFIRMED — do not fulfill' in html
    assert "'PAID IN SANDBOX — test only'" in html
    assert 'select.disabled=blocked' in html
    assert "$('save').disabled=blocked" in html


def test_sales_export_protects_csv_and_contains_order_fields():
    html = (ROOT / 'static/sdc_sales_reports.html').read_text(encoding='utf-8')
    assert 'formulaSafe(value)' in html
    for col in ('Payment', 'Subtotal cents', 'Shipping cents', 'Tax cents',
                'Total cents', 'Carrier', 'Tracking', 'Test mode'):
        assert "'" + col + "'" in html
    assert "sdc-sales-reports.csv" in html
