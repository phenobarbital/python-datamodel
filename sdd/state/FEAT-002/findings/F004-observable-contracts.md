---
id: F004
query_id: Q004
type: read
executed_at: 2026-09-08
depth: 0
---

# Serialization and compatibility surface

## Citations

- `datamodel/models.py:134`, `reset_values`, `old_value`: exposes assignment history.
- `datamodel/models.py:209`, `to_dict`: dataclasses.asdict traversal plus options; mutates the supplied nonempty exclusion set by adding `_pgoutput`.
- `datamodel/models.py:304`, `json`, `to_json`: constructs an encoder and calls it with dataclasses.asdict output.
- `datamodel/parsers/json.pyx:96`, `JSONContent.default`: Decimal emits float; custom handling extends orjson.
- `tests/test_descriptors.py:43`, `InventoryItem` and descriptor tests: real descriptors participate in initialization and subsequent assignment.
- `tests/test_field.py:8`, Field tests: metadata, defaults, primary keys and default factories.
- `tests/test_validations.py:210`, `test_actor_with_accounts_validation`: selected checks distinguish ValueError and ValidationError.
- `tests/test_inherit.py`, `tests/test_aliases.py`, `tests/test_unions.py`, `tests/test_json.py`: existing compatibility test targets.

## Verification

`.venv/bin/python -m pytest tests/test_field.py tests/test_inherit.py tests/test_descriptors.py tests/test_aliases.py tests/test_validations.py tests/test_unions.py tests/test_json.py -q`

Result: **69 passed in 0.23s**. This is targeted coverage, not the complete suite or company integration coverage.

## Implications

Optimizing JSON traversal requires preserving conversion choices, hooks, options and failure behavior. Do not replace the copying behavior of public to_dict with a shallow dictionary. Differential execution must capture values AND types, errors, input mutation, identity where observable, callback counts/order and dataclass/ORM behavior. Side-effectful factories and callbacks must not execute twice against live systems during comparisons.
