---
id: F007
query_id: Q007
type: read
executed_at: 2026-09-08
depth: 1
---

# Parallel validation feasibility

## Citations

- `rust/rs_core/src/lib.rs:180`, `get_field_info`: walks Python field objects on each call, extracts owned strings/i64/f64, skips unsupported types.
- `rust/rs_core/src/lib.rs:245`, `parse_datamodel`: explicitly documented as a mock-up; materializes a native vector and calls `into_par_iter`, returning name/bool pairs. Does not detach the calling thread from Python.
- `rust/rs_core/src/lib.rs:113`, `FieldType::parse`: scalar branches return true; temporal branches expect FieldValue::Str, while extraction creates temporal variants.
- `rust/rs_validators/src/lib.rs`: empty file. The prototype is in rs_core, correcting the earlier progress-message path.
- `datamodel/validation.pyx:28`, `valid_int`: isinstance(value, int), with Python subclass semantics.
- `datamodel/validation.pyx:62`, `valid_datetime`: accepts datetime and date.
- `datamodel/validation.pyx:305`, `_validate_constraints`: Python metadata, numeric comparisons, len and re.match; preserves detailed error messages.
- `datamodel/converters.pyx:2296`, `processing_fields`: validation occurs after each field's conversion; some failures raise immediately.
- `rust/rs_core/Cargo.toml`, `rust/rs_validators/Cargo.toml`: PyO3 0.29, Rayon dependency.

No rs_core/rs_validators references were found in runtime datamodel sources, setup.py or pyproject.toml (generated files excluded); Cargo workspace membership alone does not activate a runtime backend.

## Official references

- [PyO3 parallelism](https://pyo3.rs/main/parallelism): detach for native parallel work; accessing Python requires each worker to attach. Holding the GIL while waiting for workers that need it can deadlock. Pure Rust workers can compute concurrently even if the caller holds the GIL, but other Python threads remain blocked.
- [Rayon ParallelIterator](https://docs.rs/rayon/latest/rayon/iter/trait.ParallelIterator.html): parallel subdivision has overhead; sequential inner work may be preferable for small computations.

## Assessment

Migrating the single-field `_validation_` through a Python-callable Rust wrapper leaves dispatch, conversion and assignment overhead and adds a boundary per field. A coarse call using a cached model plan is a stronger candidate. Sequential Rust may efficiently inspect Python values while attached; no requirement to copy every value into a Rust representation for that variant.

Parallel workers should receive owned, native, immutable snapshots of proven-pure workloads. Snapshot extraction and result reconstruction remain serial costs. Preserve source-order error behavior, callback counts, hooks and mutations. Reordering conversion then validation into two whole-model phases can itself change behavior. Parallelism must therefore have explicit eligibility rules, serial barriers/fallback, and measured thresholds. Prefer large batches or expensive homogeneous nested collections over eleven cheap scalar checks; batch support is a future optional capability, not a replacement constructor.

The existing profile cannot isolate `_validation_`, so no fraction or speedup is attributed to it. Amdahl's law is illustrative only: if validation were 30% of construction, making it infinitely fast would cap end-to-end speedup at 1/(1-0.30), about 1.43x.
