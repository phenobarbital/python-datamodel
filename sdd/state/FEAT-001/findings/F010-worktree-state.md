---
id: F010
query_id: Q010
type: git_log
intent: State of the migrate-uv-python314 worktree/branch relative to main
executed_at: 2026-09-07T21:31:00Z
duration_ms: 300
parent_id: null
depth: 0
---

# F010 — Stale worktree `migrate-uv-python314` is fully merged and 8 commits behind main

## Summary

A second worktree exists at `.claude/worktrees/migrate-uv-python314` on
branch `worktree-migrate-uv-python314` (HEAD `08b9169`, 2026-08-07). It has
0 commits ahead of `main` and is 8 commits behind. Its content is fully
contained in `main`; it is a leftover from the August migration and can be
removed before new infra work begins. It also means grep hits under
`.claude/worktrees/` are duplicates, not new evidence.

## Citations

- cmd: `git worktree list`
  excerpt: |
    /home/jesuslara/proyectos/python-datamodel                                         88b4439 [main]
    /home/jesuslara/proyectos/python-datamodel/.claude/worktrees/migrate-uv-python314  08b9169 [worktree-migrate-uv-python314]

- cmd: `git rev-list --count worktree-migrate-uv-python314..main` → 8
- cmd: `git rev-list --count main..worktree-migrate-uv-python314` → 0
- commit: `08b9169`  date: 2026-08-07
  message: "fix: make release delegates to build target to include stage-rust"
