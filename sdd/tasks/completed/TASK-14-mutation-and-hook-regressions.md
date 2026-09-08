# TASK-14: Verify mutation, hooks and generic fallback parity

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (3h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-13
**Parallel**: false
**Parallelism notes**: Validates the completed gate before any further structural refactor; own regression tests only.
**Assigned-to**: unassigned

---

## Context

Implements M3 of the approved specification; contributes to AC2, AC4, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Build adversarial differential cases for metadata/backing-map replacement and mutation, constraints set to None versus removed, parser/validator/type/Meta changes and dynamic field replacement.
- Include callbacks mutating current and subsequent fields, failed conversion followed by validation, and first-error ordering with side effects.
- Cover descriptors, callable/awaitable fields, Union/Literal/nested containers, typed subclasses, assignment history and public dataclass operations.
- Detect semantic regressions without silently changing the oracle. Failures requiring production fixes return to the gate owner within its declared scope.

**NOT in scope**: Production behavior fixes, documentation of unverified success, or skipping failing consumer inputs.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `tests/compatibility/test_mutation_parity.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_hook_parity.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_generic_fallback.py` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
from datamodel import BaseModel, Field
from datamodel.converters import register_parser
from datamodel.converters import processing_fields
from datamodel.validation import _validation, validators
```

### Existing Signatures to Use

- datamodel/base.py:35-55 — errors/state observable at construction.
- datamodel/models.py:134-152,209-226,304-308 — reset_values/old_value, to_dict and json.
- datamodel/abstract.py:66-145 — assignment history and parser-only assignment validation.
- tests/test_descriptors.py:6-80 — descriptors execute through normal attribute access; tests/test_field.py:8-70 — fields/defaults/metadata.
- datamodel/base.py:59-114 — register_parser(cls,target_type,func,field_name=None), add_field, create_field, set.
- datamodel/converters.pyx:532 — cpdef object register_parser(object _type, object parser_func), mutable TYPE_PARSERS registry.
- datamodel/abstract.py:66-145,516-534 — assignment, extra-field mutation and aliases.
- datamodel/fields.pyx:215-247 — mutation through _meta can change the metadata view.
- datamodel/validation.pyx:351-355,399-405,488-500 — live constraints and custom callback route; absent key differs from None.
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

Reference behavior includes quirks such as cached primitive validators taking a different callback route. Regression tests preserve those quirks rather than activating new validations.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-13` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Required mutation/hook/generic tests match the reference for both strict modes.
- [ ] Custom callbacks execute in identical order/count even when an earlier field fails.
- [ ] Policy data is absent from externally observable field lists, JSON and dictionary output.
- [ ] Tests distinguish an intentionally altered gate so they do not merely mirror the implementation.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC2, AC4, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_mutation_parity.py tests/compatibility/test_hook_parity.py tests/compatibility/test_generic_fallback.py -q`.
- Run existing descriptor, inheritance, alias and union coverage in the rebuilt candidate environment.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-14 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented in exactly the three declared files. **No production
code changed** -- this task is the adversarial safety net for TASK-13's gate,
and its job is to find regressions, not to fix them. It found none.

**Why these tests cannot merely mirror the implementation** (the acceptance
criterion that shapes the whole design). Every scenario is executed **twice, in
two separate processes**, each bound to its own compiled artifacts: once
against the rebuilt 0.10.21 engineering reference, once against the candidate.
The assertion is that the two agree. The oracle is therefore the reference
build -- not my expectations and not the gate's behaviour. A test written to
match whatever the gate happens to do would fail the moment the reference
disagreed.

`assert_parity()` additionally refuses to pass if a scenario failed to *execute*
on the reference, so a broken scenario cannot masquerade as parity, and it
asserts the two runs really loaded different builds
(`test_both_environments_are_really_different_builds`) -- without that, both
children could load one build and every comparison would be vacuous.

**The comparison is proven able to fail.**
`test_the_comparison_detects_an_intentionally_altered_gate` takes a real
scenario result and corrupts it the way a broken gate would -- the constraint
violation simply vanishes -- then asserts `compare` reports a divergence. Had
that reported nothing, every "parity holds" result in these files would be
worthless.

**What is covered** (18 tests, ~45 scenarios):

*Mutation* (`test_mutation_parity.py`): replacing the whole `_meta` backing map
after the policy was built; a constraint **set to `None` versus removed**
(the absent/None distinction the task calls out); a zero-valued bound, which is
a real bound and not "absent"; constraint added then removed; string
constraints mutated; validator replaced, cleared; parser replaced; field `type`
replaced; `Meta.strict` flipped after class creation; dynamic field
replacement; `str`/`int` subclasses; boundary values (0, False, empty string,
0.0, 2**96, negative).

*Hooks* (`test_hook_parity.py`): encoder call **count and order**, including
`encoder_runs_when_an_earlier_field_fails` and a three-field ordering scenario
run both with and without a failing middle field -- the AC's "identical
order/count even when an earlier field fails"; encoder raising; the dead `str`
encoder route staying dead; the dead primitive-validator route staying dead;
the live `List[str]` validator running; a validator returning `False`;
`__post_init__` running exactly once, mutating its own field, mutating a *later*
field, raising, and adding metadata mid-flight; descriptors; assignment history
via `old_value`; `reset_values`.

*Generic fallback* (`test_generic_fallback.py`): typed containers, wrong inner
types, empty containers and factory independence, nested containers; `Optional`,
`Union`, `Literal`, `Enum`; nested models from dict and from instance,
`as_objects`, inheritance with an overridden field; callables, aliases,
`default_factory` sharing; failed conversion followed by validation, parse-error
ordering across three fields, and a strict parse error. Plus
`test_mixed_fast_and_generic_fields_in_one_model`, a seven-field model mixing
fast-path and generic fields -- the realistic case where leaked state between
fields would show.

**Two scenario bugs of mine, caught by the harness rather than by luck.** Both
`get_errors()` scenarios initially crashed **on the reference as well as the
candidate**: `get_errors()` returns `None`, not `{}`, on a clean model. Because
`assert_parity` treats a reference-side execution failure as a hard failure
rather than something to compare, they could not slip through as "both sides
agree". Fixed with `get_errors() or {}`.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_mutation_parity.py
  tests/compatibility/test_hook_parity.py
  tests/compatibility/test_generic_fallback.py -q` -> **18 passed**, 0 failed,
  0 skipped (reference worktree present), **zero divergences** in every
  scenario.
- Existing descriptor/inheritance/alias/union coverage in the rebuilt candidate:
  `.venv/bin/python -m pytest tests/test_descriptors.py tests/test_qsmodel.py
  tests/test_converter.py tests/test_field.py -q` -> **37 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **657 passed, 2 skipped, 0 failed**
  (639 before this task + 18 new).
- `.venv/bin/python -m ruff check --select F,E9` on all three files -> clean.

**Evidence paths and acceptance coverage**:
- AC2 / AC4 (mutation, hook and generic parity in both strict modes):
  all three files; both modes exercised explicitly by
  `test_strict_and_non_strict_agree`, and every scenario dict carries its own
  `Meta.strict` choice.
- Identical callback order and count with an earlier failure:
  `test_callback_order_is_identical_with_a_failing_field`,
  `test_encoder_parity`.
- AC7 (policy absent from observable output):
  `test_policy_is_invisible_on_both_builds`, which compares the field list,
  columns, `__dataclass_fields__`, `to_dict()` keys, `json()` and the union of
  all metadata keys across both builds, then additionally greps the rendered
  candidate output for `_policy`/`FieldPolicy`.
- Tests distinguish an altered gate:
  `test_the_comparison_detects_an_intentionally_altered_gate`.

**Deviations from spec**: none. Notes for the reviewer:
1. The shared harness (`run_scenarios`, `assert_parity`, and the child script)
   lives in `test_mutation_parity.py` and is imported by the other two files.
   All three are owned by this task, so no unowned file was touched; the
   alternative would have been triplicating a ~120-line subprocess harness.
2. No rebuild was needed (no production change), so
   `tests/compatibility/reference_manifest.json` did **not** need regenerating
   this time -- unlike TASK-11/12/13.
3. Scenarios are passed to the children as source strings and `exec`'d there.
   That is deliberate: the scenario must be compiled against the *child's*
   `datamodel`, so it cannot be a closure captured in this process.
