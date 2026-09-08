# TASK-17: Prototype a coarse sequential Rust validation executor

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-16
**Parallel**: true
**Parallelism notes**: May develop alongside serialization in disjoint files; benchmark execution remains exclusive.
**Assigned-to**: unassigned

---

## Context

Implements M5 of the approved specification; contributes to AC2, AC7, AC8. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Create a bounded experimental cached-plan model-level executor for exact supported native/scalar work, with explicit legacy eligibility fallback before side effects.
- Preserve ordered conversion/validation; never skip an unsupported field or repeat a partially executed parser on fallback.
- Expose/build the extension only for development harness use. Keep default package loading and constructors unchanged.
- Avoid panic/unwrap handling of invalid input; preserve Python arbitrary integers, Decimal, regex/Unicode and temporal semantics through compatible logic or fallback.
- Document the new private interface for the benchmark task; retain the optimized Cython artifact from its predecessor.

**NOT in scope**: Parallelism, installed wheel wiring, scalar-by-scalar Rust calls or global replacement of rs_parsers.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `rust/rs_core/src/lib.rs` | MODIFY | Scoped runtime/experimental implementation |
| `rust/rs_core/Cargo.toml` | MODIFY | Scoped runtime/experimental implementation |
| `benchmarks/native_validation.py` | CREATE | Development-only measurement harness |
| `tests/compatibility/test_native_executor.py` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel.converters import processing_fields
from datamodel.validation import _validation, validators
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- rust/rs_core/src/lib.rs:1-7 — `use pyo3::prelude::*;` and `use rayon::prelude::*;`.
- rust/rs_core/src/lib.rs:180-237 — get_field_info extracts a new native vector, narrows integer values and skips unsupported field types.
- rust/rs_core/src/lib.rs:245-282 — parse_datamodel(py: Python<'_>, dataclass_instance: Py<PyAny>) -> PyResult<Vec<(String,bool)>>; current Rayon prototype is not compatible model validation.
- rust/rs_core/Cargo.toml:1-19 — cdylib rs_core; PyO3 0.29, Rayon 1.5.3 declaration, chrono 0.4.
- rust/Cargo.toml:1-14 — workspace includes rs_core, rs_parsers and rs_validators.
- datamodel/rs_parsers/__init__.py:8-30 — existing optional rs_parsers loader, not a loader for rs_core.
- datamodel/converters.pyx:1922 — cpdef dict processing_fields(object obj, list columns).
- datamodel/converters.pyx:1988-2006,2297-2312 — parser errors can fall through into validation; preserve overwrites and ordering.
- datamodel/converters.pyx:2314 — cdef object _validation_(str name, object value, object f, object _type, object meta, str field_category, bint as_objects=False).
- datamodel/converters.pyx:2372 — cdef object _field_checks_(object f, str name, object value, object meta); special values and db_default semantics.
- datamodel/validation.pyx:307-467 — cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type).
- datamodel/validation.pyx:469-503 — cpdef dict _validation(object F, str name, object value, object annotated_type, object val_type, str field_type, bint as_objects=False); metadata callback distinct from cached-validator route.
- datamodel/validation.pxd:4 — existing Cython declaration; converters.pyx:33 uses `from .validation cimport _validate_constraints`.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

The existing bool-pair result is not an existing compatible error contract. New internal signatures must be recorded before importing them in tests. No dependency upgrade unless a concrete blocked build warrants scoped review.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-16` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] A sequential native prototype and development harness can execute a declared eligible subset with parity.
- [ ] Unsupported values/fields select legacy behavior before callbacks; no silent accepted-type narrowing.
- [ ] No default-backend/package-loader changes or new public constructor APIs are introduced.
- [ ] Known i64 and temporal-variant prototype flaws are excluded/corrected in the exercised path.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC2, AC7, AC8 evidence is linked in the completion note.

## Test Specification

- Build the experimental cdylib in release mode through its existing Cargo manifest, recording actual command/artifact path.
- Run `python -m pytest tests/compatibility/test_native_executor.py -q` with the test extension explicitly available.
- Cover exact scalar success, large integer fallback, wrong-type result, invalid constraints and callback-bearing fallback.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-17 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented in three of the four declared files (see Deviations for
the fourth). The prototype works, and the single most useful thing it produced
is a **negative finding about its own reach** — recorded below rather than left
for TASK-18 to discover.

**Private interface** (documented in `rust/rs_core/src/lib.rs` and re-derived at
runtime by `describe_interface()`, so TASK-18 verifies rather than infers):

| symbol | meaning |
|---|---|
| `rs_core.SUPPORTED_KINDS` | `("str", "int", "float", "bool")` |
| `rs_core.NativePlan(descriptors)` | descriptors are `(name, kind, min, max, min_len, max_len)` |
| `plan.eligible` / `.field_count` / `.kinds` | plan shape |
| `plan.execute(values: dict)` | `list[(name, bool)]` **or `None`** |

**`None` means "ineligible — run the legacy Python path". It is not a
validation result**, and nothing in the harness or tests treats it as one.

**The design rule that carries everything: eligibility is decided in a first
pass over every field, before any result is produced.** A single-pass
implementation would decide the leading fields and only then discover an
unusable one, leaving a half-executed row. Returning `None` for the *whole* row
is what lets the caller re-run from a clean state with no parser running twice.
Pinned by `test_an_ineligible_field_declines_the_whole_row`, which deliberately
places the int field **last** so a single-pass implementation would fail it.

**A field is never skipped.** An unsupported kind makes the entire plan
ineligible (`test_an_unsupported_kind_makes_the_whole_plan_ineligible`), so no
caller can validate a subset and believe it validated the model. This is
exactly the flaw in the pre-existing `get_field_info`, which `continue`s past
unsupported types.

**Both named prototype flaws are addressed:**

1. **i64.** An `int` outside i64 makes the row **ineligible** — never truncated,
   and never reported invalid. Python integers are arbitrary precision, so
   calling `2**96` invalid would narrow the accepted set. The pre-existing
   `validate_datamodel`/`parse_datamodel` do exactly that; they are left
   untouched and are **not on the exercised path**. Covered for `2**63`,
   `-(2**63)-1`, `2**200`, with the in-range boundaries `2**63-1` and `-(2**63)`
   asserted to still execute.
2. **Temporal variants.** `date`/`datetime`/`time` are **excluded** from the
   supported set rather than handled. The prototype's
   `NaiveDate::parse_from_str(s, "%Y-%m-%d")` does not reproduce Python's
   temporal variants, and the task permits excluding *or* correcting — excluding
   is the honest option for a bounded experiment.

**Also refused, each for a stated reason:** `Decimal`, `UUID`, containers,
unions, nested models; subclass instances — including `bool` where `int` is
expected, because `bool` subclasses `int` and Python's isinstance-based
`valid_int` accepts it; missing keys (presence/default handling is not
implemented); and **any field carrying a user encoder or validator**, since the
executor validates only and running natively would skip the callback
(`test_callback_bearing_fields_fall_back`, `test_validator_bearing_fields_fall_back`).

**No panic path on user data.** No `unwrap`/`expect` anywhere in the new code;
every extraction is checked and failure means fallback.
`test_hostile_values_do_not_panic` feeds `None`, `[]`, `{}`, a bare `object()`,
`NaN`, `inf`, `bytes` and an object whose `__eq__` raises.

**Unicode length is counted in characters, not bytes**
(`text.chars().count()`), matching Python's `len()` on `str` — pinned with a
3-character/5-byte string.

**HONEST FINDING — the prototype cannot run the acceptance workloads.** Both
corpus models are ineligible:

| model | unhandled fields |
|---|---|
| `Employee` | `employee_id`, `salary`, `hired_at`, `updated_at`, `skills`, `manager` |
| `UnconstrainedScalars` | `a_decimal`, `a_uuid`, `a_date`, `a_datetime` |

Every benchmark model carries `Decimal`, `UUID`, temporal or container fields.
So the executor covers **none** of the workloads AC5 is measured on. That is a
finding for TASK-18's promotion analysis, not a failure of this task — the task
asked for a *bounded* prototype and a declared eligible subset — but it means
AC8's "at least 10% additional improvement on its declared eligible workload"
will have to be argued on a workload that is not currently in the corpus.
`test_benchmark_corpus_models_are_honestly_reported_ineligible` keeps that
visible.

**Demonstrated with parity on a declared eligible subset**: 5 rows, **4 executed
natively, 1 fell back** (the `2**96` row), **zero parity mismatches** against
the Python path.

**Verification commands/results**:
- Build: `cargo build --release` in `rust/rs_core` -> artifact
  `rust/target/release/librs_core.so`, sha256 recorded by the harness on every
  load (`9dc8688c…` at time of writing).
- `.venv/bin/python -m pytest tests/compatibility/test_native_executor.py -q`
  -> **33 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **713 passed, 2 skipped, 0 failed**
  (680 before this task + 33 new).
- `.venv/bin/python benchmarks/native_validation.py` -> builds, loads, reports
  eligibility and parity as above.
- `.venv/bin/python -m ruff check --select F,E9 benchmarks/native_validation.py
  tests/compatibility/test_native_executor.py` -> clean.

**Evidence paths and acceptance coverage**:
- AC8 (sequential prototype + harness with parity on a declared eligible
  subset): `benchmarks/native_validation.py` (`parity_report`, `measure`);
  `test_native_decisions_match_the_python_path`,
  `test_constraint_decisions_match_the_python_path`.
- AC2/AC7 (no narrowing, no silent acceptance): the whole of Part 4 —
  large-integer fallback, subclass fallback, bool-as-int fallback, wrong-type
  decisions, missing-field fallback, callback-bearing fallback.
- No default-backend/loader change, no new public API:
  `test_datamodel_does_not_import_rs_core`,
  `test_no_new_public_constructor_api`,
  `test_the_extension_is_loaded_explicitly_by_path`.
- Statelessness/repeatability: `test_execute_is_repeatable_and_holds_no_state`
  (a fallback must not leave the plan altered), `test_results_are_fresh_objects`.

**Deviations from spec**: one, flagged.

1. **`rust/rs_core/Cargo.toml` is listed as MODIFY but was left unchanged.**
   Nothing in it needed to change: the crate already declares
   `crate-type = ["cdylib"]`, already depends on the pyo3 version used, and
   already builds. `rayon` remains a dependency because the pre-existing
   `parse_datamodel` prototype uses it — removing it would delete existing
   functionality, and parallelism is explicitly out of scope for this task
   either way. Editing the manifest purely to match the file table would have
   been a change with no purpose.
2. The timing the harness prints (native validation ~870 ns vs Python
   construction ~14,600 ns) is **not** a speed-up claim and is labelled as such
   in the output and in the report's `caveat` field: it compares a bare
   validity check against a full construction including conversion, assignment
   and hooks. Full-cost parity is TASK-18's job.
3. No `.pyx` changed, so no rebuild and no
   `tests/compatibility/reference_manifest.json` regeneration was needed.
