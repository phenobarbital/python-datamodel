---
id: F013
query_id: Q013
type: grep
intent: Existing platform-conditional code and C++ stdlib usage in .pyx
executed_at: 2026-09-07T21:31:00Z
duration_ms: 200
parent_id: null
depth: 0
---

# F013 — No platform conditionals anywhere; one libcpp cimport

## Summary

No `sys.platform`, `platform.system()`, `os.name` or `win32` check exists in
`datamodel/` or `setup.py`. The only C++-specific Cython construct is
`from libcpp cimport bool` in `functions.pyx`; `fields.pyx` and
`parsers/json.pyx` are compiled as C++ only because `language="c++"` is set
in setup.py. This means the Windows blocker is confined to build flags
(F003), not to source code.

## Citations

- path: `datamodel/functions.pyx`
  lines: 6
  symbol: cimport
  excerpt: |
    from libcpp cimport bool as bool_t

- path: `setup.py`
  lines: 12-13
  symbol: (cross-ref F003)
  excerpt: |
    COMPILE_ARGS = ["-O3"]
    EXTRA_LINK_ARGS = ["-lstdc++"]
