"""Slice 0.5 CUDA detector."""

from __future__ import annotations

import subprocess


def detect_cuda() -> bool:
    """Return True when CUDA/NVIDIA presence is detected on the host.

    This is a host-level signal only. It does not guarantee that every backend
    runtime in the active Python environment can actually execute on CUDA.
    """

    try:
        import torch  # type: ignore
    except ImportError:
        torch = None  # type: ignore[assignment]

    if torch is not None:
        try:
            if bool(torch.cuda.is_available()):
                return True
        except Exception:
            pass

    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    except Exception:
        return False


def detect_cuda_via_providers(providers: list[str]) -> bool:
    """Return True when provider list includes CUDAExecutionProvider."""

    try:
        return any("CUDAExecutionProvider" in str(provider) for provider in providers)
    except Exception:
        return False
