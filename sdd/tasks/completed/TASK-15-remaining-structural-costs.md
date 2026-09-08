# TASK-15: Profile and reduce remaining structural execution costs

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (3h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-14
**Parallel**: false
**Parallelism notes**: Serial core refactor after gated-path parity. Measure alone.
**Assigned-to**: unassigned

---

## Context

Implements M4 of the approved specification; contributes to AC4, AC5, AC6, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Profile release/diagnostic builds after the gate to identify residual column snapshot, metadata and assignment overhead.
- Implement only a small measured compatible improvement in the identified path, or persist evidence explaining why each candidate was retained.
- Keep generated initializer semantics, descriptors, __values__/old_value behavior, aliases, dynamic columns and callback-visible order intact.
- Do not cache a column snapshot using only mapping identity/length, or substitute membership state that can become stale after public list/dict mutation.

**NOT in scope**: Class-cache bug fixes, default-sharing changes, wholesale generated initializer replacement or a language migration.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `datamodel/base.py` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/abstract.py` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/converters.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `tests/compatibility/test_structural_parity.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/structural.json` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
from datamodel.fields import Field
from datamodel.abstract import ModelMeta
from datamodel.converters import encoders
from datamodel.validation import validators
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
- datamodel/fields.pyx:70-155,215-247 — class Field(ff), default policy storage does not exist; _meta backing map and dataclasses.Field initialization.
- datamodel/abstract.py:180,249-260 — _initialize_fields(attrs, annotations, strict), df.parser/df.validator assignment.
- datamodel/abstract.py:352-419,462-487 — metaclass cache-hit/miss handling, final class columns and shared fields; key omits default/configuration.
- datamodel/validation.pyx:28-96 — built-in validators/validators map; known identity must not be inferred from a function's display name.
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

Allocation-free-looking changes can invoke equality or descriptors differently. Performance never overrides reference parity.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-14` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Each attempted improvement has before/after evidence and differential parity.
- [ ] No new stale metadata/column state or assignment-history behavior is introduced.
- [ ] Negative experiments leave the stable path intact with a completed report rather than speculative code.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC4, AC5, AC6, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_structural_parity.py tests/test_field.py tests/test_descriptors.py -q`.
- Use the common benchmark protocol and compare raw/native, dynamic fields, hooks and 50-field scaling.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-15 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: **This is a negative result, and it is the honest one.** No candidate
delivered a measurable, safe improvement. The two largest remaining savings are
unsafe for reasons I demonstrated empirically rather than assumed, and the two
safe candidates measured as no change. The stable path is left intact and the
full evidence is persisted in
`benchmarks/results/compatible-model-performance/structural.json`.

**Profile (Employee native, 20,000 builds, cProfile).** Residual cost after the
TASK-13 gate concentrates in two places:

| where | cost | note |
|---|---|---|
| `base.py:35 __post_init__` | 0.485 s tottime | includes `processing_fields`; cProfile cannot separate a cpdef function |
| `abstract.py:66 _dc_method_setattr_` | 220,000 calls, 0.143 s | 11 assignments x 20,000 builds; each does a `startswith`/`endswith` pair **and an O(n) LIST membership scan** |

**Verdicts (all six candidates are in `structural.json` with their numbers):**

| id | candidate | opportunity | verdict |
|---|---|---|---|
| A1 | pass live `__columns__.items()` view instead of a snapshot | **510 ns/build (~2%)** | REJECTED -- unsafe |
| A2 | cache the column snapshot on the class | 510 ns/build | REJECTED -- no safe invalidation |
| B | replace the `__fields__` list scan with a set | 90 ns (11 fields) to 460 ns (50 fields) per assignment | REJECTED -- stale membership |
| C | remove the redundant second `not in __fields__` guard | -- | APPLIED, but **not** a measured win |
| D | cheaper dunder test | -- | REJECTED -- measured as *not* cheaper |
| E | `tuple()` instead of `list()` for the snapshot | ~10 ns | REJECTED -- inside noise |

**A1 -- the snapshot is load-bearing, not incidental.** `list(cols.items())`
costs 570.8 ns while the bare view costs 59.9 ns, so passing the view would
save ~510 ns (~2% of a 26 us Employee build). But a user callback that mutates
`__columns__` while `processing_fields` is iterating **works today**, precisely
because `__post_init__` iterates a copy. I verified it on **both** builds: an
encoder that inserts a new column mid-build returns normally. Passing the live
view would turn that into `RuntimeError: dictionary changed size during
iteration`. That is a silent behaviour regression bought for 2%, so: no.

**B -- the stale-membership hazard is real, in both directions.** This is
exactly what the task scope forbids, and it is not theoretical. `__fields__` is
a public list mutated in place -- by `_dc_method_setattr_` itself and by users.
Verified on both builds: after `Model.__fields__.append("manual")`, assigning
`.manual` **is** honoured as a known field; a set built at class creation would
not see that. Falling back to `__columns__` for membership is also wrong: the
same probe shows `"manual" in __columns__` is `False`, so the two containers
genuinely diverge.

**D -- measured, not assumed.** The "obviously cheaper" dunder alternatives are
not cheaper: first-char short-circuit is 51.93 ns vs `startswith`+`endswith` at
52.27 ns (noise) and clearly *worse* for actual dunder names (95.13 vs 79.83);
slice comparison is worse in both cases. CPython's `str.startswith` is already
fast for short literals. Had I trusted intuition I would have shipped a
pessimisation and called it an optimisation.

**C -- what was actually applied, described honestly.** The second
`if name not in self.__fields__:` guard was dead by control flow: the earlier
`if name in self.__fields__` branch returns unconditionally, and nothing between
the two checks can mutate `__fields__` (a `Meta.frozen` read and an
`object.__setattr__` of an unrelated attribute). Removing it eliminates a second
O(n) list scan on the extra-attribute path. **It has no measurable effect on any
benchmark workload**, and the paired measurement says so plainly (reference
546.7/546.2/551.7 ns vs candidate 556.5/563.9/556.8 ns -- marginally *slower*,
well inside noise). The reason is that a new attribute is appended to
`__fields__` on first assignment, so every later assignment takes the early
branch and never reaches the removed code. It is justified by proof, not by
measurement, and I am not claiming it as a speed-up.

**Two claims of mine that the tests corrected.** Both were caught before they
reached the report as fact:
1. I wrote that `create_field` updates `__columns__` without `__fields__`. It
   does not -- it ends with `setattr`, which routes through
   `_dc_method_setattr_` and appends. The failing test made me look;
   `structural.json` and the test docstring now say so explicitly. The real
   example is **`add_field`**, which does diverge.
2. `add_field` additionally leaves the class **unconstructible** -- the next
   build raises `AttributeError` because `processing_fields` `getattr`s a
   column that was never installed and never added to `__fields__`. Verified
   identical on 0.10.21, so it is pre-existing, and now pinned by
   `test_add_field_leaves_the_class_unconstructible` so a future "helpful"
   reconciliation of the two containers cannot silently change it.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_structural_parity.py
  tests/test_field.py tests/test_descriptors.py -q` -> **29 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **675 passed, 2 skipped, 0 failed**
  (657 before this task + 18 new).
- **Differential corpus: 45/45 cases, 0 divergences.**
- `.venv/bin/python -m ruff check --select F,E9
  tests/compatibility/test_structural_parity.py` -> clean.
- All timings: medians of 15-21 batches after warm-up, pinned to CPU 9,
  compared against TASK-9's calibrated ~2% empirical cross-build floor.

**Evidence paths and acceptance coverage**:
- AC4 / AC7 (no new stale state, assignment history intact):
  `test_public_fields_list_mutation_is_honoured`,
  `test_fields_and_columns_are_not_interchangeable`,
  `test_dynamically_added_field_becomes_a_known_field`,
  `test_values_and_old_value_are_unchanged`, `test_aliases_still_resolve`,
  plus the extra-policy tests for `allow`/`ignore`/`forbid` and strict mode.
- Before/after evidence and differential parity for every attempt:
  `structural.json` (`candidates[]`, each with `measured` and `verdict`), and
  45/45 corpus parity.
- Negative experiments leave the stable path intact with a completed report:
  `structural.json.headline` states the negative result;
  `test_structural_report_exists_and_records_every_verdict` requires a verdict
  and a reason for all six candidates, and
  `test_structural_report_does_not_claim_an_unmeasured_win` fails if the report
  ever dresses the applied change up as a speed-up.
- AC5/AC6 context: the improvement target rests on the TASK-13 gate (measured
  ~12-17%), not on this task. TASK-16 runs the acceptance protocol.

**Deviations from spec**: none in scope. Notes:
1. **`base.py` and `converters.pyx` are listed as MODIFY but were deliberately
   left unchanged.** Every change I could make to them is candidate A1/A2/E,
   all rejected above with evidence. Editing them anyway, to match the file
   table, would have meant shipping speculative code -- which the task's own
   acceptance criteria forbid ("negative experiments leave the stable path
   intact with a completed report rather than speculative code").
2. No `.pyx` changed, so no rebuild was required and
   `tests/compatibility/reference_manifest.json` did **not** need regenerating.
3. `datamodel/abstract.py` still carries its pre-existing unused
   `functools.lru_cache` import (ruff F401). Confirmed pre-existing by stashing
   in TASK-11; left alone rather than widening the diff.
4. A `frozen = True` model could not be exercised: `dataclasses` refuses a
   frozen dataclass inheriting a non-frozen one, and `BaseModel` is non-frozen.
   The frozen branch of `_dc_method_setattr_` is therefore not directly
   reachable from a subclass in a test, and I removed the test rather than
   leave one that asserted something impossible.
