"""Doorks 2.0 platform selection foundation.

This phase intentionally does not expose PDS business endpoints under another
platform. The Doorks and SDC workspaces are non-data placeholders until their
stores and API permissions have been separated.
"""
import hmac
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/platforms", tags=["platforms"])
PLATFORMS = ("pds", "doorks", "sdc")

class Selection(BaseModel):
    platform: str
    pin: str = ""

def _admin(request: Request):
    user = getattr(request.state, "auth_user", None)
    if not user or str(getattr(request.state, "auth_role", "")) != "office_admin":
        raise HTTPException(403, "Only Office Admin can switch platforms")

@router.get("/current")
def current(request: Request):
    user = getattr(request.state, "auth_user", None)
    if not user:
        raise HTTPException(401, "Login required")
    admin = getattr(request.state, "auth_role", "") == "office_admin"
    platform = str(request.session.get("active_platform") or "pds") if admin else "pds"
    if platform not in PLATFORMS: platform = "pds"
    return {"platform": platform, "can_switch": admin, "available": list(PLATFORMS) if admin else ["pds"]}

@router.post("/switch")
def switch(request: Request, payload: Selection):
    _admin(request)
    target = payload.platform.lower().strip()
    if target not in PLATFORMS: raise HTTPException(400, "Unknown platform")
    if target != "pds":
        env_name = "DOORKS_PLATFORM_PIN" if target == "doorks" else "SDC_PLATFORM_PIN"
        expected = os.getenv(env_name, "0803" if target == "doorks" else "0404")
        if not hmac.compare_digest(payload.pin, expected):
            raise HTTPException(403, "Incorrect platform PIN")
    request.session["active_platform"] = target
    return {"platform": target, "can_switch": True}
