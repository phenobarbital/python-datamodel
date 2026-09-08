# TASK-12: Remove unnecessary successful-validation allocations

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-11
**Parallel**: false
**Parallelism notes**: Serial after policy and before gate because both touch converters/validation.
**Assigned-to**: unassigned

---

## Context

Implements M3 of the approved specification; contributes to AC2, AC4, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Delay error dictionaries in internal successful paths until failure without altering public/cpdef return types.
- Preserve separate fresh dictionaries for externally callable success results; do not share a mutable singleton or substitute None where dict is the contract.
- Remove only demonstrably unobservable unused work; custom fields and overloaded operations retain their behavior.
- Add targeted result/exception parity and allocation evidence; do not introduce a different per-field allocation to replace the removed one.

**NOT in scope**: Validation gating, altered constraint predicates, new public sentinels or custom validator semantics.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `datamodel/converters.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/validation.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `tests/compatibility/test_validation_allocations.py` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel.converters import processing_fields
from datamodel.validation import _validation, validators
from datamodel.exceptions import ValidationError
from datamodel import BaseModel, Field, Column
```

### Existing Signatures to Use

- datamodel/converters.pyx:1922 — cpdef dict processing_fields(object obj, list columns).
- datamodel/converters.pyx:1988-2006,2297-2312 — parser errors can fall through into validation; preserve overwrites and ordering.
- datamodel/converters.pyx:2314 — cdef object _validation_(str name, object value, object f, object _type, object meta, str field_category, bint as_objects=False).
- datamodel/converters.pyx:2372 — cdef object _field_checks_(object f, str name, object value, object meta); special values and db_default semantics.
- datamodel/validation.pyx:307-467 — cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type).
- datamodel/validation.pyx:469-503 — cpdef dict _validation(object F, str name, object value, object annotated_type, object val_type, str field_type, bint as_objects=False); metadata callback distinct from cached-validator route.
- datamodel/validation.pxd:4 — existing Cython declaration; converters.pyx:33 uses `from .validation cimport _validate_constraints`.
- datamodel/__init__.py:6-9 — existing public exports.
- datamodel/base.py:29-55 — BaseModel.__post_init__(self) -> None snapshots columns, calls processing_fields, and handles strict/non-strict validity.
- datamodel/exceptions.pyx:24-38 — ValidationError(message, payload=None); string output includes ordered payload field names.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

`_validation_` is cdef; `_validation` is cpdef. Verify both boundaries and preserve externally observable empty-dict returns.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-11` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] All error branch payloads/messages and order match; dictionaries returned to different calls are independently mutable.
- [ ] Successful internal fast cases avoid the formerly unconditional error allocation.
- [ ] No parser or callback executes an extra time and no error-fallthrough path changes.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC2, AC4, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_validation_allocations.py tests/test_converter.py -q`.
- Use diagnostic allocation comparisons separately from release timings; compare strict/non-strict multi-error behavior through the differential runner.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-12 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented in the three declared files. Two allocations were
provably dead and were removed; one was allocated too early and is now
allocated at the point of return.

| where | what | frequency |
|---|---|---|
| `validation.pyx::_validate_constraints` | `error = {}` assigned every call, **never read** | once per primitive field, per construction |
| `validation.pyx::_validation` | `cdef dict error = {}` allocated on entry, returned only by the final statement | once per field; wasted by every early return |
| `converters.pyx::processing_fields` | `cdef dict _typeinfo = {}` declared, never referenced | once per model construction |

Each was verified dead by reading every path, not by assuming: in
`_validate_constraints` every failure returns `_create_error(...)`, which builds
its own dict, and the success path returns a fresh `{}`, so nothing ever read
the variable. `_typeinfo` has exactly one occurrence in the whole function --
its own declaration.

**The success contract is unchanged, which is the part that could have gone
wrong.** `_validation` is `cpdef`, so its return type is a public contract. It
still returns a **fresh, independently mutable `dict`** -- never `None`, never a
shared empty singleton. Pinned by `test_successful_validation_still_returns_a_dict`,
`test_each_successful_call_returns_a_distinct_object`,
`test_successful_results_are_independently_mutable`,
`test_many_successful_results_are_all_distinct` (50 distinct ids) and
`test_success_result_is_not_interned_across_types`.

**HONEST MEASUREMENT -- this is below the noise floor and is not claimed as a
speed-up.** The removed dicts are *transient*: allocated and freed inside one
call, so they never appear in retained memory and a `tracemalloc` delta over a
batch shows nothing. Their cost was allocator churn (CPU). A targeted paired
micro-measurement on a pinned core (6-field model, 2 constrained, 2000
constructions x 40 batches, three independent pairs) gave ratios of **0.9953,
0.9957 and 1.0010** -- about 0.3-0.5%, with one pair showing nothing at all.
TASK-9's calibrated **empirical cross-build floor is ~2%**, so this effect is
comfortably *inside* the noise. The justification for this change is therefore
structural (the work was provably dead), not empirical. Recording it as a
measured improvement would be exactly the error TASK-9's control exists to
prevent.

**Three of my initial test assumptions were wrong, and the reference build
settled all three.** Rather than "fix" the code to match my expectations, I ran
the identical probes against 0.10.21 and found the candidate already agreed
with it in every case:

1. `_validation(field, 'v', None, int, ...)` returns an **error**, not `{}`. I
   had asserted `{}` after reading only `_validate_constraints`, which does
   return early for `None` -- but `_validation` then continues to the instance
   check, which rejects `None` for an `int` field. Both builds agree; the
   observed behaviour is now pinned.
2. A custom `validator=` on a **primitive** runs **zero** times on both builds
   (`abstract.py` caches `validators[int]` into `f.validator`, so the user
   callback is never reached). TASK-7 recorded the same dead route. It is now
   pinned as characterization *specifically so that a later refactor cannot
   quietly revive it* -- going from 0 to 1 call would itself be a behaviour
   change. The live `List[str]` route is used for the real "exactly once"
   assertion.
3. An `encoder=` on a **str** field is likewise dead (`parse_basic`
   short-circuits `str` before its encoder branch). The float route is live, so
   the error-fallthrough test uses that instead.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_validation_allocations.py
  tests/test_converter.py -q` -> **47 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **606 passed, 2 skipped, 0 failed**
  (581 before this task + 25 new; no new reference-relative regression).
- Extensions rebuilt with `python setup.py build_ext --inplace` before testing.
- **Differential corpus: 45/45 cases, 0 divergences** vs 0.10.21.
- **asyncdb consumer differential: 31 passed, 0 divergences.**
- `.venv/bin/python -m ruff check --select F,E9
  tests/compatibility/test_validation_allocations.py` -> clean.
- Reference/candidate probe of all three contested behaviours -> identical
  output on both builds (transcript summarised above).

**Evidence paths and acceptance coverage**:
- AC2 / AC4 (error payloads, messages and order match; no error-fallthrough
  change): `test_error_payload_shape_is_preserved`,
  `test_error_key_order_is_stable_across_calls`,
  `test_min_and_max_violations_still_produce_distinct_messages`,
  `test_string_constraint_errors_are_preserved`,
  `test_type_errors_are_still_reported`,
  `test_none_still_falls_through_the_constraint_path_to_a_type_error`,
  `test_multiple_field_errors_are_all_reported`,
  `test_strict_model_still_raises_with_a_payload`,
  `test_a_failing_field_does_not_suppress_later_fields`; plus 45/45 corpus
  parity, which covers strict/non-strict multi-error behaviour through the
  differential runner as the task's test spec requires.
- AC7 (independently mutable results, no shared state):
  `test_error_results_are_independently_mutable`,
  `test_error_dicts_from_two_instances_do_not_share_state`,
  `test_to_dict_is_still_fresh_per_call`, plus the Part 1 freshness tests.
- No extra parser/callback execution:
  `test_a_custom_encoder_runs_exactly_once_per_field`,
  `test_a_live_custom_validator_runs_exactly_once`,
  `test_post_init_hook_runs_exactly_once`,
  `test_a_custom_validator_on_a_primitive_stays_dead`.
- No replacement allocation introduced:
  `test_no_new_per_field_allocation_replaced_the_removed_one`,
  `test_repeated_validation_retains_nothing`.

**Deviations from spec**: none in scope of the three declared files. Two notes:

1. `tests/compatibility/reference_manifest.json` regenerated again, for the
   same reason as TASK-11: rebuilding the candidate changes its `.so` digests
   and the provenance guard correctly rejects the stale record (1 failure + 12
   errors until regenerated). `verify_manifest()` reports `problems: []`.
   This will recur for every remaining task that rebuilds the candidate.
2. The generated `datamodel/*.html` Cython annotation files were rewritten by
   the rebuild and reverted again as build noise, out of scope.
