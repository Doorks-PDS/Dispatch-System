"""PDS navigation order without replacing buttons, handlers or labels."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / 'static/app.js').read_text()


def test_pds_job_flow_sidebar_places_todo_before_all_jobs():
    assert 'if(pdsJobCol) [navJobFlow,navMyAssignments,navAllJobs,navDoorLogs].forEach' in APP
    assert 'if(pdsJobCol) [navJobFlow,navAllJobs,navMyAssignments,navDoorLogs].forEach' not in APP
    assert "navMyAssignments.innerHTML = '<span>To-Do List</span><small>My Scheduled Tasks</small>';" in APP
    assert 'btn.innerHTML = `<span>All Jobs</span><small>Current + Legacy</small>`;' in APP
