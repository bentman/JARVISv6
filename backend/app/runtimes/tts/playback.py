from __future__ import annotations

import threading
import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf


def has_output_device() -> bool:
    try:
        devices = sd.query_devices()
    except Exception:
        return False

    for device in devices:
        try:
            if float(device.get("max_output_channels", 0)) > 0:
                return True
        except Exception:
            continue
    return False


def play_audio(audio_path: str) -> None:
    path = Path(audio_path)
    if not path.exists():
        raise RuntimeError(f"play_audio: file not found: {audio_path}")

    if not has_output_device():
        raise RuntimeError("play_audio: no output device available")

    data, sample_rate = sf.read(str(path))
    try:
        sd.play(data, sample_rate)
        sd.wait()
    finally:
        try:
            sd.stop()
        except Exception as exc:
            raise RuntimeError(f"play_audio: output stream release failed ({exc})") from exc


def play_audio_interruptible(
    audio_path: str,
    interrupt_flag: threading.Event,
    *,
    poll_interval_seconds: float = 0.05,
) -> bool:
    path = Path(audio_path)
    if not path.exists():
        raise RuntimeError(f"play_audio_interruptible: file not found: {audio_path}")

    if not has_output_device():
        raise RuntimeError("play_audio_interruptible: no output device available")

    data, sample_rate = sf.read(str(path))
    try:
        sd.play(data, sample_rate)
        while getattr(sd.get_stream(), "active", False):
            if interrupt_flag.is_set():
                return False
            time.sleep(poll_interval_seconds)
        return True
    finally:
        try:
            sd.stop()
        except Exception as exc:
            raise RuntimeError(
                f"play_audio_interruptible: output stream release failed ({exc})"
            ) from exc
