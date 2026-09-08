# FEAT-2 evidence — compatible model execution performance

Machine-readable reports and their analyses for FEAT-2. Start with
[`summary.json`](summary.json) for the aggregate AC1–AC12 roll-up, or
[`docs/performance.md`](../../../docs/performance.md) for the narrative.

> **Release status: NOT CERTIFIED.** AC1–AC7 and AC11 pass, AC8/AC9/AC10 are
> completed negative experiments, **AC12 is blocked** at 1 of 10 platform cells.
> `summary.json` → `release_ready: false`.

---

## Index

| file | what it holds |
|---|---|
| **`summary.json`** | **Aggregate AC1–AC12 roll-up, what ships, what does not, evidence hashes.** |
| `baseline.json` | First full acceptance capture (TASK-9). Raw per-process samples, same-source control, noise floor. Recorded on byte-identical source, so every verdict in it is an artifact — that is the point of it. |
| `cython.json` / `cython.md` | **The acceptance run that matters.** AC3/AC5/AC6 verdicts, raw samples, diagnostics. AC5 evaluated against the thresholds revised by spec Amendment 1. |
| `asyncdb-baseline.json` | Real `asyncdb` 2.16.0 consumer differential: pinned artifact, verified adapter API, 18 cases × 6 models, 0 divergences. |
| `structural.json` | TASK-15. Six candidate structural optimizations, **all rejected or retracted**, each with measurements and the reason. |
| `rust-sequential.json` / `.md` | AC8. Sequential native executor: **retain Cython**, with the coverage and boundary-economics arguments. |
| `rust-parallel.json` / `.md` | AC9. Bounded parallel execution: **retain sequential**, with the full size × thread grid. |
| `serialization.json` / `.md` | AC10. Two `json()` candidates: **retain current path**. |
| `platforms.json` / `.md` | AC12. Ten-cell platform matrix: **1 verified**, with four named release blockers. |

---

## How to read these reports

**A confidence interval excluding 1.0 is not, by itself, evidence.** Every
acceptance run includes a *same-source control*: two independently built
worktrees of the **same** reference commit, measured against each other. The
true ratio there is 1.0 by construction, yet it has produced up to **three
spurious "regression" verdicts** and a cross-build noise floor of **0.95–2.12%**
across runs. Anything smaller than that floor is noise, whatever its interval
says.

**`None` never means "valid".** In the native experiment reports, a `None`
result means *ineligible — the caller must run the legacy Python path*. It is
not a validation outcome.

**Negative results are results.** Four of the reports here conclude "do not
ship this". They record measurements, the reason, and a
`what_would_change_the_answer` section, so a future attempt starts from evidence
rather than repeating the experiment.

---

## Headline numbers

| | |
|---|---|
| reference | `d932c720` (0.10.21), rebuilt in isolation |
| candidate | this branch, 0.12.0 |
| workloads improved | **11 of 15** |
| `Employee` construction | **−9.6% raw / −9.9% native** |
| all-scalar model | **−16.0%** |
| worst regression | `class_creation` **+4.35%** median, +4.54% p95 (budget 5%) |
| generic dispatches per build | Employee **2**, all-scalar **0** (was 11) |
| behavioural divergences found | **0**, by every instrument |

---

## Reproducing

```bash
# full acceptance protocol (requires a second, independently built worktree of
# the reference commit to serve as the same-source control)
python benchmarks/model_performance.py --pin-cpu <cpu> \
    --control-root <second build of d932c720> --output out.json

# generic dispatch budget, measured in a separate profiling build whose
# counters are compiled out of release builds
python tests/compatibility/profile_validation.py --builds 20000

# native experiments
python -m pytest tests/compatibility/test_native_executor.py \
                tests/compatibility/test_parallel_validation.py -q

# platform matrix aggregator
python -m pytest tests/compatibility/test_matrix_runner.py -q

# differential parity against the reference build, and everything else
python -m pytest tests/compatibility/ -q
python -m pytest tests/ -q
```

Timings are machine-specific by nature. The protocol and the calibrated noise
floor — not the absolute nanoseconds — are the deliverable.
