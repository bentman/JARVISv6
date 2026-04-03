from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from backend.app.artifacts.storage import read_turn_artifact, write_turn_artifact
from backend.app.artifacts.turn_artifact import TurnArtifact
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.session_manager import Session
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import CapabilityFlags, FullCapabilityReport, HardwareProfile
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.stt import barge_in
from backend.app.runtimes.stt.barge_in import BargeInDetector
from backend.app.runtimes.tts import playback
from backend.app.services import voice_service
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- 4.1 interruption contract + state semantics ----


def test_turn_artifact_interruption_fields_present() -> None:
    fields = TurnArtifact.__dataclass_fields__
    assert "interrupted" in fields
    assert "interrupted_at" in fields
    assert "response_chars_spoken" in fields


def test_turn_artifact_interruption_defaults() -> None:
    artifact = TurnArtifact(
        turn_id="turn-1",
        session_id="session-1",
        turn_index=0,
        input_modality="voice",
        transcript="hello",
        prompt_text="prompt",
        response_text="response",
        personality_profile_id="default",
        stt_model=None,
        llm_runtime="OllamaLLM",
        tts_runtime=None,
        final_state="IDLE",
        failure_reason=None,
        started_at=_now_iso(),
        responded_at=_now_iso(),
        completed_at=_now_iso(),
    )
    assert artifact.interrupted is False
    assert artifact.interrupted_at is None
    assert artifact.response_chars_spoken is None


def test_engine_speaking_to_interrupted_allowed() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.TRANSCRIBING)
    engine.transition(ConversationState.REASONING)
    engine.transition(ConversationState.RESPONDING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    assert engine.state == ConversationState.INTERRUPTED


def test_engine_interrupted_to_recovering_allowed() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)
    assert engine.state == ConversationState.RECOVERING


def test_engine_recovering_to_listening_allowed() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)
    engine.transition(ConversationState.LISTENING)
    assert engine.state == ConversationState.LISTENING


def test_engine_recovering_to_failed_allowed() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)
    engine.transition(ConversationState.FAILED)
    assert engine.state == ConversationState.FAILED


def test_engine_interrupted_to_idle_blocked() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    with pytest.raises(RuntimeError, match="illegal transition INTERRUPTED"):
        engine.transition(ConversationState.IDLE)


def test_engine_interrupted_to_responding_blocked() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    with pytest.raises(RuntimeError, match="illegal transition INTERRUPTED"):
        engine.transition(ConversationState.RESPONDING)


def test_engine_recovering_to_idle_blocked() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    engine.transition(ConversationState.SPEAKING)
    engine.transition(ConversationState.INTERRUPTED)
    engine.transition(ConversationState.RECOVERING)
    with pytest.raises(RuntimeError, match="illegal transition RECOVERING"):
        engine.transition(ConversationState.IDLE)


# ---- 4.2 barge-in detector ----


class _FakeInputStream:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def test_barge_in_detector_sets_flag_on_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict[str, _FakeInputStream] = {}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeInputStream(callback)
        holder["stream"] = stream
        return stream

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag, threshold=0.02, min_trigger_frames=2)
    detector.start()

    low_energy = np.zeros((1024, 1), dtype=np.float32)
    high_energy = np.full((1024, 1), 0.1, dtype=np.float32)

    holder["stream"].callback(low_energy, 1024, None, None)
    holder["stream"].callback(high_energy, 1024, None, None)
    assert flag.is_set() is False
    holder["stream"].callback(high_energy, 1024, None, None)
    assert flag.is_set() is True


def test_barge_in_detector_no_flag_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict[str, _FakeInputStream] = {}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeInputStream(callback)
        holder["stream"] = stream
        return stream

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag, threshold=0.5, min_trigger_frames=2)
    detector.start()

    below_threshold = np.full((1024, 1), 0.01, dtype=np.float32)
    holder["stream"].callback(below_threshold, 1024, None, None)
    holder["stream"].callback(below_threshold, 1024, None, None)
    holder["stream"].callback(below_threshold, 1024, None, None)
    assert flag.is_set() is False


def test_barge_in_detector_failed_on_stream_open_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _input_stream_factory(**kwargs):
        raise OSError("input unavailable")

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag)
    detector.start()

    assert detector.failed is True
    assert detector.failure_reason is not None
    assert "input unavailable" in detector.failure_reason
    assert flag.is_set() is False


def test_barge_in_detector_stop_does_not_call_sd_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict[str, _FakeInputStream] = {}
    sd_stop_called = {"called": False}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeInputStream(callback)
        holder["stream"] = stream
        return stream

    def _sd_stop() -> None:
        sd_stop_called["called"] = True

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)
    monkeypatch.setattr(barge_in.sd, "stop", _sd_stop)

    flag = threading.Event()
    detector = BargeInDetector(flag)
    detector.start()
    detector.stop()

    assert holder["stream"].stopped is True
    assert holder["stream"].closed is True
    assert sd_stop_called["called"] is False


# ---- 4.3 interruptible playback ----


class _StreamState:
    def __init__(self, active_sequence: list[bool]) -> None:
        self._sequence = list(active_sequence)

    @property
    def active(self) -> bool:
        if self._sequence:
            return self._sequence.pop(0)
        return False


def test_play_audio_interruptible_pre_set_flag_returns_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    stop_calls = {"count": 0}
    interrupt_flag = threading.Event()
    interrupt_flag.set()

    monkeypatch.setattr(playback, "has_output_device", lambda: True)
    monkeypatch.setattr(playback.sf, "read", lambda _path: (np.zeros((32, 1), dtype=np.float32), 16000))
    monkeypatch.setattr(playback.sd, "play", lambda data, rate: None)
    monkeypatch.setattr(playback.sd, "stop", lambda: stop_calls.__setitem__("count", stop_calls["count"] + 1))
    monkeypatch.setattr(playback.sd, "get_stream", lambda: _StreamState([True, False]))
    monkeypatch.setattr(playback.time, "sleep", lambda _seconds: None)

    result = playback.play_audio_interruptible(str(audio), interrupt_flag)

    assert result is False
    assert stop_calls["count"] >= 1


def test_play_audio_interruptible_interrupts_active_playback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    stop_calls = {"count": 0}
    sleep_calls = {"count": 0}
    interrupt_flag = threading.Event()

    monkeypatch.setattr(playback, "has_output_device", lambda: True)
    monkeypatch.setattr(playback.sf, "read", lambda _path: (np.zeros((32, 1), dtype=np.float32), 16000))
    monkeypatch.setattr(playback.sd, "play", lambda data, rate: None)
    monkeypatch.setattr(playback.sd, "stop", lambda: stop_calls.__setitem__("count", stop_calls["count"] + 1))
    monkeypatch.setattr(playback.sd, "get_stream", lambda: _StreamState([True, True, False]))

    def _sleep(_seconds: float) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] == 1:
            interrupt_flag.set()

    monkeypatch.setattr(playback.time, "sleep", _sleep)

    result = playback.play_audio_interruptible(str(audio), interrupt_flag)

    assert result is False
    assert stop_calls["count"] >= 1


def test_play_audio_interruptible_natural_completion_returns_true(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    stop_calls = {"count": 0}
    interrupt_flag = threading.Event()

    monkeypatch.setattr(playback, "has_output_device", lambda: True)
    monkeypatch.setattr(playback.sf, "read", lambda _path: (np.zeros((32, 1), dtype=np.float32), 16000))
    monkeypatch.setattr(playback.sd, "play", lambda data, rate: None)
    monkeypatch.setattr(playback.sd, "stop", lambda: stop_calls.__setitem__("count", stop_calls["count"] + 1))
    monkeypatch.setattr(playback.sd, "get_stream", lambda: _StreamState([False]))
    monkeypatch.setattr(playback.time, "sleep", lambda _seconds: None)

    result = playback.play_audio_interruptible(str(audio), interrupt_flag)

    assert result is True
    assert stop_calls["count"] >= 1


# ---- 4.4 voice orchestration ----


def test_voice_turn_result_interrupted_contract() -> None:
    result = VoiceTurnResult(response=None, interrupted=True, interrupted_at="2026-04-02T00:00:00+00:00")
    assert result.response is None
    assert result.interrupted is True
    assert result.interrupted_at == "2026-04-02T00:00:00+00:00"


def test_voice_service_interrupted_produces_correct_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    session = Session(session_id="slice4-5-session", started_at=_now_iso(), ended_at=None, turn_count=0)

    def _run_turn_stub(report, personality, transcript, *, session=None, memory=None, input_modality="voice") -> str:
        assert session is not None
        write_turn_artifact(
            TurnArtifact(
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
        )
        return "unit response"

    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: _FakeSTT())
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: _FakeTTS())
    monkeypatch.setattr(voice_service, "run_turn", _run_turn_stub)
    monkeypatch.setattr(voice_service, "BargeInDetector", _FakeDetector)
    monkeypatch.setattr(voice_service, "play_audio_interruptible", lambda _audio_path, _interrupt_flag: False)
    monkeypatch.setattr(voice_service.sd, "stop", lambda: None)

    result = voice_service.run_voice_turn(_report(), _personality(), session=session)

    assert result.interrupted is True
    assert result.response is None
    assert result.interrupted_at is not None
    artifact = read_turn_artifact(session.session_id, "turn-0001")
    assert artifact.interrupted is True
    assert artifact.interrupted_at == result.interrupted_at
    assert artifact.final_state == "INTERRUPTED"


def test_voice_service_detector_failure_degrades_to_blocking_play(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeSTT:
        def transcribe(self, _audio_path: str) -> str:
            return "test transcript"

    class _FakeTTS:
        def synthesize(self, _text: str, output_path: str) -> str:
            return output_path

    class _FailedDetector:
        failed = True
        failure_reason = "input unavailable"

        def __init__(self, _interrupt_flag) -> None:
            pass

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    play_audio_called = {"called": False}

    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: _FakeSTT())
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: _FakeTTS())
    monkeypatch.setattr(
        voice_service,
        "run_turn",
        lambda report, personality, transcript, *, session=None, memory=None, input_modality="voice": "unit response",
    )
    monkeypatch.setattr(voice_service, "BargeInDetector", _FailedDetector)
    monkeypatch.setattr(voice_service, "play_audio", lambda _audio_path: play_audio_called.__setitem__("called", True))

    result = voice_service.run_voice_turn(_report(), _personality())

    assert play_audio_called["called"] is True
    assert result.interrupted is False
    assert isinstance(result.response, str)
    assert result.response.strip()
