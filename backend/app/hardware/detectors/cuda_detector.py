"""Slice 0.5 CUDA detector."""

from __future__ import annotations

import subprocess


def detect_cuda() -> bool:
    """Return True when CUDA is detected via torch or host CUDA tooling."""

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
