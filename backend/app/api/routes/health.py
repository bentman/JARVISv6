from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.dependencies import (
    is_startup_context_ready,
    get_startup_context_if_ready,
    get_startup_error,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    error = get_startup_error()
    if error:
        return {"status": "error", "error": error}

    if not is_startup_context_ready():
        return {"status": "starting"}

    context = get_startup_context_if_ready()
    if context is None:
        return {"status": "starting"}

    summary = context.summary
    return {
        "status": "ok",
        "profile_id": summary.profile_id,
        "stt_ready": summary.stt_ready,
        "tts_ready": summary.tts_ready,
        "llm_ready": summary.llm_ready,
    }
