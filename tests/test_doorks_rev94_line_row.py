from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_shared_office_and_vendor_row():
 s=(ROOT/'static/doorks_shared_ticket.js').read_text()
 a=(ROOT/'static/app.js').read_text()
 assert 'function createDocumentLineRow(' in s
 assert 'rows.append(createDocumentLineRow(' in s
 assert "mode:'office'" in a and 'shared(item,idx,' in a
 assert 'await doorksLoadSharedTicket();' in a
