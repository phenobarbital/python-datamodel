---
description: Full security audit of the python-datamodel project — dependencies, secrets, code surface, CI/release supply chain, plus the config check
argument-hint: "[--scope deps|secrets|code|ci|config|all] [--report <path>]"
allowed-tools: Bash, Read, Grep, Glob, Write
---

# /security-audit — Full Project Audit, 3–8 min

Senior application-security pass over the `python-datamodel` project:
the Python package, Cython extensions, Rust (PyO3) crates, GitHub Actions
workflows, and the Claude Code config.

Produce a **scored** report with a prioritized remediation plan. Save it to
`docs/security-audit-<YYYY-MM-DD>.md` (or `--report <path>`).

Scope defaults to `all`; `--scope` runs a single phase.

---

## Phase 0 — Map the surface

```bash
find datamodel -name '*.py' -o -name '*.pyx' -o -name '*.pxd' | wc -l
find . -name Cargo.toml -not -path '*/target/*'
ls .github/workflows/ 2>/dev/null
```

Record what is **published to PyPI** — a vulnerability in published code
ships to every downstream installer, raising severity by one level.

---

## Phase 1 — Config (delegates to `/security-check`)

Run every phase of `.claude/commands/security-check.md`: agent privileges,
hook exfiltration, command/skill injection, memory poisoning, MCP, permissions.
Carry its findings into the score.

**Score**: 0 CRITICAL and 0 HIGH → +20 · any HIGH → +10 · any CRITICAL → 0

---

## Phase 2 — Secrets across the project

```bash
# Provider key shapes
grep -rnE 'sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}|AKIA[A-Z0-9]{16}|xox[bpsa]-[A-Za-z0-9-]{20,}|AIza[A-Za-z0-9_-]{35}' \
  --include='*.py' --include='*.pyx' --include='*.toml' --include='*.yaml' --include='*.yml' \
  --include='*.json' --include='*.md' --include='*.sh' --include='*.rs' \
  --exclude-dir={.venv,.git,node_modules,build,dist,target,__pycache__,.claude} . 2>/dev/null | head -30

# Assignment-shaped literals
grep -rnE '(api[_-]?key|password|passwd|secret|token)\s*=\s*["'"'"'][^"'"'"'$\{][^"'"'"']{12,}["'"'"']' \
  --include='*.py' --include='*.pyx' --include='*.yaml' --include='*.yml' \
  --exclude-dir={.venv,.git,build,dist,target,__pycache__} . 2>/dev/null | head -30

grep -rn 'BEGIN [A-Z ]*PRIVATE KEY' --exclude-dir={.venv,.git,target} . 2>/dev/null

# .env hygiene
git ls-files | grep -E '(^|/)\.env($|\.)' || echo "OK: no .env tracked"
```

Every hit needs triage. Report only what you confirmed by reading the line.

**Score**: 0 live secrets → +20 · 1–3 → +10 · 4+ → 0 · private key committed → −10

---

## Phase 3 — Dependency and supply chain

```bash
source .venv/bin/activate

# Python
uvx pip-audit --strict 2>&1 | tail -40 || echo "pip-audit unavailable"

# Rust (if Cargo.toml exists)
for c in $(find . -name Cargo.toml -not -path '*/target/*' -not -path '*/.venv/*'); do
  dir=$(dirname "$c")
  [ -f "$dir/Cargo.toml" ] && (cd "$dir" && cargo audit 2>&1 | tail -15)
done

# Lockfile integrity
git status --porcelain uv.lock 2>/dev/null

# Unpinned / floating deps
grep -nE '>=|~=' pyproject.toml | head -20

# Direct-from-git or URL dependencies
grep -rnE '@\s*git\+|\bgit\+https|http://' pyproject.toml
```

- [ ] A `git+` URL dependency? → **HIGH** (unreviewable, mutable source)
- [ ] Any `http://` dependency URL? → **CRITICAL**

**Score**: 0 vulns → +20 · only low/medium → +12 · any high → +5 · any critical → 0

---

## Phase 4 — Code attack surface

Focus on the Cython/C extensions and any dynamic execution paths:

```bash
# 1. Dynamic execution
grep -rnE '\b(eval|exec)\s*\(|__import__\s*\(|pickle\.loads|yaml\.load\s*\((?!.*Loader)|marshal\.loads' \
  --include='*.py' --include='*.pyx' datamodel/ | grep -v test | head -30

# 2. Shell execution
grep -rnE 'subprocess\.(run|Popen|call|check_output)|os\.system|shell\s*=\s*True' \
  --include='*.py' --include='*.pyx' datamodel/ | grep -v test | head -30

# 3. Unsafe C/Cython patterns — buffer overflows, unchecked mallocs
grep -rnE 'malloc|sprintf|strcpy|strcat' --include='*.pyx' --include='*.pxd' datamodel/ | head -20

# 4. SQL injection surfaces (if any DB interaction)
grep -rnE 'f".*SELECT|f".*INSERT|f".*UPDATE|f".*DELETE|\.execute\(f"' \
  --include='*.py' --include='*.pyx' datamodel/ | head -20

# 5. Deserialization
grep -rnE 'pickle\.|shelve\.|marshal\.' --include='*.py' datamodel/ | grep -v test | head -20
```

Rate by reachability from user input:

- [ ] `eval`/`exec`/`pickle.loads` on user data → **CRITICAL**
- [ ] `shell=True` with interpolated variable → **CRITICAL**
- [ ] `yaml.load` without `SafeLoader` → **HIGH**
- [ ] Unchecked `sprintf`/`malloc` in Cython → **HIGH**
- [ ] SQL injection in f-strings → **HIGH**

**Score**: no reachable sink → +25 · reachable but mitigated → +15 · one
reachable unmitigated → +5 · several → 0

---

## Phase 5 — CI and release supply chain

```bash
ls .github/workflows/
# Actions pinned to a tag vs a SHA
grep -rnE 'uses:\s*[^@]+@' .github/workflows/ | grep -vE '@[0-9a-f]{40}' | head -30
# Elevated permissions
grep -rn -B3 -A3 'permissions:' .github/workflows/
# Secrets referenced
grep -rnE 'secrets\.[A-Z_]+' .github/workflows/
# Triggers that run on untrusted PR content
grep -rn 'pull_request_target\|workflow_run' .github/workflows/
```

- [ ] `pull_request_target` with checkout of PR head? → **CRITICAL**
- [ ] Third-party action pinned to a tag (not SHA)? → **MEDIUM/HIGH**
- [ ] `permissions:` broader than needed? → **MEDIUM**
- [ ] Branch protection on `main`?
      ```bash
      gh api repos/:owner/:repo/branches/main/protection 2>&1 | head -20
      ```

**Score**: all clean → +15 · minor gaps → +8 · CRITICAL → 0

---

## Phase 6 — Score and report

Total out of 100 (20 config + 20 secrets + 20 deps + 25 code + 15 CI):

| Score | Posture |
|---|---|
| 90–100 | Strong |
| 70–89 | Good, gaps to close |
| 50–69 | Needs work |
| < 50 | At risk — stop feature work and remediate |

Write to `docs/security-audit-<date>.md`:

```markdown
# Security Audit — python-datamodel

Date: <ISO>   Branch: <branch>   Commit: <sha>
Score: <N>/100 — <posture>

## Findings by severity
### CRITICAL
- **<title>** — `<file>:<line>`
  - Path from untrusted input: <concrete chain>
  - Impact: <what an attacker gets>
  - Fix: <exact change>

### HIGH / MEDIUM / LOW
  (same shape)

## Phase scores
| Phase | Score | Notes |
|---|---|---|
| Config | /20 | |
| Secrets | /20 | |
| Dependencies | /20 | |
| Code surface | /25 | |
| CI & release | /15 | |

## Verified clean
- <checks that passed>

## Remediation plan
1. <highest severity x lowest effort first>

## Not covered
- <what this audit did not reach>
```

---

## Rules

- **Never** paste a discovered secret value into the report.
- Every finding needs a **concrete failure path**, not a pattern match.
- Distinguish **reachable** from **present**.
- If a scanner is missing, report the phase as **not covered**.
- Read-only by default.

## Related

| Command | Scope |
|---|---|
| `/security-audit` | Full project (THIS) |
| `/security-check` | Config only, ~60s |
| `/code-review` | Correctness and quality |
