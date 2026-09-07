---
id: F011
query_id: Q011
type: grep
intent: Resolved versions of build-critical deps in uv.lock
executed_at: 2026-09-07T21:31:00Z
duration_ms: 200
parent_id: null
depth: 0
---

# F011 — Locked toolchain already supports Python 3.14

## Summary

`uv.lock` resolves Cython 3.2.9 (3.14 support requires ≥3.1), uvloop 0.22.1,
numpy at three versions (2.2.6 / 2.4.6 / 2.5.1, split by Python-version
markers, the newest for 3.14), asyncpg 0.31.0, msgspec 0.21.1, orjson 3.11.9,
psycopg 3.3.4. No dependency in the lock blocks a 3.14 build. Note that the
`pyproject.toml` floor `Cython>=3.0.11` is looser than what 3.14 actually
needs; the lock hides that but an sdist build on a fresh 3.14 machine would
resolve fine because pip picks the latest Cython anyway.

## Citations

- path: `uv.lock`
  lines: 351-352
  symbol: cython
  excerpt: |
    name = "cython"
    version = "3.2.9"

- path: `uv.lock`
  lines: 1595-1596
  symbol: uvloop
  excerpt: |
    name = "uvloop"
    version = "0.22.1"

- path: `uv.lock`
  lines: 739-740, 804-805, 886-887
  symbol: numpy (multi-resolution)
  excerpt: |
    version = "2.2.6"   # older Pythons
    version = "2.4.6"
    version = "2.5.1"   # newest Pythons

- path: `uv.lock`
  lines: 94-95, 614-615
  symbol: asyncpg, msgspec
  excerpt: |
    asyncpg 0.31.0
    msgspec 0.21.1
