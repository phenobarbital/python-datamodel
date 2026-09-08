#!/usr/bin/env python
"""Count generic ``_validation_`` dispatches in a separate profiling build.

FEAT-2 / TASK-13.  The gate in ``converters.pyx`` claims that an exactly-typed
supported scalar no longer reaches the generic ``_validation_`` dispatch.  This
script *measures* that claim rather than asserting it.

Why a separate build
====================

The counter is guarded by a C macro, ``DATAMODEL_PROFILE_VALIDATION``, which
defaults to ``0``.  Because it is a compile-time constant, the C compiler folds
the guarded branch away completely: a release build contains no counter and no
test of a counter, so diagnostic instrumentation cannot affect release timings.
The trade-off is that counting requires a build with the macro defined -- which
is what this script produces, in a temporary directory, leaving the worktree's
own artifacts untouched.

Usage
=====

::

    python tests/compatibility/profile_validation.py            # 20,000 builds
    python tests/compatibility/profile_validation.py --builds 100
    python tests/compatibility/profile_validation.py --keep     # keep the build

The script prints a table and exits non-zero if any budget is exceeded, so it
can be used as a gate as well as a report.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[2]

#: Acceptance budgets from the task.  "dispatches per build", not per field.
BUDGETS = {
    # Employee has 11 fields: 9 exact supported scalars (which the gate must
    # take over) and 2 typing fields, List[str] and Optional[Employee], which
    # legitimately still dispatch.
    "employee_raw": 3,
    "employee_native": 3,
    # Every field is an unconstrained supported scalar, so nothing may reach
    # the generic dispatch at all.
    "unconstrained_native": 0,
}

_CHILD = r'''
import json, sys
root = sys.argv[1]
harness = sys.argv[2]
builds = int(sys.argv[3])

sys.path.insert(0, root)
import datamodel
loaded = datamodel.__file__
if not loaded.startswith(root):
    raise SystemExit("profiling build not loaded: %s" % loaded)

from datamodel.validation import (
    profiling_compiled_in, generic_dispatch_count, reset_generic_dispatch_count,
)
if not profiling_compiled_in():
    raise SystemExit("this build has no counters compiled in")

while root in sys.path:
    sys.path.remove(root)
sys.path.insert(0, harness)
from tests.fixtures.model_performance import cases as C

report = {"datamodel_file": loaded, "builds": builds, "workloads": {}}
for name in ("employee_raw", "employee_native", "unconstrained_native"):
    case = C.CASES_BY_NAME[name]
    model = case.resolve_model()
    payload = case.build()
    model(**payload)                      # warm up class construction
    reset_generic_dispatch_count()
    for _ in range(builds):
        model(**case.build())
    total = generic_dispatch_count()
    report["workloads"][name] = {
        "total_dispatches": total,
        "per_build": total / builds,
        "fields": len(model.__columns__),
    }
print(json.dumps(report))
'''


def _build_profiling_tree(destination: Path) -> Path:
    """Copy the package and build it with the counter macro defined."""
    root = destination / "profiling_build"
    root.mkdir(parents=True, exist_ok=True)

    shutil.copytree(HARNESS_ROOT / "datamodel", root / "datamodel")
    for name in ("setup.py", "pyproject.toml", "README.md"):
        source = HARNESS_ROOT / name
        if source.is_file():
            shutil.copy2(source, root / name)

    # Force a real recompile: a copied .c/.so would otherwise be considered
    # up to date and the macro would never reach the compiler.
    for pattern in ("*.c", "*.so", "*.html"):
        for stale in (root / "datamodel").rglob(pattern):
            # Keep the Rust extension: it is not built from .pyx here.
            if "rs_parsers" in stale.parts and stale.suffix == ".so":
                continue
            stale.unlink()

    environment = dict(os.environ)
    existing = environment.get("CFLAGS", "")
    environment["CFLAGS"] = (existing + " -DDATAMODEL_PROFILE_VALIDATION=1").strip()

    completed = subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=str(root), env=environment, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "profiling build failed\n--- stdout ---\n"
            f"{completed.stdout[-4000:]}\n--- stderr ---\n{completed.stderr[-4000:]}"
        )
    return root


def run(builds: int, keep: bool) -> dict:
    workspace = Path(tempfile.mkdtemp(prefix="datamodel-profile-"))
    try:
        root = _build_profiling_tree(workspace)
        completed = subprocess.run(
            [sys.executable, "-c", _CHILD, str(root), str(HARNESS_ROOT), str(builds)],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONNOUSERSITE": "1",
                 "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode != 0:
            raise SystemExit(
                f"profiling run failed\n{completed.stdout}\n{completed.stderr}"
            )
        report = json.loads(completed.stdout)
    finally:
        if keep:
            print(f"profiling build kept at {workspace}", file=sys.stderr)
        else:
            shutil.rmtree(workspace, ignore_errors=True)

    report["budgets"] = BUDGETS
    report["python"] = sys.version
    report["platform"] = sysconfig.get_platform()
    violations = []
    for name, budget in BUDGETS.items():
        measured = report["workloads"][name]["per_build"]
        if measured > budget:
            violations.append(
                f"{name}: {measured:.3f} dispatches/build exceeds budget {budget}"
            )
    report["violations"] = violations
    report["within_budget"] = not violations
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--builds", type=int, default=20_000)
    parser.add_argument("--keep", action="store_true",
                        help="do not delete the temporary profiling build")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run(args.builds, args.keep)

    print(f"profiling build: {report['datamodel_file']}")
    print(f"builds per workload: {report['builds']}")
    print()
    print(f"{'workload':24} {'fields':>7} {'dispatches':>12} {'per build':>10} "
          f"{'budget':>7}  verdict")
    print("-" * 76)
    for name, budget in BUDGETS.items():
        entry = report["workloads"][name]
        verdict = "ok" if entry["per_build"] <= budget else "OVER BUDGET"
        print(f"{name:24} {entry['fields']:>7} {entry['total_dispatches']:>12} "
              f"{entry['per_build']:>10.3f} {budget:>7}  {verdict}")
    print()
    for violation in report["violations"]:
        print(f"VIOLATION: {violation}", file=sys.stderr)

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"written: {args.json}")

    return 0 if report["within_budget"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
