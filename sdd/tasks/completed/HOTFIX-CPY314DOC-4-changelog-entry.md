# HOTFIX-CPY314DOC-4: Record corrective changelog entry

**Feature**: cpython314-field-doc-compatibility (hotfix; no Jira key)
**Spec**: `sdd/specs/cpython314-field-doc-compatibility.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: S (< 2h)
**Depends-on**: HOTFIX-CPY314DOC-2, HOTFIX-CPY314DOC-3
**Assigned-to**: unassigned

---

## Context

> After the fix (HOTFIX-CPY314DOC-1), tests (HOTFIX-CPY314DOC-2), and CI smoke
> (HOTFIX-CPY314DOC-3) are in place, this task records the correction in the
> changelog with provenance and scope limits. Covers spec §3 M4.

---

## Scope

- Add a `### Fixed` subsection under the `[0.11.0]` heading in `CHANGELOG.md`.
- Entry must describe: pre-existing `Field.__init__` incompatibility with
  CPython 3.14's required `doc` argument, the version-conditional forwarding fix,
  and that this is a targeted compatibility repair — not a full 3.14 certification.
- Note that annotation discovery on 3.14 remains a separate tracked blocker.

**NOT in scope**: bumping the version number (spec §1 non-goals), the fix itself,
or test changes.

---

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `CHANGELOG.md` | MODIFY | Add Fixed subsection under [0.11.0] |

---

## Codebase Contract (Anti-Hallucination)

### Verified Imports
N/A — markdown-only task.

### Existing Signatures to Use
```markdown
# CHANGELOG.md:8
## [0.11.0]

### Added
* Optional `python-datamodel[uvloop]` extra ...
...

### Changed
...

### Notes
...
```

### Does NOT Exist
- ~~A `### Fixed` subsection~~ — does not exist yet under `[0.11.0]`; this task adds it
- ~~A version bump in this hotfix~~ — spec explicitly forbids unrequested version changes

---

## Implementation Blueprint

### Steps (in order)
1. Insert a `### Fixed` subsection after the `### Notes` block under `[0.11.0]` — *why*: Keep a Changelog convention groups fixes under `### Fixed`.
2. Write the entry describing the doc-forwarding fix and its scope limits — *why*: spec §5 AC-7 requires provenance and certification limits.

### `CHANGELOG.md` (MODIFY)
```markdown
# occurrences: 1 (verified: grep -c '### Notes' CHANGELOG.md)
# AFTER — insert below `### Notes` block (verified: CHANGELOG.md:32-34)

### Fixed
* `datamodel.fields.Field.__init__()` now passes the caller's `doc` value to
  the `dataclasses.Field` superclass on CPython 3.14+, which added `doc` as a
  required initializer argument. On 3.10–3.13 the superclass call is unchanged.
  This was a pre-existing incompatibility (present since the `doc` parameter was
  introduced upstream), not a regression from recent work. Annotation discovery
  on CPython 3.14 remains a separate tracked compatibility blocker.
```
**Why**: uses Keep a Changelog `### Fixed` convention. The wording matches spec
AC-7's requirements: identifies pre-existing incompatibility, references
upstream cause, and explicitly notes what is NOT certified by this fix.

### FILL IN checklist
- [ ] Verify the `### Notes` block ends before the `## [0.0.15]` heading; insert between them

---

## Acceptance Criteria

- [ ] `### Fixed` subsection exists under `## [0.11.0]`
- [ ] Entry describes the specific `doc` forwarding fix
- [ ] Entry identifies pre-existing incompatibility (not a regression)
- [ ] Entry notes annotation discovery remains a separate blocker
- [ ] No version number change introduced
- [ ] No other changelog sections modified

---

## Test Specification

> No automated tests — manual review of CHANGELOG.md content.

---

## Agent Instructions

When you pick up this task:

1. **Read the spec** at the path listed above for full context
2. **Check dependencies** — verify HOTFIX-CPY314DOC-2 and HOTFIX-CPY314DOC-3 are in `tasks/completed/`
3. **Verify the Codebase Contract** — confirm CHANGELOG.md structure
4. **Update status** in `sdd/tasks/index/cpython314-field-doc-compatibility.json` → `"in-progress"`
5. **Implement** — add the Fixed subsection
6. **Verify** — review the changelog reads correctly
7. **Move this file** to `sdd/tasks/completed/HOTFIX-CPY314DOC-4-changelog-entry.md`
8. **Update index** → `"done"`
9. **Fill in the Completion Note** below

---

## Completion Note

**Completed by**: Claude Opus 4.6 (sdd-start session)
**Date**: 2026-09-16
**Notes**: Added `### Fixed` subsection to CHANGELOG.md under `## [0.11.0]`, between the existing `### Notes` block and `## [0.0.15]`. Entry describes the doc-forwarding fix, identifies it as a pre-existing incompatibility, and notes annotation discovery remains a separate blocker.

**Deviations from spec**: none
