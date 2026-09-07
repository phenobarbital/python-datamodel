---
id: F015
query_id: Q015
type: grep
intent: User-facing docs mentioning uvloop, Windows, install instructions
executed_at: 2026-09-07T21:31:00Z
duration_ms: 150
parent_id: null
depth: 0
---

# F015 — Docs never mention uvloop or Windows; INSTALL.md is stale

## Summary

`README.md` documents only `pip install python-datamodel`. `INSTALL.md`
still tells contributors to install `setuptools-rust`, which the August
migration replaced with maturin. `CHANGELOG.md` has no relevant entries and
`docs/` has no uvloop mention. Any new `[uvloop]` extra or Windows support
will need a README/INSTALL/CHANGELOG update.

## Citations

- path: `README.md`
  lines: 22
  excerpt: |
    $ pip install python-datamodel

- path: `INSTALL.md`
  lines: 17
  excerpt: |
    pip install cython maturin sdist setuptools wheel setuptools-rust

- path: `datamodel/version.py`
  lines: 5-9
  symbol: `__description__`, `__version__`
  excerpt: |
    'simple library based on python +3.8 to use Dataclass-syntax'
    __version__ = '0.10.21'
