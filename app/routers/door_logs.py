from fastapi import APIRouter, Request
from uuid import uuid4

router = APIRouter()

@router.get("/door-logs")
def list_logs(request: Request):
    return request.app.state.door_logs_store.load()

@router.post("/door-logs")
def create_log(data: dict, request: Request):
    return request.app.state.door_logs_store.create(data)

@router.put("/door-logs/{log_id}")
def update_log(log_id: str, data: dict, request: Request):
    request.app.state.door_logs_store.update(log_id, data)
    return {"ok": True}

@router.delete("/door-logs/{log_id}")
def delete_log(log_id: str, request: Request):
    request.app.state.door_logs_store.delete(log_id)
    return {"ok": True}
