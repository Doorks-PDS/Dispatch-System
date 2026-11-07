from pathlib import Path
S=Path(__file__).resolve().parents[1]/'static'
def test_shared_editor_exported():
    js=(S/'doorks_shared_ticket.js').read_text()
    assert 'function createTicketChangeRequest(' in js
    assert 'createTicketChangeRequest,createTicketFieldInput,createTicketEditPanel,registerOfficeControllers' in js
    assert "if(!['customer','vendor'].includes(role))" in js
    assert "typeof options.submit!=='function'" in js
def test_both_roles_use_shared_editor():
    html=(S/'doorks_home.html').read_text()
    assert "role:'customer',submit:payload=>api('accounts/work-orders/change-request'" in html
    assert "role:'vendor',submit:payload=>api('vendor-account/assignments/change-request'" in html
    assert 'window.DoorksSharedTicket.renderDocument(preview' in html
