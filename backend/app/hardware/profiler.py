"""Slice 0.8 device-class classifier for hardware profiler assembly."""

from __future__ import annotations

import platform
import subprocess

import psutil

from backend.app.core.capabilities import CapabilityFlags, FullCapabilityReport, HardwareProfile
from backend.app.hardware.detectors.cpu_detector import detect_cpu
from backend.app.hardware.detectors.cuda_detector import detect_cuda
from backend.app.hardware.detectors.gpu_detector import detect_gpu
from backend.app.hardware.detectors.memory_detector import detect_memory
from backend.app.hardware.detectors.npu_detector import detect_npu
from backend.app.hardware.detectors.os_detector import detect_os


def _windows_battery_present() -> bool:
    """Return True when a battery is present on Windows hosts."""

    if platform.system() != "Windows":
        return False

    try:
        battery = psutil.sensors_battery()
    except Exception:
        return False

    if battery is None:
        return False

    # Guard against UPS telemetry being exposed as Win32_Battery on desktops.
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Battery | Select-Object -ExpandProperty Name",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode == 0:
            identity = (proc.stdout or "").lower()
            if any(token in identity for token in ("ups", "back-ups", "american power conversion", "apc")):
                return False
    except Exception:
        pass

    return True


def classify_device_class(
    os_info: dict[str, str],
    mem_info: dict[str, float],
    cuda_available: bool,
    npu_info: dict[str, str | float | bool | None],
    battery_present: bool | None = None,
) -> str:
    """Classify device as desktop/laptop/constrained using Slice 0.8 rules."""

    os_name = str(os_info.get("os") or "")
    arch = str(os_info.get("arch") or "")
    npu_vendor = str(npu_info.get("npu_vendor") or "").lower()

    try:
        memory_total_gb = float(mem_info.get("memory_total_gb", 0.0))
    except Exception:
        memory_total_gb = 0.0

    if os_name.lower() == "darwin" and arch.lower() in {"arm64", "aarch64"}:
        return "laptop"

    if npu_vendor == "qualcomm":
        return "laptop"

    battery = _windows_battery_present() if battery_present is None else bool(battery_present)
    if os_name.lower() == "windows" and battery:
        return "laptop"

    if memory_total_gb < 16.0 and not bool(cuda_available):
        return "constrained"

    return "desktop"


def _recommend_stt(profile: HardwareProfile, requires_degraded_mode: bool) -> tuple[str, str]:
    """Return Slice 0.9 STT runtime/model recommendation from profile inputs."""

    if requires_degraded_mode:
        return "faster-whisper", "whisper-tiny"

    if (
        (profile.gpu_vendor or "").lower() == "nvidia"
        and bool(profile.cuda_available)
        and profile.device_class == "desktop"
    ):
        return "faster-whisper", "whisper-large-v3-turbo"

    if profile.os == "Darwin" and profile.arch.upper() in {"ARM64", "AARCH64"}:
        return "whisper.cpp", "whisper-large-v3-turbo"

    if (profile.npu_vendor or "").lower() == "intel":
        return "openvino-whisper", "whisper-small"

    if (profile.npu_vendor or "").lower() == "qualcomm":
        return "onnx-whisper", "whisper-small"

    if not bool(profile.gpu_available):
        if float(profile.memory_total_gb) >= 16.0:
            return "faster-whisper", "whisper-small"
        return "faster-whisper", "whisper-base"

    return "faster-whisper", "whisper-small"


def derive_capability_flags(profile: HardwareProfile) -> CapabilityFlags:
    """Derive deterministic Slice 0.9 capability flags from HardwareProfile."""

    memory_total_gb = float(profile.memory_total_gb)
    memory_available_gb = float(profile.memory_available_gb)
    gpu_available = bool(profile.gpu_available)
    cuda_available = bool(profile.cuda_available)
    npu_available = bool(profile.npu_available)

    requires_degraded_mode = (memory_total_gb < 4.0) or (
        (not gpu_available) and (memory_total_gb < 8.0)
    )
    stt_runtime, stt_model = _recommend_stt(profile, requires_degraded_mode)

    # `profile.cuda_available` is currently a host-level CUDA/NVIDIA presence
    # signal. Runtime-specific CUDA usability must still be decided by each
    # backend stack (for example, CTranslate2 for STT or PyTorch for TTS).
    return CapabilityFlags(
        supports_local_llm=memory_total_gb >= 8.0,
        supports_gpu_llm=gpu_available,
        supports_cuda_llm=cuda_available,
        supports_local_stt=memory_total_gb >= 4.0,
        supports_local_tts=True,
        supports_wake_word=memory_available_gb >= 2.0,
        supports_realtime_voice=(cuda_available or npu_available or memory_total_gb >= 16.0),
        supports_desktop_shell=profile.os in {"Windows", "Darwin", "Linux"},
        requires_degraded_mode=requires_degraded_mode,
        stt_recommended_runtime=stt_runtime,
        stt_recommended_model=stt_model,
    )


def _build_profile(
    os_info: dict[str, str],
    cpu_info: dict[str, str | int | float],
    mem_info: dict[str, float],
    gpu_info: dict[str, bool | str | float | None],
    cuda_available: bool,
    npu_info: dict[str, bool | str | float | None],
    device_class: str,
) -> HardwareProfile:
    """Build HardwareProfile from detector outputs using normalized defaults."""

    def _optional_float(value: bool | str | float | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    gpu_vendor = gpu_info.get("gpu_vendor")
    memory_total_gb = float(mem_info.get("memory_total_gb", 0.0))
    profile_id = (
        f"{(gpu_vendor or 'cpu')}-"
        f"{'cuda' if bool(cuda_available) else 'nocuda'}-"
        f"{device_class}-{int(memory_total_gb)}gb"
    )

    return HardwareProfile(
        os=str(os_info.get("os") or "unknown"),
        arch=str(os_info.get("arch") or "unknown"),
        cpu_name=str(cpu_info.get("cpu_name") or "unknown"),
        cpu_physical_cores=int(cpu_info.get("cpu_physical_cores") or 1),
        cpu_logical_cores=int(cpu_info.get("cpu_logical_cores") or 1),
        cpu_max_freq_mhz=float(cpu_info.get("cpu_max_freq_mhz") or 0.0),
        gpu_available=bool(gpu_info.get("gpu_available")),
        gpu_name=(str(gpu_info.get("gpu_name")) if gpu_info.get("gpu_name") is not None else None),
        gpu_vendor=(str(gpu_vendor) if gpu_vendor is not None else None),
        gpu_vram_gb=_optional_float(gpu_info.get("gpu_vram_gb")),
        cuda_available=bool(cuda_available),
        npu_available=bool(npu_info.get("npu_available")),
        npu_vendor=(str(npu_info.get("npu_vendor")) if npu_info.get("npu_vendor") is not None else None),
        npu_tops=_optional_float(npu_info.get("npu_tops")),
        memory_total_gb=memory_total_gb,
        memory_available_gb=float(mem_info.get("memory_available_gb", 0.0)),
        device_class=device_class,
        profile_id=profile_id,
    )


def run_profiler() -> FullCapabilityReport:
    """Run Slice 0.10 hardware profiling and emit FullCapabilityReport."""

    os_info = detect_os()
    cpu_info = detect_cpu()
    mem_info = detect_memory()
    gpu_info = detect_gpu()
    # Host-level CUDA/NVIDIA presence only. Runtime stacks may still require
    # their own backend-specific availability checks before selecting CUDA.
    cuda_available = bool(detect_cuda())

    npu_info = detect_npu()
    device_class = classify_device_class(
        os_info=os_info,
        mem_info=mem_info,
        cuda_available=cuda_available,
        npu_info=npu_info,
    )

    profile = _build_profile(
        os_info=os_info,
        cpu_info=cpu_info,
        mem_info=mem_info,
        gpu_info=gpu_info,
        cuda_available=cuda_available,
        npu_info=npu_info,
        device_class=device_class,
    )
    flags = derive_capability_flags(profile)
    return FullCapabilityReport(profile=profile, flags=flags)
