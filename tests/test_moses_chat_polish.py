"""Regression checks for the accessible Moses assistant panel polish."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text()

def test_moses_keeps_accessible_composer_and_history():
    assert "history.setAttribute('role','log')" in APP
    assert "input.setAttribute('aria-label','Message Moses')" in APP
    assert "const compose=document.createElement('div')" in APP
    assert "compose.append(suggestions,composeLabel,input,voiceControls,composeRow)" in APP
    assert "moses-chat-shell[hidden]" in APP

def test_moses_new_chat_does_not_write_records_or_wipe_unsent_text():
    assert "newChat.textContent='New chat'" in APP
    assert "mosesTurns=[];mosesLastAction=null;history.replaceChildren();setMosesMode('idle');input.focus()" in APP
    assert "if(send.disabled)return" in APP
    assert "moses-chat-line[data-author=you]" in APP

def test_moses_samsung_voice_is_opt_in_and_does_not_autosend():
    assert "micButton.onclick=()=>" in APP
    assert "Dictation ready. Review and press Send to Moses." in APP
    assert "if(orb.dataset.mode==='listening')setMosesMode('idle')" in APP
    assert "@media(max-width:640px)" in APP
    assert "prefers-reduced-motion:reduce" in APP
