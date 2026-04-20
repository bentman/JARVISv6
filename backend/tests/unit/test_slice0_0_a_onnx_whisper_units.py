from __future__ import annotations

from pathlib import Path
import wave

import numpy as np
import pytest

from backend.app.runtimes.stt.onnx_runtime import OnnxWhisperSTT


def test_onnx_whisper_is_available_returns_true_when_onnxruntime_import_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeOnnxRuntime:
        pass

    class _FakeOnnxAsr:
        pass

    def _import(name: str):
        if name == "onnxruntime":
            return _FakeOnnxRuntime()
        if name == "onnx_asr":
            return _FakeOnnxAsr()
        raise ImportError(name)

    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.importlib.import_module",
        _import,
    )

    runtime = OnnxWhisperSTT("whisper-small-onnx")
    assert runtime.is_available() is True


def test_onnx_whisper_is_available_returns_false_when_onnxruntime_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_name: str):
        raise ImportError("onnxruntime missing")

    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.importlib.import_module",
        _raise,
    )

    runtime = OnnxWhisperSTT("whisper-small-onnx")
    assert runtime.is_available() is False


def _install_fake_onnx_whisper_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAsrRuntime:
        def recognize(self, audio_path: str) -> str:
            assert audio_path.endswith("utterance.wav")
            return "hello from onnx"

    class _FakeOnnxAsrModule:
        @staticmethod
        def load_model(model_name: str, path: str, providers=None):
            assert model_name == "whisper"
            assert providers == ["CPUExecutionProvider"]
            assert path
            return _FakeAsrRuntime()

    class _FakeOnnxRuntime:
        pass

    def _import(name: str):
        if name == "onnxruntime":
            return _FakeOnnxRuntime()
        if name == "onnx_asr":
            return _FakeOnnxAsrModule()
        raise ImportError(name)

    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.importlib.import_module",
        _import,
    )


def _write_test_wav(path: Path) -> None:
    samples = (np.sin(np.linspace(0, 8 * np.pi, 16000, endpoint=False)) * 12000).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(samples.tobytes())


def test_onnx_whisper_raises_when_audio_path_missing() -> None:
    runtime = OnnxWhisperSTT("whisper-small-onnx")
    with pytest.raises(RuntimeError, match=r"OnnxWhisperSTT: transcription failed \(audio file not found:"):
        runtime.transcribe("missing-audio.wav")


def test_onnx_whisper_raises_when_model_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio = tmp_path / "utterance.wav"
    _write_test_wav(audio)

    _install_fake_onnx_whisper_modules(monkeypatch)
    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.get_model_entry",
        lambda _model_name: {
            "hf_repo_id": "onnx-community/whisper-small-ONNX",
            "local_dir": str(tmp_path / "missing-model-dir"),
        },
    )
    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.ensure_model",
        lambda **_kwargs: str(tmp_path / "missing-model-dir"),
    )

    runtime = OnnxWhisperSTT("whisper-small-onnx")
    with pytest.raises(RuntimeError, match=r"OnnxWhisperSTT: transcription failed \(model directory not found:"):
        runtime.transcribe(str(audio))


def test_onnx_whisper_transcribe_returns_string_for_valid_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio = tmp_path / "utterance.wav"
    _write_test_wav(audio)

    model_dir = tmp_path / "models" / "stt" / "whisper-small-onnx"
    onnx_dir = model_dir / "onnx"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    (onnx_dir / "encoder_model.onnx").write_bytes(b"onnx")
    (onnx_dir / "decoder_model_merged.onnx").write_bytes(b"onnx")
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "vocab.json").write_text("{}", encoding="utf-8")
    (model_dir / "preprocessor_config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")

    _install_fake_onnx_whisper_modules(monkeypatch)
    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.get_model_entry",
        lambda _model_name: {
            "hf_repo_id": "onnx-community/whisper-small-ONNX",
            "local_dir": str(model_dir),
        },
    )
    monkeypatch.setattr(
        "backend.app.runtimes.stt.onnx_runtime.ensure_model",
        lambda **_kwargs: str(model_dir),
    )

    runtime = OnnxWhisperSTT("whisper-small-onnx")
    transcript = runtime.transcribe(str(audio))
    assert transcript == "hello from onnx"
