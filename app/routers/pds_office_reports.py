"""Secondary PIN for sensitive PDS payroll and roll-up views.

The PIN is a supplement to employee-role permissions, not a replacement.
Do not put the PIN in the JS bundle or print it to logs.
"""
from __future__ import annotations

import hmac
import os
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/pds-office-reports", tags=["pds-office-reports"])

class PinInput(BaseModel):
    pin: str

def _office(request: Request) -> str:
    account = getattr(request.state, "auth_user", None)
    role = getattr(request.state, "auth_role", None)
    if not isinstance(account, dict) or role not in ("office", "office_admin"):
        raise HTTPException(403, "Office access required")
    if request.session.get("active_platform", "pds") not in (None, "pds"):
        raise HTTPException(403, "PDS workspace required")
    uid = str(account.get("id") or "")
    if not uid:
        raise HTTPException(401, "Employee sign-in required")
    return uid

@router.get("/access")
def access(request: Request):
    uid = _office(request)
    return {"unlocked": hmac.compare_digest(str(request.session.get("pds_office_report_user") or ""), uid)}

@router.post("/unlock")
def unlock(payload: PinInput, request: Request):
    uid = _office(request)
    now = int(time.time())
    block_until = int(request.session.get("pds_office_report_block_until") or 0)
    if block_until > now:
        raise HTTPException(429, "Too many attempts. Try again later.")
    expected = os.getenv("PDS_OFFICE_REPORT_PIN", "2005")
    if not hmac.compare_digest(payload.pin, expected):
        attempts = int(request.session.get("pds_office_report_failures") or 0) + 1
        request.session["pds_office_report_failures"] = attempts
        if attempts >= 5:
            request.session["pds_office_report_block_until"] = now + 300
            request.session["pds_office_report_failures"] = 0
        raise HTTPException(403, "Incorrect PIN")
    request.session["pds_office_report_user"] = uid
    request.session.pop("pds_office_report_failures", None)
    request.session.pop("pds_office_report_block_until", None)
    return {"unlocked": True}

@router.post("/lock")
def lock(request: Request):
    _office(request)
    request.session.pop("pds_office_report_user", None)
    return {"unlocked": False}
