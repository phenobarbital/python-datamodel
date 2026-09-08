---
type: feature
base_branch: dev
id: FEAT-2
slug: compatible-model-performance
status: approved
isolation: per-spec
source: sdd/proposals/compatible-model-performance.proposal.md
research_state: sdd/state/FEAT-002/
---

# Feature Specification: Compatible model execution performance

**Feature ID**: FEAT-2
**Date**: 2026-09-08
**Author**: Codex, from Jesus Lara's requirements and proposal
**Status**: review
**Target version**: next backward-compatible release; release number to be assigned by the maintainer, without changing this specification's behavior guarantees
**Proposal**: `sdd/proposals/compatible-model-performance.proposal.md`, including the validation-gating follow-up
**Research**: `sdd/state/FEAT-002/findings/F001-*.md` through `F008-*.md`
**Identity provenance**: allocator returned `FEAT-2` verbatim; reservation commit `8a838177bc71a626907f9f967e89f83f5adfe537`. The zero-padded `FEAT-002` research directory is the same proposal's prior research identity, not another feature or an ID reuse exception.

---

## 1. Motivation & Business Requirements

### Problem Statement

Company ORM consumers depend on python-datamodel's dataclass-compatible API and observable runtime behavior. Migrating those consumers to Pydantic is outside this feature. Construction needs to become faster without requiring changes to model declarations or application code.

The proposal's local Employee benchmark measured median raw construction at 36.5 µs, already-typed construction at 29.2 µs, and Pydantic model construction at 2.5 µs. These are historical, single-workload observations with different library contracts, not performance acceptance baselines. The user subsequently reported 220,000 `_validation_` calls for 20,000 builds and approximately 15 µs in that stage. The source confirms dispatch for every field that reaches the validation stage; it does not prove that all of that time is removable. See findings F003 and F008.

Nine Employee fields receive built-in validators automatically; `skills` and `manager` take generic validation paths. A missing user validator or missing constraints does not imply an absence of validation work. Optimization must eliminate redundant execution while retaining implicit type, presence, nested and error semantics.

### Goals

- G1. Preserve the complete existing consumer contract: construction, coercion, validation, errors, dataclass/ORM integration, mutation, hooks and serialization.
- G2. Make loop-level validation gating the first production optimization. Precompute stable per-field execution policy and avoid the generic dispatcher when equivalent narrow checks or proven conversion postconditions suffice.
- G3. Reduce successful-path allocations and repeated dispatch/metadata work, with cache correctness under existing mutation routes.
- G4. Establish reproducible differential and performance evidence before enabling optimized behavior by default.
- G5. Evaluate a coarse sequential Rust executor after the Cython improvements; evaluate parallel native work for sufficiently large independent workloads.
- G6. Evaluate serialization independently, retaining the existing output and copying contracts.

### Non-Goals (explicitly out of scope)

- Pydantic migration, Pydantic runtime dependency, Pydantic coercion/error semantics, or a new model declaration API.
- Disabling validation, requiring a rebuild/cache-invalidation call, changing default strictness, or requiring a batch constructor for existing consumers.
- Fixing incidental legacy bugs, changing parser callback semantics, or making previously ignored constraints active as part of a performance change.
- Replacing dataclass initialization or assignment/history behavior wholesale.
- Mandatory threading for each small model, a guaranteed 15x speedup, or treating the estimated 15 µs as measured savings.
- Platform expansion, package version bumps, or rewriting the parallel infrastructure work in FEAT-001.

### Compatibility authority

The initial engineering reference is commit `d932c720e9e36bbacdaca2b1a2af0688f2636c40`, package version `0.10.21`. Rebuild its relevant extensions in an isolated environment and record source and binary hashes. Existing locally installed extensions are useful diagnostics but do not establish source/binary equivalence.

The deployed company version(s) and representative integration corpus remain a release dependency. Their absence does not prevent implementation against the engineering reference, but prevents claiming complete company compatibility or approving default rollout. When supplied, add each deployed artifact as a reference. Conflicting consumer baselines require explicit scope resolution; never silently choose new behavior.

## 2. Architectural Design

### Overview

Retain the generated dataclass initializer, alias handling and existing per-field conversion order. Add a conservative execution policy at class/field setup. At the existing validation boundary, combine that policy with the current value, parser outcome and live field settings to select specialized validation or the existing dispatcher. Build errors only on failure where their former allocation has no observable effect.

The production requirement is a compatible Cython fast path. Rust, parallelism and serialization are bounded experiments with recorded promotion decisions. An experiment may conclude that the legacy path should remain; it must supply measurements and incompatibility evidence rather than remain unfinished. Failed experimental implementations must not become a default backend.

### Component Diagram

```text
Class creation -> guarded per-field policy (stable dispatch choices)
                                   |
Existing dataclass initialization  |
  -> existing ordered conversion <-+
  -> live eligibility / required-work decision
       | proven safe             | custom / complex / changed / uncertain
       v                         v
     narrow checks             existing _validation_
       +-------------------------+
                   |
         existing state/errors/exception behavior

After parity and measurement:
same execution policy -> sequential Rust experiment -> bulk parallel experiment
existing JSON path   -> separate serialization experiment
```

### Integration Points

| Existing component | Integration | Constraint |
|---|---|---|
| `ModelMeta._initialize_fields` / `ModelMeta.__new__` | Classify field execution once | Account for cache-hit and inherited fields; no cross-class policy sharing through an incomplete class-cache key |
| `Field` | Hold private policy or associate it with an owning class plan | Keep public fields, metadata, dataclass behavior and serialization compatible |
| `BaseModel.__post_init__` | Retain entry to `processing_fields` | Preserve strict/non-strict state and exception construction |
| `processing_fields` | Gate validation at the current location | Preserve conversion/writeback/interleaving and current error fall-through |
| `_validation_` / `_validation` / `_validate_constraints` | Legacy fallback and specialized checks | Built-in and user callback routes remain semantically distinct |
| `register_parser`, dynamic field methods, mutable metadata | Observe current behavior | No caller-managed invalidation requirement |
| `ModelMixin.json` / `JSONContent` | Separate serialization candidate | Preserve encoder construction/options, output types and hooks |
| `rust/rs_core` | Experimental executor | Existing prototype is not a compatible production engine |

### Data Models — proposed private policy

These names describe **new internal state**, not existing imports or public APIs. An equivalent compact Cython representation is allowed; do not construct Python policy objects per instance.

| Policy element | Meaning |
|---|---|
| `kind` | Conservative dispatch class: legacy, supported scalar, or subsequently proven container |
| `work_mask` | Possible presence, type/structure, constraint and custom/generic work for that policy |
| `declared_type`, `field_identity` | Identity guards for the policy's original interpretation |
| `builtin_parser`, `builtin_validator` | Known implementation identities, never a promise about arbitrary callback results |
| `constraint_shape` | Which legacy constraint sources may apply for this type; not a cached assertion that mutable constraints are absent |

Default policy is legacy. A newly added field, an uninitialized policy, an unknown type, a custom Field subclass, a descriptor, or a changed identity must work through the existing path. Cache entries must not contain instance values, errors, default-factory results or input-derived validity decisions.

Class-owned plans must use actual class/field identity and be constructed from the final fields seen by the legacy pipeline, including on metaclass-cache hits. Attach plans to their owning class or otherwise ensure collectability; do not introduce an unbounded global strong-reference cache. Existing shared Field/default behavior must not be silently corrected by the plan.

### Required validation-gate algorithm

1. Run existing field access, empty/default handling and conversion in their current order. Preserve the existing equality-based writeback decisions. Record success/proof information without an additional user callback or equality invocation.
2. Decide eligibility at the validation boundary, **after** conversion and any callback that could mutate configuration. Never decide permanently from the incoming value alone.
3. Unknown/custom/changed fields, parse failures and value subclasses with potentially observable operations use `_validation_`. The initial fast path targets exact scalar values and known built-in implementations.
4. Preserve `_validation_`'s special-value behavior, including empty/missing handling, required/primary/null rules and `db_default`. Initially send these cases through the legacy dispatcher; do not generalize “empty” to falsiness or equate `0`/`False` with missing.
5. For eligible nonempty values, establish equivalent type validity using the successful known conversion branch or a narrow guard. “Already typed” and “has no constraints” are insufficient proofs. Keep unsupported subclass acceptance through the fallback, rather than narrowing the public accepted types.
6. Consult the constraints the legacy route actually executes. If residual constraints exist, run their equivalent checks in the same order. If nothing remains, skip `_validation_`. Specialized constrained paths may also bypass `_validation_` while still checking the constraints.
7. Preserve the legacy distinction between the cached `f.validator` route and the custom validator in `f.metadata`. Do not invoke callbacks the reference did not invoke, or skip ones it did. A custom callback or replaced built-in implementation forces the corresponding legacy path initially.
8. On failure, preserve the same field error contents and exception behavior. Where a narrow type guard fails, calling the legacy dispatcher to produce the canonical error is preferred. Do not invoke a parser/factory again to generate the error.

The dispatcher gate may be represented by a boolean only when that boolean means **no required work remains for this invocation**. A class-time `validator is None` or `has_constraints is False` flag is not sufficient.

### Mutation and invalidation policy

The first implementation caches stable dispatch shape and implementation identity, and reads mutable semantic inputs live. Do not wrap public dictionaries in new observable types or freeze their contents just to obtain fast version counters.

- Retain the current column snapshot per invocation until a replacement can preserve direct dictionary changes, ordering and changes made during callbacks. Dictionary identity and length alone cannot detect replacement of a field or constraint value.
- Read the active metadata/constraint values and Meta settings needed by the reference route at the same semantic stage. The current `metadata` view can expose changes through the underlying `_meta` dictionary; guard against replacement of either object. Preserve absent-key versus explicit-None behavior.
- Guard field type/category and built-in parser/validator identities. Same object identity does not prove mutable metadata unchanged. Invalid guards select legacy execution; they do not reject construction or require application intervention.
- Parser registration must keep affecting the same call sites at the same time as before. Initial policies must not cache a result of the mutable parser registry for generic paths.
- A callback may mutate another field, a current constraint or a subsequent configuration setting during construction. Do not cache those values for the entire model in a way that hides an update the legacy loop sees.
- Fully snapshotting mutable constraint contents is deferred unless all exposed mutation routes are covered with equivalent behavior. The performance target does not justify stale validation decisions.

### Success-path allocation changes

Delay `_validation_`'s error dictionary until a branch needs an error. Preserve fresh, independently mutable results for externally callable functions that return dictionaries; do not replace their success return with `None` or a shared mutable singleton. Internal boolean/sentinel results may be introduced only behind unchanged public/cpdef boundaries. Avoid moving lazy allocation into a new per-field tuple or object allocation.

Remove unused metadata reads only for plain built-in Field behavior where access has no externally observable hook. Preserve error precedence and any exceptions raised by custom fields by retaining their old path.

### Rust and parallel execution experiments

The sequential Rust experiment must compare against the **optimized Cython** baseline. Prefer one model-level call with an already-built plan over one Python-callable Rust function per field. It must preserve ordered conversion/validation or conservatively select the entire legacy model path before running callbacks. Do not parse twice when falling back after partial execution.

Begin with supported exact native/scalar inputs and explicit legacy fallback. Python arbitrary-size integers, Decimal precision/context, Unicode, regex semantics, date/datetime acceptance, UUID types and custom Python operations are compatibility boundaries. Do not globally substitute the existing Rust scalar parsers: the large-integer counterexample in F002 already disproves parity.

The parallel experiment uses owned immutable snapshots of independent pure work, a detached calling thread during native computation, bounded reusable Rayon workers, and original-order result reconstruction. Snapshot extraction, object reconstruction and synchronization count toward total latency. Worker code must not dereference Python objects or invoke Python callbacks while detached. No claim is made that a Rust function accessing Python values is automatically GIL-free.

Benchmark record batches and large homogeneous collections, initially at sizes 1, 10, 100, 1,000 and 10,000. Ordinary constructor calls remain sequential unless a separate measured, compatible internal collection threshold qualifies them. Batch execution is a development experiment in this feature; no new public batch API is introduced.

Preserve serial barriers for side effects, first-raised exceptions, field order, callback counts and mutations. Sorting errors after speculative callbacks is insufficient. Parallel eligibility requires proof that discarded speculative pure results are unobservable. Avoid `unwrap`/panic behavior for invalid user input and avoid nested thread-pool oversubscription. Negative benchmark or parity results must result in a documented decision to retain sequential execution.

### Serialization experiment

Measure `json()` separately from `to_dict()`, with cold and warm encoder costs separated. A candidate may reduce intermediary copying/traversal only when custom encoders, `__deepcopy__`, nested dataclasses, Decimal conversion, exclusion/null behavior and exact output remain equivalent. Preserve public dictionary-copy semantics and per-call encoder options; do not globally cache mutable encoder instances. A failed parity or performance comparison leaves the current path active.

### New Public Interfaces

None. Existing constructors, `Field`/`Column`, dataclass operations, model methods and configuration keep their signatures. Diagnostic backend selection and call counters belong to the test/benchmark build or private harness, not model configuration requirements. No Pydantic schemas become part of the public contract.

## 3. Module Breakdown

All listed new paths are planned deliverables. Existing paths are verified in §6. Tasks must declare narrower ownership within this list.

| Module | Paths | Responsibility | Depends on |
|---|---|---|---|
| M1 — Reference and measurement harness | **New** `tests/compatibility/`, `tests/fixtures/model_performance/`, `benchmarks/model_performance.py` | Paired isolated reference/candidate runs, deterministic corpus, timings and provenance | None |
| M2 — Conservative field policy | Existing `datamodel/fields.pyx`, `datamodel/abstract.py`, `datamodel/validation.pyx`; **new** `tests/test_validation_policy.py` | Stable policy, known built-in identities, safe default and mutation guards | M1 |
| M3 — Gated Cython validation | Existing `datamodel/converters.pyx`, `datamodel/validation.pyx`, `datamodel/validation.pxd`; **new** `tests/test_validation_fastpath.py` | Loop gate, equivalent narrow checks, lazy errors and legacy fallback | M2 |
| M4 — Further measured structural work | Existing `datamodel/base.py`, `datamodel/abstract.py`, `datamodel/converters.pyx` | Profile remaining assignment/column/metadata costs; implement only proven compatible improvements or record why deferred | M3 |
| M5 — Sequential Rust experiment | Existing `rust/rs_core/src/lib.rs`, `rust/rs_core/Cargo.toml`; **new** `benchmarks/native_validation.py` | Cached coarse native executor, parity and total-cost comparison; explicit promotion decision | M3 |
| M6 — Parallel experiment | Same native experiment paths as M5 | Pure-work eligibility, chunks, bounded workers and measured crossover | M5 |
| M7 — Serialization experiment | Existing `datamodel/models.py`, `datamodel/parsers/json.pyx`, `tests/test_json.py`; harness from M1 | Compatible candidate or documented decision to retain current traversal | M1; final measurement after M3 |
| M8 — Evidence and release documentation | **New** `docs/performance.md`, `benchmarks/results/compatible-model-performance/` | Reproducible reports, compatibility coverage, decisions, fallback behavior and rollout requirements | M1–M7 |

M5/M6 may build their development extension explicitly without changing default package loading. This specification does not authorize unreviewed packaging/default-backend wiring on the strength of a microbenchmark. If promotion requires additional installed artifacts, update the spec's exact loader/build contract before task assignment for that change.

## 4. Test Specification

### Unit Tests

Names below are planned tests, not existing imports.

| Test / family | Required observation |
|---|---|
| `test_policy_defaults_to_legacy` | Uninitialized/dynamic/custom fields do not silently lose checks |
| `test_unconstrained_scalar_skips_dispatch` | Known valid nonempty scalar inputs skip the generic dispatcher while preserving typed results |
| `test_constraints_survive_fastpath` | Numeric bounds/equality and string lengths/patterns retain limits, precedence and error text |
| `test_invalid_parser_result_is_rejected` | Replaced parser returning an invalid type gets the reference error without duplicate invocation |
| `test_presence_rules_match_reference` | Missing, None, empty string/container, zero, False, required, primary, nullable and db_default match both strict modes |
| `test_mutation_is_visible` | `_meta` updates/deletions, metadata replacement, constraint attributes, parser/validator/type changes, Meta changes and registry updates match the reference without rebuild calls |
| `test_callback_mutates_next_field` | Mutation during one field's processing is visible at the same later field stage |
| `test_error_order_and_fallthrough` | Multiple invalid fields, immediate exceptions and parse-error overwrite/fall-through retain payload and callback order |
| `test_generic_and_subclass_fallback` | Unions, Literal, callable/awaitable, nested containers, subclasses and unknown values retain the reference path/behavior |
| `test_policy_isolation_and_lifetime` | Same-name classes, inherited/replaced fields, dynamic classes and class collection do not introduce stale/shared plans or unbounded retention |
| `test_success_results_not_shared` | Externally returned success dictionaries and error payloads remain independently mutable |
| `test_native_boundaries` | Large integers, Decimal context/range, bool/int distinction, temporal inputs, Unicode and unsupported values never narrow the legacy contract |
| `test_parallel_order_and_threshold` | Small work is sequential; pure parallel cases preserve results/order; callback-bearing cases retain serial behavior |
| `test_serialization_parity` | Exact JSON type/content/options and dictionary copying/hook behavior match |

### Integration Tests

Run the complete repository test suite against fresh candidate extensions and the reference on matching interpreters. Do not count a passing subset as complete compatibility. Reproduce baseline failures separately and identify unavailable external services without weakening assertions or marking newly introduced failures as baseline defects.

Relevant existing coverage includes `tests/test_field.py`, `tests/test_converter.py`, `tests/test_validations.py`, `tests/test_valid_callables.py`, `tests/test_inherit.py`, `tests/test_descriptors.py`, `tests/test_aliases.py`, `tests/test_unions.py` and `tests/test_json.py`. Add coverage for constructor positional/keyword behavior, dataclass fields/asdict/replace, equality/hash/repr, model hooks, assignment/history, dynamic fields, ORM primary-key helpers and downstream consumer tests.

Test every supported CPython version in the project's 3.10–3.14 release matrix. Run Linux x86_64 coverage and any Windows support delivered by FEAT-001 before claiming those deployments compatible. Missing locally installed interpreters are a CI/release requirement, not permission to reduce declared support. Any new native backend must leave the existing path usable when its extension is absent. Existing rs_parsers-absent behavior must be characterized separately; this feature must not silently claim its currently incomplete fallback is fully functional.

### Test Data / Fixtures

Port the existing Employee shape and raw/native values to deterministic fixtures without changing its contracts. Add small unconstrained/constrained scalar models, 50-field models, nested ORM relationships, typed containers, invalid payloads and custom callback models. Construct independent mutable inputs for each backend while preserving each fixture's internal alias graph; never reuse a model mutated by the other backend.

The reference/candidate harness runs in separate subprocesses/environments. Compare values with type tags, ordered field states, exception type/message/payload/cause, input mutations, callback event logs and observable alias/copy relationships. Do not normalize int/bool, Decimal/string, date/datetime or bytes/str into equality. Address-dependent identity is compared as relationships within each run, not literal memory addresses across processes. Stub clocks/randomness and side effects; never run production callbacks twice in live systems.

### Performance protocol

Use freshly built release artifacts with matching compiler flags, dependency versions and backend availability. Record commit, binary hashes, Python/Cython/Rust versions, CPU/OS, warm-up, affinity where available, GC policy and worker count. Keep instrumentation disabled for acceptance timings; use separate profiling builds for native call counts and allocation attribution.

Use at least seven paired fresh-process runs per backend. Each process warms the case for 1,000 operations and records at least 30 batches of 2,000 constructions (smaller batch sizes are allowed for large nested data if recorded and equal between variants). Time batches, not a clock call around every constructor. Alternate reference/candidate order. Keep input preparation outside timing when isolating constructors; additionally time end-to-end bulk extraction/reconstruction for native experiments.

Report median per-build latency and upper-tail batch latency, ratios, variability, peak temporary allocations and retained memory. Use process-level paired ratios for uncertainty estimation; a claimed improvement must have a 95% confidence interval below 1.0. If machine noise prevents distinguishing a 5% regression, rerun in a controlled environment rather than declare success.

Workloads: Employee raw/native, unconstrained primitives, constrained fields, nested/container models, custom hooks, invalid input, 50-field models, cold class creation, assignment, JSON and dictionary conversion. Pydantic and stdlib may be contextual references; only same-contract old/new python-datamodel ratios decide acceptance.

## 5. Acceptance Criteria

The numeric thresholds below are engineering targets proposed for review, not measured gains or a claim that the user specified a speedup guarantee.

- [ ] AC1. Reference artifact/provenance and deterministic compatibility corpus are recorded; reference and candidate use freshly built matching environments.
- [ ] AC2. All applicable existing tests pass with no new failures; all differential cases match exact behavior. Any existing failure is reproduced on the reference and explicitly tracked.
- [ ] AC3. Successful, nonempty, ordinary Employee inputs require at most **3 generic `_validation_` dispatches per build**, down from the current 11; an all-unconstrained supported scalar fixture requires zero generic dispatches. Inline/specialized checks still execute required validation. Counters are collected in a separate diagnostic build.
- [ ] AC4. Missing/null, parse failure, custom behavior, constraint and mutation cases retain their reference outcomes, error payloads, order and callback counts. No rebuild call or model declaration change is required.
- [ ] AC5 (**revised 2026-09-08 — see Amendment 1**). The optimized Cython candidate, measured against the engineering reference using §4's protocol, reduces median construction latency by at least:
  - **8%** for both raw and native Employee, with the whole 95% confidence interval below 1.0; and
  - **12%** for an all-unconstrained supported-scalar model.

  Actual savings, the confidence interval and remaining generic dispatches are reported; no absolute 15 µs saving is assumed. *(Original target: 20% on Employee raw and native. Not met; measured limit and rationale in Amendment 1.)*
- [ ] AC6. Representative nested/custom/invalid/assignment/serialization cases regress by no more than **5%** in median or upper-tail batch latency. Cold class creation and retained per-class memory are reported; cache-growth tests show bounded/collectable storage, and steady-state construction does not rebuild the class plan.
- [ ] AC7. Required public/cpdef return types, fresh mutable results, dataclass behavior, ORM primary keys, aliases, defaults and assignment/history are unchanged. New policy state does not leak into JSON, field lists or public dictionary results.
- [ ] AC8. Sequential Rust experiment records full-cost parity and performance against optimized Cython. Promotion requires all applicable parity/regression gates and at least **10% additional improvement** on its declared eligible workload. Otherwise a completed report retains Cython.
- [ ] AC9. Parallel experiment records tested sizes, thread counts, memory and crossover. Promotion requires at least **1.25x throughput** versus sequential Rust on an eligible large workload, including transfer/reconstruction costs, and preserved small-work sequential behavior. Otherwise a completed report retains sequential execution. No new public batch API ships under this spec.
- [ ] AC10. Serialization experiment records exact parity and cold/warm results. Promote only with at least **10% warm JSON improvement** and no regression beyond AC6; otherwise retain the current path and document the result.
- [ ] AC11. `docs/performance.md` and machine-readable benchmark reports describe gains, remaining costs, fallback cases, mutation behavior and all experiment decisions. No benchmark bypasses validation or narrows accepted inputs to meet a target.
- [ ] AC12. Before default rollout, the maintainer identifies deployed baseline(s), supplies/approves representative company ORM integration results, and confirms the Python/platform coverage. Pending external evidence remains an explicit release blocker; repository-only tests do not certify complete company compatibility.

If AC3/AC5 cannot be met compatibly, report the measured limit and revise the specification through review. Do not mark the feature complete solely because Rust/parallel experiments were performed or because some scalar benchmark improved.

### Amendment 1 — AC5 threshold revised (2026-09-08)

Invoked under the clause immediately above. **Approved by Jesus Lara (spec
owner) on 2026-09-08** after the measured limit was reported.

**Measured limit.** Two full acceptance runs under §4's protocol, on a quiet
machine (calibration spread 5.6% and 8.2%, zero suspect processes, no protocol
shortfalls), with a same-source control establishing a cross-build noise floor
of 0.95–1.55%:

| workload | run 1 | run 2 |
|---|---|---|
| Employee raw | 10.63% | 9.58% |
| Employee native | 10.95% | 9.91% |
| unconstrained scalars (native) | 15.8% | 16.0% |
| wide 50-field models | ~11.5% | ~11.3% |

11 of 15 workloads improved; best 16.0%, median 9.9%. A 20% effect is
comfortably resolvable at this noise level (worst resolvable effect 1.24%), so
the shortfall is a measured result, not an instrument limitation.

**Why 20% is not reachable compatibly.** AC3's mechanism is *exhausted*: the
diagnostic build confirms an all-scalar model now reaches the generic
`_validation_` dispatch **zero** times per build, and Employee exactly **twice**
— its two non-scalar fields (`List[str]`, `Optional[Employee]`), which are
ineligible by design. Roughly 10% is what that dispatch actually cost. Employee
is the *weakest* improved workload for precisely this reason, which is why the
revised criterion states the scalar case separately rather than hiding it in a
single number.

The remaining cost is per-field conversion, the `_dc_method_setattr_` path and
the per-build column snapshot. The latter two were profiled and **rejected as
unsafe with demonstrated evidence** (`benchmarks/results/compatible-model-performance/structural.json`):
passing a live `__columns__.items()` view breaks a callback that mutates
`__columns__` mid-build (tolerated on both builds today), and a cached
membership set goes stale because `__fields__` is public and mutated in place —
including by property setters, as an adversarial review demonstrated.

**Why the revised numbers.** 8% and 12% sit clear of the ~1.5% noise floor and
retain real headroom below the measured values, so ordinary machine variation
will not flake them, while still failing loudly if the gate regresses or is
accidentally disabled (Employee would fall to ~0%). They are deliberately *not*
set to the measured values, which would make the gate unfalsifiable.

**Scope of this amendment.** AC5 only. AC6 and every compatibility criterion
(AC1, AC2, AC4, AC7, AC12) are unchanged and all pass as originally written —
which matches the resolved business priority in §8: *"preserve current
compatibility with asyncdb.models but adding speed up improvement."* The native
experiments (AC8/AC9/AC10) keep their own promotion thresholds and are still
measured against the frozen optimized-Cython candidate, so this amendment does
not lower the bar for them.

## 6. Codebase Contract

Verified against the engineering reference listed in §1. Relevant production source is unchanged from the initial proposal reference; the intervening runtime-tree change removed the unused profiling artifact. Paths below exist and their cited sections were read. Line numbers are anchors and must be rechecked after earlier implementation tasks modify a file.

### Verified Imports

These Python imports were executed successfully in the existing local environment; this verifies symbol availability, not fresh-build provenance.

```python
from datamodel import BaseModel, Field, Column  # datamodel/__init__.py:6,8
from datamodel.abstract import ModelMeta  # datamodel/abstract.py:148
from datamodel.models import ModelMixin  # datamodel/models.py:96
from datamodel.converters import processing_fields, register_parser, encoders
# datamodel/converters.pyx:1922,532,511
from datamodel.validation import _validation, validators
# datamodel/validation.pyx:469,83
from datamodel.exceptions import ValidationError  # datamodel/exceptions.pyx:24
from datamodel.parsers.json import JSONContent  # datamodel/parsers/json.pyx:85
```

Existing Cython-only interface, declared in `datamodel/validation.pxd:4` and used from `datamodel/converters.pyx:33`:

```cython
from .validation cimport _validate_constraints
```

`_validation_` is a `cdef` function in the converters module, not the similarly named Python-importable `_validation` in the validation module.

### Existing Class and Function Signatures

| Verified location | Existing signature / state | Contract |
|---|---|---|
| `datamodel/fields.pyx:70,128` | `class Field(ff)`; `__init__(self, default=None, nullable=True, required=False, factory=None, min=None, max=None, validator=None, pattern=None, alias=None, kw_only=False, metadata=None, doc=None, **kwargs)` | Python class extending dataclasses.Field; public mutable configuration plus cached parser/validator/type information |
| `datamodel/fields.pyx:215,241,302` | `_meta` dictionary; dataclasses.Field initialization; `typeinfo` property | Metadata view can expose backing-dictionary updates; do not infer semantic immutability from a mapping proxy |
| `datamodel/abstract.py:180` | `_initialize_fields(attrs, annotations, strict)` (static method) | Returns columns, type categories, typing arguments, aliases and primary keys |
| `datamodel/abstract.py:249,258` | `df.parser = encoders[_type]`; `df.validator = validators[_type]` | Built-in function caching and custom encoder override |
| `datamodel/abstract.py:352,358` | `ModelMeta.__new__(cls, name, bases, attrs, **kwargs)`; key `(name, tuple(bases), tuple(sorted(annotations.items())))` | Existing cache omits defaults/configuration and shallow-copies field mappings; do not reuse it as a complete plan key |
| `datamodel/abstract.py:462,471` | dataclass decoration; `__columns__`, `__fields__`, `__values__`, `__aliases__`, `__primary_keys__` | Preserve the actual class's existing observable state, including legacy sharing |
| `datamodel/abstract.py:66,128,516` | `_dc_method_setattr_(self, name: str, value: Any) -> None`; `_validate_field_assignment(self, name: str, value: Any) -> Any`; `ModelMeta.__call__(cls, *args, **kwargs)` | Assignment bookkeeping and parser-only assignment conversion; aliases before constructor |
| `datamodel/base.py:35,41` | `BaseModel.__post_init__(self) -> None`; `list(self.__columns__.items())` | Snapshot field order then dispatch; strict/non-strict result processing |
| `datamodel/base.py:59,69,82,104` | `register_parser(cls, target_type: Any, func: Callable, field_name: str = None)`; `add_field`; `create_field`; `set` | Runtime extension paths must remain visible |
| `datamodel/converters.pyx:532` | `cpdef object register_parser(object _type, object parser_func)` | Mutates module Cython `TYPE_PARSERS`; no existing registry epoch API |
| `datamodel/converters.pyx:964` | `cpdef object parse_basic(object T, object data, object encoder = None)` | Existing conversion entry, not an unconditional type-validity guarantee |
| `datamodel/converters.pyx:1922,2297` | `cpdef dict processing_fields(object obj, list columns)` | Existing conversion loop and unconditional validation boundary |
| `datamodel/converters.pyx:2314` | `cdef object _validation_(str name, object value, object f, object _type, object meta, str field_category, bint as_objects = False)` | Special values, set checks, cached validator or generic fallback |
| `datamodel/converters.pyx:2372` | `cdef object _field_checks_(object f, str name, object value, object meta)` | Primary, required, nullable and db_default behavior |
| `datamodel/validation.pyx:307` | `cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type)` | Legacy string/numeric checks and error construction |
| `datamodel/validation.pyx:469` | `cpdef dict _validation(object F, str name, object value, object annotated_type, object val_type, str field_type, bint as_objects=False)` | Custom metadata callback and generic validation |
| `datamodel/exceptions.pyx:24,26` | `cdef class ValidationError(ModelException)`; `__init__(self, str message, dict payload = None)` | Error payload and field-order-dependent string output |
| `datamodel/models.py:134,138,209,304` | `reset_values`; `old_value`; `to_dict(self, remove_nulls=False, convert_enums=False, as_values=False, exclude=None)`; `json(self, **kwargs)` | History, copying and JSON encoder behavior |
| `datamodel/parsers/json.pyx:85,95` | `cdef class JSONContent`; `default(self, object obj)` | Includes Decimal-to-float encoding and custom types |
| `rust/rs_core/src/lib.rs:180,245` | `get_field_info(...)`; `parse_datamodel(py: Python<'_>, dataclass_instance: Py<PyAny>) -> PyResult<Vec<(String, bool)>>` | Prototype extracts per call, narrows integers, skips unsupported types, uses Rayon, returns booleans rather than compatible errors |
| `datamodel/rs_parsers/__init__.py:8` | `HAS_RUST = False`, optional imports | Presence flag alone does not prove every converter uses Rust or that absent-Rust fallback works |
| `setup.py:15,82` | Extension list and `cythonize(extensions, annotate=True)` | Existing Cython build; extra declarations must match extension boundaries |
| `pyproject.toml:19,42,58` | Python >=3.10; runtime and development dependencies | Pydantic is a development dependency; no new runtime engine dependency is required |

### Behavioral anchors

- `validation.pyx:28` accepts Python int subclasses (including bool); `:59` accepts date as well as datetime for its datetime validator. Exact-type fast paths must fall back to preserve broader acceptance.
- `validation.pyx:355` and `:400` distinguish metadata keys from attribute defaults. Explicit None can suppress an attribute fallback; preserve this rather than checking only for truthy values.
- `validation.pyx:427` and `:437` use inclusive numeric bounds although existing error text says “greater than”/“less than.” Preserve both the predicate and message.
- `converters.pyx:2354` routes cached primitive validators separately from `validation.pyx:488`'s metadata callback. Do not combine them into new callback semantics.
- `converters.pyx:1994` captures some parser exceptions and continues into validation. Moving all failures to a new uniform early-exit path changes behavior.
- `models.py:216` may mutate a supplied exclusion set; `:220` and `:306` use dataclasses.asdict. A performance refactor must not silently change those effects.

### Does NOT Exist (Anti-Hallucination)

- No existing `needs_validation`, `_validation_work` or `__validation_plan__` implementation was found in runtime sources/tests. The policy in §2 is new work.
- No public `validate_many` or `model_validate_many` API was found. Benchmark-only batch experiments must not claim one exists.
- `rust/rs_validators/src/lib.rs` is empty; it is not a callable production validator engine.
- `rust/rs_core` is a prototype, not a drop-in implementation of `_validation_`; Cargo workspace membership does not wire it into the Python constructor.
- No Python import of the Cython `cdef _validation_` is available through the existing interface; use build instrumentation or an explicitly new private test mechanism.
- No existing automatic version counter covers arbitrary Field/Meta/backing-metadata changes. Do not invent one in a task or assume mutations are intercepted.
- Proposed benchmark, compatibility-test, result and performance-documentation paths in §3 are new deliverables and were absent when this contract was prepared.

## 7. Implementation Notes & Constraints

### Patterns to Follow

- Keep small changes independently measurable, beginning with M1–M3. Preserve legacy execution for cases outside proven eligibility.
- Keep release-build benchmarks separate from diagnostic Cython profiling; instrumentation changes call costs.
- Preserve the cpdef surface and necessary `.pxd` declarations. A faster Cython implementation is acceptable without a language migration.
- Persist performance reports with enough environment/provenance detail to reproduce decisions. Never persist production secrets or live customer payloads in fixtures.

### Worktree Strategy

**Isolation: per-spec.** After approval, use one feature worktree based on `dev` for this spec. M2–M4 share core fields/metaclass/converter files and must be sequenced; M5–M6 share the native experiment and must also be sequenced. M1 fixtures and M7 serialization can be prepared independently once their contracts are stable, but integrate and measure in the same spec worktree. No sub-agent delegation is required by this specification.

Coordinate build/package changes with the existing FEAT-001 infrastructure feature. This feature must not overwrite its compiler flags, interpreter matrix or Rust staging work. If that work lands during implementation, rebase/merge normally and rebuild both benchmark variants comparably. Per-task file ownership must prevent simultaneous edits to the same Cython or Rust modules.

### Known Risks / Gotchas

- Cython code still using Python Field objects can spend most time in dynamic dispatch; native code alone is not proof of speed.
- A stale “no constraints” flag is a correctness defect. Live mutable settings remain necessary unless stronger invalidation is proven.
- User-defined equality, length, descriptors, callbacks and deepcopy hooks can be observable. Eligibility must be conservative; the contract is not restricted to happy-path value equality.
- Existing cache collisions and shared state are characterization cases. Avoid amplifying them; separate any behavior-changing fix from this feature.
- Pure Rust workers may parallelize compute, but Python extraction/reconstruction and callbacks constrain gains. Keep worker/memory costs in measurements.
- Previously built `.so`/`.pyd` artifacts can mask source changes. Verify loaded paths and hashes after every native rebuild.
- The allocator emitted the non-padded ID `FEAT-2`. Preserve it. Before decomposition verify downstream ID tooling accepts that spelling; do not reserve a second ID or silently create another feature identity. Research paths remain `FEAT-002`.

### External Dependencies

| Package / tool | Existing declared version | Use |
|---|---|---|
| Cython | >=3.0.11 in current build/dev declarations | Existing compiled execution; honor any floor raised by FEAT-001 |
| pytest / pytest-asyncio | >=7.0.0 / >=0.21.0 | Existing tests and compatibility harness |
| orjson / ciso8601 | >=3.10.11 / >=2.3.2 | Existing encoding/parsing behavior |
| PyO3 | 0.29 | Existing Rust/Python interface, experimental executor |
| Rayon | workspace 1.10; rs_core declares 1.5.3 | Existing native parallelism dependency; verify resolved lock version at experiment build |
| Pydantic | >=2.0, development only | Contextual benchmark and existing SDD tools |

No dependency upgrade is required to begin M1–M3. Pin actual resolved versions in benchmark environments. Any additional profiling/build tool must be development-only. Primary architectural references from the proposal: [Pydantic architecture](https://pydantic.dev/docs/validation/latest/internals/architecture/), [PyO3 parallelism](https://pyo3.rs/main/parallelism), and [Rayon ParallelIterator](https://docs.rs/rayon/latest/rayon/iter/trait.ParallelIterator.html); these inform design, not behavioral compatibility guarantees.

## 8. Open Questions

- [x] Compatibility requirement — user: “we need to preserve the complete backward compatibility with current codebase.” Applied to G1, the differential corpus and AC2/AC4/AC7/AC12.
- [x] Rust/parallelism exploration — user: “maybe one aggresive idea is migrating _validation_ to rust and executes the validation in parallel?” Included as M5–M6; no automatic promotion is inferred.
- [x] Structural refactor — user: “Gating that call at the loop on a precomputed per-field flag is where the remaining ~15 µs lives, we need to also do some refactor for optimization there.” Included as the first production optimization, M2–M3, with the estimate retained as unverified attribution.
- [x] Which deployed version/commit and company ORM model/test corpus define compatibility? — Owner: Jesus Lara/company maintainers. Engineering reference specified in §1; blocks company release certification, not initial harness/gate implementation.: schema examples in examples/ folder and asyncdb.models (that uses under-the-hood python-datamodel) requires strict compat.
- [x] Which workloads and latency/throughput targets have business priority? — Owner: Jesus Lara. Current review proposal prioritizes constructor/ORM hydration; quantitative engineering targets are AC3/AC5/AC6: The idea is not be a "pydantic" equivalent, is preserve current compatibility with asyncdb.models but adding speed up improvement.
- [x] Which deployment Python/platform combinations must support acceleration? — Owner: release maintainer. Preserve the current supported matrix and integrate FEAT-001 coverage; certify actual company platforms before rollout: yes, all in FEAT-001 matrix.
- [x] What release number and rollout date should carry the compatible Cython optimization? — Owner: release maintainer. Does not affect implementation architecture or authorize a version bump here: 0.11.0 will be released with these changes.

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-09-08 | Codex | Formal spec from proposal and both follow-ups; verified contracts, mutation-safe gating, differential/performance acceptance and conditional native experiments |
