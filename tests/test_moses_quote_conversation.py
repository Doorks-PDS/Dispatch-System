import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
try:
    from patch_chat import transform
except ImportError:
    transform = None


def load_helper():
    file=BASE/'app/services/moses_quote_conversation.py'
    spec=importlib.util.spec_from_file_location('moses_quote_conversation_test',file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def request(platform='pds',role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role),session={'active_platform':platform})


def agent(monkeypatch, enabled=True, answer='Ready', add_proposal=False, throw=False):
    # Match imported module path without a live model or network calls.
    m=SimpleNamespace(enabled=lambda platform: enabled)
    def invoke(req,message,history):
        assert message == 'prepare estimate for job 1026-73'
        if throw: raise ValueError('Provider uncertain')
        if add_proposal:req.state.moses_action_proposals.append({'id':'receipt'})
        return answer
    m.answer=invoke
    monkeypatch.setitem(sys.modules,'app.services.moses_agent',m)


def test_enabled_office_pds_agent(monkeypatch):
    agent(monkeypatch,add_proposal=True)
    result=load_helper().dispatch(request(),'prepare estimate for job 1026-73',[])
    assert result['answer']=='Ready' and result['agent_connected']
    assert result['action_proposals']==[{'id':'receipt'}]

@pytest.mark.parametrize('platform,role', [('sdc','office_admin'),('doorks','office_admin'),('pds','tech'),('pds','office')])
def test_workspace_and_role_boundaries(monkeypatch,platform,role):
    agent(monkeypatch)
    assert load_helper().dispatch(request(platform,role),'prepare estimate for job 1026-73',[]) is None


def test_disabled_agent_preserves_fallback(monkeypatch):
    agent(monkeypatch,enabled=False)
    assert load_helper().dispatch(request(),'prepare estimate for job 1026-73',[]) is None


def test_provider_error_never_claims_execution(monkeypatch):
    agent(monkeypatch,throw=True)
    result=load_helper().dispatch(request(),'prepare estimate for job 1026-73',[])
    assert result['agent_connected'] is False
    assert 'no completion is confirmed' in result['answer']


def test_inserts_after_queue_before_legacy_quote_fallback():
    if transform is None: pytest.skip("Installer transform tested outside application source")
    original='''def chat(request, text, history):
    if True:
        quote_request = True
        if False:
            return {'queue_cards': []}
        terms = []
        if quote_request:
            terms.append('test')
    return terms
'''
    updated=transform(original)
    assert updated.index('if False:') < updated.index('_quote_agent_dispatch') < updated.index('terms = []')
    assert 'if quote_request:' in updated
    with pytest.raises(RuntimeError):transform(updated)


def test_incompatible_router_refuses_edit():
    if transform is None: pytest.skip("Installer transform tested outside application source")
    with pytest.raises(RuntimeError):transform('def chat(): pass')
