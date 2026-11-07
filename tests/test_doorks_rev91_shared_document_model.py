"""Revision 91 shared office/vendor document arithmetic contract."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_document_calculations_cover_office_and_vendor_fields():
    js = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    script = '''const vm=require('vm');const fs=require('fs');
const context={window:{},document:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const calc=context.window.DoorksSharedTicket.calculateDocumentTotals;
const result=calc([
{qty:2,rate:175,kind:'labor',taxable:false},
{quantity:3,rate:20,kind:'part',taxable:true},
{qty:1,rate:10,kind:'fuel',taxable:false},
{quantity:2,unit_price:15,kind:'parts',taxable:true}
],7.75);
process.stdout.write(JSON.stringify(result));'''
    result = subprocess.run(['node', '-e', script, str(ROOT / 'static/doorks_shared_ticket.js')], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    assert data['subtotal'] == 450
    assert data['taxableSubtotal'] == 90
    assert abs(data['tax'] - 6.975) < 0.00001
    assert data['categories']['labor'] == 350
    assert data['categories']['parts'] == 90
    assert data['categories']['fuel'] == 10


def test_office_builder_uses_shared_categories():
    js = (ROOT / 'static/app.js').read_text()
    assert 'totals?.categories' in js
    assert 'window.DoorksSharedTicket?.calculateDocumentTotals' in js
