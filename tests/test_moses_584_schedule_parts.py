"""Moses 5.84: personal schedule readability and one-box completion parts."""
from pathlib import Path
import json
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'static/app.js').read_text(encoding='utf-8')


def test_unified_parts_form_and_one_save_path():
    section = JS[JS.index('async function openCompletionOrRecommendation('):JS.index('function renderMyAssignments()')]
    assert 'id="cf_parts" type="search"' in section
    assert 'id="cf_parts_matches"' in section
    assert 'id="cf_parts_selected"' in section
    assert 'id="cf_parts_other"' in section
    assert 'Parts used from technician van (optional)' not in section
    assert "search.addEventListener('input',showMatches)" in section
    assert "const available=(partId)=>Number(currentVan()?.items?" in section
    assert 'amount>100000' in section
    assert 'quantity>available(id)' in section
    assert 'byPart.set(id,(byPart.get(id)||0)+amount)' in section
    assert 'payload.parts_used = ""' in section
    assert 'vanUsage.manualItems.length' in section
    assert 'Other parts used:' in section
    assert 'Van stock used:' in section
    assert 'savedForm = await apiAddCompletion(job.id, payload)' in section
    assert section.index('savedForm = await apiAddCompletion(job.id, payload)') < section.index("fetchJSON('/pds-van-stock/completion-usage'")


def test_no_unlisted_inventory_deduction_and_technician_change_protection():
    section = JS[JS.index('const addEntry=(part,freeText='):JS.index('const syncTimeOnsite =')]
    assert "if(van&&inVan>0)addEntry(part)" in section
    assert "else addEntry(null,formatPart(part))" in section
    assert "for(const entry of entries.filter(e=>e.part))" in section
    assert "entry.part=null" in section
    assert "if(entry.part){" in section
    assert "else manualItems.push(" in section
    assert 'available(id)' in section
    assert "loadFailed=true" in section


def test_week_cards_are_status_colored_with_clear_text_and_click_action():
    section = JS[JS.index('function renderMyAssignments()'):JS.index('function renderToDoListView()')]
    for token in ('pds-week-grid','pds-week-column','pds-todo-visit',
                  'pds-visit-time','pds-visit-customer','pds-visit-status',
                  "pdsScheduleStatusColor(job.status)","const full=await apiGetJob(job.id)"):
        assert token in section
    assert 'overflow-x:auto;width:100%' in section
    assert "column.dataset.today=String(iso===todayIso)" in section
    assert "const todayIso=[today.getFullYear()" in section


@pytest.mark.skipif(shutil.which('node') is None, reason='Node required')
def test_schedule_colors_cover_key_statuses_and_javascript_parses():
    result = subprocess.run(['node', '--check', str(ROOT/'static/app.js')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    source = re.search(r'  function pdsScheduleStatusColor\(status\)\{.*?\n  \}', JS, re.S)
    assert source
    program = source.group(0)+'\nconsole.log(JSON.stringify(["Dispatch","Scheduled","Quote","Parts on Order","Complete","Complete/Quote"].map(pdsScheduleStatusColor)));'
    colors = json.loads(subprocess.check_output(['node','-e',program],text=True))
    assert len(colors)==6 and len(set(colors))==6 and all(x.startswith('#') for x in colors)
