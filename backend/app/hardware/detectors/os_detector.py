"""Slice 0.2 OS and architecture detector."""

from __future__ import annotations

import platform


def detect_os() -> dict[str, str]:
    """Return normalized OS/platform fields with unknown fallbacks."""

    os_name = platform.system() or "unknown"
    os_release = platform.release() or "unknown"
    arch = platform.machine() or "unknown"

    return {
        "os": os_name,
        "os_release": os_release,
        "arch": arch,
    }