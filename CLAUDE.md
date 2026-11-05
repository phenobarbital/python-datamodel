# python-datamodel Development Guide for Claude

## Project

Python DataModel — a high-performance dataclass library with Cython extensions,
type coercion, validation, and schema generation.

**Main Branch**: `main`

## Development Environment

### Package Management & Virtual Environment

**CRITICAL RULES:**
1. **Package Manager**: Use **`uv`** exclusively for package management
   ```bash
   uv pip install <package>
   uv pip list
   uv add <package>
   ```

2. **Virtual Environment**: ALWAYS activate before Python operations
   ```bash
   source .venv/bin/activate
   ```
   **NEVER** run `uv`, `python`, or `pip` commands without activating first.

3. **Dependencies**: Manage all dependencies via `pyproject.toml`

### Build

Cython extensions must be compiled before testing:
```bash
source .venv/bin/activate
python setup.py build_ext --inplace
```

### Testing & Linting

```bash
source .venv/bin/activate
pytest                    # run full test suite
pytest tests/test_foo.py  # run a specific test file
ruff check datamodel/     # lint
```

## Non-Negotiable Rules

### Environment
- Package manager: `uv` exclusively (`uv add`, `uv pip install`)
- ALWAYS activate venv before any command: `source .venv/bin/activate`
- NEVER run python/uv/pip without activating first

### Code Standards
- Type hints on all functions and classes
- snake_case for functions/variables, PascalCase for classes
- Logger instead of print statements
- Run `pytest` after ANY logic change — no exceptions

### Security
- Never commit API keys — use environment variables
- Never run `rm -rf` or system-level deletions
- No form submissions or logins without user approval

### Adversarial Second Opinion

Use an external CLI agent as an independent perspective for adversarial
code reviews, design opinions, brainstorming, research cross-checks, and
implementation sanity checks. The reviewer is **`codex` (OpenAI)**.

Rules:
- Never feed the reviewer your reasoning, justification, or preferred
  conclusion. Give it only the diff, the requirement, and the question.
  Supplying your conclusions produces ratification, not review.
- Treat reviewer output as advisory. For every substantive finding,
  explicitly mark it as `CONFIRM` (adopt), `REJECT` (with reason), or
  `ESCALATE`.
- Never silently concede to the reviewer and never silently drop a finding.
- Run each reviewer call as a full background agent session. Typical runtime
  is 30 seconds to 2 minutes; do not call it per edit or from hooks.
- For parallel perspective, use one Claude subagent and one background
  reviewer session with the same neutral brief, then synthesize agreements
  and disagreements.
- **Verify the reviewer's evidence before believing it.** If it claims a
  test run, a file, or a symbol, spot-check that the thing exists. Treat an
  unverifiable claim as no finding at all, and say the review was
  unusable rather than reporting it as a pass.

**Detection:**
```bash
if command -v codex &>/dev/null; then REVIEWER="codex"
else echo "No external reviewer CLI found"; fi
```

#### codex commands
```bash
# Reviews
codex exec review --uncommitted
codex exec review --base main
codex exec review --commit <sha>

# Opinions, brainstorming, and cross-checks
codex exec --sandbox read-only -o <scratch-file> "<neutral brief>"

# Follow-up in the same Codex session
codex exec resume --last "<question>"
```

#### Design research at spec time (FEAT-545)

The same codex seat gives an **independent design opinion** in `/sdd-spec`
§3b, over the *accepted* brainstorm/proposal only — never over the spec
draft. The pass is **optional and never blocking**: no `codex`, failed
probe, timeout or invalid output ⇒ spec §9 reads `Status: skipped (<reason>)`
and the command continues. Every suggestion is triaged `CONFIRM` / `REJECT` /
`ESCALATE` in spec **§9 Design Research Cross-Check**; the transcript is
committed under `sdd/state/<FEAT-ID>/design_research/`.

# SDD Workflow & Worktree Policy

---

## Git Configuration

Long-lived branches:

- **`main`** — tagged releases only. Hotfixes land here via PR;
  no feature work ever bases on `main`.
- **`dev`** — integration branch for all feature work. Default base
  for `type: feature` flows.

**Flow types** (FEAT-145):
- `feature` — base is `dev` (default). NEVER `main`.
- `hotfix` — base is `main` (mandatory).

**`/sdd-done` NEVER pushes to or opens a PR against `main`** —
hotfix PRs are user-initiated.

## Worktrees

Everything about worktrees — location (`.claude/worktrees/`), naming,
creation, working inside one, finishing and cleanup — lives in the rules
under `.claude/rules/` (worktree-start-feature.md, worktree-pr-and-clean.md,
worktree-status.md, using-git-worktrees.md).

## SDD Auto-Commit Rule

> **CRITICAL**: Every SDD command that creates or modifies files MUST commit
> them on the appropriate branch before finishing. Uncommitted files are
> invisible to worktrees and other sessions.

| Command | What it commits | Where (FEAT-145) |
|---------|-----------------|------------------|
| `/sdd-brainstorm` | `sdd/proposals/<n>.brainstorm.md` (with frontmatter) | `base_branch` |
| `/sdd-proposal`   | `sdd/proposals/<n>.proposal.md` (with frontmatter)  | `base_branch` |
| `/sdd-spec`       | `sdd/specs/<n>.spec.md` (with frontmatter) + FEAT-ID reservation to `sdd/tasks/.id_ledger.json` | `base_branch` |
| `/sdd-task`       | `sdd/tasks/index/<feature>.json` + `sdd/tasks/active/TASK-*` + TASK-ID reservation to `sdd/tasks/.id_ledger.json` — NO worktree created | `base_branch` |
| `/sdd-start`      | Per-spec index status update + implementation code  | worktree (feature branch) |
| `/sdd-done`       | Verification stamp on per-spec index (committed on feature branch); merges feature → `base_branch` | worktree (feature branch), merged to `base_branch` by Step 9 |

Commit message convention:
```
sdd: <action> for <feature-name>
```

**Note (FEAT-466)**: `/sdd-spec` and `/sdd-task` reservation commits do
**not** occur for `type: hotfix`. A bugfix reserves no `FEAT-<NNN>`/`TASK-<NNN>` id.

**Note (FEAT-145)**: `/sdd-start` no longer needs to `cd` back to the main
repo to update SDD state — per-spec indexes mean each feature owns its own
index file, so the worktree's commit covers code AND state in one stroke.

**Note (FEAT-387)**: `sdd/tasks/.id_ledger.json` is a git-tracked
compare-and-swap counter for `TASK-<NNN>`/`FEAT-<NNN>` numbers. Its
reservation commit is independent — pushed to `base_branch` immediately,
BEFORE the calling command's own task/spec files are written, never bundled
into the same commit.

## Typical Workflow

```bash
git checkout dev && git pull origin dev
/sdd-spec <feature> -- ...                 # spec, committed to dev
/sdd-task sdd/specs/<feature>.spec.md      # tasks, committed to dev
/sdd-start TASK-<NNN>                      # creates the worktree, implements the task
cd .claude/worktrees/feat-FEAT-<NNN>-<slug>
/sdd-start TASK-<NNN+1> …                  # or: claude --agent sdd-worker
/sdd-done FEAT-<NNN>                       # verify, push, merge → dev, clean up
```

## Autonomous Agent (`sdd-worker`)

The `sdd-worker` agent (`.claude/agents/sdd-worker.md`) implements all tasks for
a feature sequentially. Launch it **inside** a manually-created worktree:

```bash
cd .claude/worktrees/<feature-worktree>
claude --agent sdd-worker --model sonnet --verbose
```

Key properties: uses Sonnet, implements EXACTLY what tasks
specify (no redesigns), commits after each task.

For background execution:
```bash
cd .claude/worktrees/feat-014
tmux new -s feat-014 \
  "claude --agent sdd-worker --model sonnet --verbose"
# Ctrl+B, D to detach — tmux attach -t feat-014 to reconnect
```

## Task Index Schema (FEAT-145 — per-spec)

Each feature has its own per-spec index at `sdd/tasks/index/<feature-slug>.json`.
The header carries flow metadata cached from the spec frontmatter; the
`tasks[]` array is local to that feature only.

```json
{
  "feature": "<feature-slug>",
  "feature_id": "FEAT-<NNN>",
  "spec": "sdd/specs/<feature-slug>.spec.md",
  "type": "feature",
  "base_branch": "dev",
  "created_at": "<ISO-8601>",
  "completed_at": null,
  "tasks": [
    {
      "id": "TASK-<NNN>",
      "feature_id": "FEAT-<NNN>",
      "feature": "<feature-slug>",
      "status": "pending",
      "depends_on": [],
      "...": "..."
    }
  ]
}
```

Both `feature_id` and `feature` must be present on every task entry.
Commands resolve features by matching either field (exact, numeric suffix,
or substring) against the per-spec index headers.

<!-- parrot:wiki:begin -->
## Codebase Knowledge Graph (LLM Wiki)

This repository maintains a machine-first knowledge graph of the
codebase (pages + typed edges over a local SQLite plane, built by
`wikitoolkit build`). For ANY question about the codebase — where
something lives, how modules relate, what a subsystem does — you MUST
run a scoped wiki query FIRST, before Grep/Glob/Read or any shell
search (`grep`/`rg`/`find`/`cat` via Bash):

- `wikitoolkit query "<question>"` — token-budgeted, ranked page
  stubs for a scoped question. ALWAYS start here.
- `wikitoolkit page <id>` — read one page in full (file summaries,
  API outlines, content). Use the ids returned by `query`.
- `wikitoolkit related <id>` — follow typed edges (`contains`,
  `references`) to neighbouring files/modules.
- `wikitoolkit status` — plane statistics and staleness.
- `wikitoolkit build` — refresh the graph after large changes
  (a git post-commit hook may already keep it fresh).

These same operations are also exposed as native MCP tools —
`wiki_query`, `wiki_page`, `wiki_related`, `wiki_remember`, `wiki_note`,
`wiki_status` — via the `wikitoolkit` MCP stdio server registered in
this repo's `.mcp.json` (FEAT-403). If they appear in your tool list,
prefer calling them directly; they have equal standing with Grep/Read
at tool-selection time instead of competing via a Bash-invoked CLI.

**Symbol lookup and blast radius (FEAT-498).** For a specific
function/class/method — not a general question — prefer the structural
tools over `wiki_query`: `wikitoolkit symbols lookup <name>`
(`wiki_symbol_lookup` MCP tool) finds it by name/qualname directly;
`wikitoolkit symbols outline <file>` (`wiki_code_outline`) lists a
file's symbols before you read the whole thing; `wikitoolkit symbols
blast <symbol>` (`wiki_blast_radius`) shows every symbol that
transitively calls/extends/implements it — run this BEFORE editing a
widely-used function or class to see what you might break.

**Query discipline** (avoids the two most common ways the wiki
"fails" — which are usually caller error, not missing coverage):

1. **Query for the *thing*, not for your *hypothesis* about it.** The
   ranking is lexical — extra concept words steer it toward those
   concepts. To locate a class or feature, name the symbol/module/
   subsystem you want (`"attestation model service"`), not your theory
   about where it might live.
2. **Follow the thread before falling back.** If a result scores low
   or names a parent module, resolve it with `wikitoolkit page <id>`
   or `wikitoolkit related <id>` — one hop usually lands the real
   page. Do NOT jump to grep just because the first `query` didn't
   rank the exact page first.

Only fall back to Grep/Glob/Read (or shell search) once a clean query
*and* a page/related follow-up have genuinely come up empty — and say
so before you do. Consider `wikitoolkit build` if results look stale.

**Saving knowledge (persistent memory).** The wiki is also your
durable memory — what you save here survives this session and is
found by future `wikitoolkit query` calls ("the agent forgets, the
graph does not"). When you learn a durable fact, make a decision, or
extract a lesson worth keeping, SAVE it:

- `wikitoolkit remember "<fact>" --category [note|decision|lesson|concept]
  [--title "<short title>"] [--link <page_id> --rel <relation>]` —
  file new knowledge (idempotent: same title+category updates the
  existing memory). Link it to the pages it is about.
- `wikitoolkit note <page_id> "<text>"` — append an attributed,
  dated note to an existing page.
- `wikitoolkit link <src_id> <dst_id> --rel <relation>` — connect
  two pages with a typed, asserted edge.
- `wikitoolkit memories` — list saved memories;
  `wikitoolkit audit` — the attributed write log.

Save selectively: durable decisions, gotchas, and cross-file
relationships — not session chatter. Every write is attributed and
auditable.

The `/parrotwiki` command wraps these (e.g. `/parrotwiki query how
does ingest work`, `/parrotwiki remember <fact>`, `/parrotwiki --wiki`
to export a human-readable markdown wiki).
<!-- parrot:wiki:end -->
