"""Slice 0.7 memory detector."""

from __future__ import annotations

import psutil


def detect_memory() -> dict[str, float]:
    """Return normalized memory fields with zero-valued fallback on failure."""

    try:
        vm = psutil.virtual_memory()
        return {
            "memory_total_gb": round(vm.total / (1024**3), 2),
            "memory_available_gb": round(vm.available / (1024**3), 2),
            "memory_percent_used": float(vm.percent),
        }
    except Exception:
        return {
            "memory_total_gb": 0.0,
            "memory_available_gb": 0.0,
            "memory_percent_used": 0.0,
        }
