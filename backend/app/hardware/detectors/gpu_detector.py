"""Slice 0.4 GPU detector."""

from __future__ import annotations

import json
import subprocess
import sys


def _infer_vendor(name: str) -> str:
    """Infer GPU vendor from a GPU name string."""

    normalized = name.lower()
    if "nvidia" in normalized:
        return "nvidia"
    if "amd" in normalized or "radeon" in normalized:
        return "amd"
    if "intel" in normalized:
        return "intel"
    if "apple" in normalized:
        return "apple"
    if "qualcomm" in normalized or "adreno" in normalized:
        return "qualcomm"
    return "unknown"


def _default_result() -> dict[str, object]:
    """Return default detector output for no-GPU/unknown states."""

    return {
        "gpu_available": False,
        "gpu_name": None,
        "gpu_vendor": None,
        "gpu_vram_gb": None,
        "providers": [],
        "source": "none",
    }


def _detect_nvidia_vram_gb(gpu_name: str) -> float | None:
    """Use nvidia-smi to get accurate dedicated VRAM for NVIDIA GPUs when available."""

    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return None

        for line in completed.stdout.splitlines():
            parts = [part.strip() for part in line.split(",", 1)]
            if len(parts) != 2:
                continue
            name, memory_mb = parts
            if gpu_name.lower() in name.lower() or name.lower() in gpu_name.lower():
                try:
                    return round(float(memory_mb) / 1024, 2)
                except ValueError:
                    return None
    except Exception:
        return None

    return None


def detect_gpu() -> dict[str, object]:
    """Detect GPU presence and metadata using guarded multi-pass probing."""

    result: dict[str, object] = _default_result()

    # Pass 1: GPUtil (primary for NVIDIA and VRAM)
    try:
        import GPUtil  # type: ignore

        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return {
                "gpu_available": True,
                "gpu_name": gpu.name,
                "gpu_vendor": _infer_vendor(gpu.name),
                "gpu_vram_gb": round(float(gpu.memoryTotal) / 1024, 2),
                "providers": [],
                "source": "gputil",
            }
    except Exception:
        pass

    # Pass 2: onnxruntime provider hints
    providers: list[str] = []
    try:
        import onnxruntime as ort  # type: ignore

        providers = list(ort.get_available_providers())
        provider_map: dict[str, tuple[str, str]] = {
            "cudaexecutionprovider": ("nvidia", "nvidia-provider"),
            "coremlexecutionprovider": ("apple", "coreml-provider"),
            "dmlexecutionprovider": ("microsoft", "directml-provider"),
            "rocmexecutionprovider": ("amd", "rocm-provider"),
        }

        lowered = [provider.lower() for provider in providers]
        for key, (vendor, source) in provider_map.items():
            if key in lowered:
                return {
                    "gpu_available": True,
                    "gpu_name": source,
                    "gpu_vendor": vendor,
                    "gpu_vram_gb": None,
                    "providers": providers,
                    "source": "onnxruntime",
                }
    except Exception:
        pass

    # Pass 3: Windows CIM fallback
    if sys.platform == "win32":
        try:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name,AdapterRAM,PNPDeviceID | ConvertTo-Json -Depth 3",
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                payload = json.loads(completed.stdout)
                records = payload if isinstance(payload, list) else [payload]
                for record in records:
                    name = str(record.get("Name") or "").strip()
                    if not name:
                        continue

                    adapter_ram = record.get("AdapterRAM")
                    vram_gb = None
                    if isinstance(adapter_ram, (int, float)) and adapter_ram > 0:
                        vram_gb = round(float(adapter_ram) / (1024**3), 2)

                    vendor = _infer_vendor(name)
                    if vendor == "nvidia":
                        nvidia_vram = _detect_nvidia_vram_gb(name)
                        if nvidia_vram is not None:
                            vram_gb = nvidia_vram

                    return {
                        "gpu_available": True,
                        "gpu_name": name,
                        "gpu_vendor": vendor,
                        "gpu_vram_gb": vram_gb,
                        "providers": providers,
                        "source": "windows-cim",
                    }
        except Exception:
            pass

    result["providers"] = providers
    return result
