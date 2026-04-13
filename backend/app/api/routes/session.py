from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_session_service, get_startup_context


router = APIRouter(prefix="/session")


class TextTurnRequest(BaseModel):
    text: str


@router.post("/start")
def start_session() -> dict[str, object]:
    context = get_startup_context()
    service = get_session_service()
    service.start(context.report, context.personality, context.summary)
    state = service.state
    return {
        "session_id": state.session_id,
        "status": state.status,
    }


@router.post("/stop")
def stop_session() -> dict[str, object]:
    service = get_session_service()
    state_before = service.state
    service.stop()
    return {
        "session_id": state_before.session_id,
        "status": "stopped",
    }


@router.get("/state")
def get_state() -> dict[str, object]:
    state = get_session_service().state
    return {
        "status": state.status,
        "session_id": state.session_id,
        "turn_count": state.turn_count,
        "degraded_conditions": list(state.degraded_conditions),
        "last_response": state.last_response,
        "last_transcript": state.last_transcript,
    }


@router.post("/text")
def submit_text(request: TextTurnRequest) -> dict[str, bool]:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    service = get_session_service()
    if service.state.status in {"idle", "stopped"}:
        raise HTTPException(status_code=409, detail="session is not running")

    service.submit_text(request.text)
    return {"queued": True}
