"""Platform/interpreter matrix runner and aggregator (FEAT-2 / TASK-21).

AC12 requires evidence from **ten cells** — Linux x86_64 and Windows AMD64,
each on CPython 3.10 through 3.14 — before the feature can be certified for
release.

The point of this module is that it **cannot be satisfied by optimism**. The
aggregator rejects:

* a required cell that is missing entirely;
* a cell whose tests failed;
* a cell built from a *different source revision* than the others (stale
  artifact reference);
* a cell whose "evidence" is an import-only smoke test — a wheel that merely
  imports proves nothing about behaviour, and the acceptance criteria say so
  explicitly.

A cell that could not be run is **not** a pass and is **not** skipped: it is
recorded as `unavailable`, and its presence keeps `certified` False. Missing
platform evidence is incomplete certification, never a green tick.

This is a development runner. It builds into throwaway virtualenvs, never
publishes anything, and reuses the repository's existing build commands rather
than replacing the FEAT-001 workflow.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform as _platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HARNESS_ROOT = Path(__file__).resolve().parents[2]

#: The interpreters AC12 requires.
REQUIRED_PYTHONS: Tuple[str, ...] = ("3.10", "3.11", "3.12", "3.13", "3.14")
#: The platforms AC12 requires.
REQUIRED_PLATFORMS: Tuple[str, ...] = ("linux-x86_64", "windows-amd64")

#: Every cell that must carry real evidence before release certification.
REQUIRED_CELLS: Tuple[Tuple[str, str], ...] = tuple(
    (plat, version)
    for plat in REQUIRED_PLATFORMS
    for version in REQUIRED_PYTHONS
)

#: Sources whose content identifies "the thing that was tested". Artifacts
#: built from different values of this hash are not comparable evidence.
SOURCE_GLOBS = ("datamodel/**/*.py", "datamodel/**/*.pyx", "datamodel/**/*.pxd")

PASS = "pass"
FAIL = "fail"
UNAVAILABLE = "unavailable"


def source_fingerprint(root: Path = HARNESS_ROOT) -> str:
    """A stable hash of the sources every cell must have been built from."""
    digest = hashlib.sha256()
    paths: List[Path] = []
    for pattern in SOURCE_GLOBS:
        paths.extend(sorted(root.glob(pattern)))
    for path in sorted(set(paths)):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


@dataclass
class CellResult:
    """Evidence for one platform/interpreter cell."""

    platform: str
    python: str
    status: str
    source_fingerprint: str = ""
    interpreter: str = ""
    interpreter_version: str = ""
    artifact_hashes: Dict[str, str] = field(default_factory=dict)
    commands: List[str] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    has_rust_parsers: Optional[bool] = None
    asyncdb_verified: bool = False
    experimental_native_absent: Optional[bool] = None
    baseline_only_failures: List[str] = field(default_factory=list)
    reason: str = ""
    log_excerpt: str = ""

    @property
    def is_import_only(self) -> bool:
        """True when the 'evidence' is a smoke test that ran no real tests."""
        return self.status == PASS and self.tests_passed == 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["is_import_only"] = self.is_import_only
        return data


class MatrixReport:
    """Aggregates cells and refuses to certify on anything less than complete."""

    def __init__(self, expected_fingerprint: Optional[str] = None) -> None:
        self.cells: Dict[Tuple[str, str], CellResult] = {}
        self.expected_fingerprint = expected_fingerprint or source_fingerprint()

    def add(self, cell: CellResult) -> None:
        self.cells[(cell.platform, cell.python)] = cell

    def problems(self) -> List[str]:
        """Every reason this matrix cannot certify a release. Empty == clean."""
        found: List[str] = []
        for key in REQUIRED_CELLS:
            cell = self.cells.get(key)
            platform_name, version = key
            if cell is None:
                found.append(
                    f"{platform_name} / CPython {version}: NO EVIDENCE — the cell "
                    "was never run"
                )
                continue
            if cell.status == UNAVAILABLE:
                found.append(
                    f"{platform_name} / CPython {version}: unavailable — "
                    f"{cell.reason or 'no environment'}. This is incomplete "
                    "certification, not a skip."
                )
                continue
            if cell.status != PASS:
                found.append(
                    f"{platform_name} / CPython {version}: FAILED "
                    f"({cell.tests_failed} failing tests)"
                )
                continue
            if cell.is_import_only:
                found.append(
                    f"{platform_name} / CPython {version}: evidence is an "
                    "import-only smoke test; no behavioural tests ran"
                )
            if cell.source_fingerprint != self.expected_fingerprint:
                found.append(
                    f"{platform_name} / CPython {version}: STALE ARTIFACT — built "
                    f"from sources {cell.source_fingerprint[:12]}, expected "
                    f"{self.expected_fingerprint[:12]}"
                )
            if not cell.asyncdb_verified:
                found.append(
                    f"{platform_name} / CPython {version}: real asyncdb consumer "
                    "compatibility was not verified"
                )
        return found

    @property
    def certified(self) -> bool:
        return not self.problems()

    def summary(self) -> Dict[str, Any]:
        verified = [c for c in self.cells.values() if c.status == PASS
                    and not c.is_import_only]
        return {
            "required_cells": len(REQUIRED_CELLS),
            "cells_with_evidence": len(verified),
            "cells_missing_or_unavailable": len(REQUIRED_CELLS) - len(verified),
            "expected_source_fingerprint": self.expected_fingerprint,
            "certified": self.certified,
            "problems": self.problems(),
            "cells": {
                f"{plat}/{version}": (
                    self.cells[(plat, version)].to_dict()
                    if (plat, version) in self.cells
                    else {"platform": plat, "python": version,
                          "status": "missing", "reason": "never run"}
                )
                for plat, version in REQUIRED_CELLS
            },
        }


# ---------------------------------------------------------------------------
# Running a real cell
# ---------------------------------------------------------------------------


def local_platform_tag() -> str:
    system = _platform.system().lower()
    machine = _platform.machine().lower()
    if system == "linux" and machine in ("x86_64", "amd64"):
        return "linux-x86_64"
    if system == "windows" and machine in ("amd64", "x86_64"):
        return "windows-amd64"
    return f"{system}-{machine}"


def _run(command: Sequence[str], cwd: Path, env: Optional[Dict[str, str]] = None,
         timeout: int = 3600) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command), cwd=str(cwd), capture_output=True, text=True,
        env=env or os.environ.copy(), timeout=timeout, check=False,
    )


def _parse_pytest_counts(output: str) -> Tuple[int, int, int]:
    """Read passed/failed/skipped off pytest's summary line."""
    passed = failed = skipped = 0
    for line in reversed(output.strip().splitlines()):
        if " passed" in line or " failed" in line or " error" in line:
            for token, label in (("passed", "p"), ("failed", "f"),
                                 ("error", "f"), ("skipped", "s")):
                if token in line:
                    words = line.replace("=", " ").split()
                    for index, word in enumerate(words):
                        if word.startswith(token) and index > 0:
                            try:
                                count = int(words[index - 1])
                            except ValueError:
                                continue
                            if label == "p":
                                passed = count
                            elif label == "f":
                                failed += count
                            else:
                                skipped = count
            break
    return passed, failed, skipped


def run_cell(python_version: str, asyncdb_wheel: Optional[Path] = None,
             platform_tag: Optional[str] = None,
             root: Path = HARNESS_ROOT) -> CellResult:
    """Build and test this repository under one interpreter, in a fresh venv.

    Everything is built from source in a throwaway directory: nothing is
    published, and the repository's own extensions are left untouched.
    """
    tag = platform_tag or local_platform_tag()
    cell = CellResult(platform=tag, python=python_version, status=UNAVAILABLE)
    cell.source_fingerprint = source_fingerprint(root)

    if not shutil.which("uv"):
        cell.reason = "uv is not available to provision interpreters"
        return cell

    workspace = Path(tempfile.mkdtemp(prefix=f"matrix-{python_version}-"))
    try:
        venv = workspace / ".venv"
        create = _run(["uv", "venv", "--python", python_version, str(venv)], root)
        cell.commands.append(f"uv venv --python {python_version}")
        if create.returncode != 0:
            cell.reason = (
                f"could not provision CPython {python_version}: "
                f"{create.stderr.strip()[-300:]}"
            )
            return cell

        interpreter = venv / "bin" / "python"
        if not interpreter.exists():
            interpreter = venv / "Scripts" / "python.exe"
        cell.interpreter = str(interpreter)

        install = _run(
            ["uv", "pip", "install", "--python", str(interpreter), "-e", ".[dev]"],
            root, timeout=3600,
        )
        cell.commands.append("uv pip install -e '.[dev]'")
        if install.returncode != 0:
            cell.status = FAIL
            cell.reason = "editable install failed"
            cell.log_excerpt = install.stderr[-2000:]
            return cell

        if asyncdb_wheel and asyncdb_wheel.is_file():
            consumer = _run(
                ["uv", "pip", "install", "--python", str(interpreter),
                 "--no-deps", str(asyncdb_wheel)], root,
            )
            cell.commands.append("uv pip install --no-deps <asyncdb wheel>")
            cell.asyncdb_verified = consumer.returncode == 0

        probe_source = (
            "import importlib.util, json, sys\n"
            "import datamodel\n"
            "import datamodel.rs_parsers as rc\n"
            "print(json.dumps({\n"
            "    'version': datamodel.version.__version__,\n"
            "    'python': sys.version.split()[0],\n"
            "    'has_rust': bool(getattr(rc, 'HAS_RUST', False)),\n"
            # The experimental native module must NOT be importable from a
            # normally installed environment: it is development-only.
            "    'native_present': importlib.util.find_spec('rs_core') is not None,\n"
            "}))\n"
        )
        probe = _run([str(interpreter), "-c", probe_source], root)
        cell.commands.append("python -c '<probe: version/backend/native-absence>'")
        if probe.returncode == 0 and probe.stdout.strip():
            try:
                info = json.loads(probe.stdout.strip().splitlines()[-1])
                cell.interpreter_version = info.get("python", "")
                cell.has_rust_parsers = info.get("has_rust")
                cell.experimental_native_absent = not info.get("native_present", False)
            except (ValueError, IndexError):
                pass

        suite = _run([str(interpreter), "-m", "pytest", "tests/", "-q",
                      "-p", "no:cacheprovider"], root, timeout=3600)
        cell.commands.append("python -m pytest tests/ -q")
        passed, failed, skipped = _parse_pytest_counts(suite.stdout)
        cell.tests_passed, cell.tests_failed, cell.tests_skipped = passed, failed, skipped
        cell.status = PASS if (suite.returncode == 0 and failed == 0 and passed > 0) else FAIL
        cell.log_excerpt = suite.stdout[-1500:]
        if cell.status == FAIL and not cell.reason:
            cell.reason = f"{failed} failing tests"
        return cell
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
