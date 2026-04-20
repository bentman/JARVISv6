from __future__ import annotations

from backend.app.core.capabilities import BackendReadiness, CapabilityFlags, HardwareProfile
from backend.app.hardware.profiler import (
    _derive_backend_readiness,
    classify_device_class,
    derive_capability_flags,
    resolve_backend_evidence_tokens,
    run_profiler,
)


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


def test_backend_readiness_shape_is_separate_from_capability_flags(monkeypatch) -> None:
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

    monkeypatch.setattr(
        "backend.app.hardware.profiler.get_stt_device_readiness",
        lambda _p: {"cuda_ready": True, "cpu_ready": True, "selected_device": "cuda"},
    )
    monkeypatch.setattr(
        "backend.app.hardware.profiler.get_tts_device_readiness",
        lambda _p: {"cuda_ready": False, "cpu_ready": True, "selected_device": "cpu"},
    )

    readiness = _derive_backend_readiness(profile)
    assert isinstance(readiness, BackendReadiness)
    assert readiness.stt_selected_device == "cuda"
    assert readiness.tts_selected_device in {"cpu", "cuda"}
    assert readiness.llm_local_ready is False
    assert readiness.llm_service_ready is False
    assert readiness.llm_selected_runtime == "unavailable"


def test_run_profiler_overrides_recommended_device_from_readiness(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.hardware.profiler.detect_os", lambda: {"os": "Windows", "arch": "AMD64"})
    monkeypatch.setattr(
        "backend.app.hardware.profiler.detect_cpu",
        lambda: {
            "cpu_name": "unit-cpu",
            "cpu_physical_cores": 8,
            "cpu_logical_cores": 16,
            "cpu_max_freq_mhz": 3000.0,
        },
    )
    monkeypatch.setattr(
        "backend.app.hardware.profiler.detect_memory",
        lambda: {"memory_total_gb": 32.0, "memory_available_gb": 20.0},
    )
    monkeypatch.setattr(
        "backend.app.hardware.profiler.detect_gpu",
        lambda: {
            "gpu_available": True,
            "gpu_name": "NVIDIA",
            "gpu_vendor": "nvidia",
            "gpu_vram_gb": 12.0,
        },
    )
    monkeypatch.setattr("backend.app.hardware.profiler.detect_cuda", lambda: True)
    monkeypatch.setattr(
        "backend.app.hardware.profiler.detect_npu",
        lambda: {"npu_available": False, "npu_vendor": None, "npu_tops": None},
    )
    monkeypatch.setattr(
        "backend.app.hardware.profiler.get_stt_device_readiness",
        lambda _p: {"cuda_ready": False, "cpu_ready": True, "selected_device": "cpu"},
    )
    monkeypatch.setattr(
        "backend.app.hardware.profiler.get_tts_device_readiness",
        lambda _p: {"cuda_ready": False, "cpu_ready": True, "selected_device": "cpu"},
    )

    report = run_profiler()

    assert report.profile.cuda_available is True
    assert report.readiness.stt_selected_device == "cpu"
    assert report.flags.stt_recommended_device == "cpu"
    assert report.readiness.tts_selected_device == "cpu"
    assert report.flags.tts_recommended_device == "cpu"
    assert report.readiness.llm_local_ready is False
    assert report.readiness.llm_service_ready is False
    assert report.readiness.llm_selected_runtime == "unavailable"


def test_arm64_host_resolves_stt_recommendation_to_onnx_whisper_cpu() -> None:
    profile = HardwareProfile(
        os="Windows",
        arch="ARM64",
        cpu_name="unit-cpu",
        cpu_physical_cores=8,
        cpu_logical_cores=8,
        cpu_max_freq_mhz=3000.0,
        gpu_available=False,
        gpu_name=None,
        gpu_vendor=None,
        gpu_vram_gb=None,
        cuda_available=False,
        npu_available=False,
        npu_vendor=None,
        npu_tops=None,
        memory_total_gb=16.0,
        memory_available_gb=8.0,
        device_class="desktop",
        profile_id="arm64-unit",
    )

    flags = derive_capability_flags(profile)

    assert flags.stt_recommended_runtime == "onnx-whisper"
    assert flags.stt_recommended_model == "whisper-small-onnx"
    assert flags.stt_recommended_device == "cpu"


def test_arm64_host_resolves_tts_recommendation_to_onnx_kokoro_cpu() -> None:
    profile = HardwareProfile(
        os="Windows",
        arch="ARM64",
        cpu_name="unit-cpu",
        cpu_physical_cores=8,
        cpu_logical_cores=8,
        cpu_max_freq_mhz=3000.0,
        gpu_available=False,
        gpu_name=None,
        gpu_vendor=None,
        gpu_vram_gb=None,
        cuda_available=False,
        npu_available=False,
        npu_vendor=None,
        npu_tops=None,
        memory_total_gb=16.0,
        memory_available_gb=8.0,
        device_class="desktop",
        profile_id="arm64-unit",
    )

    flags = derive_capability_flags(profile)

    assert flags.tts_recommended_runtime == "onnx-kokoro"
    assert flags.tts_recommended_model == "kokoro-v1.0-onnx"
    assert flags.tts_recommended_device == "cpu"


def test_arm64_stt_evidence_tokens_do_not_include_cuda_dll_tokens() -> None:
    tokens = resolve_backend_evidence_tokens("stt", ["hw-cpu-base", "hw-arm64-base"])

    assert tokens == ["import:onnxruntime", "stt_runtime:onnx-whisper"]
    assert "dll:cublas64_12.dll" not in tokens
    assert "dll:cudnn64_9.dll" not in tokens


def test_arm64_tts_evidence_tokens_do_not_include_torch_cuda_token() -> None:
    tokens = resolve_backend_evidence_tokens("tts", ["hw-cpu-base", "hw-arm64-base"])

    assert tokens == ["import:kokoro_onnx", "tts_runtime:onnx-kokoro"]
    assert "torch_cuda:available" not in tokens


def test_x64_cuda_host_stt_recommendation_unchanged_regression() -> None:
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

    assert flags.stt_recommended_runtime == "faster-whisper"
    assert flags.stt_recommended_model == "whisper-large-v3-turbo"
    assert flags.stt_recommended_device == "cuda"


def test_x64_cuda_host_tts_recommendation_unchanged_regression() -> None:
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

    assert flags.tts_recommended_runtime == "kokoro"
    assert flags.tts_recommended_model == "kokoro-v1.0"
    assert flags.tts_recommended_device == "cuda"
