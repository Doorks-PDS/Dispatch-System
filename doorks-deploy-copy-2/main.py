from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from contextvars import ContextVar

from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File, Query
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from starlette.responses import FileResponse

from app.services.atlas_chat import handle_chat
from app.services.storage import get_repo_data_dir, get_writable_data_dir

try:
    from app.services.forms_library import list_forms as _list_forms  # type: ignore
except Exception:
    _list_forms = None  # type: ignore

try:
    from app.services.forms_library import get_form_path as _get_form_path  # type: ignore
except Exception:
    _get_form_path = None  # type: ignore

from app.services.calendar_store import CalendarStore
from app.services.legacy_store import LegacyStore
from app.routers.calendar import router as calendar_router

from app.services.notifications_store import NotificationsStore
from app.routers.notifications import router as notifications_router

from app.services.timecards_store import TimeCardsStore
from app.routers.timecards import router as timecards_router

from app.services.employees_store import EmployeesStore
from app.routers.employees import router as employees_router

from app.services.documents_store import DocumentsStore
from app.routers.documents import router as documents_router

from app.services.crm_store import CRMStore
from app.routers.crm import router as crm_router

from app.services.timeoff_store import TimeOffStore
from app.routers.timeoff import router as timeoff_router

from app.routers.data import router as data_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.services.user_store import UsersStore


PROJECT_ROOT = Path(__file__).resolve().parent
REPO_DATA_DIR = get_repo_data_dir(PROJECT_ROOT)
DATA_DIR = get_writable_data_dir(PROJECT_ROOT)
FORMS_DIR = REPO_DATA_DIR / "forms"
UPLOADS_DIR = DATA_DIR / "uploads"
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FORMS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

TECH_KEYS = {os.getenv("DOORKS_TECH_KEY", "tech123")}
OFFICE_KEYS = {os.getenv("DOORKS_OFFICE_KEY", "office123")}
CURRENT_AUTH = ContextVar("doorks_current_auth", default=None)
SEED_ADMIN = {
    "username": "Jason Brewster",
    "name": "Jason Brewster",
    "email": "Jason@prioritydoors.com",
    "role": "office_admin",
    "password_hash": "pbkdf2_sha256$260000$9Ndx9ecZVvwzWHfsaoh6ng==$1ldgeJrA9FNeQeAvFgneKJbj2sk0cDmSEGFcu4IFCLQ=",
    "pin_hash": "pbkdf2_sha256$260000$wC6Oaof4bpcfdwZJg4vp5A==$f9CG0olKcfslD6xlTV6Tl2tbvDhaFLnO4TQMUfUH+3s=",
}


def _current_auth_role() -> Optional[str]:
    ctx = CURRENT_AUTH.get() or {}
    role = ctx.get("role") if isinstance(ctx, dict) else None
    return str(role) if role else None


def _current_auth_user() -> Optional[Dict[str, Any]]:
    ctx = CURRENT_AUTH.get() or {}
    user = ctx.get("user") if isinstance(ctx, dict) else None
    return user if isinstance(user, dict) else None


def require_key(x_api_key: Optional[str], request: Optional[Request] = None) -> str:
    role = None
    if request is not None:
        role = getattr(request.state, "auth_role", None)
        if not role:
            try:
                session = getattr(request, "session", {}) or {}
                user_id = str(session.get("user_id") or "").strip()
                if user_id:
                    raw = app.state.users_store.get_by_id(user_id)
                    if raw and raw.get("active", True):
                        role = str(raw.get("role") or "tech")
            except Exception:
                role = None
    if not role:
        role = _current_auth_role()
    if role:
        return role
    if x_api_key and x_api_key in OFFICE_KEYS:
        return "office_admin"
    if x_api_key and x_api_key in TECH_KEYS:
        return "tech"
    raise HTTPException(status_code=401, detail="Login required")


def list_forms(project_root: Path) -> List[Dict[str, Any]]:
    if _list_forms is not None:
        return _list_forms(str(project_root))
    out = []
    for p in sorted(FORMS_DIR.glob("*.pdf")):
        fid = p.stem.lower().replace(" ", "_").replace("-", "_")
        out.append(
            {
                "id": fid,
                "title": p.stem.replace("-", " "),
                "description": "",
                "tags": [],
                "download_url": f"/forms/download/{fid}",
            }
        )
    return out


def resolve_form_file(form_id: str) -> Tuple[Path, str]:
    if _get_form_path is not None:
        fp = _get_form_path(form_id, str(PROJECT_ROOT))
        p = Path(fp)
        if not p.exists():
            raise HTTPException(status_code=404, detail="Form not found")
        return p, p.name

    for c in FORMS_DIR.glob("*.pdf"):
        fid = c.stem.lower().replace(" ", "_").replace("-", "_")
        if fid == form_id.lower():
            return c, c.name
    raise HTTPException(status_code=404, detail="Form not found")


app = FastAPI(title="Doorks", version="6.7.0")

app.state.project_root = str(PROJECT_ROOT)
app.state.repo_data_dir = str(REPO_DATA_DIR)
app.state.data_dir = str(DATA_DIR)
app.state.require_key = require_key
app.state.calendar_store = CalendarStore(PROJECT_ROOT)
app.state.legacy_store = LegacyStore(PROJECT_ROOT)
app.state.notifications_store = NotificationsStore(PROJECT_ROOT)
app.state.timecards_store = TimeCardsStore(PROJECT_ROOT)
app.state.employees_store = EmployeesStore(PROJECT_ROOT)
app.state.documents_store = DocumentsStore(PROJECT_ROOT)
app.state.crm_store = CRMStore(PROJECT_ROOT)
app.state.timeoff_store = TimeOffStore(PROJECT_ROOT)
app.state.users_store = UsersStore(PROJECT_ROOT)
app.state.users_store.ensure_seed_user(**SEED_ADMIN)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(calendar_router)
app.include_router(data_router)
app.include_router(notifications_router)
app.include_router(timecards_router)
app.include_router(employees_router)
app.include_router(documents_router)
app.include_router(crm_router)
app.include_router(timeoff_router)
app.include_router(auth_router)
app.include_router(admin_router)


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = None
        role = None
        try:
            session = getattr(request, "session", {}) or {}
            user_id = str(session.get("user_id") or "").strip()
            if user_id:
                raw = request.app.state.users_store.get_by_id(user_id)
                if raw and raw.get("active", True):
                    user = {
                        "id": raw.get("id", ""),
                        "username": raw.get("username", ""),
                        "name": raw.get("name", ""),
                        "email": raw.get("email", ""),
                        "role": raw.get("role", "tech"),
                        "active": bool(raw.get("active", True)),
                    }
                    role = str(user.get("role") or "tech")
        except Exception:
            user = None
            role = None

        request.state.auth_user = user
        request.state.auth_role = role
        token = CURRENT_AUTH.set({"user": user, "role": role})
        try:
            response = await call_next(request)
        finally:
            CURRENT_AUTH.reset(token)
        return response


app.add_middleware(AuthContextMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("DOORKS_SESSION_SECRET", "doorks-local-dev-secret-jason-2026"),
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 12,
)


class ChatRequest(BaseModel):
    q: str
    mode: Optional[str] = None
    conversation_id: Optional[str] = None
    debug: Optional[bool] = False
    include_sources: Optional[bool] = False


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def ui(_: Request):
    template_path = TEMPLATES_DIR / "ui.html"
    if not template_path.exists():
        return HTMLResponse(content="UI template missing. Create templates/ui.html.", status_code=500)
    html = template_path.read_text(encoding="utf-8", errors="ignore")
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    html = html.replace("__GOOGLE_MAPS_API_KEY__", google_maps_api_key)
    return HTMLResponse(content=html)


@app.get("/forms")
def forms(_: Request, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key, request=_)
    return {"ok": True, "forms": list_forms(PROJECT_ROOT)}


@app.get("/forms/download/{form_id}")
def forms_download(_: Request, form_id: str, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key, request=_)
    fp, filename = resolve_form_file(form_id)
    return FileResponse(path=str(fp), media_type="application/pdf", filename=filename)


@app.post("/media/upload")
async def media_upload(
    x_api_key: Optional[str] = Header(default=None),
    files: List[UploadFile] = File(...),
):
    require_key(x_api_key)

    saved = []
    for f in files:
        name = (f.filename or "upload").replace("/", "_").replace("\\", "_")
        dest = UPLOADS_DIR / name
        content = await f.read()
        dest.write_bytes(content)
        saved.append({"filename": name, "bytes": len(content), "path": str(dest)})

    return {"ok": True, "files": saved}


@app.get("/parts/list")
def parts_list(
    q: str = Query(default=""),
    limit: int = Query(default=500, ge=1, le=5000),
    x_api_key: Optional[str] = Header(default=None),
):
    require_key(x_api_key)

    path = DATA_DIR / "parts_list.csv"
    if not path.exists():
        return {"ok": True, "items": []}

    items = []
    qn = (q or "").strip().lower()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {
                "Item": row.get("Item", ""),
                "Description": row.get("Description", ""),
                "Cost": row.get("Cost", ""),
                "Preferred Vendor": row.get("Preferred Vendor", ""),
                "Price": row.get("Price", ""),
            }
            hay = " ".join([str(item["Item"]), str(item["Description"]), str(item["Preferred Vendor"])]).lower()
            if qn and qn not in hay:
                continue
            items.append(item)
            if len(items) >= limit:
                break
    return {"ok": True, "items": items}


@app.post("/atlas/chat")
def atlas_chat(payload: ChatRequest, x_api_key: Optional[str] = Header(default=None)):
    role = require_key(x_api_key)
    mode = (payload.mode or "").strip().lower() or "tech"
    resp = handle_chat(
        q=payload.q,
        mode=mode,
        conversation_id=payload.conversation_id,
        requester_role=role,
        project_root=str(PROJECT_ROOT),
        debug=bool(payload.debug),
        include_sources=bool(payload.include_sources),
    )
    return JSONResponse(resp)


@app.get("/health")
def health():
    return {"ok": True, "service": "doorks", "version": "6.6.0"}
