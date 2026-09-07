---
id: F008
query_id: Q008
type: read
executed_at: 2026-09-08
depth: 1
---

# Gate validation on remaining work, not absent user options

## Summary

The user reports 220,000 `_validation_` calls for 20,000 builds and attributes approximately 15 µs to this work. The current source confirms unconditional dispatch for each field reaching the loop's validation stage; descriptor and early-exit paths are exceptions. The reported call count is consistent with 11 fields per successful Employee construction. This investigation did not reproduce the user's instrumented profile or establish that all 15 µs can be removed.

## Citations

- `datamodel/converters.pyx:2296`, `processing_fields`: unconditional `_validation_` call after conversion.
- `datamodel/converters.pyx:2315`, `_validation_`: empty/special-value field checks; set member checks; cached validator and constraints; generic `_validation` fallback. Allocates an error dictionary on entry, even for success.
- `datamodel/abstract.py:257`, `_initialize_fields`: assigns built-in validators from the validators table irrespective of user-supplied validation options.
- `datamodel/validation.pyx:473`, `_validation`: custom metadata validator, primitive constraints, enums, callable/awaitable types, Literal and generic type checks.
- `datamodel/fields.pyx:128`, `Field.__init__`: mutable field attributes; `_meta` dictionary supplies metadata through dataclasses.Field initialization.
- `examples/rust_benchmark.py:35`, `Employee`: 11 annotated fields.

## Read-only runtime probes

Loading Employee and inspecting `__columns__` shows nine primitive fields with non-null cached validators. Only `skills` and `manager` have `validator is None`; both have category `typing`, which falls back to generic validation. Thus `f.validator is None` cannot serve as a skip flag.

Creating a temporary one-field integer model in a separate Python process, then assigning its field parser to `lambda value: "invalid"`, produces:

```text
ValidationError {'value': {'field': 'value', 'value': 'invalid', 'error': "Field value expected an integer, got 'invalid' of type str"}}
```

The field has no explicit constraints or user validator. Its built-in validator remains necessary unless the fast path proves the parser result is valid. No repository code was changed by the probe.

## Proposed implementation requirements

1. Precompute a conservative validation mode or work mask: presence checks, residual type/structure checks, constraints, and custom/generic behavior. Default unknown/dynamic cases to the legacy path.
2. At the conversion loop, bypass the generic dispatcher only when the specific successful conversion branch proves its postcondition and no required checks remain. A class-time flag may select candidate fields; it cannot alone prove properties of each input or arbitrary callback result.
3. Retain field checks for empty, missing and special values in the same order. Preserve error behavior after parse failure; do not add a blanket `continue` after conversion exceptions.
4. Use narrow inline type guards or specialized validation where a field needs a cheap residual check, avoiding the full dispatcher without disabling its contract.
5. Avoid empty error allocations and constraint scans when demonstrably unnecessary. Preserve error dictionaries and exact messages on failures.
6. Account for public mutable metadata, parser/validator replacement, field type/category changes and inheritance. A one-time false flag must never silently suppress subsequently added behavior. Version tracking requires a design covering all exposed mutation routes; otherwise retain live checks or conservatively avoid caching affected decisions.
7. Measure dispatcher calls, allocations and uninstrumented latency before/after. Validate raw/native success, invalid parser results, required/null/default cases, constraints, generics, mutation and strict/non-strict errors. Report measured savings rather than treating total cumulative validation time as removable overhead.

This refactor precedes Rust/parallelism so native experiments operate on the necessary workload. The exact number of safely eliminable Employee calls is not yet established.
