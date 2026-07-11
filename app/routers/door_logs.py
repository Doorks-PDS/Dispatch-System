from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/door-logs")
def list_logs(request: Request):
    return request.app.state.door_logs_store.load()


@router.post("/door-logs")
def create_log(data: dict, request: Request):
    return request.app.state.door_logs_store.create(data)


@router.put("/door-logs/{log_id}")
def update_log(log_id: str, data: dict, request: Request):
    try:
        return request.app.state.door_logs_store.update(log_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/door-logs/{log_id}/history")
def append_history(log_id: str, data: dict, request: Request):
    try:
        return request.app.state.door_logs_store.append_history(log_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/door-logs/{log_id}")
def delete_log(log_id: str, request: Request):
    request.app.state.door_logs_store.delete(log_id)
    return {"ok": True}
