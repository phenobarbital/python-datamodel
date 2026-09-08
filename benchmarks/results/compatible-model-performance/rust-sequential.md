# FEAT-2 — Sequential Rust executor: decision (TASK-18)

## Decision: **RETAIN CYTHON**

The sequential native executor is **not promotion-eligible** under AC8. Two
independent grounds, either of which is sufficient on its own.

This is a **completed negative experiment with measurements**, not an
unfinished build. The prototype works, parity holds, and the numbers below say
it should not ship.

---

## 1. Ground one — coverage: it can run none of the workloads

| model | eligible? | why not |
|---|---|---|
| `Employee` | **no** | `employee_id` (UUID), `salary` (Decimal), `hired_at` (date), `updated_at` (datetime), `skills` (List), `manager` (Optional) |
| `UnconstrainedScalars` | **no** | `a_decimal`, `a_uuid`, `a_date`, `a_datetime` |

**0 of the 15 acceptance workloads are eligible.** Every corpus model carries a
`Decimal`, `UUID`, temporal or container field, and the executor declines all of
them by design — its `chrono` handling does not reproduce Python's temporal
variants, so excluding them is the honest choice rather than handling them
wrongly.

AC8 requires *"at least 10% additional improvement on its declared eligible
workload."* There is no such workload in the corpus. A prototype demonstrated
only on a purpose-built scalar model cannot clear a gate defined against the
acceptance suite.

---

## 2. Ground two — economics: the boundary costs most of the prize

| quantity | value |
|---|---|
| Cython construction (median of process medians) | **15,058 ns** |
| Native boundary floor — build mapping, cross into Rust, validate, return | **1,163 ns** |
| Boundary as a share of one construction | **7.8%** |
| Total saving the Cython gate itself delivered (TASK-16, Employee native) | **~9.9%** |
| Theoretical headroom remaining | **~2.1%** |
| AC8 requirement | **≥ 10% additional** |

Native can, at absolute best, remove the validation the Cython path performs.
It must spend 7.8% of a construction just to *ask* the question — against a
total available prize of roughly 9.9%. Even if native validation itself were
instantaneous and covered every type, the arithmetic does not reach 10%
additional improvement. It is not close.

Cold plan creation is a further **816 ns**, measured separately and deliberately
**not** amortised into the warm figures.

### The number that must not be quoted

The harness also reports an optimistic ratio of **0.098** — the native path
appearing ~10× faster. **That is not a speed-up and must not be cited as one.**
The optimistic path skips conversion, defaults, aliases, assignment and hooks
entirely (`object.__new__` plus a `dict` update). The difference is dominated by
work that was *omitted*, not by validation made faster. It is recorded as an
upper bound on the design, with that warning attached in the JSON
(`WARNING_about_the_optimistic_ratio`), precisely so nobody later mistakes it
for evidence of promotion.

---

## 3. Parity — holds, and is not the point

| | |
|---|---|
| rows exercised | 5 |
| executed natively | 4 |
| fell back | 1 (the `2**96` row) |
| **parity mismatches** | **0** |

Parity is a *precondition* for promotion, not a reason for it. The executor
agrees with the Python path on everything it accepts, declines everything it
cannot reason about, and never truncates an arbitrary-precision integer.

**Fallbacks are additive, never a substitute.** A declined row costs the native
attempt *plus* the full Python path, so a workload with a meaningful fallback
rate is strictly worse off than pure Cython. The measured demo rate is 20%.

**No callback duplication.** The executor validates only and never runs a user
callback, so a fallback leaves hooks having fired exactly once — verified by
test, not assumed.

---

## 4. Method

Measured with **paired processes and alternating order** — 6 pairs, 25 batches
of 2,000 per process — so the decision rests on process-level ratios rather than
a single in-process scalar microbenchmark, matching the discipline of the
acceptance protocol. Raw per-batch samples for every process are embedded in
`rust-sequential.json` under `measurements.raw`.

Full cost is charged to the native side: building the values mapping, crossing
the boundary in both directions, interpreting the result, constructing errors,
materialising the instance, plan creation (cold) and plan reuse (warm), and the
cost of falling back.

---

## 5. What would change the answer

Recorded so a future attempt starts from evidence rather than from scratch:

1. **Native coverage of `Decimal`, `UUID` and temporal types with exact Python
   semantics.** That is where the real corpus cost lives, and it is exactly what
   the prototype declines.
2. **A cheaper boundary.** Today it consumes most of the available saving before
   any validation happens. A design that avoids materialising a Python `dict`
   per row would change the arithmetic.
3. **A workload dominated by validation.** The Cython gate already removed the
   generic dispatch, so what remains in a construction is mostly conversion,
   assignment and hooks — none of which this executor addresses.

---

## 6. What was retained and what was not touched

The frozen optimized Cython artifact from TASK-16 remains the implementation.
This task changed **no production Cython or Rust source**, installed no default
backend, and introduced no public API. The experimental crate stays
development-only and is loaded explicitly by path by the harness.

**Reproduce:**

```
python -c "import sys; sys.path.insert(0,'.'); \
    from benchmarks.native_validation import full_cost_comparison; \
    print(full_cost_comparison())"
python -m pytest tests/compatibility/test_native_executor.py -q
```
