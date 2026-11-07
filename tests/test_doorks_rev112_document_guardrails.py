"""Rev112 document guardrails: executable JavaScript contract checks."""
import subprocess
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / 'static' / 'doorks_shared_ticket.js'


def test_vendor_document_rejects_unbounded_or_invalid_amounts():
    script = r'''
    global.window={};
    require(process.argv[1]);
    const d=window.DoorksSharedTicket;
    const base={assignmentId:'A1',documentType:'estimate',items:[{description:'Service',quantity:1,rate:175}]};
    const good=d.buildVendorDocumentSubmission(base);
    if(good.amount!==175)throw Error('Valid total changed');
    for(const line of [
      {description:'Bad',quantity:1,rate:Infinity},
      {description:'Bad',quantity:1,rate:1e12},
      {description:'Bad',quantity:1e12,rate:1},
      {description:'Bad',quantity:0,rate:10}
    ]){
      let rejected=false;
      try{d.buildVendorDocumentSubmission({...base,items:[line]})}catch(e){rejected=true}
      if(!rejected)throw Error('Unsafe vendor line accepted: '+JSON.stringify(line));
    }
    '''
    subprocess.run(['node', '-e', script, str(JS)], check=True, capture_output=True, text=True)
