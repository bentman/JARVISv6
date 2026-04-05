from __future__ import annotations

from datetime import datetime, timezone

from backend.app.artifacts.storage import (
    list_session_turns,
    read_turn_artifact,
    write_turn_artifact,
)
from backend.app.artifacts.turn_artifact import TurnArtifact
from backend.app.conversation.session_manager import SessionManager
from backend.app.core.capabilities import (
    BackendReadiness,
    CapabilityFlags,
    FullCapabilityReport,
    HardwareProfile,
)
from backend.app.memory.working import TurnSummary, WorkingMemory
from backend.app.memory.write_policy import evaluate_write_policy
from backend.app.personality.schema import PersonalityProfile
from backend.app.personality.loader import load_personality_profile
from backend.app.services import turn_service


def _report() -> FullCapabilityReport:
    return FullCapabilityReport(
        profile=HardwareProfile(
            os="Windows",
            arch="AMD64",
            cpu_name="unit-cpu",
            cpu_physical_cores=8,
            cpu_logical_cores=16,
            cpu_max_freq_mhz=3000.0,
            gpu_available=True,
            gpu_name="NVIDIA",
            gpu_vendor="nvidia",
            gpu_vram_gb=12.0,
            cuda_available=True,
            npu_available=False,
            npu_vendor=None,
            npu_tops=None,
            memory_total_gb=32.0,
            memory_available_gb=20.0,
            device_class="desktop",
            profile_id="nvidia-cuda-desktop-32gb",
        ),
        flags=CapabilityFlags(
            supports_local_llm=True,
            supports_gpu_llm=True,
            supports_cuda_llm=True,
            supports_local_stt=True,
            supports_local_tts=True,
            supports_wake_word=True,
            supports_realtime_voice=True,
            supports_desktop_shell=True,
            requires_degraded_mode=False,
            stt_recommended_runtime="faster-whisper",
            stt_recommended_model="whisper-large-v3-turbo",
        ),
        readiness=BackendReadiness(
            stt_cuda_ready=True,
            stt_cpu_ready=True,
            stt_selected_device="cpu",
            tts_cuda_ready=False,
            tts_cpu_ready=True,
            tts_selected_device="cpu",
            llm_local_ready=False,
            llm_service_ready=False,
            llm_selected_runtime="unavailable",
        ),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _personality() -> PersonalityProfile:
    return PersonalityProfile(
        profile_id="default",
        display_name="JARVIS",
        identity_summary="A direct, capable local assistant.",
        tone="neutral",
        brevity="concise",
        formality="professional",
        warmth="measured",
        assertiveness="moderate",
        humor_policy="none",
        response_style="direct",
        acknowledgment_style="minimal",
        interruption_style="stop-and-listen",
        voice_pacing="moderate",
        voice_energy="calm",
        safety_overrides=[],
        enabled=True,
    )


def test_session_open_produces_id(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = SessionManager.open_session()
    assert isinstance(session.session_id, str)
    assert session.session_id.strip() != ""


def test_session_increment_updates_turn_count(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = SessionManager.open_session()
    SessionManager.increment_turn(session)
    assert session.turn_count == 1


def test_session_close_sets_ended_at(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = SessionManager.open_session()
    SessionManager.close_session(session)
    assert session.ended_at is not None


def test_turn_artifact_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifact = TurnArtifact(
        turn_id="turn-1",
        session_id="session-1",
        turn_index=0,
        input_modality="text",
        transcript="remember this",
        prompt_text="prompt",
        response_text="response",
        personality_profile_id="default",
        stt_model=None,
        llm_runtime="OllamaLLM",
        tts_runtime=None,
        final_state="IDLE",
        failure_reason=None,
        started_at=_now(),
        responded_at=_now(),
        completed_at=_now(),
    )
    write_turn_artifact(artifact)
    loaded = read_turn_artifact("session-1", "turn-1")
    assert loaded.transcript == "remember this"


def test_list_session_turns_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert list_session_turns("missing-session") == []


def test_list_session_turns_chronological(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    write_turn_artifact(
        TurnArtifact(
            turn_id="b",
            session_id="session-order",
            turn_index=1,
            input_modality="text",
            transcript="t1",
            prompt_text="p1",
            response_text="r1",
            personality_profile_id="default",
            stt_model=None,
            llm_runtime="OllamaLLM",
            tts_runtime=None,
            final_state="IDLE",
            failure_reason=None,
            started_at=_now(),
            responded_at=_now(),
            completed_at=_now(),
        )
    )
    write_turn_artifact(
        TurnArtifact(
            turn_id="a",
            session_id="session-order",
            turn_index=0,
            input_modality="text",
            transcript="t0",
            prompt_text="p0",
            response_text="r0",
            personality_profile_id="default",
            stt_model=None,
            llm_runtime="OllamaLLM",
            tts_runtime=None,
            final_state="IDLE",
            failure_reason=None,
            started_at=_now(),
            responded_at=_now(),
            completed_at=_now(),
        )
    )

    assert list_session_turns("session-order") == ["a", "b"]


def test_working_memory_add_and_retrieve() -> None:
    memory = WorkingMemory(max_turns=5)
    memory.add_turn(TurnSummary(turn_index=0, transcript="u", response_text="a"))
    turns = memory.get_context_turns()
    assert len(turns) == 1
    assert turns[0].transcript == "u"


def test_working_memory_rolling_window() -> None:
    memory = WorkingMemory(max_turns=2)
    memory.add_turn(TurnSummary(turn_index=0, transcript="u0", response_text="a0"))
    memory.add_turn(TurnSummary(turn_index=1, transcript="u1", response_text="a1"))
    memory.add_turn(TurnSummary(turn_index=2, transcript="u2", response_text="a2"))
    turns = memory.get_context_turns()
    assert len(turns) == 2
    assert turns[0].transcript == "u1"
    assert turns[1].transcript == "u2"


def test_working_memory_clear() -> None:
    memory = WorkingMemory(max_turns=5)
    memory.add_turn(TurnSummary(turn_index=0, transcript="u", response_text="a"))
    memory.clear()
    assert memory.get_context_turns() == []


def test_write_policy_normal() -> None:
    decision = evaluate_write_policy("hello", "hi", "IDLE")
    assert decision.should_write is True


def test_write_policy_failed() -> None:
    decision = evaluate_write_policy("hello", "hi", "FAILED")
    assert decision.should_write is False


def test_write_policy_empty_transcript() -> None:
    decision = evaluate_write_policy("   ", "hi", "IDLE")
    assert decision.should_write is False


def test_write_policy_empty_response() -> None:
    decision = evaluate_write_policy("hello", "", "IDLE")
    assert decision.should_write is False


def test_prompt_assembler_without_context() -> None:
    personality = load_personality_profile("default")
    prompt = turn_service.assemble_prompt("hello", personality)
    assert "User turn:" in prompt
    assert "hello" in prompt


def test_prompt_assembler_with_context() -> None:
    personality = load_personality_profile("default")
    context = [TurnSummary(turn_index=0, transcript="My codename is JARVIS.", response_text="Understood.")]
    prompt = turn_service.assemble_prompt(
        "What codename did I give you?",
        personality,
        context_turns=context,
    )
    assert "[Prior turns:]" in prompt
    assert "My codename is JARVIS." in prompt
    assert "What codename did I give you?" in prompt


def test_run_turn_writes_artifact_and_updates_memory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = _report()
    personality = _personality()
    session = SessionManager.open_session()
    memory = WorkingMemory(max_turns=5)

    monkeypatch.setattr(turn_service, "select_llm_runtime", lambda: object())
    monkeypatch.setattr(turn_service, "get_response", lambda prompt, llm: "Unit response")

    response = turn_service.run_turn(
        report,
        personality,
        "My codename is JARVIS.",
        session=session,
        memory=memory,
        input_modality="text",
    )

    turn_ids = list_session_turns(session.session_id)
    assert isinstance(response, str)
    assert len(response.strip()) > 0
    assert session.turn_count == 1
    assert len(memory.get_context_turns()) == 1
    assert len(turn_ids) == 1


def test_run_turn_skips_memory_on_policy_reject(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = _report()
    personality = _personality()
    session = SessionManager.open_session()
    memory = WorkingMemory(max_turns=5)

    monkeypatch.setattr(turn_service, "select_llm_runtime", lambda: object())
    monkeypatch.setattr(turn_service, "get_response", lambda prompt, llm: "")

    try:
        turn_service.run_turn(
            report,
            personality,
            "My codename is JARVIS.",
            session=session,
            memory=memory,
            input_modality="text",
        )
    except RuntimeError:
        pass

    assert len(memory.get_context_turns()) == 0
    assert session.turn_count == 1
