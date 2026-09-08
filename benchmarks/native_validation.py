#!/usr/bin/env python
"""Development harness for the experimental native executor (FEAT-2 / TASK-17).

**Development-only.**  Nothing in ``datamodel`` imports ``rs_core``; the
package's default loading and constructors are untouched.  This module builds
the experimental cdylib through its own Cargo manifest and loads it explicitly
by path, so the extension can never be picked up accidentally by an
application.

What the executor is
====================

``rs_core.NativePlan`` is a *bounded, sequential, model-level* validator for a
declared eligible subset of scalar fields.  It is not a backend and it is not
wired into anything: TASK-18 measures it, and only then is promotion even
discussed.

The interface it exposes is documented in ``rust/rs_core/src/lib.rs`` and
re-stated by :func:`describe_interface` below, so a dependent task can verify
it rather than infer it from names.

The one rule that matters
=========================

``plan.execute(row)`` returns ``None`` to mean **"ineligible -- run the legacy
Python path"**.  That is not a validation result and must never be treated as
one.  Eligibility is decided in a first pass over every field *before* any
result is produced, so a row is never half-executed: the caller re-runs from a
clean state and no parser runs twice.

Usage
=====

::

    python benchmarks/native_validation.py                 # build + report
    python benchmarks/native_validation.py --no-build      # reuse the artifact
    python benchmarks/native_validation.py --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HARNESS_ROOT = Path(__file__).resolve().parents[1]
CRATE_DIR = HARNESS_ROOT / "rust" / "rs_core"
ARTIFACT = HARNESS_ROOT / "rust" / "target" / "release" / "librs_core.so"

#: Python types this executor is allowed to see. Anything else makes the whole
#: model ineligible -- a field is never skipped.
KIND_BY_TYPE = {str: "str", int: "int", float: "float", bool: "bool"}


class NativeUnavailable(RuntimeError):
    """The experimental extension could not be built or loaded."""


def build_extension(quiet: bool = True) -> Dict[str, Any]:
    """Build the experimental cdylib in release mode. Records what it ran."""
    if not shutil.which("cargo"):
        raise NativeUnavailable(
            "cargo is not on PATH, so the experimental extension cannot be "
            "built. This is NOT a pass: the native experiment is unverified."
        )
    command = ["cargo", "build", "--release"]
    completed = subprocess.run(
        command, cwd=str(CRATE_DIR), capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise NativeUnavailable(
            f"cargo build failed ({completed.returncode})\n"
            f"{completed.stdout[-3000:]}\n{completed.stderr[-3000:]}"
        )
    if not ARTIFACT.is_file():
        raise NativeUnavailable(f"build reported success but {ARTIFACT} is missing")
    if not quiet:
        print(completed.stderr.strip().splitlines()[-1] if completed.stderr else "")
    return {
        "command": " ".join(command),
        "cwd": str(CRATE_DIR),
        "artifact": str(ARTIFACT),
        "sha256": hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(),
        "bytes": ARTIFACT.stat().st_size,
    }


def load_native(build: bool = True):
    """Import the experimental extension from its built artifact, by path.

    The artifact is copied to a temporary ``rs_core.so`` first: the cdylib is
    named ``librs_core.so``, and CPython requires the file stem to match the
    module's init symbol.
    """
    provenance = build_extension() if build else {
        "artifact": str(ARTIFACT),
        "sha256": hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        if ARTIFACT.is_file() else None,
        "command": "(not rebuilt)",
    }
    if not ARTIFACT.is_file():
        raise NativeUnavailable(f"{ARTIFACT} does not exist; build it first")

    workspace = Path(tempfile.mkdtemp(prefix="rs-core-"))
    target = workspace / "rs_core.so"
    shutil.copy2(ARTIFACT, target)
    spec = importlib.util.spec_from_file_location("rs_core", str(target))
    if spec is None or spec.loader is None:
        raise NativeUnavailable(f"could not create a module spec for {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.__provenance__ = provenance
    module.__loaded_from__ = str(target)
    return module


def describe_interface(native) -> Dict[str, Any]:
    """The private interface, re-derived from the loaded module."""
    return {
        "supported_kinds": list(native.SUPPORTED_KINDS),
        "plan_factory": "rs_core.NativePlan(descriptors)",
        "descriptor": "(name, kind, min, max, min_len, max_len)",
        "plan_attributes": ["eligible", "field_count", "kinds"],
        "execute": "plan.execute(values: dict) -> list[(name, bool)] | None",
        "none_means": (
            "INELIGIBLE -- the caller MUST run the legacy Python path. It is "
            "not a validation result."
        ),
        "excluded_by_design": [
            "temporal kinds (date/datetime/time): the prototype's chrono "
            "parsing does not reproduce Python's temporal variants, so those "
            "fields are ineligible rather than handled wrongly",
            "Decimal, UUID, containers, unions, nested models",
            "int values outside i64: ineligible, never truncated",
            "subclass instances, including bool where int is expected",
            "missing keys (presence/default handling is not implemented)",
        ],
    }


@dataclass(frozen=True)
class ModelPlan:
    """A native plan plus the reason it may be unusable."""

    plan: Any
    descriptors: Tuple[Tuple[Any, ...], ...]
    eligible: bool
    ineligible_fields: Tuple[str, ...]


def descriptors_for(model) -> Tuple[List[Tuple[Any, ...]], List[str]]:
    """Derive plan descriptors from a datamodel class.

    Returns ``(descriptors, ineligible_field_names)``. A field whose annotated
    type is not in :data:`KIND_BY_TYPE` is reported as ineligible rather than
    dropped, so the caller can see exactly why a model cannot run natively.
    """
    descriptors: List[Tuple[Any, ...]] = []
    ineligible: List[str] = []
    for name, field in model.__columns__.items():
        kind = KIND_BY_TYPE.get(field.type)
        if kind is None:
            ineligible.append(name)
            continue
        metadata = dict(field.metadata)
        # A field carrying a user callback is ineligible even though its type
        # is supported: the executor validates only, so a custom validator or
        # encoder could change the outcome, and running natively would skip it.
        if metadata.get("validator") is not None or metadata.get("encoder") is not None:
            ineligible.append(name)
            continue
        # A user-replaced parser is the same problem seen from the other side.
        if getattr(field, "parser", None) is not None and metadata.get("encoder"):
            ineligible.append(name)
            continue
        descriptors.append((
            name, kind,
            metadata.get("min"), metadata.get("max"),
            metadata.get("min_length"), metadata.get("max_length"),
        ))
    return descriptors, ineligible


def plan_for(native, model) -> ModelPlan:
    descriptors, ineligible = descriptors_for(model)
    if ineligible:
        # Mirror the executor's own rule at the harness level: a model with any
        # unhandled field is not a native candidate at all.
        descriptors = descriptors + [(name, "unsupported", None, None, None, None)
                                     for name in ineligible]
    plan = native.NativePlan(descriptors)
    return ModelPlan(
        plan=plan,
        descriptors=tuple(descriptors),
        eligible=plan.eligible and not ineligible,
        ineligible_fields=tuple(ineligible),
    )


def python_validity(model, row: Dict[str, Any]) -> Dict[str, bool]:
    """What the Cython path decides for the same row, per field.

    Used to check parity. A field is 'valid' when the model reports no error
    for it.
    """
    instance = None
    errors: Dict[str, Any] = {}
    try:
        instance = model(**row)
        errors = instance.get_errors() or {}
    except Exception:  # noqa: BLE001 - a raised model means every field is suspect
        return {}
    return {name: name not in errors for name in row}


def measure(native, model, rows: Sequence[Dict[str, Any]],
            batches: int = 20, batch_size: int = 1000) -> Dict[str, Any]:
    """Time the native executor against model construction, sequentially.

    This is a *shape* measurement for TASK-18 to build on, not an acceptance
    result: it compares a bare validity check against a full construction, so
    the two are not doing the same work. It is reported as such.
    """
    model_plan = plan_for(native, model)
    if not model_plan.eligible:
        return {"eligible": False, "ineligible_fields": list(model_plan.ineligible_fields)}

    plan = model_plan.plan
    row = dict(rows[0])
    for _ in range(200):
        plan.execute(row)
        model(**row)

    native_samples, python_samples = [], []
    for _ in range(batches):
        start = time.perf_counter_ns()
        for _ in range(batch_size):
            plan.execute(row)
        native_samples.append((time.perf_counter_ns() - start) / batch_size)

        start = time.perf_counter_ns()
        for _ in range(batch_size):
            model(**row)
        python_samples.append((time.perf_counter_ns() - start) / batch_size)

    native_samples.sort()
    python_samples.sort()
    return {
        "eligible": True,
        "fields": plan.field_count,
        "native_validate_ns": native_samples[len(native_samples) // 2],
        "python_construct_ns": python_samples[len(python_samples) // 2],
        "caveat": (
            "NOT comparable as a speed-up: the native figure is validation "
            "only, the Python figure is a full construction including "
            "conversion, assignment and hooks. TASK-18 must measure "
            "full-cost parity."
        ),
    }


def eligible_demo_model():
    """A model inside the executor's declared eligible subset.

    Deliberately built here rather than reused from the benchmark corpus: the
    corpus models all contain Decimal/UUID/temporal/container fields and are
    therefore ineligible by design, which is itself a finding this harness
    reports. A prototype still has to be demonstrated on something it *can*
    run, and this is that something -- named as a demo so nobody mistakes it
    for an acceptance workload.
    """
    from datamodel import BaseModel, Column  # noqa: PLC0415

    return type("NativeEligibleDemo", (BaseModel,), {
        "__annotations__": {
            "an_int": int, "a_str": str, "a_float": float, "a_bool": bool,
            "bounded": int, "short": str,
        },
        "an_int": Column(required=False, default=0),
        "a_str": Column(required=False, default="x"),
        "a_float": Column(required=False, default=0.0),
        "a_bool": Column(required=False, default=False),
        "bounded": Column(required=False, default=1, min=1, max=10),
        "short": Column(required=False, default="ab", max_length=5),
        "Meta": type("Meta", (), {"strict": False}),
    })


def eligible_demo_rows() -> List[Dict[str, Any]]:
    """Rows covering success, constraint failure, wrong type and fallback."""
    return [
        {"an_int": 7, "a_str": "hello", "a_float": 1.5, "a_bool": True,
         "bounded": 5, "short": "ok"},
        {"an_int": 0, "a_str": "", "a_float": 0.0, "a_bool": False,
         "bounded": 1, "short": ""},
        # constraint violations
        {"an_int": 1, "a_str": "s", "a_float": 1.0, "a_bool": True,
         "bounded": 99, "short": "waytoolong"},
        # arbitrary-precision int -> must fall back, never truncate
        {"an_int": 2 ** 96, "a_str": "s", "a_float": 1.0, "a_bool": True,
         "bounded": 5, "short": "ok"},
        # wrong types
        {"an_int": [1], "a_str": "s", "a_float": 1.0, "a_bool": True,
         "bounded": 5, "short": "ok"},
    ]


def parity_report(native, model, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare native decisions against the Python path for every row.

    Only rows the executor accepts are compared -- a fallback is not a
    disagreement, it is the executor declining, which is the behaviour the
    whole design rests on.
    """
    model_plan = plan_for(native, model)
    executed = 0
    fell_back = 0
    mismatches: List[Dict[str, Any]] = []

    for row in rows:
        result = model_plan.plan.execute(dict(row))
        if result is None:
            fell_back += 1
            continue
        executed += 1
        expected = python_validity(model, dict(row))
        if not expected:
            # The Python path raised for this row; the native executor made a
            # per-field decision. Record it rather than silently passing.
            mismatches.append({"row": {k: repr(v) for k, v in row.items()},
                               "reason": "python path raised, native did not"})
            continue
        for name, ok in result:
            if name in expected and expected[name] != ok:
                mismatches.append({
                    "field": name, "native": ok, "python": expected[name],
                    "row": {k: repr(v) for k, v in row.items()},
                })

    return {"rows": len(rows), "executed": executed, "fell_back": fell_back,
            "mismatches": len(mismatches), "detail": mismatches[:10]}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        native = load_native(build=not args.no_build)
    except NativeUnavailable as exc:
        print(f"native experiment UNAVAILABLE: {exc}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(HARNESS_ROOT))
    from tests.fixtures.model_performance.models import (  # noqa: PLC0415
        Employee, UnconstrainedScalars,
    )

    report: Dict[str, Any] = {
        "feature": "FEAT-2", "task": "TASK-17",
        "provenance": native.__provenance__,
        "interface": describe_interface(native),
        "models": {},
    }

    eligible_model = eligible_demo_model()
    rows = eligible_demo_rows()

    for model in (eligible_model, UnconstrainedScalars, Employee):
        model_plan = plan_for(native, model)
        entry: Dict[str, Any] = {
            "eligible": model_plan.eligible,
            "ineligible_fields": list(model_plan.ineligible_fields),
            "plan_kinds": list(model_plan.plan.kinds),
        }
        if model_plan.eligible:
            entry["parity"] = parity_report(native, model, rows)
            entry["timing"] = measure(native, model, rows)
        report["models"][model.__name__] = entry

    print(f"artifact: {report['provenance'].get('artifact')}")
    print(f"sha256:   {report['provenance'].get('sha256')}")
    print(f"kinds:    {report['interface']['supported_kinds']}")
    print()
    for name, entry in report["models"].items():
        status = "eligible" if entry["eligible"] else "INELIGIBLE"
        print(f"{name:26} {status}")
        if entry["ineligible_fields"]:
            print(f"  unhandled fields: {', '.join(entry['ineligible_fields'])}")
        parity = entry.get("parity")
        if parity:
            print(f"  rows: {parity['rows']}  executed natively: "
                  f"{parity['executed']}  fell back: {parity['fell_back']}  "
                  f"parity mismatches: {parity['mismatches']}")
        timing = entry.get("timing")
        if timing and timing.get("eligible"):
            print(f"  native validate {timing['native_validate_ns']:.0f} ns  vs  "
                  f"python construct {timing['python_construct_ns']:.0f} ns")
    print()
    print("Reminder: execute() -> None means fall back to Python, not 'invalid'.")
    print("The timing above is NOT a speed-up claim - see `caveat` in the JSON.")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"written: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
