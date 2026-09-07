---
id: F006
query_id: Q006
type: read
intent: Check how the Rust extension is loaded and whether it degrades gracefully
executed_at: 2026-09-07T21:30:00Z
duration_ms: 150
parent_id: null
depth: 0
---

# F006 — rs_parsers already implements the optional-import pattern to reuse

## Summary

`datamodel/rs_parsers/__init__.py` wraps the native import in
`try/except ImportError` and exposes a `HAS_RUST` flag. This is precisely the
"optional lazy import with graceful fallback" pattern the source asks for
with uvloop, and it doubles as the Windows fallback if no `.pyd` is shipped.
Only `__init__.py` is git-tracked; the local `.so` files (cp312, cp313) are
build artifacts ignored via `*.so` in `.gitignore`.

## Citations

- path: `datamodel/rs_parsers/__init__.py`
  lines: 8-30
  symbol: `HAS_RUST`
  excerpt: |
    HAS_RUST = False

    try:
        from ._rs_parsers import (  # type: ignore[import-not-found]
            to_string,
            ...
        )
        HAS_RUST = True
    except ImportError:
        pass

- path: `.gitignore`
  lines: 7,75
  symbol: ignore rules
  excerpt: |
    *.so
    target/
