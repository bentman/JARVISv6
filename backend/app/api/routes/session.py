from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.artifacts.storage import list_session_turns, read_turn_artifact
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
    turns: list[dict[str, object]] = []
    if state.session_id:
        turn_ids = list_session_turns(state.session_id)
        for turn_id in turn_ids[-50:]:
            artifact = read_turn_artifact(state.session_id, turn_id)
            turns.append(
                {
                    "turn_id": artifact.turn_id,
                    "turn_index": artifact.turn_index,
                    "input_modality": artifact.input_modality,
                    "transcript": artifact.transcript,
                    "response_text": artifact.response_text,
                }
            )

    return {
        "status": state.status,
        "session_id": state.session_id,
        "wake_active": bool(getattr(state, "wake_active", False)),
        "turn_count": state.turn_count,
        "last_turn_id": state.last_turn_id,
        "degraded_conditions": list(state.degraded_conditions),
        "last_response": state.last_response,
        "last_transcript": state.last_transcript,
        "turns": turns,
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


@router.post("/ptt")
def push_to_talk() -> dict[str, bool]:
    service = get_session_service()
    if service.state.status in {"idle", "stopped"}:
        raise HTTPException(status_code=409, detail="session is not running")

    service.push_to_talk()
    return {"queued": True}
