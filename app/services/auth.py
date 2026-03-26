from fastapi import Header, HTTPException, status

# Simple API key store (later: move to env vars / DB)
ADMIN_KEY = "admin123"
TECH_KEY = "tech123"


def get_role_from_key(api_key: str) -> str | None:
    if api_key == ADMIN_KEY:
        return "admin"
    if api_key == TECH_KEY:
        return "tech"
    return None


def require_user_key(x_api_key: str = Header(None)):
    """
    Allows BOTH admin and tech.
    Use this for Atlas search and any general endpoints.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )

    role = get_role_from_key(x_api_key)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return {"role": role, "api_key": x_api_key}


def require_admin_key(x_api_key: str = Header(None)):
    """
    Allows ONLY admin.
    Use this for /admin/* routes.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )

    role = get_role_from_key(x_api_key)
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key required",
        )

    return {"role": role, "api_key": x_api_key}

