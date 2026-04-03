from __future__ import annotations

from datetime import datetime, timezone

from backend.app.artifacts.storage import read_turn_artifact, write_turn_artifact
from backend.app.artifacts.turn_artifact import TurnArtifact
from backend.app.conversation.session_manager import Session
from backend.app.core.capabilities import CapabilityFlags, FullCapabilityReport, HardwareProfile
from backend.app.personality.schema import PersonalityProfile
from backend.app.services import voice_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            supports_wake_word=False,
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


def test_run_voice_turn_interrupted_updates_artifact(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)

    class _FakeSTT:
        def transcribe(self, _audio_path: str) -> str:
            return "test transcript"

    class _FakeTTS:
        def synthesize(self, _text: str, output_path: str) -> str:
            return output_path

    detector_state = {"stopped": False}

    class _FakeDetector:
        failed = False
        failure_reason = None

        def __init__(self, _interrupt_flag) -> None:
            pass

        def start(self) -> None:
            return None

        def stop(self) -> None:
            detector_state["stopped"] = True

    session = Session(session_id="slice4-4-session", started_at=_now_iso(), ended_at=None, turn_count=0)

    def _run_turn_stub(report, personality, transcript, *, session=None, memory=None, input_modality="voice") -> str:
        assert session is not None
        artifact = TurnArtifact(
            turn_id="turn-0001",
            session_id=session.session_id,
            turn_index=session.turn_count,
            input_modality=input_modality,
            transcript=transcript,
            prompt_text="prompt",
            response_text="unit response",
            personality_profile_id=personality.profile_id,
            stt_model=None,
            llm_runtime="UnitLLM",
            tts_runtime=None,
            final_state="IDLE",
            failure_reason=None,
            started_at=_now_iso(),
            responded_at=_now_iso(),
            completed_at=_now_iso(),
        )
        write_turn_artifact(artifact)
        return "unit response"

    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: _FakeSTT())
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: _FakeTTS())
    monkeypatch.setattr(voice_service, "run_turn", _run_turn_stub)
    monkeypatch.setattr(voice_service, "BargeInDetector", _FakeDetector)
    monkeypatch.setattr(voice_service, "play_audio_interruptible", lambda _audio_path, _interrupt_flag: False)
    monkeypatch.setattr(voice_service.sd, "stop", lambda: None)

    result = voice_service.run_voice_turn(_report(), _personality(), session=session)

    assert result.response is None
    assert result.interrupted is True
    assert result.interrupted_at is not None
    assert detector_state["stopped"] is True

    artifact = read_turn_artifact(session.session_id, "turn-0001")
    assert artifact.interrupted is True
    assert artifact.interrupted_at == result.interrupted_at
    assert artifact.final_state == "INTERRUPTED"


def test_run_voice_turn_non_interrupted_returns_normal_contract(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)

    class _FakeSTT:
        def transcribe(self, _audio_path: str) -> str:
            return "test transcript"

    class _FakeTTS:
        def synthesize(self, _text: str, output_path: str) -> str:
            return output_path

    class _FakeDetector:
        failed = False
        failure_reason = None

        def __init__(self, _interrupt_flag) -> None:
            pass

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: _FakeSTT())
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: _FakeTTS())
    monkeypatch.setattr(
        voice_service,
        "run_turn",
        lambda report, personality, transcript, *, session=None, memory=None, input_modality="voice": "unit response",
    )
    monkeypatch.setattr(voice_service, "BargeInDetector", _FakeDetector)
    monkeypatch.setattr(voice_service, "play_audio_interruptible", lambda _audio_path, _interrupt_flag: True)
    monkeypatch.setattr(voice_service.sd, "stop", lambda: None)

    result = voice_service.run_voice_turn(_report(), _personality())

    assert result.response == "unit response"
    assert result.interrupted is False
    assert result.interrupted_at is None
