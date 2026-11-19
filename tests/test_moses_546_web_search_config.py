"""Moses internet access remains an explicit, read-only hosted-tool opt-in."""
from app.services import moses_agent


def test_moses_sdk_internet_research_explicitly_opted_in(monkeypatch):
    monkeypatch.delenv('DOORKS_MOSES_WEB_SEARCH_ENABLED', raising=False)
    disabled=moses_agent.readiness('pds')
    assert disabled['internet_research_requested'] is False
    assert disabled['internet_research_verified'] is False
    monkeypatch.setenv('DOORKS_MOSES_WEB_SEARCH_ENABLED','true')
    enabled=moses_agent.readiness('pds')
    assert enabled['internet_research_requested'] is True
    assert enabled['internet_research_verified'] is False  # configuration != live send/search test


def test_public_web_research_cannot_replace_business_action_approval():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[1]/'app/services/moses_agent.py').read_text()
    assert "WebSearchTool(search_context_size='medium')" in src
    assert 'hosted_web_tools' in src
    assert 'Actual external messages' in src
    assert 'require workspace' in src
    assert 'get_moses_action_receipt' in src
