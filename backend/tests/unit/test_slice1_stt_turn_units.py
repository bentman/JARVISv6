from __future__ import annotations

import sys
import types

import pytest

from backend.app.cognition.prompt_assembler import assemble_prompt
from backend.app.cognition.responder import get_response
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import CapabilityFlags, FullCapabilityReport, HardwareProfile
from backend.app.personality.loader import load_personality_profile
from backend.app.personality.schema import PersonalityProfile
from backend.app.routing import runtime_selector
from backend.app.runtimes.llm.base import LLMBase
from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT
from backend.app.models.catalog import get_model_entry


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
            supports_local_tts=False,
            supports_wake_word=False,
            supports_realtime_voice=True,
            supports_desktop_shell=True,
            requires_degraded_mode=False,
            stt_recommended_runtime="faster-whisper",
            stt_recommended_model="whisper-large-v3-turbo",
        ),
    )


def test_personality_schema_fields() -> None:
    p = _personality()
    assert p.profile_id == "default"
    assert p.enabled is True


def test_personality_loader_default() -> None:
    p = load_personality_profile("default")
    assert p.profile_id == "default"


def test_personality_loader_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_personality_profile("nonexistent")


def test_conversation_states_complete() -> None:
    expected = {
        "BOOTSTRAP",
        "PROFILING",
        "IDLE",
        "LISTENING",
        "TRANSCRIBING",
        "REASONING",
        "ACTING",
        "RESPONDING",
        "SPEAKING",
        "INTERRUPTED",
        "RECOVERING",
        "FAILED",
    }
    assert {s.name for s in ConversationState} == expected


def test_engine_transition() -> None:
    engine = ConversationEngine(_report(), _personality())
    engine.transition(ConversationState.LISTENING)
    assert engine.state == ConversationState.LISTENING


def test_engine_same_state_raises() -> None:
    engine = ConversationEngine(_report(), _personality())
    with pytest.raises(RuntimeError):
        engine.transition(ConversationState.IDLE)


def test_prompt_assembler_includes_transcript() -> None:
    prompt = assemble_prompt("hello world", _personality())
    assert "hello world" in prompt


def test_prompt_assembler_includes_personality() -> None:
    p = _personality()
    prompt = assemble_prompt("hello world", p)
    assert (p.identity_summary in prompt) or (p.tone in prompt)


class _EmptyLLM(LLMBase):
    def complete(self, prompt: str) -> str:
        return ""

    def is_available(self) -> bool:
        return True


def test_responder_empty_raises() -> None:
    with pytest.raises(RuntimeError):
        get_response("prompt", _EmptyLLM())


def test_llm_selector_prefers_llama_cpp(monkeypatch) -> None:
    class LlamaTrue:
        def is_available(self) -> bool:
            return True

    class OllamaUnused:
        def is_available(self) -> bool:
            return True

    monkeypatch.setattr(runtime_selector, "LlamaCppLLM", LlamaTrue)
    monkeypatch.setattr(runtime_selector, "OllamaLLM", OllamaUnused)

    selected = runtime_selector.select_llm_runtime()
    assert isinstance(selected, LlamaTrue)


def test_llm_selector_falls_through_to_ollama(monkeypatch) -> None:
    class LlamaFalse:
        def is_available(self) -> bool:
            return False

    class OllamaTrue:
        def is_available(self) -> bool:
            return True

    monkeypatch.setattr(runtime_selector, "LlamaCppLLM", LlamaFalse)
    monkeypatch.setattr(runtime_selector, "OllamaLLM", OllamaTrue)

    selected = runtime_selector.select_llm_runtime()
    assert isinstance(selected, OllamaTrue)


def test_llm_selector_raises_when_none_available(monkeypatch) -> None:
    class LlamaFalse:
        def is_available(self) -> bool:
            return False

    class OllamaFalse:
        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(runtime_selector, "LlamaCppLLM", LlamaFalse)
    monkeypatch.setattr(runtime_selector, "OllamaLLM", OllamaFalse)

    with pytest.raises(RuntimeError):
        runtime_selector.select_llm_runtime()


def test_stt_catalog_entry_resolution_for_recommended_model() -> None:
    model_name = _report().flags.stt_recommended_model
    entry = get_model_entry(model_name)
    assert entry["hf_repo_id"]
    assert entry["local_dir"].endswith(model_name)


def test_stt_ensure_model_integration_expectation_monkeypatched(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, str]] = []
    expected_dir = str(tmp_path / "models" / "stt" / "whisper-large-v3-turbo")

    def fake_get_model_entry(model_name: str):
        assert model_name == "whisper-large-v3-turbo"
        return {
            "hf_repo_id": "openai/whisper-large-v3-turbo",
            "local_dir": expected_dir,
        }

    def fake_ensure_model(hf_repo_id: str, local_dir: str) -> str:
        calls.append((hf_repo_id, local_dir))
        return local_dir

    class FakeWhisperModel:
        def __init__(self, model_path: str, device: str):
            self.model_path = model_path
            self.device = device

    monkeypatch.setattr(
        "backend.app.runtimes.stt.local_runtime.get_model_entry",
        fake_get_model_entry,
    )
    monkeypatch.setattr(
        "backend.app.runtimes.stt.local_runtime.ensure_model",
        fake_ensure_model,
    )
    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    stt = FasterWhisperSTT("whisper-large-v3-turbo", device="cpu")
    stt._ensure_model()

    assert calls == [("openai/whisper-large-v3-turbo", expected_dir)]


def test_stt_fail_closed_when_catalog_mapping_invalid(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "utterance.wav"
    audio.write_bytes(b"RIFF")

    def fake_get_model_entry(_model_name: str):
        return {"hf_repo_id": "openai/whisper-large-v3-turbo"}

    class FakeWhisperModel:
        def __init__(self, model_path: str, device: str):
            self.model_path = model_path
            self.device = device

        def transcribe(self, _path: str):
            return [], None

    monkeypatch.setattr(
        "backend.app.runtimes.stt.local_runtime.get_model_entry",
        fake_get_model_entry,
    )
    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    stt = FasterWhisperSTT("whisper-large-v3-turbo", device="cpu")
    with pytest.raises(RuntimeError, match="catalog missing local_dir"):
        stt.transcribe(str(audio))
