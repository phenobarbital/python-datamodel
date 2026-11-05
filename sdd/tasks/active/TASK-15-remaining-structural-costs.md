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

*(Fill in only after implementation and verification.)*

**Completed by**: pending
**Date**: pending
**Notes**: pending
**Verification commands/results**: pending
**Evidence paths and acceptance coverage**: pending
**Deviations from spec**: pending
