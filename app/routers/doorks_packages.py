"""Package feature manifest. Shared backend, isolated tenant storage per deployment.
No billing or entitlement enforcement is implied by this manifest.
"""
from fastapi import APIRouter
router=APIRouter(prefix='/doorks-packages',tags=['doorks-packages'])
BASIC=['dashboard','work_orders','job_flow','scheduling','customers','contacts','employees','payroll','timecards','pto','overtime','approvals','documents']
PLATINUM=BASIC+['customer_portal','vendor_portal','public_inquiries','inventory','purchasing','advanced_reports']
PREMIUM=PLATINUM+['accounting','receivables','supplier_bills','reconciliation','moses_ai','ai_intake','document_automation']
PACKAGES={'basic':BASIC,'platinum':PLATINUM,'premium':PREMIUM,'personalized':PREMIUM+['custom_integrations','custom_forms','custom_branding']}
@router.get('/manifest')
def manifest():
    return {'packages':{key:{'features':value,'payroll_included':True} for key,value in PACKAGES.items()},'note':'Informational feature matrix only; not entitlement enforcement.'}
