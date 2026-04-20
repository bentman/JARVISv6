from __future__ import annotations

from pathlib import Path
import wave

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.stt.base import STTBase
from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT
from backend.app.runtimes.stt.onnx_runtime import OnnxWhisperSTT


_STT_RUNTIME_CACHE: dict[tuple[str, str, str], STTBase] = {}


def _write_pcm16_wav(output_file: Path, recording: object, sample_rate: int) -> None:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: audio runtime unavailable ({exc})") from exc

    audio = np.asarray(recording)
    if audio.size == 0:
        raise RuntimeError("capture_utterance: capture failed (empty audio payload)")

    if audio.ndim == 1:
        channels = 1
    elif audio.ndim == 2:
        channels = int(audio.shape[1])
        if channels <= 0:
            raise RuntimeError("capture_utterance: capture failed (invalid channel count)")
    else:
        raise RuntimeError("capture_utterance: capture failed (unsupported audio shape)")

    if np.issubdtype(audio.dtype, np.floating):
        audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    elif np.issubdtype(audio.dtype, np.integer):
        audio_i16 = np.clip(audio, -32768, 32767).astype(np.int16)
    else:
        raise RuntimeError("capture_utterance: capture failed (unsupported audio dtype)")

    try:
        with wave.open(str(output_file), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(audio_i16.tobytes())
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: capture failed ({exc})") from exc


def select_stt_runtime(report: FullCapabilityReport) -> STTBase | None:
    try:
        runtime_family = report.flags.stt_recommended_runtime
        if runtime_family not in {"faster-whisper", "onnx-whisper"}:
            return None

        model_name = report.flags.stt_recommended_model
        selected_device = report.flags.stt_recommended_device
        if selected_device not in {"cuda", "cpu"}:
            return None

        if selected_device == "cuda":
            device = "cuda"
        else:
            device = "cpu"

        cache_key = (runtime_family, model_name, device)

        cached = _STT_RUNTIME_CACHE.get(cache_key)
        if cached is not None and cached.is_available():
            return cached

        if runtime_family == "faster-whisper":
            runtime: STTBase = FasterWhisperSTT(
                model_name,
                device=device,
            )
        else:
            runtime = OnnxWhisperSTT(
                model_name,
                device=device,
            )

        if not runtime.is_available():
            return None

        _STT_RUNTIME_CACHE[cache_key] = runtime
        return runtime
    except Exception:
        return None


def capture_utterance(output_path: str, duration_seconds: int = 5) -> str:
    try:
        import sounddevice as sd  # type: ignore
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
        sd.stop()
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: audio stream reset failed ({exc})") from exc

    try:
        recording = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
        sd.wait()
        _write_pcm16_wav(output_file, recording, sample_rate)
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: capture failed ({exc})") from exc
    finally:
        try:
            sd.stop()
        except Exception as exc:
            raise RuntimeError(f"capture_utterance: audio stream release failed ({exc})") from exc

    return str(output_file)
