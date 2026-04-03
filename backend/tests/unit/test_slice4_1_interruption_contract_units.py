from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.artifacts.turn_artifact import TurnArtifact
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import CapabilityFlags, FullCapabilityReport, HardwareProfile
from backend.app.personality.schema import PersonalityProfile
from backend.app.services.voice_service import VoiceTurnResult


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
    )


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_voice_turn_result_shape_and_defaults() -> None:
    default_result = VoiceTurnResult()
    assert default_result.response is None
    assert default_result.interrupted is False
    assert default_result.interrupted_at is None

    explicit_result = VoiceTurnResult(
        response="ok",
        interrupted=True,
        interrupted_at="2026-04-02T00:00:00+00:00",
    )
    assert explicit_result.response == "ok"
    assert explicit_result.interrupted is True
    assert explicit_result.interrupted_at == "2026-04-02T00:00:00+00:00"


def test_turn_artifact_interruption_fields_and_defaults() -> None:
    artifact = TurnArtifact(
        turn_id="turn-1",
        session_id="session-1",
        turn_index=0,
        input_modality="voice",
        transcript="hello",
        prompt_text="prompt",
        response_text="response",
        personality_profile_id="default",
        stt_model="whisper-base",
        llm_runtime="OllamaLLM",
        tts_runtime="kokoro",
        final_state="IDLE",
        failure_reason=None,
        started_at=_now(),
        responded_at=_now(),
        completed_at=_now(),
    )

    assert artifact.interrupted is False
    assert artifact.interrupted_at is None
    assert artifact.response_chars_spoken is None


def test_engine_legal_interruption_recovery_path() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.TRANSCRIBING)
    engine.transition(ConversationState.REASONING)
    engine.transition(ConversationState.RESPONDING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)
    engine.transition(ConversationState.LISTENING)
    assert engine.state == ConversationState.LISTENING


@pytest.mark.parametrize(
    "illegal_state",
    [
        ConversationState.IDLE,
        ConversationState.RESPONDING,
        ConversationState.SPEAKING,
        ConversationState.FAILED,
    ],
)
def test_engine_illegal_exits_from_interrupted(illegal_state: ConversationState) -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)

    with pytest.raises(RuntimeError, match="illegal transition INTERRUPTED"):
        engine.transition(illegal_state)


@pytest.mark.parametrize(
    "illegal_state",
    [
        ConversationState.IDLE,
        ConversationState.REASONING,
        ConversationState.SPEAKING,
        ConversationState.RESPONDING,
    ],
)
def test_engine_illegal_exits_from_recovering(illegal_state: ConversationState) -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)

    with pytest.raises(RuntimeError, match="illegal transition RECOVERING"):
        engine.transition(illegal_state)
