from __future__ import annotations

from backend.app.core.capabilities import CapabilityFlags, HardwareProfile
from backend.app.hardware.profiler import classify_device_class, derive_capability_flags


def test_classify_device_class_windows_constrained_path() -> None:
    device_class = classify_device_class(
        os_info={"os": "Windows", "arch": "AMD64"},
        mem_info={"memory_total_gb": 8.0},
        cuda_available=False,
        npu_info={"npu_vendor": None},
        battery_present=False,
    )
    assert device_class == "constrained"


def test_derive_capability_flags_returns_capability_flags() -> None:
    profile = HardwareProfile(
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
    )

    flags = derive_capability_flags(profile)
    assert isinstance(flags, CapabilityFlags)
    assert flags.stt_recommended_runtime == "faster-whisper"
    assert flags.stt_recommended_model == "whisper-large-v3-turbo"
