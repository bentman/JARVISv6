from __future__ import annotations

import json
from pathlib import Path

from backend.app.core.capabilities import HardwareProfile


MANIFEST_DIR = Path("config/hardware")
SUPPORTED_CONDITION_KEYS = {
    "os",
    "arch",
    "gpu_available",
    "gpu_vendor",
    "cuda_available",
    "npu_available",
    "npu_vendor",
    "memory_total_gb",
    "device_class",
}


def _normalize_scalar(value: object) -> object:
    if isinstance(value, str):
        return value.lower()
    return value


def _match_condition(actual: object, expected: object, key: str) -> bool:
    if key == "memory_total_gb":
        if not isinstance(expected, dict):
            raise ValueError("memory_total_gb condition must be an object with min/max")
        min_v = expected.get("min")
        max_v = expected.get("max")
        if min_v is not None and not isinstance(min_v, (int, float)):
            raise ValueError("memory_total_gb.min must be numeric")
        if max_v is not None and not isinstance(max_v, (int, float)):
            raise ValueError("memory_total_gb.max must be numeric")
        if set(expected.keys()) - {"min", "max"}:
            raise ValueError("memory_total_gb only supports min/max keys")
        if not isinstance(actual, (int, float)):
            raise ValueError("memory_total_gb profile value must be numeric")
        value = float(actual)
        if min_v is not None and value < float(min_v):
            return False
        if max_v is not None and value > float(max_v):
            return False
        return True

    if isinstance(expected, (bool, str)):
        return _normalize_scalar(actual) == _normalize_scalar(expected)

    if isinstance(expected, list):
        if not expected:
            raise ValueError("list condition values must not be empty")
        normalized_actual = _normalize_scalar(actual)
        normalized_values = [_normalize_scalar(item) for item in expected]
        return normalized_actual in normalized_values

    raise ValueError(f"unsupported condition shape for {key}")


def _manifest_matches(profile: HardwareProfile, applies_when: dict) -> bool:
    if not isinstance(applies_when, dict):
        raise ValueError("applies_when must be an object")

    profile_map = {
        "os": profile.os,
        "arch": profile.arch,
        "gpu_available": profile.gpu_available,
        "gpu_vendor": profile.gpu_vendor,
        "cuda_available": profile.cuda_available,
        "npu_available": profile.npu_available,
        "npu_vendor": profile.npu_vendor,
        "memory_total_gb": profile.memory_total_gb,
        "device_class": profile.device_class,
    }

    for key, expected in applies_when.items():
        if key not in SUPPORTED_CONDITION_KEYS:
            raise ValueError(f"unsupported condition key: {key}")
        actual = profile_map[key]
        if not _match_condition(actual, expected, key):
            return False

    return True


def _merge_unique_preserve_order(values: list[str], target: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def resolve_hardware_profiles(profile: HardwareProfile) -> dict:
    matched_manifest_ids: list[str] = []
    matched_manifest_paths: list[str] = []
    merged_python_packages: list[str] = []
    merged_pip_extra_index_urls: list[str] = []

    for manifest_path in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        merge_behavior = manifest.get("merge_behavior")
        if merge_behavior != "additive":
            raise ValueError(f"unsupported merge_behavior in {manifest_path.name}: {merge_behavior}")

        applies_when = manifest.get("applies_when")
        if not _manifest_matches(profile, applies_when):
            continue

        additive = manifest.get("additive_requirements")
        if not isinstance(additive, dict):
            raise ValueError(f"invalid additive_requirements in {manifest_path.name}")

        python_packages = additive.get("python_packages")
        if not isinstance(python_packages, list) or not all(isinstance(x, str) for x in python_packages):
            raise ValueError(f"python_packages must be a list[str] in {manifest_path.name}")

        install = additive.get("install", {})
        if not isinstance(install, dict):
            raise ValueError(f"install must be an object in {manifest_path.name}")
        pip_extra_index_urls = install.get("pip_extra_index_urls", [])
        if not isinstance(pip_extra_index_urls, list) or not all(
            isinstance(x, str) and bool(x.strip()) for x in pip_extra_index_urls
        ):
            raise ValueError(f"install.pip_extra_index_urls must be a list[str] in {manifest_path.name}")

        matched_manifest_ids.append(str(manifest.get("manifest_id")))
        matched_manifest_paths.append(str(manifest_path.as_posix()))
        _merge_unique_preserve_order(python_packages, merged_python_packages)
        _merge_unique_preserve_order(pip_extra_index_urls, merged_pip_extra_index_urls)

    return {
        "matched_manifest_ids": matched_manifest_ids,
        "matched_manifest_paths": matched_manifest_paths,
        "merged_additive_requirements": {
            "python_packages": merged_python_packages,
            "install": {
                "pip_extra_index_urls": merged_pip_extra_index_urls,
            },
        },
    }
