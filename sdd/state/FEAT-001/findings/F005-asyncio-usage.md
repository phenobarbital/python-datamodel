---
id: F005
query_id: Q005
type: grep
intent: Find where an asyncio event loop is created/configured (candidate site for uvloop auto-use)
executed_at: 2026-09-07T21:30:00Z
duration_ms: 200
parent_id: null
depth: 0
---

# F005 — The library never creates or configures an event loop

## Summary

Within `datamodel/`, `asyncio` is imported in a single file and used once,
only for type introspection (`asyncio.iscoroutinefunction`). There is no
`set_event_loop_policy`, `new_event_loop`, `get_event_loop` or
`asyncio.run` anywhere in the package. Consequently there is no natural
place where "automatic uvloop usage" would take effect today; any such
behaviour must be newly designed (helper module or opt-in hook).

## Citations

- path: `datamodel/validation.pyx`
  lines: 7
  symbol: module imports
  excerpt: |
    import asyncio

- path: `datamodel/validation.pyx`
  lines: 524
  symbol: callable validation
  excerpt: |
    if asyncio.iscoroutinefunction(value):
