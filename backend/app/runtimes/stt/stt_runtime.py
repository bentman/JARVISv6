from __future__ import annotations

from pathlib import Path


def capture_utterance(output_path: str, duration_seconds: int = 5) -> str:
    try:
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: audio runtime unavailable ({exc})") from exc

    try:
        input_devices = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: unable to query input devices ({exc})") from exc

    if not input_devices:
        raise RuntimeError("capture_utterance: no input device available")

    sample_rate = 16000
    channels = 1
    frames = int(sample_rate * duration_seconds)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        recording = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
        sd.wait()
        sf.write(str(output_file), recording, sample_rate, subtype="PCM_16")
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: capture failed ({exc})") from exc

    return str(output_file)
