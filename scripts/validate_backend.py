"""V6 backend validation harness with scoped pytest execution and report output."""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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

    if not Path(suite_path).exists():
        message = f"Directory not found: {suite_path}"
        logger.log(f"[FAIL] {message}")
        return SuiteResult(status="FAIL", summary=message)

    xml_path = Path(f".pytest_{suite_name}_{logger.timestamp}.xml")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        suite_path,
        "--junitxml",
        str(xml_path),
        "-v",
        "--tb=short",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    rows, summary = parse_junit_results(xml_path)
    status = "PASS"
    has_skip = False

    for row_status, test_name in rows:
        if row_status == "PASS":
            logger.log(f"[PASS] PASS: {test_name}")
        elif row_status == "SKIP":
            logger.log(f"[SKIP] SKIP: {test_name}")
            has_skip = True
        else:
            logger.log(f"[FAIL] FAIL: {test_name}")
            status = "FAIL"

    if result.returncode not in (0, 5):
        status = "FAIL"

    if status == "PASS" and has_skip:
        status = "PASS_WITH_SKIPS"

    if status == "FAIL" and not rows:
        stderr_excerpt = ANSI_RE.sub("", (result.stderr or result.stdout or "")).strip()
        if stderr_excerpt:
            logger.log(stderr_excerpt[:1000])

    logger.log(f"{status}: {suite_name}: {summary}")

    try:
        xml_path.unlink(missing_ok=True)
    except Exception:
        pass

    return SuiteResult(status=status, summary=summary)


def main(argv: list[str]) -> int:
    try:
        selected_suites = parse_scope(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    logger = ValidationLogger()
    results: dict[str, SuiteResult] = {}

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
