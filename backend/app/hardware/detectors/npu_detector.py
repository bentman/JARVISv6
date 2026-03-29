"""Slice 0.6 NPU detector."""

from __future__ import annotations

import platform
import subprocess


def _result(npu_available: bool, npu_vendor: str | None, npu_tops: float | None) -> dict[str, bool | str | float | None]:
    return {
        "npu_available": bool(npu_available),
        "npu_vendor": npu_vendor,
        "npu_tops": npu_tops,
    }


def _detect_apple_npu() -> dict[str, bool | str | float | None] | None:
    try:
        import torch  # type: ignore
    except ImportError:
        return None

    try:
        mps_available = bool(torch.backends.mps.is_available())
    except Exception:
        return None

    is_apple_silicon = (
        platform.system().lower() == "darwin"
        and platform.machine().lower() in {"arm64", "aarch64"}
    )
    if mps_available and is_apple_silicon:
        return _result(True, "apple", None)
    return None


def _detect_intel_npu() -> dict[str, bool | str | float | None] | None:
    try:
        import openvino as ov  # type: ignore
    except ImportError:
        ov = None  # type: ignore[assignment]

    if ov is not None:
        try:
            core = ov.Core()
            if any("NPU" in str(device).upper() for device in core.available_devices):
                return _result(True, "intel", 34.0)
        except Exception:
            pass

    try:
        import onnxruntime as ort  # type: ignore
    except ImportError:
        return None

    try:
        providers = [str(provider).lower() for provider in ort.get_available_providers()]
    except Exception:
        return None

    if any("openvino" in provider or "npu" in provider for provider in providers):
        return _result(True, "intel", 34.0)
    return None


def _detect_qualcomm_npu() -> dict[str, bool | str | float | None] | None:
    try:
        import qaic  # type: ignore  # noqa: F401

        return _result(True, "qualcomm", 45.0)
    except ImportError:
        pass

    try:
        hints = f"{platform.machine()} {platform.processor()}".lower()
    except Exception:
        return None

    if any(token in hints for token in ("qcom", "qualcomm", "snapdragon", "hexagon")):
        return _result(True, "qualcomm", 45.0)
    return None


def _detect_windows_npu_identity_fallback() -> dict[str, bool | str | float | None] | None:
    if platform.system() != "Windows":
        return None

    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_PnPEntity | Select-Object -ExpandProperty Name",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    names = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    include_tokens = ("npu", "neural processing", "ai accelerator", "hexagon npu", "vpu")
    exclude_tokens = ("audio", "usb", "hid")

    matched: list[str] = []
    for name in names:
        lower_name = name.lower()
        if any(token in lower_name for token in include_tokens) and not any(
            token in lower_name for token in exclude_tokens
        ):
            matched.append(lower_name)

    if not matched:
        return None

    if any("qualcomm" in name or "hexagon" in name or "snapdragon" in name for name in matched):
        return _result(True, "qualcomm", 45.0)
    if any("intel" in name for name in matched):
        return _result(True, "intel", 34.0)
    if any("apple" in name for name in matched):
        return _result(True, "apple", None)
    return _result(True, "unknown", None)


def detect_npu() -> dict[str, bool | str | float | None]:
    """Detect NPU availability, vendor, and TOPS when explicitly known."""

    for detector in (
        _detect_apple_npu,
        _detect_intel_npu,
        _detect_qualcomm_npu,
        _detect_windows_npu_identity_fallback,
    ):
        try:
            detected = detector()
        except Exception:
            detected = None
        if detected is not None:
            return detected

    return _result(False, None, None)
