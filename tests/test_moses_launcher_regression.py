"""Prevent a broken Moses launcher and unwanted PDS sidebar shortcut."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

def test_moses_command_center_mounts_in_actual_header_action_parent():
    assert "headerActions.insertBefore(commandBtn,close)" in APP
    assert "header.insertBefore(commandBtn,close)" not in APP

def test_moses_floating_bubble_is_main_entry_point():
    assert "launch.id='workspaceMosesBubble'" in APP
    assert "document.body.append(launch,panel)" in APP
    assert "navMosesShortcut" not in APP

def test_moses_chat_panel_has_accessible_close_and_composer():
    assert "close.setAttribute('aria-label','Close Moses')" in APP
    assert "input.setAttribute('aria-label','Message Moses')" in APP

def test_single_todo_navigation_is_after_all_jobs_before_door_records():
    assert "[navJobFlow,navAllJobs,navMyAssignments,navDoorLogs]" in APP
    assert "navMosesShortcut" not in APP
