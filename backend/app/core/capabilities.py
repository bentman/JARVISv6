"""Normalized capability schema surface for JARVISv6 Slice 0.1.

This module is the single source of truth for hardware capability typing used by
downstream systems. It intentionally contains schema/type definitions only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HardwareProfile:
    """Raw hardware detection output."""

    os: str
    arch: str
    cpu_name: str
    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_max_freq_mhz: float
    gpu_available: bool
    gpu_name: str | None
    gpu_vendor: str | None
    gpu_vram_gb: float | None
    cuda_available: bool
    npu_available: bool
    npu_vendor: str | None
    npu_tops: float | None
    memory_total_gb: float
    memory_available_gb: float
    device_class: str
    profile_id: str


@dataclass(slots=True)
class CapabilityFlags:
    """Derived capability decisions from a hardware profile."""

    supports_local_llm: bool
    supports_gpu_llm: bool
    supports_cuda_llm: bool
    supports_local_stt: bool
    supports_local_tts: bool
    supports_wake_word: bool
    supports_realtime_voice: bool
    supports_desktop_shell: bool
    requires_degraded_mode: bool
    stt_recommended_runtime: str = "faster-whisper"
    stt_recommended_model: str = "whisper-base"
    stt_recommended_device: str = "cpu"
    tts_recommended_runtime: str = "kokoro"
    tts_recommended_model: str = "kokoro-v1.0"
    tts_recommended_device: str = "cpu"


@dataclass(slots=True)
class BackendReadiness:
    """Verified backend-readiness snapshot kept separate from host capability facts."""

    stt_cuda_ready: bool = False
    stt_cpu_ready: bool = False
    stt_selected_device: str = "unavailable"
    tts_cuda_ready: bool = False
    tts_cpu_ready: bool = False
    tts_selected_device: str = "unavailable"
    llm_local_ready: bool = False
    llm_service_ready: bool = False
    llm_selected_runtime: str = "unavailable"


@dataclass(slots=True)
class FullCapabilityReport:
    """Top-level emitted capability report."""

    profile: HardwareProfile
    flags: CapabilityFlags
    readiness: BackendReadiness


__all__ = ["HardwareProfile", "CapabilityFlags", "BackendReadiness", "FullCapabilityReport"]