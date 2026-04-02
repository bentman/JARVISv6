from __future__ import annotations

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
