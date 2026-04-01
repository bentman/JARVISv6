from __future__ import annotations

from backend.app.artifacts.storage import list_session_turns, read_turn_artifact
from backend.app.conversation.session_manager import SessionManager
from backend.app.hardware.profiler import run_profiler
from backend.app.memory.working import WorkingMemory
from backend.app.personality.loader import load_personality_profile
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM
from backend.app.services.turn_service import run_turn


def test_session_continuity_runtime() -> None:
    report = run_profiler()
    personality = load_personality_profile("default")

    assert OllamaLLM().is_available(), "[PREREQ FAILED] ollama unavailable"

    session = SessionManager.open_session()
    memory = WorkingMemory(max_turns=5)

    response1 = run_turn(
        report,
        personality,
        "My codename is JARVIS.",
        session=session,
        memory=memory,
        input_modality="text",
    )
    response2 = run_turn(
        report,
        personality,
        "What codename did I give you?",
        session=session,
        memory=memory,
        input_modality="text",
    )

    turn_ids = list_session_turns(session.session_id)
    artifact2 = read_turn_artifact(session.session_id, turn_ids[1])

    assert len(turn_ids) == 2
    assert session.turn_count == 2
    assert len(memory.get_context_turns()) == 2
    assert "My codename is JARVIS." in artifact2.prompt_text
    assert "What codename did I give you?" in artifact2.prompt_text
    assert isinstance(response1, str) and len(response1.strip()) > 0
    assert isinstance(response2, str) and len(response2.strip()) > 0
