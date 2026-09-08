# TASK-16: Verify Cython speed and compatibility acceptance gates

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-9, TASK-10, TASK-15
**Parallel**: false
**Parallelism notes**: Exclusive measurement task after core changes and required asyncdb baseline; freezes the comparison point for native experiments.
**Assigned-to**: unassigned

---

## Context

Implements M3–M4 / M8 of the approved specification; contributes to AC1, AC2, AC3, AC4, AC5, AC6, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Rebuild engineering reference and optimized candidate, run paired acceptance timings, differential corpus and real asyncdb integration suite.
- Record dispatcher counts from separate diagnostic builds and allocation/lifetime observations without mixing profiling overhead into timings.
- Apply the 20% raw/native Employee improvement and <=5% representative median/p95 batch regression limits; report uncertainty and exact version/hash context.
- Freeze candidate commit/artifact hash as the optimized Cython comparison for later experiments.

**NOT in scope**: Modifying production sources, loosening thresholds, promoting Rust, or claiming full platform coverage from the local interpreter.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `benchmarks/results/compatible-model-performance/cython.json` | CREATE | Reproducible evidence and decision report |
| `benchmarks/results/compatible-model-performance/cython.md` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
from datamodel.converters import processing_fields
from datamodel.validation import _validation, validators
```

### Existing Signatures to Use

- examples/rust_benchmark.py:35-51 — Employee's 11 fields, required/primary metadata and age bounds; PAYLOAD/NATIVE_PAYLOAD at 105-139.
- examples/test_qsmodel.py:38-68 — QueryModel schema with optional nested containers and defaults.
- examples/test_datadriver.py:8-45 — DataDriver with InitVar and custom __post_init__ calling super; inspect before executing examples with top-level code.
- tests/test_qsmodel.py:12-82 — existing QueryModel fixture pattern; tests/test_converter.py:6-61 — Organization/Client nested ORM-like models.
- datamodel/base.py:35-55 — errors/state observable at construction.
- datamodel/models.py:134-152,209-226,304-308 — reset_values/old_value, to_dict and json.
- datamodel/abstract.py:66-145 — assignment history and parser-only assignment validation.
- tests/test_descriptors.py:6-80 — descriptors execute through normal attribute access; tests/test_field.py:8-70 — fields/defaults/metadata.
- datamodel/converters.pyx:1922 — cpdef dict processing_fields(object obj, list columns).
- datamodel/converters.pyx:1988-2006,2297-2312 — parser errors can fall through into validation; preserve overwrites and ordering.
- datamodel/converters.pyx:2314 — cdef object _validation_(str name, object value, object f, object _type, object meta, str field_category, bint as_objects=False).
- datamodel/converters.pyx:2372 — cdef object _field_checks_(object f, str name, object value, object meta); special values and db_default semantics.
- datamodel/validation.pyx:307-467 — cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type).
- datamodel/validation.pyx:469-503 — cpdef dict _validation(object F, str name, object value, object annotated_type, object val_type, str field_type, bint as_objects=False); metadata callback distinct from cached-validator route.
- datamodel/validation.pxd:4 — existing Cython declaration; converters.pyx:33 uses `from .validation cimport _validate_constraints`.
- setup.py:15-29,98-106 — _compiler_flags() selects /O2 on Windows and -O3 on POSIX; guarded setup invocation and existing Cython extensions.
- pyproject.toml:1-8,19,57-74 — Cython>=3.2.8, Python>=3.10, optional uvloop and dev dependencies after FEAT-001.
- scripts/stage_rust_ext.py:30-59 — build_wheel(manifest: str, out_dir: str, interpreter: str, manylinux: str | None, maturin_bin: str = 'maturin') -> int; builds rs_parsers through maturin, not the experimental rs_core loader.
- .github/workflows/release.yml:13-25,49-65 — Ubuntu/Windows × CPython3.10–3.14, Linux x86_64/Windows AMD64, skips musllinux; current wheel test only asserts HAS_RUST.
- datamodel/version.py:9 — current version is already 0.11.0; do not bump it again.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

Pin compiler/dependency flags consistently despite the engineering reference preceding FEAT-001. Any build-only reference accommodation must be documented.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-9`, `TASK-10`, `TASK-15` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] AC3 call limits and AC5 construction improvement are demonstrated with required sample counts and confidence interval.
- [ ] AC6 regressions and cache lifetime checks meet thresholds; compatible asyncdb/examples cases pass.
- [ ] If thresholds fail, this task remains incomplete pending compatible remediation or reviewed spec change; a negative optimization result is not a waiver.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC2, AC3, AC4, AC5, AC6, AC7 evidence is linked in the completion note.

## Test Specification

- Run the full acceptance configuration of benchmarks/model_performance.py documented by its implementing task.
- Run all available repository/differential/asyncdb tests in fresh environments and record failures reproduced only on baseline separately.
- Validate report references to raw process samples and diagnostic call counts.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-16 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**STATUS: INCOMPLETE — BLOCKED ON AC5 ONLY.**

Second acceptance run, after remediation. **AC3, AC6 and every compatibility
gate now pass.** AC5 does not, and it cannot be closed by further remediation:
the mechanism it depends on is exhausted.

The task stays open per its own criteria: *"a negative optimization result is
not a waiver."*

**Run by**: sdd-worker (Claude Opus 5) | **Date**: 2026-09-08
**Evidence**: `benchmarks/results/compatible-model-performance/cython.md`
(analysis) and `cython.json` (machine-readable; raw per-process samples and
diagnostics embedded).

### Gates

| gate | required | measured | status |
|---|---|---|---|
| AC5 construction improvement | >= 20% | **9.58% raw / 9.91% native** | **FAIL** |
| AC6 regression, median | <= 5% | worst `class_creation` **+4.35%** (CI up +4.64%) | PASS |
| AC6 regression, p95 | <= 5% | worst overall **+4.54%** | PASS |
| AC3 dispatch budget | <=3/<=3/0 | **2.0 / 2.0 / 0.0** | PASS |
| AC1/AC2/AC4/AC7 compatibility | zero divergence | **0 everywhere** | PASS |

11 of 15 workloads improved; best 16.0%, median 9.9%.

### What changed since the first run

1. **The diagnosed remediation.** `build_field_policy` was called from two
   sites; the `_initialize_fields` one was duplicated work at 2,300 ns/field.
   Removed, plus a per-field empty-`frozenset` allocation. `class_creation`
   went +4.91% -> +4.35% with the CI upper bound falling 5.72% -> 4.64%, which
   is what clears AC6.
2. **Two real correctness bugs fixed**, found by adversarial review and each
   reproduced against 0.10.21 first: a custom metaclass could spoof policy
   eligibility (hash/`__eq__` based) and silently disable validation; and the
   `__fields__` guard TASK-15 removed was **not** redundant, because
   `object.__setattr__` runs data descriptors. Both now have regression tests.
   TASK-15's applied change is retracted; that task is now a fully negative
   result.
3. **A deliberate ~1% cost for correctness**: the diversion check now mirrors
   legacy's `value == _type` instead of `value is _type`. That is most of why
   Employee moved 10.6% -> 9.6%. Flagged, not buried.

### Why AC5 cannot be remediated further

The dispatch counter proves the elimination is complete:
`unconstrained_native` reaches `_validation_` **zero** times per build, Employee
exactly twice (its two ineligible non-scalar fields). ~10% is what that
dispatch cost. What remains is per-field conversion, the
`_dc_method_setattr_` path, and the per-build column snapshot — and the last
two were rejected as unsafe in TASK-15 **with evidence** (a live `items()` view
breaks a callback that mutates `__columns__` mid-build; a membership set goes
stale because `__fields__` is public and mutated in place, including by
property setters).

### Verification

- `python benchmarks/model_performance.py --pin-cpu 9 --control-root <ref2>` ->
  486 s, acceptance mode, **no protocol shortfalls**, 5.6% calibration spread,
  **0 suspect processes**, cross-build floor 1.55%.
- `python tests/compatibility/profile_validation.py --builds 20000` ->
  2.000 / 2.000 / 0.000 per build, within budget, exit 0.
- Differential corpus -> **45 cases, 0 divergences**.
- asyncdb consumer -> **31 passed, 0 divergences**.
- `python -m pytest tests/ -q` -> **680 passed, 2 skipped, 0 failed**
  (stable across repeated runs after fixing an order-dependent test).

### Decision required (human)

1. Fund further compatible optimization — real work, since the two cheapest
   targets are already ruled out on safety grounds.
2. Take a **reviewed** spec change to the 20% threshold. ~10% across 11 of 15
   workloads with zero behavioural change is a defensible release; the
   threshold must not be quietly lowered to match the result.
3. Accept and carry into TASK-17..20, which measure against this frozen
   candidate anyway.

The candidate commit and both environments' extension digests are frozen in
`cython.json` -> `frozen_candidate`.
