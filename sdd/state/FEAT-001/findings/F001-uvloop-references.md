---
id: F001
query_id: Q001
type: grep
intent: Locate every uvloop reference (code, build config, docs)
executed_at: 2026-09-07T21:30:00Z
duration_ms: 400
parent_id: null
depth: 0
---

# F001 — uvloop is declared but never imported

## Summary

`uvloop` appears in exactly one authoritative location: the `dependencies`
list in `pyproject.toml`. It is **never imported** in any `.py`, `.pyx` or
`.pxd` file under `datamodel/`, nor in `tests/`, nor in docs. The only other
hits are a mirror of that same line inside the old migration plan and inside
the stale `.claude/worktrees/migrate-uv-python314` copy of the repo.

## Citations

- path: `pyproject.toml`
  lines: 44
  symbol: `[project].dependencies`
  excerpt: |
    "uvloop>=0.21.0; sys_platform != 'win32'",

- path: `docs/superpowers/plans/2026-08-07-migrate-uv-python314.md`
  lines: 350
  symbol: (plan text, mirrors pyproject)
  excerpt: |
    "uvloop>=0.21.0; sys_platform != 'win32'",

## Notes

Absence is the key evidence: there is no existing "lazy import" to make
optional. The dependency is dead weight for end users today, and the
"automatic usage" requested in the source has no current call site (see F005).
