from __future__ import annotations

from backend.app.core.capabilities import (
    BackendReadiness,
    CapabilityFlags,
    FullCapabilityReport,
    HardwareProfile,
)
from backend.app.personality.schema import PersonalityProfile
from backend.app.services import startup_service


def _report(*, stt_selected_device: str = "cpu", tts_selected_device: str = "cpu") -> FullCapabilityReport:
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
        ),
        readiness=BackendReadiness(
            stt_cuda_ready=stt_selected_device == "cuda",
            stt_cpu_ready=stt_selected_device == "cpu",
            stt_selected_device=stt_selected_device,
            tts_cuda_ready=tts_selected_device == "cuda",
            tts_cpu_ready=tts_selected_device == "cpu",
            tts_selected_device=tts_selected_device,
            llm_local_ready=False,
            llm_service_ready=False,
            llm_selected_runtime="unavailable",
        ),
    )


def _personality() -> PersonalityProfile:
    return PersonalityProfile(
        profile_id="default",
        display_name="J.A.R.V.I.S.",
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


def test_startup_summary_contract_fields_present() -> None:
    fields = startup_service.StartupSummary.__dataclass_fields__
    assert "profile_id" in fields
    assert "device_class" in fields
    assert "stt_ready" in fields
    assert "stt_selected_device" in fields
    assert "tts_ready" in fields
    assert "tts_selected_device" in fields
    assert "llm_ready" in fields
    assert "llm_runtime_name" in fields
    assert "personality_profile_id" in fields
    assert "personality_display_name" in fields
    assert "degraded_conditions" in fields
    assert "voice_name" not in fields


def test_run_startup_returns_summary_report_personality(monkeypatch) -> None:
    monkeypatch.setattr(startup_service, "run_profiler", lambda: _report())
    monkeypatch.setattr(startup_service, "load_personality_profile", lambda _name: _personality())

    class _ReadyOllama:
        def is_available(self) -> bool:
            return True

    monkeypatch.setattr(startup_service, "OllamaLLM", _ReadyOllama)

    summary, report, personality = startup_service.run_startup()

    assert isinstance(summary, startup_service.StartupSummary)
    assert isinstance(report, FullCapabilityReport)
    assert isinstance(personality, PersonalityProfile)
    assert summary.stt_ready is True
    assert summary.tts_ready is True
    assert summary.llm_ready is True
    assert summary.llm_runtime_name == "OllamaLLM"
    assert summary.degraded_conditions == []


def test_run_startup_degraded_conditions_for_unavailable_paths(monkeypatch) -> None:
    monkeypatch.setattr(
        startup_service,
        "run_profiler",
        lambda: _report(stt_selected_device="unavailable", tts_selected_device="unavailable"),
    )
    monkeypatch.setattr(startup_service, "load_personality_profile", lambda _name: _personality())

    class _UnavailableOllama:
        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(startup_service, "OllamaLLM", _UnavailableOllama)

    summary, _, _ = startup_service.run_startup()

    assert summary.stt_ready is False
    assert summary.tts_ready is False
    assert summary.llm_ready is False
    assert summary.llm_runtime_name == "unavailable"
    assert "STT unavailable (no ready selected device)" in summary.degraded_conditions
    assert "TTS unavailable (no ready selected device)" in summary.degraded_conditions
    assert "LLM service unavailable (Ollama not reachable)" in summary.degraded_conditions


def test_print_startup_summary_renders_without_voice_fields(capsys) -> None:
    summary = startup_service.StartupSummary(
        profile_id="nvidia-cuda-desktop-32gb",
        device_class="desktop",
        stt_ready=True,
        stt_selected_device="cuda",
        tts_ready=True,
        tts_selected_device="cpu",
        llm_ready=False,
        llm_runtime_name="unavailable",
        personality_profile_id="default",
        personality_display_name="J.A.R.V.I.S.",
        degraded_conditions=["LLM service unavailable (Ollama not reachable)"],
    )

    startup_service.print_startup_summary(summary)
    captured = capsys.readouterr().out

    assert "Profile:" in captured
    assert "Personality:" in captured
    assert "DEGRADED:" in captured
    assert "voice:" not in captured.lower()
