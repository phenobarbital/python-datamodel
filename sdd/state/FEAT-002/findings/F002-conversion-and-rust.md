---
id: F002
query_id: Q002
type: read
executed_at: 2026-09-08
depth: 0
---

# Conversion work and Rust compatibility

## Summary

The Cython field loop uses Python Field objects and dynamic attributes, metadata lookups, equality comparisons, conversion dispatch and subsequent validation. A per-field error dictionary is created before validity is known. Rust is available but only selected conversion routes use it; the benchmark's banner does not imply every scalar conversion runs in Rust.

## Citations

- `datamodel/converters.pyx:1922`, `processing_fields`: reads fields and metadata, invokes parser, compares `newval != value`, writes converted state, calls `_validation_`.
- `datamodel/converters.pyx:2315`, `_validation_`: eagerly allocates the error dictionary, calls cached validator and constraint checks.
- `datamodel/converters.pyx:176`, `to_date`: Rust date parser followed by ciso8601 on ValueError.
- `datamodel/converters.pyx:212`, `to_datetime`: common string path tries ciso8601 before Rust.
- `datamodel/converters.pyx:243`, `to_integer`: uses Python integer conversion; preserves arbitrary-size Python integers.
- `datamodel/converters.pyx:296`, `to_decimal`: uses Python Decimal.
- `datamodel/converters.pyx:510`, `encoders`: maps primitive types to Cython converter functions.
- `datamodel/rs_parsers/__init__.py:10`: imports extension symbols; ImportError leaves HAS_RUST false and does not define fallback functions.
- `rust/rs_parsers/src/lib.rs:430`, `to_integer` string branch: parses i64.
- `rust/rs_parsers/src/lib.rs:510`, `to_decimal`: looks up Python Decimal, parses through rust_decimal and reconstructs a Python value.

## Runtime probe

Using the installed extension in the current checkout:

```text
input: '123456789012345678901234567890'
datamodel.converters.to_integer: 123456789012345678901234567890
datamodel.rs_parsers.to_integer: ValueError Invalid integer string: 123456789012345678901234567890
```

Thus substituting Rust scalar functions globally is already demonstrably incompatible. Decimal range/precision, callable semantics, exceptions, bytes and timezone handling also require differential coverage. Rust-absent behavior was inspected, not executed; the claimed graceful fallback has a source-level gap because some callers catch ValueError rather than missing-symbol AttributeError.
