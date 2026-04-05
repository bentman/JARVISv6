from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.hardware.preflight import derive_stt_device_readiness, run_hardware_preflight
from backend.app.hardware.profiler import run_profiler


def _run_model_surface(model_name: str, verify_only: bool) -> int:
    command = [
        sys.executable,
        "scripts/ensure_models.py",
        "--family",
        "stt",
        "--model",
        model_name,
    ]
    if verify_only:
        command.append("--verify-only")

    result = subprocess.run(command, check=False)
    return int(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap STT readiness before runtime use")
    parser.add_argument("--model", default="whisper-large-v3-turbo")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    model_rc = _run_model_surface(model_name=args.model, verify_only=args.verify_only)
    if model_rc != 0:
        print(f"[FAILED] stt model ensure/verify failed for {args.model}")
        return 1

    report = run_profiler()
    preflight = run_hardware_preflight(report.profile)
    stt_readiness = derive_stt_device_readiness(preflight)

    backend_scope = str(preflight.get("backend_scope") or "unknown")
    selected_device = str(stt_readiness.get("selected_device") or "unavailable")
    selected_device_ready = bool(stt_readiness.get("selected_device_ready"))
    print(
        "[READINESS] "
        f"backend_scope={backend_scope} "
        f"selected_device={selected_device} "
        f"selected_device_ready={selected_device_ready} "
        f"cuda_ready={bool(stt_readiness.get('cuda_ready'))} "
        f"cpu_ready={bool(stt_readiness.get('cpu_ready'))} "
        f"profile_id={report.profile.profile_id}"
    )

    if backend_scope != "stt":
        print(f"[FAILED] expected backend_scope=stt, got {backend_scope}")
        return 1

    if not selected_device_ready:
        print(f"[FAILED] STT readiness not proven: {preflight.get('verification_results')}")
        return 1

    print(f"[PASS] STT readiness proven for selected device: {selected_device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
