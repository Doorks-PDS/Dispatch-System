from fastapi import APIRouter, HTTPException
from app.services.trick_store import (
    load_pending,
    load_approved,
    approve_trick
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/pending")
def get_pending_tricks():
    """
    View all pending tricks awaiting approval
    """
    return {
        "count": len(load_pending()),
        "pending": load_pending()
    }


@router.get("/approved")
def get_approved_tricks():
    """
    View all approved tricks
    """
    return {
        "count": len(load_approved()),
        "approved": load_approved()
    }


@router.post("/approve")
def approve_pending_trick(query: str):
    """
    Approve a pending trick by its query text
    """
    pending = load_pending()
    if not any(t.get("query") == query for t in pending):
        raise HTTPException(status_code=404, detail="Pending trick not found")

    approve_trick(query)

    return {
        "status": "approved",
        "query": query
    }

