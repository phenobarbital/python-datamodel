---
description: Bump the package version, commit, tag and (on confirmation) create the GitHub Release that publishes to PyPI
argument-hint: "<patch|minor|major> [--dry-run] [--no-release]"
allowed-tools: Bash, Read, Edit
---

# /release — Package Release

Drive a release of `python-datamodel`: bump the version, commit, tag,
push, and — only after you say yes — create the GitHub Release that triggers
the PyPI publish.

## Usage

```
/release patch                  # e.g. 3.8.1 -> 3.8.2
/release minor
/release major
/release patch --dry-run        # preview every write, touch nothing
/release patch --no-release     # bump + commit + tag + push, stop there
```

## How versioning works here

- The version is defined in `datamodel/version.py` (or `pyproject.toml`
  `[project] version = ...`). Find the canonical source and update it.
- The git tag is the version number (`3.8.2`, `3.9.0`, …), lightweight.
- `.github/workflows/release.yml` fires on `release: [created]`, builds
  the wheel and publishes to PyPI.

---

## Step 1 — Parse and validate

1. `$ARGUMENTS` must contain exactly one of `patch`, `minor`, `major`.
   If missing or ambiguous, **ask** — do not guess.
2. Show the current version:
   ```bash
   grep -r "version" datamodel/version.py pyproject.toml 2>/dev/null | head -5
   ```
3. Confirm the branch. Releases are cut from `main` or `dev` —
   **never from a feature branch or a worktree**.
   ```bash
   git rev-parse --abbrev-ref HEAD && git rev-parse --show-toplevel
   ```
   If HEAD is a feature branch or the toplevel is under
   `.claude/worktrees/`, **abort** and say why.
4. The working tree must be clean:
   ```bash
   git status --porcelain
   ```
   If dirty, abort: "Commit or stash first — a release commit must contain
   only version files."

## Step 2 — Preview

Compute the new version and show it to the user. If `--dry-run` was in
`$ARGUMENTS`, **stop here** and report.

## Step 3 — CHANGELOG

If `CHANGELOG.md` exists:
1. Read the current `[Unreleased]` block.
2. Read what landed since the last tag:
   ```bash
   git log --oneline $(git tag --sort=-creatordate | head -1)..HEAD
   ```
3. **Draft** the release section, retitling `[Unreleased]` to
   `## [X.Y.Z] — YYYY-MM-DD`, and open a fresh empty `## [Unreleased]` above.
4. **Show the draft and get approval** before writing.

## Step 4 — Bump, commit, tag, push

1. Edit the version file(s) with the new version.
2. Stage and commit: `"release: vX.Y.Z"`
3. Tag: `git tag X.Y.Z`
4. Push: `git push && git push --tags`

If `--no-release` was passed, **stop here**.

## Step 5 — GitHub Release (irreversible — confirm)

Creating the release triggers the publish workflow. **PyPI never allows
re-uploading a version.** So:

1. State what is about to happen.
2. **Ask for explicit confirmation.**
3. Then:
   ```bash
   gh release create X.Y.Z --generate-notes
   ```

## Step 6 — Report

```
Release vX.Y.Z

  Version bumped:   X.Y.Z
  Commit:           <sha>
  Tag:              X.Y.Z  (pushed)
  GH Release:       created / skipped
```

## Error handling

| Situation | Action |
|---|---|
| No bump type in `$ARGUMENTS` | Ask. Never default to `patch`. |
| Dirty working tree | Abort — release commits carry version files only. |
| On a feature branch or in a worktree | Abort. Releases come from `main`/`dev`. |
| Tag already exists | Abort — investigate. |
| `gh release view` says it exists | Abort — already published. |
