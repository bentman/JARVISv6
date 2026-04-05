from __future__ import annotations

from pathlib import Path

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.stt.base import STTBase
from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT


_STT_RUNTIME_CACHE: dict[tuple[str, str], STTBase] = {}


def select_stt_runtime(report: FullCapabilityReport) -> STTBase | None:
    try:
        if report.flags.stt_recommended_runtime != "faster-whisper":
            return None

        model_name = report.flags.stt_recommended_model
        selected_device = report.flags.stt_recommended_device
        if selected_device not in {"cuda", "cpu"}:
            return None

        if selected_device == "cuda":
            device = "cuda"
        else:
            device = "cpu"

        cache_key = (model_name, device)

        cached = _STT_RUNTIME_CACHE.get(cache_key)
        if cached is not None and cached.is_available():
            return cached

        runtime: STTBase = FasterWhisperSTT(
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
        sd.stop()
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: audio stream reset failed ({exc})") from exc

    try:
        recording = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
        sd.wait()
        sf.write(str(output_file), recording, sample_rate, subtype="PCM_16")
    except Exception as exc:
        raise RuntimeError(f"capture_utterance: capture failed ({exc})") from exc
    finally:
        try:
            sd.stop()
        except Exception as exc:
            raise RuntimeError(f"capture_utterance: audio stream release failed ({exc})") from exc

    return str(output_file)
