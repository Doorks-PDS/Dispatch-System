"""Van/completion integration remains present in the real PDS interface."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'static' / 'app.js').read_text(encoding='utf-8')

def test_completion_form_records_explicit_stock_only_after_saving():
    segment = JS[JS.index('async function openCompletionOrRecommendation('):]
    assert 'class="pds-parts-used-panel"' in segment
    assert 'cf_parts_matches' in segment
    assert 'cf_parts_other' in segment
    assert "savedForm = await apiAddCompletion(job.id, payload);" in segment
    assert segment.index('savedForm = await apiAddCompletion(job.id, payload);') < segment.index("fetchJSON('/pds-van-stock/completion-usage'")
    assert 'Quantities are checked against van stock' in segment
    assert 'vanUsage.labels.get(i.part_id)' in segment
    assert 'byPart.set(id,(byPart.get(id)||0)+amount)' in segment
    assert 'Van stock used:' in segment
    assert 'Some van stock was NOT deducted' in segment

def test_manual_movement_is_compact_and_can_transfer_to_another_van():
    assert "document.createElement('details');record.className='card'" in JS
    assert 'Van → Another Van' in JS
    assert "submit('/pds-van-stock/transfers'" in JS
    assert 'Stock already left warehouse' not in JS or 'not the warehouse again' in JS
