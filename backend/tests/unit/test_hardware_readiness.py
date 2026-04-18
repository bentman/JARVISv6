from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.core.capabilities import HardwareProfile
from backend.app.hardware.preflight import run_hardware_preflight
from backend.app.hardware.preflight import derive_backend_device_readiness
from backend.app.hardware.preflight import derive_stt_device_readiness
from backend.app.hardware.profiler import get_stt_device_readiness
from backend.app.hardware.profile_resolver import resolve_hardware_profiles
from scripts import bootstrap_readiness


MANIFEST_DIR = Path("config/hardware")
MANIFEST_FILES = [
    "hw_cpu_base.json",
    "hw_gpu_present.json",
    "hw_gpu_noncuda.json",
    "hw_gpu_nvidia_cuda.json",
    "hw_npu_present.json",
]
REQUIRED_KEYS = {
    "manifest_id",
    "version",
    "applies_when",
    "additive_requirements",
    "merge_behavior",
}
REQUIREMENTS_PATH = Path("backend/requirements.txt")


def _load_manifest(filename: str) -> dict:
    path = MANIFEST_DIR / filename
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def test_hardware_manifest_files_exist() -> None:
    for filename in MANIFEST_FILES:
        assert (MANIFEST_DIR / filename).exists(), f"missing manifest: {filename}"


def test_hardware_manifests_have_required_keys() -> None:
    for filename in MANIFEST_FILES:
        manifest = _load_manifest(filename)
        assert REQUIRED_KEYS.issubset(manifest.keys()), f"missing keys in {filename}"


def test_hardware_manifests_use_additive_merge_behavior() -> None:
    for filename in MANIFEST_FILES:
        manifest = _load_manifest(filename)
        assert manifest["merge_behavior"] == "additive"


def test_hardware_manifests_additive_requirements_shape() -> None:
    for filename in MANIFEST_FILES:
        manifest = _load_manifest(filename)
        additive = manifest["additive_requirements"]
        assert isinstance(additive, dict)
        assert isinstance(additive.get("python_packages"), list)
        install = additive.get("install", {})
        assert isinstance(install, dict)


def test_hardware_manifest_ids_cover_stt_profile_set() -> None:
    ids = {_load_manifest(filename)["manifest_id"] for filename in MANIFEST_FILES}
    assert {
        "hw-cpu-base",
        "hw-gpu-present",
        "hw-gpu-noncuda",
        "hw-gpu-nvidia-cuda",
        "hw-npu-present",
    }.issubset(ids)


def test_base_requirements_do_not_own_tts_cuda_torch_dependency() -> None:
    requirements_text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    assert "--extra-index-url https://download.pytorch.org/whl/cu128" not in requirements_text
    assert "torch==2.11.0+cu128" not in requirements_text


def test_hw_nvidia_cuda_manifest_owns_additive_torch_dependency_and_source() -> None:
    manifest = _load_manifest("hw_gpu_nvidia_cuda.json")
    additive = manifest["additive_requirements"]
    python_packages = additive["python_packages"]
    install = additive["install"]

    assert "torch>=2.11.0" in python_packages
    assert install["pip_extra_index_urls"] == ["https://download.pytorch.org/whl/cu128"]


def _build_profile(**overrides: object) -> HardwareProfile:
    base = {
        "os": "Windows",
        "arch": "AMD64",
        "cpu_name": "unit-cpu",
        "cpu_physical_cores": 8,
        "cpu_logical_cores": 16,
        "cpu_max_freq_mhz": 3000.0,
        "gpu_available": False,
        "gpu_name": None,
        "gpu_vendor": None,
        "gpu_vram_gb": None,
        "cuda_available": False,
        "npu_available": False,
        "npu_vendor": None,
        "npu_tops": None,
        "memory_total_gb": 32.0,
        "memory_available_gb": 20.0,
        "device_class": "desktop",
        "profile_id": "unit-profile",
    }
    base.update(overrides)
    return HardwareProfile(**base)


def test_resolver_cpu_host_resolves_base_cpu_manifest() -> None:
    result = resolve_hardware_profiles(_build_profile(gpu_available=False, cuda_available=False))
    assert result["matched_manifest_ids"] == ["hw-cpu-base", "hw-x64-base"]
    assert result["merged_additive_requirements"]["python_packages"] == [
        "onnxruntime>=1.17",
        "faster-whisper>=1.0",
        "kokoro>=0.9.4",
        "misaki[en]>=0.9.3",
    ]


def test_resolver_gpu_without_cuda_resolves_noncuda_manifest() -> None:
    result = resolve_hardware_profiles(
        _build_profile(gpu_available=True, gpu_vendor="intel", cuda_available=False)
    )
    assert result["matched_manifest_ids"] == [
        "hw-cpu-base",
        "hw-gpu-noncuda",
        "hw-gpu-present",
        "hw-x64-base",
    ]


def test_resolver_gpu_with_cuda_resolves_cuda_manifest() -> None:
    result = resolve_hardware_profiles(
        _build_profile(gpu_available=True, gpu_vendor="nvidia", cuda_available=True)
    )
    assert result["matched_manifest_ids"] == [
        "hw-cpu-base",
        "hw-gpu-nvidia-cuda",
        "hw-gpu-present",
        "hw-x64-base",
    ]
    assert "nvidia-cublas-cu12>=12.0" in result["merged_additive_requirements"]["python_packages"]


def test_resolver_npu_resolves_npu_manifest() -> None:
    result = resolve_hardware_profiles(_build_profile(npu_available=True, npu_vendor="intel"))
    assert result["matched_manifest_ids"] == ["hw-cpu-base", "hw-npu-present", "hw-x64-base"]


def test_resolver_combined_hardware_matches_multiple_manifests_additively() -> None:
    result = resolve_hardware_profiles(
        _build_profile(
            gpu_available=True,
            gpu_vendor="nvidia",
            cuda_available=True,
            npu_available=True,
            npu_vendor="qualcomm",
        )
    )
    assert result["matched_manifest_ids"] == [
        "hw-cpu-base",
        "hw-gpu-nvidia-cuda",
        "hw-gpu-present",
        "hw-npu-present",
        "hw-x64-base",
    ]
    assert result["merged_additive_requirements"]["python_packages"] == [
        "GPUtil>=1.4",
        "nvidia-ml-py>=12.0",
        "nvidia-cublas-cu12>=12.0",
        "nvidia-cudnn-cu12>=9.0",
        "torch>=2.11.0",
        "onnxruntime>=1.17",
        "faster-whisper>=1.0",
        "kokoro>=0.9.4",
        "misaki[en]>=0.9.3",
    ]
    assert result["merged_additive_requirements"]["install"]["pip_extra_index_urls"] == [
        "https://download.pytorch.org/whl/cu128"
    ]


def test_resolver_fails_closed_on_unsupported_merge_behavior(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad_manifest = {
        "manifest_id": "bad",
        "version": "0.0.1",
        "merge_behavior": "priority",
        "applies_when": {},
        "additive_requirements": {"python_packages": []},
    }

    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
    monkeypatch.setattr("backend.app.hardware.profile_resolver.MANIFEST_DIR", tmp_path)

    with pytest.raises(ValueError, match="unsupported merge_behavior"):
        resolve_hardware_profiles(_build_profile())


def test_preflight_returns_expected_result_shape_from_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-shape")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-cpu-base"],
            "matched_manifest_paths": [str((MANIFEST_DIR / "hw_cpu_base.json").as_posix())],
            "merged_additive_requirements": {
                "python_packages": [],
                "install": {"pip_extra_index_urls": []},
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight._installed_distribution_names",
        lambda: {"faster-whisper"},
    )
    monkeypatch.setattr("backend.app.hardware.preflight._verify_runtime_evidence", lambda _t: [{"token": "import:faster_whisper", "ok": True}])

    result = run_hardware_preflight(profile)

    assert set(result.keys()) == {
        "backend_scope",
        "profile_id",
        "matched_manifest_ids",
        "required_packages",
        "missing_packages_before_install",
        "installed_packages",
        "verification_results",
        "ready",
    }
    assert result["backend_scope"] == "stt"
    assert result["profile_id"] == "preflight-shape"
    assert result["matched_manifest_ids"] == ["hw-cpu-base"]
    assert result["required_packages"] == []
    assert result["missing_packages_before_install"] == []
    assert result["installed_packages"] == []
    assert result["ready"] is True


def test_preflight_installs_only_missing_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-install")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-gpu-nvidia-cuda", "hw-npu-present"],
            "matched_manifest_paths": [
                str((MANIFEST_DIR / "hw_gpu_nvidia_cuda.json").as_posix()),
                str((MANIFEST_DIR / "hw_npu_present.json").as_posix()),
            ],
            "merged_additive_requirements": {
                "python_packages": ["onnxruntime>=1.17", "onnxruntime>=1.17"],
                "install": {
                    "pip_extra_index_urls": ["https://download.pytorch.org/whl/cu128"]
                },
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight._installed_distribution_names",
        lambda: set(),
    )
    monkeypatch.setattr("backend.app.hardware.preflight._verify_runtime_evidence", lambda _t: [{"token": "import:faster_whisper", "ok": True}])

    pip_calls: list[list[str]] = []

    def _fake_run(command: list[str], check: bool, capture_output: bool, text: bool) -> None:
        pip_calls.append(command)

    monkeypatch.setattr("backend.app.hardware.preflight.subprocess.run", _fake_run)

    result = run_hardware_preflight(profile)

    assert result["required_packages"] == ["onnxruntime>=1.17"]
    assert result["missing_packages_before_install"] == ["onnxruntime>=1.17"]
    assert result["installed_packages"] == ["onnxruntime>=1.17"]
    assert len(pip_calls) == 1
    assert pip_calls[0][1:6] == [
        "-m",
        "pip",
        "install",
        "--extra-index-url",
        "https://download.pytorch.org/whl/cu128",
    ]
    assert pip_calls[0][-1] == "onnxruntime>=1.17"


def test_preflight_verification_runs_after_install(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-order")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-cpu-base"],
            "matched_manifest_paths": [str((MANIFEST_DIR / "hw_cpu_base.json").as_posix())],
            "merged_additive_requirements": {
                "python_packages": [],
                "install": {"pip_extra_index_urls": []},
            },
        },
    )
    monkeypatch.setattr("backend.app.hardware.preflight._installed_distribution_names", lambda: set())

    events: list[str] = []

    def _fake_install(
        missing: list[str],
        pip_extra_index_urls: list[str] | None = None,
    ) -> list[str]:
        events.append("install")
        assert pip_extra_index_urls == []
        return list(missing)

    def _fake_verify(tokens: list[str]) -> list[dict[str, object]]:
        assert events == ["install"]
        events.append("verify")
        return [{"token": token, "ok": True} for token in tokens]

    monkeypatch.setattr("backend.app.hardware.preflight._install_missing_packages", _fake_install)
    monkeypatch.setattr("backend.app.hardware.preflight._verify_runtime_evidence", _fake_verify)

    result = run_hardware_preflight(profile)

    assert events == ["install", "verify"]
    assert result["ready"] is True


def test_preflight_fails_closed_on_unsupported_requirement_syntax(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-bad-req")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-cpu-base"],
            "matched_manifest_paths": [str((MANIFEST_DIR / "hw_cpu_base.json").as_posix())],
            "merged_additive_requirements": {
                "python_packages": ["faster-whisper"],
                "install": {"pip_extra_index_urls": []},
            },
        },
    )
    monkeypatch.setattr("backend.app.hardware.preflight._installed_distribution_names", lambda: set())

    with pytest.raises(ValueError, match="unsupported requirement syntax"):
        run_hardware_preflight(profile)


def test_preflight_fails_closed_on_unsupported_evidence_token(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-bad-evidence")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-cpu-base"],
            "matched_manifest_paths": [str((MANIFEST_DIR / "hw_cpu_base.json").as_posix())],
            "merged_additive_requirements": {
                "python_packages": ["faster-whisper>=1.0"],
                "install": {"pip_extra_index_urls": []},
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight._installed_distribution_names",
        lambda: {"faster-whisper"},
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight._resolve_evidence_tokens_from_caller_boundary",
        lambda _scope, _manifest_ids: ["unknown:token"],
    )

    with pytest.raises(ValueError, match="unsupported evidence token"):
        run_hardware_preflight(profile)


def test_preflight_does_not_invoke_model_artifact_ensure_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="preflight-no-model-ensure")
    monkeypatch.setattr("backend.app.hardware.preflight._ensure_backend_venv_interpreter", lambda: None)
    monkeypatch.setattr(
        "backend.app.hardware.preflight.resolve_hardware_profiles",
        lambda _p: {
            "matched_manifest_ids": ["hw-gpu-noncuda"],
            "matched_manifest_paths": [str((MANIFEST_DIR / "hw_gpu_noncuda.json").as_posix())],
            "merged_additive_requirements": {
                "python_packages": [],
                "install": {"pip_extra_index_urls": []},
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight._installed_distribution_names",
        lambda: {"faster-whisper"},
    )
    monkeypatch.setattr(
        "backend.app.hardware.preflight.load_stt_catalog",
        lambda: {"runtimes": {"faster-whisper": {}}},
    )
    monkeypatch.setattr(
        "backend.app.models.manager.ensure_model",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ensure_model should not be called")),
    )

    result = run_hardware_preflight(profile)
    assert result["ready"] is True


def test_stt_device_readiness_reports_cuda_when_cuda_evidence_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _build_profile(profile_id="stt-ready-cuda")
    monkeypatch.setattr(
        "backend.app.hardware.profiler.run_hardware_preflight",
        lambda _p, **kwargs: {
            "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
            "verification_results": [
                {"token": "import:faster_whisper", "ok": True},
                {"token": "import:ctranslate2", "ok": True},
                {"token": "stt_runtime:faster-whisper", "ok": True},
                {"token": "dll:cublas64_12.dll", "ok": True},
                {"token": "dll:cudnn64_9.dll", "ok": True},
            ],
        },
    )

    result = get_stt_device_readiness(profile)

    assert result["cuda_ready"] is True
    assert result["cpu_ready"] is True
    assert result["selected_device"] == "cuda"


def test_stt_device_readiness_forces_cpu_when_cuda_evidence_not_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _build_profile(profile_id="stt-ready-cpu")
    monkeypatch.setattr(
        "backend.app.hardware.profiler.run_hardware_preflight",
        lambda _p, **kwargs: {
            "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
            "verification_results": [
                {"token": "import:faster_whisper", "ok": True},
                {"token": "import:ctranslate2", "ok": True},
                {"token": "stt_runtime:faster-whisper", "ok": True},
                {"token": "dll:cublas64_12.dll", "ok": False},
                {"token": "dll:cudnn64_9.dll", "ok": True},
            ],
        },
    )

    result = get_stt_device_readiness(profile)

    assert result["cuda_ready"] is False
    assert result["cpu_ready"] is True
    assert result["selected_device"] == "cpu"


def test_stt_device_readiness_unavailable_when_cpu_import_not_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _build_profile(profile_id="stt-ready-unavailable")
    monkeypatch.setattr(
        "backend.app.hardware.profiler.run_hardware_preflight",
        lambda _p, **kwargs: {
            "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
            "verification_results": [
                {"token": "import:faster_whisper", "ok": False},
                {"token": "import:ctranslate2", "ok": False},
                {"token": "stt_runtime:faster-whisper", "ok": False},
                {"token": "dll:cublas64_12.dll", "ok": False},
                {"token": "dll:cudnn64_9.dll", "ok": False},
            ],
        },
    )

    result = get_stt_device_readiness(profile)

    assert result["cuda_ready"] is False
    assert result["cpu_ready"] is False
    assert result["selected_device"] == "unavailable"


def test_derive_stt_device_readiness_degrades_to_cpu_when_cuda_dll_missing() -> None:
    preflight_result = {
        "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
        "verification_results": [
            {"token": "import:faster_whisper", "ok": True},
            {"token": "import:ctranslate2", "ok": True},
            {"token": "stt_runtime:faster-whisper", "ok": True},
            {"token": "dll:cublas64_12.dll", "ok": False},
            {"token": "dll:cudnn64_9.dll", "ok": True},
        ],
    }

    derived = derive_stt_device_readiness(preflight_result)

    assert derived["cuda_ready"] is False
    assert derived["cpu_ready"] is True
    assert derived["selected_device"] == "cpu"
    assert derived["selected_device_ready"] is True


def test_derive_backend_device_readiness_supports_backend_agnostic_shape() -> None:
    preflight_result = {
        "matched_manifest_ids": ["backend-gpu-cuda"],
        "verification_results": [
            {"token": "import:pkg", "ok": True},
            {"token": "runtime:token", "ok": True},
            {"token": "dll:cuda.dll", "ok": False},
        ],
    }

    derived = derive_backend_device_readiness(
        preflight_result,
        cuda_manifest_id="backend-gpu-cuda",
        cuda_required_tokens=["import:pkg", "runtime:token", "dll:cuda.dll"],
        cpu_ready_tokens=["import:pkg"],
    )

    assert derived["cuda_ready"] is False
    assert derived["cpu_ready"] is True
    assert derived["selected_device"] == "cpu"
    assert derived["selected_device_ready"] is True


def test_derive_stt_device_readiness_preserves_existing_stt_behavior() -> None:
    preflight_result = {
        "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
        "verification_results": [
            {"token": "import:faster_whisper", "ok": True},
            {"token": "import:ctranslate2", "ok": True},
            {"token": "stt_runtime:faster-whisper", "ok": True},
            {"token": "dll:cublas64_12.dll", "ok": True},
            {"token": "dll:cudnn64_9.dll", "ok": True},
        ],
    }

    derived = derive_stt_device_readiness(preflight_result)

    assert derived["cuda_ready"] is True
    assert derived["cpu_ready"] is True
    assert derived["selected_device"] == "cuda"
    assert derived["selected_device_ready"] is True


def test_tts_device_readiness_reports_cuda_when_cuda_evidence_verified() -> None:
    preflight_result = {
        "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
        "verification_results": [
            {"token": "import:kokoro", "ok": True},
            {"token": "import:torch", "ok": True},
            {"token": "tts_runtime:kokoro", "ok": True},
            {"token": "torch_cuda:available", "ok": True},
            {"token": "dll:cublas64_12.dll", "ok": True},
            {"token": "dll:cudnn64_9.dll", "ok": True},
        ],
    }

    derived = derive_backend_device_readiness(
        preflight_result,
        cuda_manifest_id="hw-gpu-nvidia-cuda",
        cuda_required_tokens=[
            "import:kokoro",
            "import:torch",
            "tts_runtime:kokoro",
            "torch_cuda:available",
            "dll:cublas64_12.dll",
            "dll:cudnn64_9.dll",
        ],
        cpu_ready_tokens=["import:kokoro"],
    )

    assert derived["cuda_ready"] is True
    assert derived["cpu_ready"] is True
    assert derived["selected_device"] == "cuda"


def test_tts_device_readiness_degrades_to_cpu_when_cuda_not_verified() -> None:
    preflight_result = {
        "matched_manifest_ids": ["hw-gpu-nvidia-cuda"],
        "verification_results": [
            {"token": "import:kokoro", "ok": True},
            {"token": "import:torch", "ok": True},
            {"token": "tts_runtime:kokoro", "ok": True},
            {"token": "torch_cuda:available", "ok": False},
            {"token": "dll:cublas64_12.dll", "ok": True},
            {"token": "dll:cudnn64_9.dll", "ok": True},
        ],
    }

    derived = derive_backend_device_readiness(
        preflight_result,
        cuda_manifest_id="hw-gpu-nvidia-cuda",
        cuda_required_tokens=[
            "import:kokoro",
            "import:torch",
            "tts_runtime:kokoro",
            "torch_cuda:available",
            "dll:cublas64_12.dll",
            "dll:cudnn64_9.dll",
        ],
        cpu_ready_tokens=["import:kokoro"],
    )

    assert derived["cuda_ready"] is False
    assert derived["cpu_ready"] is True
    assert derived["selected_device"] == "cpu"


def test_bootstrap_readiness_verify_only_uses_existing_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    profile = _build_profile(profile_id="bootstrap-readiness")
    report = type(
        "_Report",
        (),
        {
            "profile": profile,
            "flags": type(
                "_Flags",
                (),
                {
                    "stt_recommended_model": "whisper-large-v3-turbo",
                    "tts_recommended_model": "kokoro-v1.0",
                },
            )(),
        },
    )()

    monkeypatch.setattr(
        "scripts.bootstrap_readiness._run_model_surface",
        lambda *, family, model_name, verify_only: calls.append(
            ("model", (family, model_name, verify_only))
        )
        or 0,
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.run_profiler",
        lambda: report,
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.run_hardware_preflight",
        lambda p: calls.append(("preflight", p.profile_id))
        or {"backend_scope": "stt", "ready": True, "verification_results": []},
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.derive_stt_device_readiness",
        lambda _result: {
            "selected_device": "cpu",
            "selected_device_ready": True,
            "cuda_ready": False,
            "cpu_ready": True,
        },
    )

    rc = bootstrap_readiness.main(["--verify-only"])

    assert rc == 0
    assert calls == [
        ("model", ("stt", "whisper-large-v3-turbo", True)),
        ("model", ("stt", "whisper-small", True)),
        ("model", ("tts", "kokoro-v1.0", True)),
        ("preflight", "bootstrap-readiness"),
    ]


def test_bootstrap_readiness_fails_closed_when_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(profile_id="bootstrap-fail")
    report = type(
        "_Report",
        (),
        {
            "profile": profile,
            "flags": type(
                "_Flags",
                (),
                {
                    "stt_recommended_model": "whisper-large-v3-turbo",
                    "tts_recommended_model": "kokoro-v1.0",
                },
            )(),
        },
    )()
    monkeypatch.setattr(
        "scripts.bootstrap_readiness._run_model_surface",
        lambda *, family, model_name, verify_only: 0,
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.run_profiler",
        lambda: report,
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.run_hardware_preflight",
        lambda _p: {
            "backend_scope": "stt",
            "ready": False,
            "verification_results": [{"token": "dll:cublas64_12.dll", "ok": False}],
        },
    )
    monkeypatch.setattr(
        "scripts.bootstrap_readiness.derive_stt_device_readiness",
        lambda _result: {
            "selected_device": "unavailable",
            "selected_device_ready": False,
            "cuda_ready": False,
            "cpu_ready": False,
        },
    )

    rc = bootstrap_readiness.main(["--verify-only"])
    assert rc == 1
