---
id: F014
query_id: Q014
type: tree
intent: CI surface: other workflows, tox config, Makefile targets
executed_at: 2026-09-07T21:31:00Z
duration_ms: 150
parent_id: null
depth: 0
---

# F014 — release.yml is the only workflow; no test CI; tox.ini is obsolete

## Summary

`.github/` holds exactly one workflow (`release.yml`, triggered on
`release: created`) plus `dependabot.yml` (pip ecosystem, daily). There is
no pull-request/test workflow, so a Windows or 3.14 regression is only
discovered at release time. `tox.ini` targets py35-py311 with `src/` paths
that do not exist in this repo and is not referenced by the Makefile or
CI; it is dead configuration.

## Citations

- path: `.github/`
  excerpt: |
    .github/
    ├── dependabot.yml
    └── workflows/
        └── release.yml

- path: `.github/dependabot.yml`
  lines: 1-6
  excerpt: |
    updates:
      - package-ecosystem: "pip"
        directory: "/"
        schedule:
          interval: "daily"

- path: `tox.ini`
  lines: 1-2, 21-24
  symbol: envlist / lint
  excerpt: |
    envlist = lint,py{35,36,37,38,39,310,311},pypy3,manifest,coverage-report
    flake8 src tests
    mypy --python-version=3.11 src tests

- path: `Makefile`
  lines: 72-76
  symbol: `build`, `release`
  excerpt: |
    build: clean
    	$(MAKE) stage-rust
    	uv build
    release: lint test build
