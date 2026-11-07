from pathlib import Path

SHARED = Path(__file__).resolve().parents[1] / 'static' / 'doorks_shared_ticket.js'

def test_shared_ticket_editor_exists():
    src = SHARED.read_text()
    assert 'function createTicketEditPanel(host,options={})' in src
    assert 'createTicketEditPanel,registerOfficeControllers' in src

def test_ticket_editor_requires_authenticated_handler_and_reuses_inputs():
    src = SHARED.read_text()
    start = src.index('function createTicketEditPanel(')
    end = src.index('// Rev96: one role-configured', start)
    body = src[start:end]
    assert "typeof options.submit!=='function'" in body
    assert 'createTicketFieldInput(field,{role' in body
    assert 'await options.submit(values)' in body
