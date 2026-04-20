import os
from fastapi import Header, HTTPException
from typing import Optional


def require_tech_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("DOORKS_TECH_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="Server missing DOORKS_TECH_KEY env var")

    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized (missing/invalid x-api-key)")


def require_admin_key(x_admin_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("DOORKS_ADMIN_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="Server missing DOORKS_ADMIN_KEY env var")

    if not x_admin_key or x_admin_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized (missing/invalid x-admin-key)")

