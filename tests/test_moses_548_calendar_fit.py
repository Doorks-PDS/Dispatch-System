from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_calendar_shows_all_that_fit_without_five_job_limit():
    app = (ROOT / 'static/app.js').read_text()
    css = (ROOT / 'static/style.css').read_text()
    assert 'dayJobs.forEach(j =>' in app
    assert 'dayJobs.slice(0, 5)' not in app
    assert 'const fitCalendarItems = () =>' in app
    assert 'Math.floor((available - markerHeight + gap) / rowSpace)' in app
    assert 'openDailySchedule(dt, dayJobs)' in app
    assert '.cal-item[hidden]{display:none!important;}' in css
    assert 'height:clamp(230px, 27vh, 300px)' in css
    assert '/static/style.css?v=__CSS_ASSET_VERSION__' in (ROOT / 'templates/ui.html').read_text()


def test_calendar_attachment_size_limit_enforced_before_loading_whole_file():
    calendar = (ROOT / 'app/routers/calendar.py').read_text()
    assert 'await f.read(MAX_CALENDAR_ATTACHMENT_BYTES + 1)' in calendar
    assert 'blobs = await _bounded_calendar_files(files)' in calendar
    assert 'except HTTPException:' in calendar
