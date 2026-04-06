"""V6 backend validation harness with scoped pytest execution and report output."""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.hardware.preflight import derive_stt_device_readiness, run_hardware_preflight
from backend.app.hardware.profiler import run_profiler
from backend.app.models.catalog import get_model_entry, get_tts_model_entry
from backend.app.models.manager import verify_model


SUITES: dict[str, str] = {
    "unit": "backend/tests/unit",
    "runtime": "backend/tests/runtime",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class ValidationLogger:
    """Mirror output to console and a timestamped report file."""

    def __init__(self) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.report_path = self.report_dir / f"backend_validation_report_{self.timestamp}.txt"
        self._buffer: list[str] = []

        self.log(f"JARVISv6 Backend Validation Session started at {datetime.now().isoformat()}")
        self.log(f"Report File: {self.report_path}")
        self.log("=" * 60)

    def log(self, message: str) -> None:
        print(message)
        self._buffer.append(message)

    def header(self, title: str) -> None:
        self.log("")
        self.log("=" * 60)
        self.log(title.upper())
        self.log("=" * 60)

    def save(self) -> None:
        self.report_path.write_text("\n".join(self._buffer) + "\n", encoding="utf-8")
        print(f"\n[SUCCESS] Report saved to {self.report_path}")


def parse_scope(argv: list[str]) -> list[str]:
    if "--scope" not in argv:
        return ["unit", "runtime"]

    index = argv.index("--scope")
    if index + 1 >= len(argv):
        raise ValueError("--scope requires a value: all|unit|runtime")

    scope = argv[index + 1].strip().lower()
    if scope == "all":
        return ["unit", "runtime"]
    if scope in SUITES:
        return [scope]

    raise ValueError(f"Invalid --scope '{scope}'. Use: all|unit|runtime")


@dataclass
class SuiteResult:
    status: str
    summary: str


def run_runtime_readiness_gate(logger: ValidationLogger) -> SuiteResult:
    """Fail-closed STT readiness gate before runtime suite execution."""

    logger.header("runtime readiness gate")
    try:
        report = run_profiler()
        preflight = run_hardware_preflight(report.profile)
        stt_readiness = derive_stt_device_readiness(preflight)
    except Exception as exc:
        message = f"readiness gate failed before runtime tests: {exc}"
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    backend_scope = str(preflight.get("backend_scope") or "")
    selected_device = str(stt_readiness.get("selected_device") or "unavailable")
    selected_device_ready = bool(stt_readiness.get("selected_device_ready"))
    logger.log(
        f"[READINESS] backend_scope={backend_scope or 'unknown'} "
        f"selected_device={selected_device} "
        f"selected_device_ready={selected_device_ready} "
        f"cuda_ready={bool(stt_readiness.get('cuda_ready'))} "
        f"cpu_ready={bool(stt_readiness.get('cpu_ready'))} "
        f"profile_id={report.profile.profile_id}"
    )

    if backend_scope != "stt":
        message = f"readiness gate expected backend_scope=stt but got '{backend_scope or 'unknown'}'"
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    if not selected_device_ready:
        verification_results = preflight.get("verification_results")
        message = (
            f"readiness gate failed: selected STT device '{selected_device}' not proven "
            f"({verification_results})"
        )
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    message = f"STT readiness proven for selected device '{selected_device}'; proceeding to runtime tests"
    logger.log(f"[PASS] {message}")
    return SuiteResult(status="PASS", summary=message)


def _resolve_runtime_voice_model_prerequisites() -> list[dict[str, str]]:
    report = run_profiler()

    stt_model = report.flags.stt_recommended_model
    stt_entry = get_model_entry(stt_model)
    stt_local_dir = stt_entry.get("local_dir")
    if not isinstance(stt_local_dir, str) or not stt_local_dir.strip():
        raise RuntimeError(f"invalid STT catalog local_dir for model '{stt_model}'")

    tts_model = report.flags.tts_recommended_model
    tts_entry = get_tts_model_entry(tts_model)
    tts_local_dir = tts_entry.get("local_dir")
    if not isinstance(tts_local_dir, str) or not tts_local_dir.strip():
        raise RuntimeError(f"invalid TTS catalog local_dir for model '{tts_model}'")

    return [
        {"family": "stt", "model": stt_model, "local_dir": stt_local_dir},
        {"family": "tts", "model": tts_model, "local_dir": tts_local_dir},
    ]


def run_runtime_voice_model_prereq_gate(logger: ValidationLogger) -> SuiteResult:
    """Fail-closed voice-model prerequisite gate before runtime suite execution."""

    logger.header("runtime voice model prerequisite gate")
    try:
        requirements = _resolve_runtime_voice_model_prerequisites()
    except Exception as exc:
        message = f"voice-model prerequisite resolution failed before runtime tests: {exc}"
        logger.log(f"[PREREQ FAILED] {message}")
        return SuiteResult(status="FAIL", summary=message)

    missing: list[str] = []
    for requirement in requirements:
        family = requirement["family"]
        model = requirement["model"]
        local_dir = requirement["local_dir"]
        if verify_model(local_dir, family=family):
            logger.log(f"[PREREQ PASS] {family}:{model} present at {local_dir}")
            continue
        missing.append(f"{family}:{model} -> {local_dir}")
        logger.log(f"[PREREQ FAILED] {family}:{model} missing at {local_dir}")

    if missing:
        message = "missing required voice-model assets: " + "; ".join(missing)
        logger.log(f"[PREREQ FAILED] {message}")
        return SuiteResult(status="FAIL", summary=message)

    message = "required voice-model assets are present; proceeding to runtime readiness gate"
    logger.log(f"[PASS] {message}")
    return SuiteResult(status="PASS", summary=message)


def parse_junit_results(xml_path: Path) -> tuple[list[tuple[str, str]], str]:
    if not xml_path.exists():
        return [], "No XML report generated"

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as exc:  # pragma: no cover - fail-safe harness path
        return [], f"XML parsing error: {exc}"

    if root.tag == "testsuites":
        testsuites = [node for node in root if node.tag == "testsuite"]
    elif root.tag == "testsuite":
        testsuites = [root]
    else:
        testsuites = []

    rows: list[tuple[str, str]] = []
    failures = 0
    errors = 0
    skipped = 0
    total = 0

    for suite in testsuites:
        for case in suite.findall("testcase"):
            total += 1
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            full_name = f"{classname}::{name}" if classname else name

            if case.find("failure") is not None:
                rows.append(("FAIL", full_name))
                failures += 1
            elif case.find("error") is not None:
                rows.append(("FAIL", full_name))
                errors += 1
            elif case.find("skipped") is not None:
                rows.append(("SKIP", full_name))
                skipped += 1
            else:
                rows.append(("PASS", full_name))

    summary_parts = [f"{total} tests"]
    if failures:
        summary_parts.append(f"{failures} failed")
    if errors:
        summary_parts.append(f"{errors} errors")
    if skipped:
        summary_parts.append(f"{skipped} skipped")

    return rows, ", ".join(summary_parts)


def run_pytest_suite(logger: ValidationLogger, suite_name: str, suite_path: str) -> SuiteResult:
    logger.header(f"{suite_name} tests")

    suite_root = Path(suite_path)
    if not suite_root.exists():
        message = f"Directory not found: {suite_path}"
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    status = "PASS"
    has_skip = False
    total = 0
    failures = 0
    errors = 0
    skipped = 0

    if suite_name == "runtime":
        targets = sorted(suite_root.glob("test_*.py"))
    else:
        targets = [suite_root]

    if not targets:
        message = f"No pytest targets found: {suite_path}"
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    for target in targets:
        xml_path = Path(f".pytest_{suite_name}_{target.stem}_{logger.timestamp}.xml")
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(target),
            "--junitxml",
            str(xml_path),
            "-v",
            "--tb=short",
        ]
        if suite_name == "runtime":
            cmd.append("-s")

        result = subprocess.run(cmd, text=True)
        rows, _summary = parse_junit_results(xml_path)

        for row_status, test_name in rows:
            total += 1
            if row_status == "PASS":
                logger.log(f"[PASS] PASS: {test_name}")
            elif row_status == "SKIP":
                logger.log(f"[SKIP] SKIP: {test_name}")
                has_skip = True
                skipped += 1
            else:
                logger.log(f"[FAIL] FAIL: {test_name}")
                status = "FAIL"
                failures += 1

        if result.returncode not in (0, 5):
            status = "FAIL"
            if not rows:
                logger.log(f"[FAIL] pytest returned non-zero for target: {target}")

        try:
            xml_path.unlink(missing_ok=True)
        except Exception:
            pass

    if status == "PASS" and has_skip:
        status = "PASS_WITH_SKIPS"

    summary_parts = [f"{total} tests"]
    if failures:
        summary_parts.append(f"{failures} failed")
    if errors:
        summary_parts.append(f"{errors} errors")
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    summary = ", ".join(summary_parts)
    logger.log(f"{status}: {suite_name}: {summary}")

    return SuiteResult(status=status, summary=summary)


def main(argv: list[str]) -> int:
    try:
        selected_suites = parse_scope(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    logger = ValidationLogger()
    results: dict[str, SuiteResult] = {}

    if "runtime" in selected_suites:
        prereq_gate = run_runtime_voice_model_prereq_gate(logger)
        if prereq_gate.status == "FAIL":
            results["runtime"] = prereq_gate
            if "unit" in selected_suites:
                logger.header("unit tests")
                logger.log("[SKIP] unit suite not executed because runtime voice-model prerequisite gate failed")
                results["unit"] = SuiteResult(
                    status="PASS_WITH_SKIPS",
                    summary="0 tests, 1 skipped (runtime voice-model prerequisite gate failed)",
                )

            logger.header("Validation Summary")
            for suite_name in selected_suites:
                logger.log(f"{suite_name.upper()}: {results[suite_name].status}")
            logger.log("=" * 60)
            logger.log("")
            logger.log("[INVARIANTS]")
            for suite_name in selected_suites:
                logger.log(f"{suite_name.upper()}={results[suite_name].status}")
            logger.log("\n[FAIL] Validation failed - runtime voice-model prerequisite gate did not pass")
            logger.save()
            return 1

        gate = run_runtime_readiness_gate(logger)
        if gate.status == "FAIL":
            results["runtime"] = gate
            if "unit" in selected_suites:
                logger.header("unit tests")
                logger.log("[SKIP] unit suite not executed because runtime readiness gate failed")
                results["unit"] = SuiteResult(
                    status="PASS_WITH_SKIPS",
                    summary="0 tests, 1 skipped (runtime readiness gate failed)",
                )

            logger.header("Validation Summary")
            for suite_name in selected_suites:
                logger.log(f"{suite_name.upper()}: {results[suite_name].status}")
            logger.log("=" * 60)
            logger.log("")
            logger.log("[INVARIANTS]")
            for suite_name in selected_suites:
                logger.log(f"{suite_name.upper()}={results[suite_name].status}")
            logger.log("\n[FAIL] Validation failed - runtime readiness gate did not pass")
            logger.save()
            return 1

    for suite_name in selected_suites:
        results[suite_name] = run_pytest_suite(logger, suite_name, SUITES[suite_name])

    logger.header("Validation Summary")
    for suite_name in selected_suites:
        logger.log(f"{suite_name.upper()}: {results[suite_name].status}")
    logger.log("=" * 60)
    logger.log("")
    logger.log("[INVARIANTS]")
    for suite_name in selected_suites:
        logger.log(f"{suite_name.upper()}={results[suite_name].status}")

    has_fail = any(r.status == "FAIL" for r in results.values())
    has_skips = any(r.status == "PASS_WITH_SKIPS" for r in results.values())

    if has_fail:
        logger.log("\n[FAIL] Validation failed - see suite output above")
        exit_code = 1
    elif has_skips:
        logger.log("\n[PASS] JARVISv6 backend is VALIDATED WITH EXPECTED SKIPS!")
        exit_code = 0
    else:
        logger.log("\n[PASS] JARVISv6 backend is validated!")
        exit_code = 0

    logger.save()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
