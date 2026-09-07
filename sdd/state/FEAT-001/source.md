---
kind: inline
jira_key: null
fetched_at: 2026-09-07T00:00:00Z
summary_oneline: Make uvloop optional (lazy-import, auto-use), add Python 3.14 build, add Windows wheels in release.yml
---

# Source (inline)

Invocation: `/sdd-proposal new-infra-spec -- ...`

> python-datamodel requires uvloop as optional lazy-import, automatic usage if
> present but removing uvloop as hard dependency, add python 3.14 as new build
> and Windows compatibility on release.yml

## Extracted signals

- Name hint: `new-infra-spec`
- Three asks:
  1. uvloop: remove from hard dependencies; import lazily; use automatically when installed.
  2. Python 3.14: add as a new build target.
  3. Windows: add compatibility (wheels) to `release.yml`.
