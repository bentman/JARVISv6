from __future__ import annotations

import ctypes
import importlib
import json
import os
import re
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path

from backend.app.core.capabilities import HardwareProfile
from backend.app.hardware.profile_resolver import resolve_hardware_profiles
from backend.app.models.catalog import load_stt_catalog, load_tts_catalog


_HW_GPU_CUDA_MANIFEST_ID = "hw-gpu-nvidia-cuda"
_HW_NPU_PRESENT_MANIFEST_ID = "hw-npu-present"


_SUPPORTED_REQUIREMENT_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*)\])?(>=|==)([A-Za-z0-9_.+-]+)$"
)
_CUDA_DLL_DIRS_INITIALIZED = False
_CUDA_DLL_DIR_HANDLES: list[object] = []


def _canonical_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _merge_unique_preserve_order(values: list[str], target: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def _ensure_backend_venv_interpreter() -> None:
    executable = str(Path(sys.executable).resolve()).replace("\\", "/").lower()
    if "/backend/.venv/" not in executable:
        raise RuntimeError("preflight must run under backend/.venv interpreter")


def _parse_requirement_name(requirement: str) -> str:
    match = _SUPPORTED_REQUIREMENT_RE.fullmatch(requirement)
    if not match:
        raise ValueError(f"unsupported requirement syntax: {requirement}")
    return match.group(1)


def _installed_distribution_names() -> set[str]:
    names: set[str] = set()
    for dist in importlib_metadata.distributions():
        raw_name = dist.metadata.get("Name")
        if isinstance(raw_name, str) and raw_name.strip():
            names.add(_canonical_dist_name(raw_name))
    return names


def _detect_missing_packages(requirements: list[str]) -> list[str]:
    installed = _installed_distribution_names()
    missing: list[str] = []
    for requirement in _dedupe_preserve_order(requirements):
        package_name = _parse_requirement_name(requirement)
        if _canonical_dist_name(package_name) not in installed:
            missing.append(requirement)
    return missing


def _install_missing_packages(
    missing_requirements: list[str],
    pip_extra_index_urls: list[str] | None = None,
) -> list[str]:
    if not missing_requirements:
        return []
    command = [sys.executable, "-m", "pip", "install"]
    for extra_index_url in pip_extra_index_urls or []:
        command.extend(["--extra-index-url", extra_index_url])
    command.extend(missing_requirements)
    subprocess.run(command, check=True, capture_output=True, text=True)
    return list(missing_requirements)


def _verify_evidence_token(token: str) -> dict[str, object]:
    if token.startswith("import:"):
        module_name = token.split(":", 1)[1]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", module_name):
            raise ValueError(f"unsupported import token: {token}")
        importlib.import_module(module_name)
        return {"token": token, "ok": True}

    if token.startswith("dll:"):
        dll_name = token.split(":", 1)[1]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", dll_name):
            raise ValueError(f"unsupported dll token: {token}")
        if sys.platform.startswith("win"):
            _configure_windows_cuda_dll_dirs_for_preflight()
            try:
                ctypes.WinDLL(dll_name)
                return {"token": token, "ok": True}
            except Exception as first_exc:
                for candidate_dir in _candidate_windows_cuda_dll_dirs():
                    candidate_path = candidate_dir / dll_name
                    if not candidate_path.exists():
                        continue
                    try:
                        ctypes.WinDLL(str(candidate_path))
                        return {"token": token, "ok": True}
                    except Exception:
                        continue
                raise first_exc
        return {"token": token, "ok": False, "error": "dll evidence supported on Windows only"}

    if token.startswith("stt_runtime:"):
        runtime_name = token.split(":", 1)[1]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_name):
            raise ValueError(f"unsupported stt_runtime token: {token}")
        catalog = load_stt_catalog()
        runtimes = catalog.get("runtimes")
        is_ready = isinstance(runtimes, dict) and runtime_name in runtimes
        return {"token": token, "ok": bool(is_ready)}

    if token.startswith("tts_runtime:"):
        runtime_name = token.split(":", 1)[1]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_name):
            raise ValueError(f"unsupported tts_runtime token: {token}")
        catalog = load_tts_catalog()
        runtimes = catalog.get("runtimes")
        is_ready = isinstance(runtimes, dict) and runtime_name in runtimes
        return {"token": token, "ok": bool(is_ready)}

    if token == "torch_cuda:available":
        import torch

        return {"token": token, "ok": bool(torch.cuda.is_available())}

    raise ValueError(f"unsupported evidence token: {token}")


def _verify_runtime_evidence(tokens: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for token in tokens:
        try:
            results.append(_verify_evidence_token(token))
        except ValueError:
            # Unsupported token shapes must fail closed.
            raise
        except Exception as exc:
            results.append({"token": token, "ok": False, "error": str(exc)})
    return results


def _candidate_windows_cuda_dll_dirs() -> list[Path]:
    candidate_dirs: list[Path] = []

    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidate_dirs.append(Path(cuda_path) / "bin")

    venv = Path(sys.prefix)
    candidate_dirs.extend(
        [
            venv / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
            venv / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
            venv / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
        ]
    )
    return candidate_dirs


def _configure_windows_cuda_dll_dirs_for_preflight() -> None:
    global _CUDA_DLL_DIRS_INITIALIZED

    if _CUDA_DLL_DIRS_INITIALIZED:
        return
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        _CUDA_DLL_DIRS_INITIALIZED = True
        return

    seen: set[str] = set()
    for dll_dir in _candidate_windows_cuda_dll_dirs():
        resolved = dll_dir.resolve()
        key = str(resolved).lower()
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        try:
            handle = os.add_dll_directory(str(resolved))
            _CUDA_DLL_DIR_HANDLES.append(handle)
        except Exception:
            continue

    _CUDA_DLL_DIRS_INITIALIZED = True


def ensure_windows_cuda_dll_bootstrap() -> None:
    """Single ownership surface for Windows CUDA DLL directory bootstrap."""

    _configure_windows_cuda_dll_dirs_for_preflight()


def _resolve_evidence_tokens_from_caller_boundary(
    backend_scope: str,
    matched_manifest_ids: list[str],
) -> list[str]:
    """Resolve service-specific evidence from caller-owned boundary logic."""

    from backend.app.hardware.profiler import resolve_backend_evidence_tokens

    return resolve_backend_evidence_tokens(backend_scope, matched_manifest_ids)


def run_hardware_preflight(
    profile: HardwareProfile,
    *,
    backend_scope: str = "stt",
    evidence_tokens: list[str] | None = None,
    skip_venv_check: bool = False,
) -> dict[str, object]:
    if not skip_venv_check:
        _ensure_backend_venv_interpreter()

    resolution = resolve_hardware_profiles(profile)
    raw_manifest_ids = list(resolution.get("matched_manifest_ids") or [])
    raw_manifest_paths = list(resolution.get("matched_manifest_paths") or [])

    matched_manifest_ids = [str(item) for item in raw_manifest_ids]
    matched_manifest_paths = [str(item) for item in raw_manifest_paths]
    merged = resolution.get("merged_additive_requirements")
    if not isinstance(merged, dict):
        raise ValueError("invalid merged_additive_requirements from resolver")
    python_packages = merged.get("python_packages", [])
    if not isinstance(python_packages, list) or not all(isinstance(x, str) for x in python_packages):
        raise ValueError("merged python_packages must be a list[str]")
    install = merged.get("install", {})
    if not isinstance(install, dict):
        raise ValueError("merged install must be an object")
    pip_extra_index_urls = install.get("pip_extra_index_urls", [])
    if not isinstance(pip_extra_index_urls, list) or not all(
        isinstance(x, str) and bool(x.strip()) for x in pip_extra_index_urls
    ):
        raise ValueError("merged install.pip_extra_index_urls must be a list[str]")

    required_packages = _dedupe_preserve_order(python_packages)
    if evidence_tokens is None:
        evidence_tokens = _resolve_evidence_tokens_from_caller_boundary(
            backend_scope,
            matched_manifest_ids,
        )
    if not isinstance(evidence_tokens, list) or not all(isinstance(x, str) for x in evidence_tokens):
        raise ValueError("evidence_tokens must be a list[str]")
    evidence_tokens = _dedupe_preserve_order(evidence_tokens)

    missing_packages_before_install = _detect_missing_packages(required_packages)
    installed_packages = _install_missing_packages(
        missing_packages_before_install,
        pip_extra_index_urls=pip_extra_index_urls,
    )
    verification_results = _verify_runtime_evidence(evidence_tokens)

    ready = all(bool(item.get("ok")) for item in verification_results)

    return {
        "backend_scope": backend_scope,
        "profile_id": profile.profile_id,
        "matched_manifest_ids": matched_manifest_ids,
        "required_packages": required_packages,
        "missing_packages_before_install": missing_packages_before_install,
        "installed_packages": installed_packages,
        "verification_results": verification_results,
        "ready": ready,
    }


def derive_backend_device_readiness(
    preflight_result: dict[str, object],
    *,
    cuda_manifest_id: str,
    cuda_required_tokens: list[str],
    cpu_ready_tokens: list[str],
) -> dict[str, object]:
    """Derive backend device readiness from generic preflight verification evidence."""

    raw_verification = preflight_result.get("verification_results")
    if not isinstance(raw_verification, list):
        raise ValueError("invalid preflight verification_results shape")
    verification_results = raw_verification
    token_ok: dict[str, bool] = {}
    for item in verification_results:
        token = item.get("token")
        if not isinstance(token, str):
            continue
        token_ok[token] = bool(item.get("ok"))

    raw_manifest_ids = preflight_result.get("matched_manifest_ids")
    if not isinstance(raw_manifest_ids, list) or not all(
        isinstance(item, str) for item in raw_manifest_ids
    ):
        raise ValueError("invalid preflight matched_manifest_ids shape")
    matched_manifest_ids = raw_manifest_ids
    cuda_manifest_matched = cuda_manifest_id in matched_manifest_ids

    cuda_ready = cuda_manifest_matched and all(token_ok.get(token, False) for token in cuda_required_tokens)
    cpu_ready = all(token_ok.get(token, False) for token in cpu_ready_tokens)

    if cuda_ready:
        selected_device = "cuda"
        selected_device_ready = True
    elif cpu_ready:
        selected_device = "cpu"
        selected_device_ready = True
    else:
        selected_device = "unavailable"
        selected_device_ready = False

    return {
        "matched_manifest_ids": matched_manifest_ids,
        "cuda_ready": cuda_ready,
        "cpu_ready": cpu_ready,
        "selected_device": selected_device,
        "selected_device_ready": selected_device_ready,
    }


def derive_stt_device_readiness(preflight_result: dict[str, object]) -> dict[str, object]:
    """Derive STT device-readiness from preflight verification evidence."""

    return derive_backend_device_readiness(
        preflight_result,
        cuda_manifest_id=_HW_GPU_CUDA_MANIFEST_ID,
        cuda_required_tokens=[
        "import:faster_whisper",
        "import:ctranslate2",
        "stt_runtime:faster-whisper",
        "dll:cublas64_12.dll",
        "dll:cudnn64_9.dll",
        ],
        cpu_ready_tokens=["import:faster_whisper"],
    )


def derive_tts_device_readiness(preflight_result: dict[str, object]) -> dict[str, object]:
    """Derive TTS device-readiness from preflight verification evidence."""

    return derive_backend_device_readiness(
        preflight_result,
        cuda_manifest_id=_HW_GPU_CUDA_MANIFEST_ID,
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




