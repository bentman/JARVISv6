"""Slice 0.3 CPU detector."""

from __future__ import annotations

import platform

import psutil


def detect_cpu() -> dict[str, str | int | float]:
    """Return CPU detection fields with safe fallbacks and no propagated failures."""

    try:
        freq = psutil.cpu_freq()
        max_mhz = float(freq.max) if freq is not None else 0.0
    except Exception:
        max_mhz = 0.0

    return {
        "cpu_name": platform.processor() or "unknown",
        "cpu_physical_cores": int(psutil.cpu_count(logical=False) or 1),
        "cpu_logical_cores": int(psutil.cpu_count(logical=True) or 1),
        "cpu_max_freq_mhz": max_mhz,
    }