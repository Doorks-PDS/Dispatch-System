from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def test_shared_registry_reuses_original_office_handlers():
    js = (ROOT/'static/doorks_shared_ticket.js').read_text()
    app = (ROOT/'static/app.js').read_text()
    assert 'officeControllerStatus' in js
    assert 'if(window.DoorksSharedTicket)return doorksRegisterOfficeControllers(window.DoorksSharedTicket)' in app
    assert "typeof renderJobDetails==='function'" in app
    assert "typeof openEstimateInvoiceDrawer==='function'" in app

def test_registry_dispatches_and_denies_roles():
    script = r'''
    global.window={};global.document={};
    require('./static/doorks_shared_ticket.js');
    const s=window.DoorksSharedTicket;
    let ticket=0,document=0;
    s.registerOfficeControllers({ticket:()=>++ticket,document:()=>++document});
    if(!s.officeControllerStatus().ticket||!s.officeControllerStatus().document)process.exit(1);
    s.openTicket({role:'office'});s.openDocument({role:'admin'});
    if(ticket!==1||document!==1)process.exit(2);
    for(const role of ['customer','unknown']){
      try{s.openDocument({role});process.exit(3)}catch(e){if(!/not permitted/.test(e.message))process.exit(4)}
    }
    '''
    result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
