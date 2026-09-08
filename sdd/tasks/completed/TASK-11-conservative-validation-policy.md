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

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented M2's precomputation in the four declared files. This is
the first task in FEAT-2 that touches production code, and it deliberately
changes **no behaviour**: `_validation` is untouched, nothing reads a policy at
validation time, and the differential corpus is still 45/45 identical to
0.10.21. The gate that will finally consume this lands in TASK-13.

**Private contract for the gated-loop task** (documented at length in the
`validation.pyx` block comment so TASK-13 verifies rather than infers):

| symbol | meaning |
|---|---|
| `FieldPolicy` | `cdef class`; readonly `work_mask`, `type_ref`, `validator_ref`, `parser_ref`, `constraint_shape`, `exact_scalar` |
| `build_field_policy(field, annotated_type)` | conservative builder; returns `None` (legacy) unless every identity is exactly what we shipped |
| `policy_is_current(field, policy)` | **must be called before acting on a policy**; re-derives identities and constraint shape |
| `field_policy(field)` | the attached policy or `None`; never raises |
| `POLICY_WORK_TYPE_CHECK / _CONSTRAINTS / _CUSTOM_VALIDATOR / _ALL` | work-mask bits |

**`None` is the legacy policy and is always safe.** Every unknown, dynamic,
custom-Field, descriptor-backed, non-scalar or drifting case lands on `None`,
so a field that was never analysed behaves exactly as before. A policy is built
only when *all* of these hold: the annotated type is an exact built-in scalar
(a `str` subclass or an `IntEnum` does not qualify), `type(field) is Field`
exactly, `_type_category == 'primitive'`, and the cached validator **is**
(identity) the built-in for that type.

**The identity check is against a private snapshot, and this matters.**
`datamodel.validation.validators` is a plain, importable, mutable dict. Had
eligibility been decided against it, overwriting `validators[int]` would let an
arbitrary function be treated as a known built-in, and TASK-13's gate could
then skip work that function was meant to do. Eligibility is therefore checked
against `_BUILTIN_VALIDATORS`, a copy taken at import time before user code can
run (`test_replacing_a_public_validator_cannot_make_a_stranger_look_known`).
The task's warning that known identity "must not be inferred from a function's
display name" turned out to be sharper than it looks: the built-ins are cdef
functions reached through a Cython wrapper, so `validators[int].__name__` is
literally `"wrap"` -- name-based trust would be both unsound *and* useless
(`test_identity_is_not_inferred_from_a_function_name`).

**Only shape is cached; values stay live.** The policy records *which*
constraint keys are present (`min`, `max`, `length`, `min_length`,
`max_length`, `pattern`, the `@gt/@lt/@ge/@le/@eq/@ne/@_pattern` attributes and
`@@validator`), enumerated by reading `_validate_constraints` rather than
guessed. It never stores a constraint value, nor anything from `Meta` or a live
metadata mapping, so a later gate must still read constraints live -- which is
exactly what the reference does.

**Drift cannot leave a stale skip decision.** `policy_is_current()` re-derives
the type, validator and parser identities *and* the constraint shape, and
returns False on any change. Pinned for: swapped validator, swapped parser,
swapped type, dropped `primitive` category, a constraint added through live
`_meta` during a callback, a constraint removed, and a custom validator added
later. `test_a_constraint_added_at_runtime_is_still_enforced` goes further and
asserts the *behaviour*: a `max` added after class creation still raises.

**Built from the FINAL field set, never keyed off the class-cache key.** The
metaclass key is `(name, bases, annotations)` and omits defaults and
configuration, so it is not a semantic plan key. I confirmed the consequence is
real and **pre-existing**: two same-named classes with `min=1` and `min=50`
share one `Field` object, and the second silently sees `min=1`
(`test_class_cache_shares_field_objects_for_identical_signatures`, tagged as
characterization). Policies are rebuilt by iterating the final `cols` on both
the cache-hit and cache-miss paths, so a policy can never be attached to
another class's field. Because the Field itself is shared by that pre-existing
quirk, the policy is necessarily shared too -- and correctly describes the one
field that actually exists, so no new divergence is introduced.

That quirk also bit the tests: an early draft used a `_fresh_int_field()`
helper that defined `class Holder` on every call, so the cache handed back the
*same* Field, and the test that swaps a validator corrupted every later test.
The helper now generates a unique class name per call, with a comment saying
why.

**Collectable and bounded.** A policy lives on the Field, holds only references
the Field already holds (its type and cached callables), and keeps no instance
values, defaults, results or errors. There is no global registry:
`test_policy_does_not_retain_the_class_after_it_is_dropped` creates 25 model
classes, drops them and asserts all 25 are garbage-collected;
`test_policy_holds_no_instance_state` asserts the absence of any
value/result/error attribute; `test_no_policy_is_rebuilt_per_instance` asserts
the policy object identity is unchanged across 50 constructions.

**Invisible from outside.** `_policy` is a `__slots__` entry, deliberately not
part of `metadata`/`_meta`, so it cannot leak into field metadata, schemas,
`to_dict()` or `json()` -- each asserted, plus absence from `__fields__`,
`__columns__` and `__dataclass_fields__`.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/test_validation_policy.py -q` ->
  **45 passed**.
- `.venv/bin/python -m pytest tests/test_validation_policy.py
  tests/compatibility/test_fixture_corpus.py tests/test_field.py -q` ->
  **210 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **581 passed, 2 skipped, 0 failed**
  (536 before this task + 45 new; no new reference-relative regression).
- Extensions rebuilt with `python setup.py build_ext --inplace` before testing.
- **Differential corpus after the rebuild: 45/45 cases, 0 divergences** vs
  0.10.21 -- the AC that the corpus stays equal before the gate is activated.
- asyncdb consumer differential re-run after the rebuild: **31 passed**,
  0 divergences.
- `.venv/bin/python -m ruff check --select F,E9 tests/test_validation_policy.py`
  -> clean.

**Evidence paths and acceptance coverage**:
- AC4 / AC6 (no behavioural change, no hidden regression): 45/45 differential
  parity; `test_valid_values_still_build`, `test_type_errors_are_still_raised`,
  `test_constraints_are_still_enforced`,
  `test_a_constraint_added_at_runtime_is_still_enforced`,
  `test_required_and_null_behaviour_is_unchanged`.
- AC7 (nothing leaks into public results):
  `test_policy_does_not_appear_in_to_dict_or_json`,
  `test_policy_does_not_appear_in_field_metadata`,
  `test_policy_adds_no_public_column_or_option`; sharing behaviour
  characterized by `test_class_cache_shares_field_objects_for_identical_signatures`.
- Unsafe-permanent-skip prevention: the seven drift tests in Part 3 plus
  `test_policy_is_current_is_false_for_legacy` and
  `test_policy_is_current_rejects_a_foreign_policy_object`.
- Cache hits / inheritance / replacement / dynamics:
  `test_policies_are_built_on_a_class_cache_hit`,
  `test_inherited_fields_have_policies_on_the_subclass`,
  `test_a_replaced_field_gets_the_replacements_policy`,
  `test_a_dynamically_added_field_defaults_to_legacy`,
  `test_add_field_defaults_to_legacy`.

**Deviations from spec**: one, flagged explicitly.

1. **`tests/compatibility/reference_manifest.json` was regenerated and is
   outside this task's declared file list.** It records sha256 digests of the
   compiled extensions actually loaded, so rebuilding the candidate (mandatory
   here -- the task requires rebuilding Cython artifacts before testing)
   necessarily invalidated it, turning 1 test red and erroring 12 others on
   provenance. Regeneration is the documented, intended remedy: TASK-8's note
   states "a fresh clone must rebuild both environments and regenerate the
   manifest before the provenance tests pass. That is intentional." It is also
   a precondition for producing *this* task's own required evidence, since the
   differential cannot be trusted against stale recorded artifacts. Only the
   candidate's `fields`/`validation` digests changed; the reference entries are
   untouched, and `verify_manifest()` reports `problems: []`. **Every task from
   here on that rebuilds the candidate will need the same regeneration** -- the
   task plan should probably say so.
2. The generated Cython annotation files (`datamodel/*.html`) are tracked and
   were rewritten by the rebuild, including for `.pyx` files I never edited
   (`converters.html` churned ~4,800 lines purely from a different
   Cython/Pygments CSS). That is build noise, not content, and out of scope, so
   I reverted all of them rather than commit it.
3. `datamodel/abstract.py` has a pre-existing unused `functools.lru_cache`
   import that ruff flags. It predates this change (verified by stashing), so I
   left it rather than widen the diff.
4. The task's contract says the candidate targets 0.11.0; it is 0.12.0 on this
   branch. Carried forward unchanged from TASK-7/8/9/10; still needs the
   maintainer's reconciliation in TASK-22.
