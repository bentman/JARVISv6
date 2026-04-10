from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from backend.app.core.capabilities import (
    BackendReadiness,
    CapabilityFlags,
    FullCapabilityReport,
    HardwareProfile,
)
from backend.app.models.catalog import get_tts_model_entry
from backend.app.models.manager import verify_model
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.tts.local_runtime import KokoroTTSRuntime
from backend.app.runtimes.tts.playback import has_output_device, play_audio
from backend.app.runtimes.tts.tts_runtime import select_tts_runtime
from backend.app.services import voice_service


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
            tts_recommended_runtime="kokoro",
            tts_recommended_model="kokoro-v1.0",
            tts_recommended_device="cpu",
        ),
        readiness=BackendReadiness(
            stt_cuda_ready=True,
            stt_cpu_ready=True,
            stt_selected_device="cuda",
            tts_cuda_ready=False,
            tts_cpu_ready=True,
            tts_selected_device="cpu",
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


def test_tts_catalog_entry_resolution() -> None:
    entry = get_tts_model_entry("kokoro-v1.0")
    assert entry["hf_repo_id"]
    assert entry["local_dir"]
    assert entry["default_voice"]


def test_tts_catalog_missing_model_raises() -> None:
    with pytest.raises(KeyError):
        get_tts_model_entry("nonexistent")


def test_kokoro_tts_runtime_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=object))
    assert KokoroTTSRuntime().is_available() is True


def test_tts_runtime_selector_returns_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRuntime:
        def __init__(self, model_name: str, device: str = "cpu") -> None:
            self.model_name = model_name
            self.device = device

        def is_available(self) -> bool:
            return False

    monkeypatch.setattr("backend.app.runtimes.tts.tts_runtime.LocalTTSRuntime", FakeRuntime)
    assert select_tts_runtime(_report()) is None


def test_tts_runtime_selector_returns_instance_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRuntime:
        def __init__(self, model_name: str, device: str = "cpu") -> None:
            self.model_name = model_name
            self.device = device

        def is_available(self) -> bool:
            return True

    monkeypatch.setattr("backend.app.runtimes.tts.tts_runtime.LocalTTSRuntime", FakeRuntime)
    report = _report()
    report.flags.tts_recommended_device = "cpu"
    selected = select_tts_runtime(report)
    assert isinstance(selected, FakeRuntime)


def test_tts_runtime_selector_respects_cuda_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRuntime:
        def __init__(self, model_name: str, device: str = "cpu") -> None:
            self.model_name = model_name
            self.device = device

        def is_available(self) -> bool:
            return True

    monkeypatch.setattr("backend.app.runtimes.tts.tts_runtime.LocalTTSRuntime", FakeRuntime)
    report = _report()
    report.flags.tts_recommended_device = "cuda"
    selected = select_tts_runtime(report)
    assert isinstance(selected, FakeRuntime)
    assert selected.device == "cuda"


def test_tts_runtime_selector_returns_none_for_unavailable_recommended_device() -> None:
    report = _report()
    report.flags.tts_recommended_device = "unavailable"
    assert select_tts_runtime(report) is None


def test_play_audio_raises_on_missing_file() -> None:
    with pytest.raises(RuntimeError, match="not found"):
        play_audio("nonexistent.wav")


def test_has_output_device_returns_bool() -> None:
    assert isinstance(has_output_device(), bool)


def test_voice_service_degraded_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    class FakeEngine:
        last: "FakeEngine | None" = None

        def __init__(self, report: FullCapabilityReport, personality: PersonalityProfile) -> None:
            self.report = report
            self.personality = personality
            self.state = voice_service.ConversationState.IDLE
            self.transitions: list[str] = []
            FakeEngine.last = self

        def transition(self, new_state) -> None:
            self.state = new_state
            self.transitions.append(new_state.name)

    class FakeSTT:
        def transcribe(self, audio_path: str) -> str:
            return "test transcript"

    monkeypatch.setattr(voice_service, "ConversationEngine", FakeEngine)
    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: FakeSTT())
    monkeypatch.setattr(voice_service, "run_turn", lambda report, personality, transcript, session=None, memory=None, input_modality="voice": "unit response")
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: None)

    result = voice_service.run_voice_turn(_report(), _personality())
    response = result.response
    output = capsys.readouterr().out

    assert isinstance(result, voice_service.VoiceTurnResult)
    assert result.interrupted is False
    assert result.interrupted_at is None
    assert isinstance(response, str)
    assert response.strip()
    assert "[DEGRADED] TTS unavailable — text response only" in output
    assert FakeEngine.last is not None
    assert FakeEngine.last.state.name == "IDLE"


def test_voice_service_speaking_state_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEngine:
        last: "FakeEngine | None" = None

        def __init__(self, report: FullCapabilityReport, personality: PersonalityProfile) -> None:
            self.report = report
            self.personality = personality
            self.state = voice_service.ConversationState.IDLE
            self.transitions: list[str] = []
            FakeEngine.last = self

        def transition(self, new_state) -> None:
            self.state = new_state
            self.transitions.append(new_state.name)

    class FakeSTT:
        def transcribe(self, audio_path: str) -> str:
            return "test transcript"

    class FakeTTS:
        def synthesize(self, text: str, output_path: str) -> str:
            return output_path

    monkeypatch.setattr(voice_service, "ConversationEngine", FakeEngine)
    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: FakeSTT())
    monkeypatch.setattr(voice_service, "run_turn", lambda report, personality, transcript, session=None, memory=None, input_modality="voice": "unit response")
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: FakeTTS())
    monkeypatch.setattr(voice_service, "BargeInDetector", lambda _flag: type("Detector", (), {"start": lambda self: None, "stop": lambda self: None, "failed": False, "failure_reason": None})())
    monkeypatch.setattr(voice_service, "play_audio_interruptible", lambda _audio_path, _interrupt_flag: True)
    monkeypatch.setattr(voice_service.sd, "stop", lambda: None)

    result = voice_service.run_voice_turn(_report(), _personality())
    response = result.response

    assert isinstance(result, voice_service.VoiceTurnResult)
    assert result.interrupted is False
    assert result.interrupted_at is None
    assert isinstance(response, str)
    assert response.strip()
    assert FakeEngine.last is not None
    assert "SPEAKING" in FakeEngine.last.transitions


def test_voice_service_acknowledgment_hook_invoked_before_run_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSTT:
        def transcribe(self, audio_path: str) -> str:
            return "test transcript"

    events: list[str] = []

    def _ack(*_args, **_kwargs) -> None:
        events.append("ack")

    def _run_turn(*_args, **_kwargs) -> str:
        events.append("run_turn")
        return "unit response"

    monkeypatch.setattr(voice_service, "capture_utterance", lambda output_path, duration_seconds: output_path)
    monkeypatch.setattr(voice_service, "select_stt_runtime", lambda report: FakeSTT())
    monkeypatch.setattr(voice_service, "play_acknowledgment_if_configured", _ack)
    monkeypatch.setattr(voice_service, "run_turn", _run_turn)
    monkeypatch.setattr(voice_service, "select_tts_runtime", lambda report: None)

    result = voice_service.run_voice_turn(_report(), _personality())

    assert isinstance(result, voice_service.VoiceTurnResult)
    assert events[:2] == ["ack", "run_turn"]


def test_verify_model_tts_family(tmp_path: Path) -> None:
    tts_dir = tmp_path / "tts-model"
    tts_dir.mkdir(parents=True, exist_ok=True)
    (tts_dir / "kokoro-v1_0.pth").write_bytes(b"weights")
    assert verify_model(str(tts_dir), family="tts") is True


def test_verify_model_stt_family_unchanged(tmp_path: Path) -> None:
    stt_dir = tmp_path / "stt-model"
    stt_dir.mkdir(parents=True, exist_ok=True)
    (stt_dir / "model.bin").write_bytes(b"bin")
    (stt_dir / "config.json").write_text("{}", encoding="utf-8")
    (stt_dir / "vocabulary.json").write_text("{}", encoding="utf-8")
    assert verify_model(str(stt_dir), family="stt") is True
