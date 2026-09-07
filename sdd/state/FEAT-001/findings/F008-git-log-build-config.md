---
id: F008
query_id: Q008
type: git_log
intent: Recent history on build/CI config
executed_at: 2026-09-07T21:31:00Z
duration_ms: 500
parent_id: null
depth: 0
---

# F008 — Build config was overhauled on 2026-08-07; uvloop marker added 2026-06-19

## Summary

Five commits in the last 180 days touch the build/CI surface. On 2026-06-19
the uvloop dependency was given the `sys_platform != 'win32'` marker (a
first, partial step toward Windows). On 2026-08-07 the repo migrated to
uv + maturin, rewrote release.yml (added the 3.14 matrix entry), moved Rust
into `rust/`, and fixed the Makefile. On 2026-08-28 a Dependabot sweep
bumped Rust deps (PyO3 to 0.29). No commit has touched Windows CI or
uvloop import behaviour.

## Citations

- commit: `a7fe091`  date: 2026-06-19  author: Jesus Lara
  message: "fix: make uvloop a non-Windows-only dependency"
  files: `pyproject.toml`

- commit: `f6a863d`  date: 2026-08-07  author: Jesus
  message: "build: update config for uv + maturin"
  files: `pyproject.toml`, `setup.py`

- commit: `3d2ee73`  date: 2026-08-07  author: Jesus
  message: "ci: update release workflow for maturin + uv + Python 3.14"
  files: `.github/workflows/release.yml`

- commit: `f90ea81`  date: 2026-08-07  author: Jesus
  message: "fix: Makefile develop ordering and missing Cython/setuptools"
  files: `Makefile`, `pyproject.toml`

- commit: `d9b808c` / `b0de2f0` / `be9c058`  date: 2026-08-07  author: Jesus
  message: "refactor: move Rust code to rust/ directory with Cargo workspace" and follow-ups
  files: `rust/**`, `datamodel/rs_parsers/__init__.py`

- commit: `9ab4e63`  date: 2026-08-28  author: Jesus
  message: "security: fix all Dependabot vulnerabilities"
  files: `rust/Cargo.toml`, `rust/Cargo.lock`, `rust/rs_parsers/src/lib.rs`, `rust/rs_core/src/lib.rs`, `docs/requirements-dev.txt`
