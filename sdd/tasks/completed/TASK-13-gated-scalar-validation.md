# TASK-13: Gate generic validation with equivalent scalar checks

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-12
**Parallel**: false
**Parallelism notes**: Owns the validation boundary after policy and allocation tasks; no concurrent writes to core Cython files.
**Assigned-to**: unassigned

---

## Context

Implements M3 of the approved specification; contributes to AC2, AC3, AC4, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Use the policy at the existing post-conversion validation boundary, after mutations/callbacks, to select narrow checks or legacy `_validation_`.
- For exact known scalar values, prove type validity and read active legacy constraints; skip generic dispatch only when all required work is complete.
- Preserve empty/missing/db_default/primary/null paths, parse-error fall-through and all complex/custom/subclass behavior through conservative fallback.
- Preserve live-metadata absent/None distinctions, built-in versus metadata callback routes, constraint order and canonical errors. Never rerun conversion on fallback.
- Add diagnostic-only generic-dispatch counts, using a separate temporary/profiling build; no counters or backend options in default application flows.

**NOT in scope**: Rust, global value caching, weakening validators, parser registry snapshots, or unconditional type-equality shortcuts.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `datamodel/converters.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/validation.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/validation.pxd` | MODIFY | Scoped runtime/experimental implementation |
| `tests/test_validation_fastpath.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/profile_validation.py` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel.converters import processing_fields
from datamodel.validation import _validation, validators
from datamodel.exceptions import ValidationError
from datamodel.fields import Field
from datamodel.abstract import ModelMeta
from datamodel.converters import encoders
from datamodel.validation import validators
from datamodel import BaseModel, Field
from datamodel.converters import register_parser
```

### Existing Signatures to Use

- datamodel/converters.pyx:1922 — cpdef dict processing_fields(object obj, list columns).
- datamodel/converters.pyx:1988-2006,2297-2312 — parser errors can fall through into validation; preserve overwrites and ordering.
- datamodel/converters.pyx:2314 — cdef object _validation_(str name, object value, object f, object _type, object meta, str field_category, bint as_objects=False).
- datamodel/converters.pyx:2372 — cdef object _field_checks_(object f, str name, object value, object meta); special values and db_default semantics.
- datamodel/validation.pyx:307-467 — cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type).
- datamodel/validation.pyx:469-503 — cpdef dict _validation(object F, str name, object value, object annotated_type, object val_type, str field_type, bint as_objects=False); metadata callback distinct from cached-validator route.
- datamodel/validation.pxd:4 — existing Cython declaration; converters.pyx:33 uses `from .validation cimport _validate_constraints`.
- datamodel/fields.pyx:70-155,215-247 — class Field(ff), default policy storage does not exist; _meta backing map and dataclasses.Field initialization.
- datamodel/abstract.py:180,249-260 — _initialize_fields(attrs, annotations, strict), df.parser/df.validator assignment.
- datamodel/abstract.py:352-419,462-487 — metaclass cache-hit/miss handling, final class columns and shared fields; key omits default/configuration.
- datamodel/validation.pyx:28-96 — built-in validators/validators map; known identity must not be inferred from a function's display name.
- datamodel/base.py:59-114 — register_parser(cls,target_type,func,field_name=None), add_field, create_field, set.
- datamodel/converters.pyx:532 — cpdef object register_parser(object _type, object parser_func), mutable TYPE_PARSERS registry.
- datamodel/abstract.py:66-145,516-534 — assignment, extra-field mutation and aliases.
- datamodel/fields.pyx:215-247 — mutation through _meta can change the metadata view.
- datamodel/validation.pyx:351-355,399-405,488-500 — live constraints and custom callback route; absent key differs from None.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

The reported 15 µs is not promised savings. Public mutable semantic settings remain live. False/0 are not missing. On rejected exact-type guards use the old path to preserve subclasses.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-12` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Employee valid raw and native builds use at most 3 generic `_validation_` dispatches per build; unconstrained supported scalar fixture uses zero.
- [ ] Constraints, presence checks and invalid parser results still enforce the exact reference behavior.
- [ ] Diagnostic counters do not affect release timings; `.pxd` signatures and cpdef public surface stay compatible.
- [ ] No wrong-type callback result, runtime metadata update or replaced validator is silently accepted.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC2, AC3, AC4, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/test_validation_fastpath.py tests/test_validation_policy.py tests/test_converter.py -q`.
- Diagnostic 20000-build Employee runs report <=60000 generic dispatches; verify required inline checks independently.
- Compare valid raw/native, constrained failures, parse exceptions and strict/non-strict errors using the isolated runner.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-13 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented in the five declared files. This activates the policy
built by TASK-11. It is the first change in FEAT-2 that produces a **real,
measurable** speed-up.

**Where the gate sits.** At the existing post-conversion boundary in
`processing_fields` -- after parsing, after any encoder/callback has run, after
the value is stored -- so the gate observes exactly what the legacy path would.
`test_a_mutation_in_post_init_is_seen_by_validation` proves this by overwriting
a valid value with an out-of-range one inside `__post_init__` and asserting the
violation is still reported.

**What it replaces, exactly.** For a field carrying a cached built-in
validator, `_validation_` does:

```
error = f.validator(f, name, value, _type)      # None for an exact type
if not error and _type in (str, int, float):
    return _validate_constraints(...)
return None
```

`fastpath_kind()` reproduces that and nothing more. Because the value's type is
proven identical to the policy's `type_ref`, the built-in validator is *known*
to return `None`, so the remaining work is only the constraint read.

**Everything it refuses to take over** (each a cheap pointer comparison;
`FASTPATH_NONE` is always safe because the legacy path then runs untouched):

| refused | why |
|---|---|
| `type(value) is not plan.type_ref` | exact identity, never `isinstance` -- a `str`/`int` subclass must keep the legacy path |
| `annotated_type is not plan.type_ref` | the annotation must be the one analysed |
| `f.validator is not plan.validator_ref` | a runtime replacement must be honoured, not bypassed |
| `f.parser is not plan.parser_ref` | ditto |
| `is_empty(value)` | `_field_checks_` enforces primary-key, required, `db_default` and nullable rules |
| `value is annotated_type` | mirrors `_validation_`'s own diversion |

**`0` and `False` are values, not absence.** `is_empty(0)` and `is_empty(False)`
are both `False` -- verified against the running code, not assumed -- so numeric
zero and boolean false stay on the fast path, as the task requires. Pinned by
`test_zero_and_false_are_values_not_absence`.

**Constraints are read LIVE, never trusted from the recorded shape.** This is
the single most important safety decision in the task. The gate always calls
`_validate_constraints` for `str`/`int`/`float`, so a constraint added to
metadata *after* class creation takes effect on the very next build
(`test_a_constraint_added_at_runtime_cannot_be_skipped`), and one removed stops
applying (`test_a_constraint_removed_at_runtime_stops_applying`).

I deliberately did **not** call `policy_is_current()` in the hot path: it
rebuilds the constraint shape as a `frozenset`, which would cost more per field
than the dispatch it is meant to avoid -- it would have made the "optimisation"
a pessimisation. Its constraint-shape half is unnecessary here precisely
*because* the gate reads constraints live. It remains the full audit for
callers wanting the complete guarantee, and TASK-11's tests still cover it.

**Legacy quirks preserved rather than "fixed".** The legacy route honours
constraints only for `str`/`int`/`float`, so a `Decimal` `min`/`max` is silently
ignored. The gate reproduces that exactly
(`test_decimal_constraints_remain_ignored_on_this_route`). Activating a
previously-ignored constraint is a non-goal in spec section 1 and would itself
be a behaviour change.

**Diagnostic counters are absent from release builds, by construction.** The
counter is guarded by a C macro `DATAMODEL_PROFILE_VALIDATION` that defaults to
`0`; because it is a compile-time constant the C compiler folds the guarded
branch away entirely. There is no counter, and no test of a counter, in the
default application flow. `profiling_compiled_in()` returns `False` in the
shipped build, asserted by `test_release_build_has_no_counters_compiled_in`.
I chose a C macro over Cython's `DEF`/`IF` after checking: `IF` still compiles
under Cython 3.3 but emits a deprecation warning and is slated for removal, and
Cython's own message recommends "runtime conditions or C macros".

`tests/compatibility/profile_validation.py` therefore makes a **separate
temporary profiling build**: it copies the package to a temp directory, deletes
the stale `.c`/`.so` so the macro actually reaches the compiler, rebuilds with
`CFLAGS=-DDATAMODEL_PROFILE_VALIDATION=1`, runs the workloads in a child bound
to that build, and deletes it. The worktree's own artifacts are never touched.

**MEASURED DISPATCH COUNTS -- 20,000 builds per workload:**

| workload | fields | dispatches | per build | budget | verdict |
|---|---|---|---|---|---|
| `employee_raw` | 11 | 40,000 | 2.000 | 3 | ok |
| `employee_native` | 11 | 40,000 | 2.000 | 3 | ok |
| `unconstrained_native` | 8 | **0** | **0.000** | 0 | ok |

40,000 <= the task's 60,000 budget for a 20,000-build Employee run. The
remaining 2 dispatches per Employee build are its two non-scalar fields,
`skills: List[str]` and `manager: Optional[Employee]`, which legitimately have
no policy. `unconstrained_native` reaches the generic dispatch **zero** times.

**MEASURED SPEED-UP (indicative micro-measurement, not the acceptance
protocol).** Four independent paired runs on a pinned core, 2,000 constructions
x 30 batches, alternating builds:

| workload | reference | candidate | ratios | mean |
|---|---|---|---|---|
| `employee_native` | 30,085 ns | 26,489 ns | .8920 .8907 .8577 .8817 | **0.8805 (11.9% faster)** |
| `unconstrained_native` | 19,136 ns | 15,928 ns | .8420 .8367 .8182 .8328 | **0.8324 (16.8% faster)** |

Every individual ratio is far below TASK-9's ~2% empirical cross-build floor,
so unlike TASK-12 this is a genuine, claimable improvement. **It is still not
an acceptance measurement**: the release-quality figure must come from the full
paired protocol in `benchmarks/model_performance.py`, which TASK-16 runs against
the AC5/AC6 gates. I am reporting an indication, not declaring the gate passed.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/test_validation_fastpath.py
  tests/test_validation_policy.py tests/test_converter.py -q` -> **100 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **639 passed, 2 skipped, 0 failed**
  (606 before this task + 33 new).
- `.venv/bin/python tests/compatibility/profile_validation.py --builds 20000`
  -> table above, exit code 0.
- **Differential corpus with the gate ACTIVE: 45/45 cases, 0 divergences.**
- **asyncdb consumer differential: 31 passed, 0 divergences.**
- `.venv/bin/python -m ruff check --select F,E9 tests/test_validation_fastpath.py
  tests/compatibility/profile_validation.py` -> clean.

**Evidence paths and acceptance coverage**:
- AC2 / AC3 (dispatch budgets): the profiling table above;
  `tests/compatibility/profile_validation.py` re-derives it on demand and exits
  non-zero if a budget is exceeded, so it is a gate as well as a report.
- AC4 (constraints, presence and invalid parser results still exact): the Part 4
  and Part 5 tests, especially
  `test_a_constraint_added_at_runtime_cannot_be_skipped`,
  `test_primary_key_checks_still_run`,
  `test_nullable_false_behaviour_is_unchanged`,
  `test_required_field_still_reports_when_missing`.
- No silently accepted replacement:
  `test_a_replaced_validator_is_honoured_not_bypassed`,
  `test_clearing_the_validator_sends_the_field_to_the_generic_path`,
  `test_a_replaced_parser_sends_the_field_to_the_generic_path`.
- Subclass preservation: `test_a_str_subclass_is_not_treated_as_a_str`,
  `test_an_int_subclass_is_not_treated_as_an_int`,
  `test_bool_supplied_to_an_int_field_keeps_reference_behaviour`.
- No repeated conversion on fallback:
  `test_conversion_is_not_repeated_when_the_gate_declines`,
  `test_post_init_runs_once_with_the_gate_active`.
- AC7 (results independent): `test_results_are_not_shared_between_instances`,
  `test_error_dicts_are_not_shared_between_instances`.
- `.pxd`/cpdef compatibility: the `.pxd` gained declarations only -- the
  pre-existing `_validate_constraints` line is byte-identical -- and
  `test_public_validation_surface_is_still_importable` checks the Python-visible
  surface still imports.

**Deviations from spec**: none in scope of the five declared files. Notes:

1. **The class-cache sharing quirk bit again, this time across test files.**
   `test_conversion_is_not_repeated_when_the_gate_declines` passed alone and
   failed in the full suite: it defined `class Encoded(BaseModel)` with the same
   annotations as an identically-named class in
   `test_validation_allocations.py`, so the cache handed back that class's Field
   -- and its encoder -- and mine never ran. Renamed to
   `EncodedFastpathProbe` with a comment. Worth flagging to the maintainer:
   this is a live foot-gun for anyone writing datamodel tests, and it is
   pre-existing behaviour (characterized in TASK-11), not something this feature
   introduced.
2. `tests/compatibility/reference_manifest.json` regenerated again for the
   rebuilt candidate, as in TASK-11/12. `verify_manifest()` -> `problems: []`.
3. Generated `datamodel/*.html` reverted as build noise, out of scope.
4. The task's contract still says the candidate targets 0.11.0 while the branch
   is 0.12.0 -- unchanged, for TASK-22 to reconcile.
