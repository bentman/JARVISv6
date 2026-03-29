"""Slice 0.4 vendor-specific GPU detector."""

from __future__ import annotations

import platform
import subprocess
from typing import Any


def _build_result(
    gpu_available: bool,
    gpu_name: str | None,
    gpu_vendor: str | None,
    gpu_vram_gb: float | None,
    gpu_vram_source: str | None,
) -> dict[str, bool | str | float | None]:
    return {
        "gpu_available": bool(gpu_available),
        "gpu_name": gpu_name,
        "gpu_vendor": gpu_vendor,
        "gpu_vram_gb": gpu_vram_gb,
        "gpu_vram_source": gpu_vram_source,
    }


def _no_gpu_result() -> dict[str, bool | str | float | None]:
    return _build_result(False, None, None, None, None)


def _run_command(command: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    output = (proc.stdout or "").strip()
    return output or None


def _nvidia_adapter() -> dict[str, bool | str | float | None] | None:
    try:
        import pynvml  # type: ignore
    except ImportError:
        pynvml = None  # type: ignore[assignment]

    if pynvml is not None:
        try:
            pynvml.nvmlInit()
            try:
                device_count = int(pynvml.nvmlDeviceGetCount())
                if device_count < 1:
                    return None
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(raw_name, bytes):
                    gpu_name = raw_name.decode("utf-8", errors="ignore")
                else:
                    gpu_name = str(raw_name)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_vram_gb = round(float(mem_info.total) / (1024**3), 2)
                return _build_result(True, gpu_name or None, "nvidia", gpu_vram_gb, "nvml")
            finally:
                try:
                    pynvml.nvmlShutdown()
                except Exception:
                    pass
        except Exception:
            pass

    smi_output = _run_command(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
    )
    if smi_output:
        first = smi_output.splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        gpu_name = parts[0] if parts else None
        gpu_vram_gb = None
        if len(parts) > 1:
            try:
                gpu_vram_gb = round(float(parts[1]) / 1024.0, 2)
            except Exception:
                gpu_vram_gb = None
        return _build_result(True, gpu_name, "nvidia", gpu_vram_gb, "nvidia-smi")

    try:
        import torch  # type: ignore
    except ImportError:
        torch = None  # type: ignore[assignment]

    if torch is not None:
        try:
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                total_memory = getattr(props, "total_memory", None)
                gpu_vram_gb = (
                    round(float(total_memory) / (1024**3), 2)
                    if total_memory is not None
                    else None
                )
                return _build_result(True, gpu_name or None, "nvidia", gpu_vram_gb, "torch-cuda")
        except Exception:
            pass

    return None


def _intel_adapter() -> dict[str, bool | str | float | None] | None:
    xpu_output = _run_command(["xpu-smi", "discovery", "-j"])
    if xpu_output:
        name: str | None = None
        try:
            import json

            parsed = json.loads(xpu_output)
            devices = parsed.get("device_list") or parsed.get("devices") or []
            if isinstance(devices, list) and devices:
                first = devices[0]
                if isinstance(first, dict):
                    name = (
                        first.get("device_name")
                        or first.get("name")
                        or first.get("model")
                    )
        except Exception:
            name = None
        return _build_result(True, name, "intel", None, "xpu-smi")

    try:
        import openvino as ov  # type: ignore
    except ImportError:
        ov = None  # type: ignore[assignment]

    if ov is not None:
        try:
            core = ov.Core()
            devices = [str(d) for d in core.available_devices]
            gpu_devices = [d for d in devices if "GPU" in d.upper()]
            if gpu_devices:
                return _build_result(True, gpu_devices[0], "intel", None, "openvino")
        except Exception:
            pass

    if platform.system() == "Windows":
        ps_output = _run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ]
        )
        if ps_output:
            names = [line.strip() for line in ps_output.splitlines() if line.strip()]
            intel_name = next((n for n in names if "intel" in n.lower()), None)
            if intel_name:
                return _build_result(True, intel_name, "intel", None, None)

    return None


def _amd_adapter() -> dict[str, bool | str | float | None] | None:
    try:
        import pyrsmi  # type: ignore
    except ImportError:
        pyrsmi = None  # type: ignore[assignment]

    if pyrsmi is not None:
        initialized = False
        try:
            init_fn = (
                getattr(pyrsmi, "initialize", None)
                or getattr(pyrsmi, "init", None)
                or getattr(pyrsmi, "smi_initialize", None)
            )
            shutdown_fn = (
                getattr(pyrsmi, "shutdown", None)
                or getattr(pyrsmi, "close", None)
                or getattr(pyrsmi, "smi_shutdown", None)
            )

            if callable(init_fn):
                init_fn()
                initialized = True

            query_count = (
                getattr(pyrsmi, "get_device_count", None)
                or getattr(pyrsmi, "device_count", None)
            )
            query_name = (
                getattr(pyrsmi, "get_device_name", None)
                or getattr(pyrsmi, "device_name", None)
            )
            query_mem = (
                getattr(pyrsmi, "get_device_memory_total", None)
                or getattr(pyrsmi, "device_memory_total", None)
            )

            if not callable(query_count):
                return None

            count_raw = query_count()
            if isinstance(count_raw, bool):
                count = int(count_raw)
            elif isinstance(count_raw, (int, float, str)):
                count = int(count_raw)
            else:
                count = 0
            if count < 1:
                return None

            gpu_name: str | None = None
            if callable(query_name):
                try:
                    raw_name = query_name(0)
                    gpu_name = str(raw_name) if raw_name is not None else None
                except Exception:
                    gpu_name = None

            gpu_vram_gb: float | None = None
            if callable(query_mem):
                try:
                    total_bytes_raw = query_mem(0)
                    if isinstance(total_bytes_raw, bool):
                        total_bytes = float(total_bytes_raw)
                    elif isinstance(total_bytes_raw, (int, float, str)):
                        total_bytes = float(total_bytes_raw)
                    else:
                        total_bytes = None
                    if total_bytes is not None:
                        gpu_vram_gb = round(total_bytes / (1024**3), 2)
                except Exception:
                    gpu_vram_gb = None

            return _build_result(True, gpu_name, "amd", gpu_vram_gb, "pyrsmi")
        except Exception:
            pass
        finally:
            try:
                shutdown_fn = (
                    getattr(pyrsmi, "shutdown", None)
                    or getattr(pyrsmi, "close", None)
                    or getattr(pyrsmi, "smi_shutdown", None)
                )
                if initialized and callable(shutdown_fn):
                    shutdown_fn()
            except Exception:
                pass

    rocm_output = _run_command(["rocm-smi", "--showproductname", "--json"])
    if rocm_output:
        name: str | None = None
        try:
            import json

            parsed: Any = json.loads(rocm_output)
            if isinstance(parsed, dict):
                for _, value in parsed.items():
                    if isinstance(value, dict):
                        product = value.get("Card series") or value.get("Card model")
                        if isinstance(product, str) and product.strip():
                            name = product.strip()
                            break
        except Exception:
            name = None
        return _build_result(True, name, "amd", None, "rocm-smi")

    if platform.system() == "Windows":
        ps_output = _run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ]
        )
        if ps_output:
            names = [line.strip() for line in ps_output.splitlines() if line.strip()]
            amd_name = next(
                (n for n in names if "amd" in n.lower() or "radeon" in n.lower()),
                None,
            )
            if amd_name:
                return _build_result(True, amd_name, "amd", None, None)

    return None


def _provider_hint_fallback() -> dict[str, bool | str | float | None] | None:
    try:
        import onnxruntime as ort  # type: ignore
    except ImportError:
        return None

    try:
        providers = [str(p) for p in ort.get_available_providers()]
    except Exception:
        return None

    joined = "|".join(providers).lower()
    if "cudaexecutionprovider" in joined or "tensorrtexecutionprovider" in joined:
        return _build_result(True, None, "nvidia", None, None)
    if "rocmexecutionprovider" in joined:
        return _build_result(True, None, "amd", None, None)
    if "openvinoexecutionprovider" in joined:
        return _build_result(True, None, "intel", None, None)
    if "dmlexecutionprovider" in joined:
        return _build_result(True, None, "unknown", None, None)

    return None


def detect_gpu() -> dict[str, bool | str | float | None]:
    """Detect GPU identity and authoritative VRAM details when available."""

    for adapter in (_nvidia_adapter, _intel_adapter, _amd_adapter):
        result = adapter()
        if result and result.get("gpu_available"):
            return result

    provider_hint = _provider_hint_fallback()
    if provider_hint:
        return provider_hint

    return _no_gpu_result()
