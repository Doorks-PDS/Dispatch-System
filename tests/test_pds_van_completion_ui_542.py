"""Van/completion integration remains present in the real PDS interface."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'static' / 'app.js').read_text(encoding='utf-8')

def test_completion_form_records_explicit_stock_only_after_saving():
    segment = JS[JS.index('async function openCompletionOrRecommendation('):]
    assert 'Parts used from technician van (optional)' in segment
    assert "const savedForm = await apiAddCompletion(job.id, payload);" in segment
    assert segment.index('const savedForm = await apiAddCompletion(job.id, payload);') < segment.index("fetchJSON('/pds-van-stock/completion-usage'")
    assert 'Select a listed PDS part' in segment
    assert 'Some van stock was NOT deducted' in segment

def test_manual_movement_is_compact_and_can_transfer_to_another_van():
    assert "document.createElement('details');record.className='card'" in JS
    assert 'Van → Another Van' in JS
    assert "submit('/pds-van-stock/transfers'" in JS
    assert 'Stock already left warehouse' not in JS or 'not the warehouse again' in JS
