# TASK-11: Precompute conservative per-field validation policy

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (3h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-9
**Parallel**: true
**Parallelism notes**: May coexist with asyncdb-specific tests, which edit disjoint files; serial predecessor of converter/validator changes.
**Assigned-to**: unassigned

---

## Context

Implements M2 of the approved specification; contributes to AC4, AC6, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Introduce private conservative policy for exact supported scalar fields: stable type/field identity, known built-in implementation identity, work-mask and constraint shape.
- Initialize a legacy default; build from final fields on class-cache hits/misses and inheritance without reusing the incomplete class-cache key as a semantic plan key.
- Keep live constraint/Meta/metadata values uncached. Unknown/dynamic/custom Field/descriptor cases must default safely without callers rebuilding plans.
- Make policy storage collectable/bounded and keep instance values/default results/errors out of it; document its private contract for the gated-loop task.
- Policy creation alone must not change which validators currently execute.

**NOT in scope**: Skipping `_validation_`, changing construction or assignment rules, wrapping/freezing public mappings.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `datamodel/fields.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/abstract.py` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/validation.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `tests/test_validation_policy.py` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel.fields import Field
from datamodel.abstract import ModelMeta
from datamodel.converters import encoders
from datamodel.validation import validators
from datamodel import BaseModel, Field
from datamodel.converters import register_parser
```

### Existing Signatures to Use

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

Nine Employee fields have cached built-in validators. Policy means remaining work, not absence of user options. Keep the policy safe under metadata changes made during callbacks.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-9` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Policy tests cover cache hits, same-name definitions, inherited/replaced fields, dynamic fields and unknown/custom Field subclasses.
- [ ] Parser/validator/type identity changes cannot leave an unsafe permanent skip decision.
- [ ] No new public fields/options or policy data leak into dataclass fields/JSON; existing sharing behavior remains characterized.
- [ ] The differential corpus remains equal before the gate is activated.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC4, AC6, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/test_validation_policy.py tests/compatibility/test_fixture_corpus.py tests/test_field.py -q`.
- Check default-to-legacy, no per-instance plan reconstruction, no unbounded strong-reference retention, and live-metadata semantics.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-11 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

*(Fill in only after implementation and verification.)*

**Completed by**: pending
**Date**: pending
**Notes**: pending
**Verification commands/results**: pending
**Evidence paths and acceptance coverage**: pending
**Deviations from spec**: pending
