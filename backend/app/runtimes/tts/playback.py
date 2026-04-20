from __future__ import annotations

import threading
import time
from pathlib import Path
import wave


class _UnavailableAudioDependency:
    def __init__(self, module_name: str, import_error: BaseException) -> None:
        self._module_name = module_name
        self._import_error = import_error

    def _raise(self) -> None:
        raise RuntimeError(
            f"{self._module_name} unavailable ({self._import_error})"
        )

    def query_devices(self):
        self._raise()

    def play(self, *_args, **_kwargs):
        self._raise()

    def wait(self):
        self._raise()

    def stop(self):
        self._raise()

    def get_stream(self):
        self._raise()

    def read(self, *_args, **_kwargs):
        self._raise()


try:
    import sounddevice as sd
except Exception as exc:  # pragma: no cover - environment-dependent
    sd = _UnavailableAudioDependency("sounddevice", exc)


def _read_pcm16_wav(audio_path: str, *, op_name: str) -> tuple[object, int]:
    path = Path(audio_path)
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = int(wav_file.getnchannels())
            sample_width = int(wav_file.getsampwidth())
            sample_rate = int(wav_file.getframerate())
            frame_count = int(wav_file.getnframes())
            raw = wav_file.readframes(frame_count)
    except Exception as exc:
        raise RuntimeError(f"{op_name}: unable to read wav ({exc})") from exc

    if channels <= 0:
        raise RuntimeError(f"{op_name}: invalid wav channel count")
    if sample_width != 2:
        raise RuntimeError(f"{op_name}: unsupported wav sample width ({sample_width})")

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"{op_name}: audio runtime unavailable ({exc})") from exc

    samples = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        if samples.size % channels != 0:
            raise RuntimeError(f"{op_name}: invalid wav frame payload")
        samples = samples.reshape(-1, channels)

    audio = samples.astype(np.float32) / 32768.0
    return audio, sample_rate


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

    data, sample_rate = _read_pcm16_wav(audio_path, op_name="play_audio")
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

    data, sample_rate = _read_pcm16_wav(audio_path, op_name="play_audio_interruptible")
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
