---
id: F003
query_id: Q003
type: read
executed_at: 2026-09-08
depth: 0
---

# Measured baseline

## Citations

- `examples/rust_benchmark.py:35`, `Employee`: 11 fields with required/primary-key metadata, constraints and defaults.
- `examples/rust_benchmark.py:73`, `PydanticEmployee`: similar fields, including age bounds, with different library semantics.
- `examples/rust_benchmark.py:92`, `PydanticDCEmployee`: age bounds absent.
- `examples/rust_benchmark.py:146`, `timeit`: clock surrounds each individual call; returns distribution, no repeated-process statistics.
- `examples/rust_benchmark.py:190`, `main`: construction sanity check, native/raw comparisons, serialization and independent Rust microbenchmarks.

## Results

Command: `.venv/bin/python examples/rust_benchmark.py 10000`.
Python 3.13.11; python-datamodel package metadata 0.10.21; Pydantic 2.13.5; Rust enabled.

| Operation | Mean µs | Median µs |
|---|---:|---:|
| datamodel raw | 37.9 | 36.5 |
| datamodel native | 30.7 | 29.2 |
| stdlib dataclass native | 0.5 | 0.5 |
| Pydantic model raw | 2.8 | 2.5 |
| Pydantic dataclass raw | 4.5 | 4.2 |
| datamodel JSON | 22.1 | 13.3 |

Reported median ratios: 14.45x against Pydantic model, 8.74x against Pydantic dataclass. JSON maximum 46.899 ms with first-call warm-up marker. Rust Decimal direct mean ~0.8 µs versus Python Decimal ~0.2 µs; this microbenchmark does not establish an end-to-end backend comparison.

Separate cProfile run, 10,000 raw constructions: 0.661 s total; `BaseModel.__post_init__` cumulative 0.491 s; `_dc_method_setattr_` 110,000 calls, cumulative 0.113 s; metaclass `__call__` self 0.022 s. Compiled converter internals are not separately exposed in this profile; time attributed to post-init is not evidence that its Python body alone is expensive. Profiling adds overhead and these proportions are not exact uninstrumented fractions.

## Limitations

One local run, one small model, no isolated CPU conditions. Existing compiled extensions were used without rebuilding or proving source/binary identity. Benchmark is an untracked user file and was left intact. Native input still invokes conversion functions; raw-minus-native is not a complete decomposition into parsing versus validation. Treat Pydantic as context and use old/new python-datamodel with identical contracts for acceptance.
