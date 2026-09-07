---
id: F012
query_id: Q012
type: grep
intent: Test suite event loop usage and pytest config
executed_at: 2026-09-07T21:31:00Z
duration_ms: 200
parent_id: null
depth: 0
---

# F012 — Tests use plain asyncio loops; no conftest; duplicated pytest config

## Summary

Only `tests/test_valid_callables.py` touches the event loop, via
`asyncio.new_event_loop()` + `run_until_complete` (line 38-40). No test
references uvloop, so removing the dependency cannot break tests. There is
no `tests/conftest.py`. Two pytest configs coexist: `pytest.ini`
(`filterwarnings = ignore::DeprecationWarning`) and
`[tool.pytest.ini_options]` in pyproject (`filterwarnings = ["error"]`);
pytest gives `pytest.ini` precedence, so the pyproject block is inert. A
uvloop test (skip-if-missing) would be the natural verification for the
new optional import.

## Citations

- path: `tests/test_valid_callables.py`
  lines: 3, 38-40
  symbol: event loop usage
  excerpt: |
    import asyncio
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(instance.async_result)
    loop.close()

- path: `pytest.ini`
  lines: 1-4
  symbol: filterwarnings
  excerpt: |
    [pytest]
    filterwarnings =
        ignore::DeprecationWarning

- path: `pyproject.toml`
  lines: 111-122
  symbol: `[tool.pytest.ini_options]`
  excerpt: |
    filterwarnings = [
        "error",
    ]
