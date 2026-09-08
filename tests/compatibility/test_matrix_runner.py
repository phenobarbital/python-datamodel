"""The platform matrix aggregator must be impossible to satisfy loosely.

FEAT-2 / TASK-21. AC12 needs evidence from ten cells (Linux x86_64 and Windows
AMD64 × CPython 3.10–3.14). The danger with a matrix report is not that it says
"no" — it is that it says "yes" on the strength of cells that never ran, cells
built from different sources, or wheels that were only imported.

So these tests are almost entirely about **rejection**: for each way the
evidence can be inadequate, the aggregator must refuse to certify and must say
why. A `certified` that cannot be made False on bad input is worthless.

The runner itself (`run_cell`) builds real virtualenvs and is exercised
separately; what is asserted here is the logic that decides whether a set of
results is good enough to release on.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.matrix import (  # noqa: E402
    FAIL,
    PASS,
    REQUIRED_CELLS,
    REQUIRED_PLATFORMS,
    REQUIRED_PYTHONS,
    UNAVAILABLE,
    CellResult,
    MatrixReport,
    local_platform_tag,
    source_fingerprint,
)

FINGERPRINT = "a" * 64


def _good_cell(platform: str, python: str) -> CellResult:
    return CellResult(
        platform=platform, python=python, status=PASS,
        source_fingerprint=FINGERPRINT,
        interpreter_version=f"{python}.0",
        tests_passed=700, tests_failed=0, tests_skipped=2,
        has_rust_parsers=True, asyncdb_verified=True,
        experimental_native_absent=True,
        commands=["uv pip install -e '.[dev]'", "python -m pytest tests/ -q"],
    )


def _full_report() -> MatrixReport:
    report = MatrixReport(expected_fingerprint=FINGERPRINT)
    for platform, python in REQUIRED_CELLS:
        report.add(_good_cell(platform, python))
    return report


# ===========================================================================
# Part 1 -- the required shape
# ===========================================================================


def test_ten_cells_are_required():
    assert len(REQUIRED_CELLS) == 10
    assert set(REQUIRED_PLATFORMS) == {"linux-x86_64", "windows-amd64"}
    assert set(REQUIRED_PYTHONS) == {"3.10", "3.11", "3.12", "3.13", "3.14"}


def test_a_complete_clean_matrix_certifies():
    """The positive control: certification must be reachable at all."""
    report = _full_report()
    assert report.problems() == []
    assert report.certified is True
    assert report.summary()["cells_with_evidence"] == 10


# ===========================================================================
# Part 2 -- every way the evidence can be inadequate
# ===========================================================================


def test_a_missing_cell_blocks_certification():
    report = _full_report()
    del report.cells[("windows-amd64", "3.12")]
    problems = report.problems()
    assert not report.certified
    assert any("windows-amd64" in p and "3.12" in p and "NO EVIDENCE" in p
               for p in problems), problems


def test_every_single_missing_cell_is_detected():
    """Not just the first one: each of the ten must be individually required."""
    for platform, python in REQUIRED_CELLS:
        report = _full_report()
        del report.cells[(platform, python)]
        assert not report.certified, f"{platform}/{python} was not required"


def test_an_unavailable_cell_is_not_a_skip():
    """The failure mode this whole task exists to prevent."""
    report = _full_report()
    report.add(CellResult(platform="windows-amd64", python="3.14",
                          status=UNAVAILABLE, reason="no Windows runner"))
    problems = report.problems()
    assert not report.certified
    assert any("unavailable" in p and "not a skip" in p for p in problems), problems


def test_a_failed_cell_blocks_certification():
    report = _full_report()
    failed = _good_cell("linux-x86_64", "3.11")
    failed.status = FAIL
    failed.tests_failed = 3
    report.add(failed)
    assert not report.certified
    assert any("FAILED" in p for p in report.problems())


def test_an_import_only_smoke_test_is_not_evidence():
    """A wheel that merely imports proves nothing about behaviour."""
    report = _full_report()
    smoke = _good_cell("linux-x86_64", "3.10")
    smoke.tests_passed = 0          # imported fine, ran nothing
    report.add(smoke)
    assert smoke.is_import_only is True
    assert not report.certified
    assert any("import-only" in p for p in report.problems())


def test_a_stale_artifact_reference_blocks_certification():
    """Cells built from different sources are not comparable evidence."""
    report = _full_report()
    stale = _good_cell("linux-x86_64", "3.12")
    stale.source_fingerprint = "b" * 64
    report.add(stale)
    assert not report.certified
    assert any("STALE ARTIFACT" in p for p in report.problems())


def test_a_cell_without_asyncdb_verification_blocks_certification():
    """AC12 names the real consumer explicitly."""
    report = _full_report()
    unverified = _good_cell("windows-amd64", "3.10")
    unverified.asyncdb_verified = False
    report.add(unverified)
    assert not report.certified
    assert any("asyncdb" in p for p in report.problems())


def test_problems_are_reported_for_every_bad_cell_not_just_the_first():
    report = _full_report()
    del report.cells[("windows-amd64", "3.10")]
    broken = _good_cell("windows-amd64", "3.11")
    broken.status = FAIL
    report.add(broken)
    stale = _good_cell("linux-x86_64", "3.13")
    stale.source_fingerprint = "c" * 64
    report.add(stale)
    assert len(report.problems()) >= 3


def test_an_empty_report_certifies_nothing():
    report = MatrixReport(expected_fingerprint=FINGERPRINT)
    assert not report.certified
    assert len(report.problems()) == 10


# ===========================================================================
# Part 3 -- the fingerprint actually identifies the sources
# ===========================================================================


def test_source_fingerprint_is_stable_and_real():
    first = source_fingerprint()
    second = source_fingerprint()
    assert first == second
    assert len(first) == 64


def test_source_fingerprint_changes_when_a_source_changes(tmp_path):
    root = tmp_path / "repo"
    (root / "datamodel").mkdir(parents=True)
    target = root / "datamodel" / "thing.py"
    target.write_text("x = 1\n")
    before = source_fingerprint(root)
    target.write_text("x = 2\n")
    assert source_fingerprint(root) != before, (
        "the fingerprint ignored a source change, so stale artifacts would "
        "pass unnoticed"
    )


def test_summary_lists_every_required_cell_even_when_absent():
    report = MatrixReport(expected_fingerprint=FINGERPRINT)
    report.add(_good_cell("linux-x86_64", "3.13"))
    summary = report.summary()
    assert len(summary["cells"]) == 10
    assert summary["cells"]["windows-amd64/3.14"]["status"] == "missing"
    assert summary["certified"] is False


# ===========================================================================
# Part 4 -- the recorded matrix report
# ===========================================================================


def test_platform_tag_is_recognised():
    tag = local_platform_tag()
    assert tag in REQUIRED_PLATFORMS or "-" in tag


def test_the_platform_report_exists_and_is_honest():
    """The persisted report must not claim certification it does not have."""
    import json

    report_path = (
        Path(__file__).resolve().parents[2] / "benchmarks" / "results"
        / "compatible-model-performance" / "platforms.json"
    )
    assert report_path.is_file(), f"{report_path} is missing"
    persisted = json.loads(report_path.read_text(encoding="utf-8"))

    assert set(persisted["cells"]) == {
        f"{plat}/{ver}" for plat, ver in REQUIRED_CELLS
    }
    if persisted["certified"]:
        assert not persisted["problems"], (
            "the report claims certification while listing problems"
        )
    else:
        assert persisted["problems"], (
            "the report says it is not certified but lists no reason"
        )
    assert persisted["required_cells"] == 10


def test_the_platform_report_does_not_count_unavailable_cells_as_evidence():
    import json

    report_path = (
        Path(__file__).resolve().parents[2] / "benchmarks" / "results"
        / "compatible-model-performance" / "platforms.json"
    )
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    evidence = persisted["cells_with_evidence"]
    counted = sum(
        1 for cell in persisted["cells"].values()
        if cell.get("status") == PASS and not cell.get("is_import_only", False)
    )
    assert evidence == counted, (
        "cells_with_evidence disagrees with the per-cell statuses"
    )
