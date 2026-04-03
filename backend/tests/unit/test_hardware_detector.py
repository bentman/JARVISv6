from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.hardware.detectors.cpu_detector import detect_cpu
from backend.app.hardware.detectors.cuda_detector import detect_cuda, detect_cuda_via_providers
from backend.app.hardware.detectors.gpu_detector import detect_gpu
from backend.app.hardware.detectors.memory_detector import detect_memory
from backend.app.hardware.detectors.npu_detector import detect_npu
from backend.app.hardware.detectors.os_detector import detect_os
from backend.app.hardware import profiler


def test_os_detector_returns_expected_keys() -> None:
    result = detect_os()
    assert set(result.keys()) == {"os", "os_release", "arch"}


def test_cpu_detector_returns_expected_keys() -> None:
    result = detect_cpu()
    assert "cpu_name" in result
    assert "cpu_physical_cores" in result
    assert "cpu_logical_cores" in result
    assert "cpu_max_freq_mhz" in result


def test_gpu_detector_returns_expected_keys() -> None:
    result = detect_gpu()
    assert set(result.keys()) == {
        "gpu_available",
        "gpu_name",
        "gpu_vendor",
        "gpu_vram_gb",
        "gpu_vram_source",
    }


def test_cuda_detector_paths_are_callable() -> None:
    assert isinstance(detect_cuda(), bool)
    assert detect_cuda_via_providers(["CPUExecutionProvider"]) is False
    assert detect_cuda_via_providers(["CUDAExecutionProvider"]) is True


def test_npu_detector_returns_expected_keys() -> None:
    result = detect_npu()
    assert set(result.keys()) == {"npu_available", "npu_vendor", "npu_tops"}


def test_memory_detector_returns_expected_keys() -> None:
    result = detect_memory()
    assert set(result.keys()) == {
        "memory_total_gb",
        "memory_available_gb",
        "memory_percent_used",
    }


def test_profiler_run_is_unit_testable_with_monkeypatched_detectors(monkeypatch) -> None:
    monkeypatch.setattr(profiler, "detect_os", lambda: {"os": "Windows", "arch": "AMD64"})
    monkeypatch.setattr(
        profiler,
        "detect_cpu",
        lambda: {
            "cpu_name": "unit-cpu",
            "cpu_physical_cores": 8,
            "cpu_logical_cores": 16,
            "cpu_max_freq_mhz": 3000.0,
        },
    )
    monkeypatch.setattr(
        profiler,
        "detect_memory",
        lambda: {"memory_total_gb": 32.0, "memory_available_gb": 20.0},
    )
    monkeypatch.setattr(
        profiler,
        "detect_gpu",
        lambda: {
            "gpu_available": True,
            "gpu_name": "NVIDIA",
            "gpu_vendor": "nvidia",
            "gpu_vram_gb": 12.0,
            "gpu_vram_source": "nvml",
        },
    )
    monkeypatch.setattr(profiler, "detect_cuda", lambda: True)
    monkeypatch.setattr(
        profiler,
        "detect_npu",
        lambda: {"npu_available": False, "npu_vendor": None, "npu_tops": None},
    )

    report = profiler.run_profiler()
    assert isinstance(report, FullCapabilityReport)
    assert report.profile.profile_id == "nvidia-cuda-desktop-32gb"
