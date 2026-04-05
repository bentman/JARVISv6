from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.hardware.profiler import run_profiler


def test_profiler_live_returns_expected_runtime_contract() -> None:
    report = run_profiler()

    assert isinstance(report, FullCapabilityReport)
    assert bool(report.profile.os)
    assert float(report.profile.memory_total_gb) > 0.0
    assert report.flags.stt_recommended_runtime in {
        "faster-whisper",
        "whisper.cpp",
        "openvino-whisper",
        "onnx-whisper",
        "cpu-whisper",
    }
    assert report.flags.stt_recommended_model in {
        "whisper-large-v3-turbo",
        "whisper-small",
        "whisper-base",
        "whisper-tiny",
    }
    assert hasattr(report, "readiness")
    assert report.readiness.stt_selected_device in {"cuda", "cpu", "unavailable"}
    assert report.readiness.tts_selected_device in {"cuda", "cpu", "unavailable"}
    assert isinstance(report.readiness.llm_local_ready, bool)
    assert isinstance(report.readiness.llm_service_ready, bool)
    assert report.readiness.llm_local_ready is False
    assert report.readiness.llm_service_ready is False
    assert report.readiness.llm_selected_runtime == "unavailable"
    assert isinstance(report.profile.cuda_available, bool)

    print("profile", report.profile)
    print("flags", report.flags)
    print("readiness", report.readiness)
