---
id: FEAT-002
title: Accelerate model execution while preserving python-datamodel behavior
slug: compatible-model-performance
type: feature
mode: enrichment
status: discussion
source:
  kind: inline
  fetched_at: 2026-09-08
  summary_oneline: Improve existing ORM model performance with complete backward compatibility.
overall_confidence: medium
base_branch: dev
research_state: sdd/state/FEAT-002/
created: 2026-09-08
updated: 2026-09-08
---

# FEAT-002 — Compatible model performance

## 0. Origin

The user wants existing company ORM consumers to gain performance without migration or behavioral changes, and proposes Rust and parallel validation. Exact source and follow-up are preserved in [source.md](../state/FEAT-002/source.md).

Hard acceptance constraint: backward compatibility with the deployed company baseline. Current checkout is provisional until the deployed version and consumer corpus are identified. No implementation is included in this proposal.

## 1. Synthesis

Build a reusable execution plan per model class and optimize repeated field processing, initially using the existing Cython path. Evaluate a coarse Rust executor against that baseline, beginning with sequential execution. Restrict parallel execution to sufficiently large, proven-pure workloads after measuring transfer and scheduling costs. Preserve Python/dataclass/ORM semantics and retain legacy execution for unsupported cases. This follows Pydantic's separation of model definition from repeated validation, without assuming its conversion semantics are compatible. Evidence: F001–F007.

## 2. Codebase findings

### Localization

| Path | Symbol / location | Role | Evidence |
|---|---|---|---|
| `datamodel/abstract.py` | `ModelMeta`, `_dc_method_setattr_` | Class caches, dataclass construction, aliases, assignment | F001 |
| `datamodel/base.py` | `BaseModel.__post_init__`, dynamic field/parser methods | Execution entry and mutable model surface | F001 |
| `datamodel/fields.pyx` | `Field` | Cached metadata and Python field object | F001 |
| `datamodel/converters.pyx` | `processing_fields`, `_validation_`, `encoders` | Conversion/validation dispatch | F002 |
| `datamodel/validation.pyx` | `_validate_constraints`, primitive validators | Existing validation contracts | F007 |
| `datamodel/models.py` | `json`, `to_dict`, `old_value` | Serialization and assignment history | F004 |
| `datamodel/parsers/json.pyx` | `JSONContent.default` | Output type conversions | F004 |
| `datamodel/rs_parsers/__init__.py` | Extension loader | Rust availability | F002 |
| `rust/rs_parsers/src/lib.rs` | `to_integer`, `to_decimal` | Existing scalar native implementations | F002 |
| `rust/rs_core/src/lib.rs` | `parse_datamodel`, `get_field_info` | Experimental Rayon pipeline | F007 |
| `rust/rs_validators/src/lib.rs` | Empty file | No implemented validator engine | F007 |
| `examples/rust_benchmark.py` | `Employee`, `timeit`, `main` | Existing user benchmark | F003 |

### Measured evidence

Local 10,000-iteration run: raw construction median 36.5 µs, native construction 29.2 µs, Pydantic model 2.5 µs; reported median ratio 14.45x. JSON median 13.3 µs with a substantial cold-call outlier. Profile attributes most construction time to post-init including opaque compiled work, plus 110,000 Python assignment calls. These are directional observations, not an isolated timing of `_validation_`. F003.

The benchmark compares differing contracts: stdlib skips checks; Pydantic dataclass lacks the model's age bounds; ORM metadata and errors differ. Acceptance must compare the deployed python-datamodel baseline with the optimized version under equivalent behavior. F003–F004.

The Rust integer converter rejects a large integer string accepted by the current Cython converter. Scalar Rust substitution is therefore not backward compatible as a general policy. F002.

Recent relevant work includes metaclass cache/validation fixes on 2026-08-08 and Rust layout changes on 2026-08-07. Existing local experimental files were left intact. Baseline details and commits: F005.

## 3. Proposed scope and experiments

### Phase A — Define compatibility and reliable measurements

Freeze a reference artifact from the deployed version. Add differential characterization using representative company models and payloads, with callbacks stubbed or replayed safely. Compare exact value types, successful states, exception classes/messages/payloads/order, input mutations, field order, defaults/factory calls, aliases, descriptors, inheritance, custom hooks, dataclass operations, primary keys and assignment history. Include invalid input and uncommon numeric/temporal cases. Current targeted tests provide a starting point: 69 passed; they do not certify company compatibility. F001–F005, F007.

Benchmark warm construction, class creation, assignment, serialization, failures, nested models and realistic ORM hydration separately. Use repeated processes and batch timers, record CPU/Python/backend/build flags, and verify binary provenance. Measure allocation and retained cache memory. Profile compiled conversion and validation separately before selecting a Rust boundary. F003, F005, F007.

### Phase B — Cache executable decisions and simplify success paths

**First optimization: gate `_validation_` at the conversion loop using precomputed remaining validation work.** The user reports 220,000 calls for 20,000 Employee builds and estimates about 15 µs in this stage. Source inspection confirms the unconditional dispatch for fields reaching that stage, but the removable portion requires measurement. Nine Employee fields have built-in validators and the other two use generic validation; absence of an explicit user validator or constraints is insufficient to skip checks. F008.

Use a conservative per-field mode/work mask for presence, residual type/structure validation, constraints and custom behavior. The loop may skip the generic dispatcher only after a successful conversion branch establishes the required type/structure guarantee and no checks remain. Use cheap inline guards for proven common cases and the existing dispatcher for unknown cases. Empty/missing values, parser errors and callback results must retain existing checks and exception ordering. A single `needs_validation` flag is acceptable only if it expresses this full contract, with a safe default and valid mutation handling. F001–F002, F008.

Acceptance for this experiment: differential behavior matches the reference, intended fast paths eliminate dispatcher calls, failures retain their payloads/order, and repeated uninstrumented benchmarks show the actual latency/allocation change. Explicitly cover parser/validator and metadata mutation, inheritance, required/null/default behavior, strict/non-strict errors and nested/container values. Report how many calls remain and why; do not claim the full estimated 15 µs as savings before measurement. F008.

Proposed new internal class-owned plan: ordered field operations with precomputed dispatch/constraints and references to existing Python behavior. Candidate changes include avoiding per-instance column-list reconstruction, removing unused metadata reads, delaying error allocation until failure, and reducing Python dispatch for safe primitive cases. These are experiments, not promised gains. F001–F002.

Typed input must still run required checks, constraints and custom behavior. Equality-based writeback, subclass acceptance, callable behavior and observable object identity require parity, even when a simpler rule appears more correct. F001–F002, F004, F007.

Cache validity must include class identity, inheritance, runtime field changes, parser registration and configuration changes. Direct mutable metadata complicates version counters: either preserve live reads where necessary, detect changes without changing caller behavior, or decline the fast path. Do not demand that existing applications call a new cache-rebuild API. Shared mutable Field objects and the existing incomplete class-cache key must not propagate stale plans. F001.

### Phase C — Evaluate Rust sequentially

Preferred experimental boundary: one model-level native call using a cached plan, with supported conversion and validation performed in the existing observable order. Avoid one Python-callable Rust invocation per scalar validator. A sequential PyO3 executor may keep Python values attached to avoid unnecessary copies; use native representations selectively. Preserve the legacy implementation for unsupported paths. F002, F006–F007.

The existing Rayon prototype is exploratory: it rebuilds field information per call, narrows integers to i64, skips unsupported types and returns boolean pairs rather than compatible errors. Its temporal variants also disagree between extraction and checking. It cannot replace production validation unchanged. F007.

### Phase D — Parallelism where measured worthwhile

Proposed flow for eligible bulk work:

```text
Python inputs + cached plan
    -> extract owned native snapshots
    -> detach from interpreter
    -> sequential native loop OR bounded Rayon chunks above measured threshold
    -> attach and construct compatible ordered results/errors
```

Start with sequential Rust for ordinary model construction. Evaluate parallel chunks for independent records or expensive homogeneous collections. Include extraction, copying, scheduling, merge, allocation and error construction in timings. Do not assume Rust threads eliminate Python object access costs; Python callbacks still require interpreter attachment. F007.

Parallel eligibility must exclude side-effectful callbacks, descriptors, factories, overloaded comparisons or dependencies unless their exact observable ordering is preserved. Current per-field conversion/validation interleaving and immediate exceptions prohibit indiscriminately converting every field before validating. Deterministic error sorting alone does not preserve callback side effects. An optional batch API may expose throughput gains later; existing constructor call sites must continue working. F001–F002, F004, F007.

### Phase E — Serialization as a separate experiment

Investigate a reusable serialization plan or compatible traversal to avoid unnecessary intermediate work. Preserve existing JSON conversions, options and hooks; preserve copying behavior of public dictionary conversion. Benchmark cold and warm paths separately. F003–F004.

### Non-goals

- Migrating consumers to Pydantic or adopting its coercion/error semantics.
- Disabling validation to improve a benchmark.
- Requiring model definition changes or new cache invalidation calls.
- Fixing incidental legacy behavior as part of a performance change.
- Promising a 15x gain or introducing mandatory per-model threading before measurement.

## 4. Confidence map

| Claim | Evidence | Confidence |
|---|---|---|
| Existing Cython and metadata caches leave repeated per-instance work | F001–F003 | High |
| Validation dispatch is unconditional for fields reaching the loop's validation stage | F008 | High |
| A precomputed gate plus conversion postconditions can target unnecessary dispatch | F008 | Medium; implementation and savings unmeasured |
| Current local benchmark reproduces roughly the reported gap | F003 | High, limited to this workload |
| Existing Rust scalar functions are not universally interchangeable | F002 | High, runtime counterexample |
| Class-owned execution plans are a promising optimization direction | F001–F003, F006 | Medium, not implemented |
| Coarse sequential Rust deserves comparison before field-level threading | F002, F007 | Medium, design inference |
| Larger pure workloads are better parallel candidates than cheap scalar checks | F007 | Medium; threshold unmeasured |
| Complete company compatibility or any specific speedup is established | F003–F005 | Low; not established |

Overall confidence: medium. Localization is strong; performance gains and full compatibility require experiments and downstream evidence.

## 5. Open questions

1. Which deployed version/commit and company ORM model/test corpus define compatibility? Asked during research; current checkout is provisional.
2. Which workloads and latency/throughput targets have business priority? Constructor and ORM hydration are the initial assumption.
3. Which deployment Python/platform combinations must support acceleration? Coordinate with existing infrastructure work once specified.

## 6. Recommended next step

Review the architecture options and settle the compatibility baseline, then write a specification beginning with the differential harness and a measured sequential execution-plan experiment. SDD command: `$sdd-brainstorm compatible-model-performance`. Follow with a scoped specification; do not jump directly to broad Rust migration tasks.

## 7. Research audit

State: [FEAT-002](../state/FEAT-002/). Findings F001–F008, exact source, research plan and synthesis are persisted there. Source slices, a local benchmark, cProfile and 69 targeted tests were used in the initial research. The validation-gating follow-up adds source inspection and read-only runtime probes; it does not claim new benchmark savings. No production implementation or Rust build was performed. The wiki command was unavailable. Research used the loose budget; deep company integration and native profiling are intentionally deferred, not claimed complete.

## 8. Provenance

SDD proposal workflow and repository templates, 2026-09-08. External primary references are recorded in F006 and F007. Status is discussion; no architecture acceptance is inferred from the user's suggestion.
