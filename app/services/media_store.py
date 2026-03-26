# app/services/media_store.py

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, Any

UPLOAD_DIR = Path("data/uploads/media")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_VIDEO = {"video/mp4", "video/quicktime", "video/webm"}
ALLOWED_DOC = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

def save_upload(filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
    ext = Path(filename).suffix.lower() or ""
    asset_id = str(uuid.uuid4())
    safe_name = f"{asset_id}{ext}"
    path = UPLOAD_DIR / safe_name

    with open(path, "wb") as f:
        f.write(data)

    return {
        "asset_id": asset_id,
        "filename": filename,
        "content_type": content_type,
        "path": str(path),
        "bytes": len(data),
    }

def is_allowed(content_type: str) -> bool:
    ct = (content_type or "").lower().strip()
    return (ct in ALLOWED_IMAGE) or (ct in ALLOWED_VIDEO) or (ct in ALLOWED_DOC)
