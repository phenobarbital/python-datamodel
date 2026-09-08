# FEAT-2 — Bounded parallel native execution: decision (TASK-19)

## Decision: **RETAIN SEQUENTIAL EXECUTION**

AC9 requires **≥ 1.25× throughput** over sequential native execution. The best
result anywhere on the grid is **1.11×**. There is **no crossover size** at
which threading pays.

A completed negative experiment with measurements — the implementation works
correctly, and the numbers say threading it is not worth shipping.

---

## 1. The grid

Sizes 1 / 10 / 100 / 1000 / 10000 × thread counts 1 / 2 / 4 / 8 / 16
(including deliberate oversubscription), measured against sequential native
execution of the *same* plan.

| batch size | sequential ns/row | best speedup | at threads | AC9 (≥1.25×) |
|---|---|---|---|---|
| 1 | 1,206 | 0.27× | 1 | no |
| 10 | 1,962 | 1.03× | 8 | no |
| 100 | 937 | 0.88× | 1 | no |
| 1,000 | 1,210 | 0.99× | 1 | no |
| 10,000 | 1,501 | 1.11× | 2 | no |

At size 1 the pool is pure overhead (0.27×). At 100 and 1,000 the best result
is *sequential* (1 thread). Only at 10,000 does threading edge ahead at all, and
only to 1.11×.

**Crossover size: none.**

---

## 2. Why it cannot pay — measured, not guessed

| quantity | value |
|---|---|
| `execute_batch` total, per row | **1,357 ns** |
| Single-row boundary floor (measured independently in TASK-18) | **1,163 ns** |

The batch per-row cost is barely above the boundary floor. That means almost
all of the work is the **GIL-held snapshot and rebuild** phases — converting
Python values into owned Rust values on the way in, and building result tuples
on the way out. Only the *detached validation slice* is parallelisable.

Amdahl's law with 8 workers, as a function of how much of the work validation
actually is:

| validation share | max possible speedup |
|---|---|
| 5% | 1.05× |
| 10% | 1.10× |
| 20% | 1.21× |
| 30% | 1.36× |

The measured best of **1.11×** corresponds to validation being roughly **10%**
of the work — which matches the boundary measurement exactly. To reach AC9's
1.25× the validation share would have to exceed 20%.

So this is **not a threading problem**. More workers, a better pool, or a
smarter schedule cannot fix it. It is the same blocker TASK-18 identified: the
Python↔Rust boundary costs more than the work it is carrying. Making the
boundary cheaper is the only thing that would change the answer.

---

## 3. Safety — structural, not statistical

**No worker touches Python.** Execution is three strictly separated phases:

1. **snapshot** — GIL held; every row becomes owned Rust values or is marked
   ineligible;
2. **detach** — GIL released inside `Python::detach`; the bounded Rayon pool
   sees *only* the owned snapshot. There is no `Py<...>`, no `Bound<...>` and no
   callback reachable, so a worker cannot touch the interpreter even by
   accident, and the caller is never required to hold the GIL on anyone's
   behalf;
3. **rebuild** — GIL re-acquired; results returned in the original row order.

Verified by consequence as well as by construction: a value whose `__eq__` and
`__hash__` record every invocation is passed through a parallel batch and
records **nothing**, and a model with a `__post_init__` hook is never
constructed by the executor.

**Deterministic ordering.** `par_iter().collect()` preserves index order
regardless of completion order. Checked identical to sequential across 30
repeated runs, and under **16-way oversubscription on a 7-row batch** — far more
workers than work. A 500-row batch is checked row-by-row so identity, not just
the multiset of results, is preserved.

**Bounded, reusable workers.** The pool is built once per plan with an explicit
count and reused across batches. Asking for 0 threads yields sequential
execution rather than Rayon's one-per-core default, so nothing is ever
unbounded.

**Ineligible work stays serial.** Ineligible rows are never executed natively,
never reordered, and come back as `None` in their own slot for the caller to run
serially — arbitrary-precision integers and bool-where-int-is-expected among
them.

---

## 4. What was not introduced

* no public batch API on any model;
* no constructor threading default;
* no package deployment — the crate stays development-only and is loaded
  explicitly by path;
* no parallel execution of arbitrary Python callbacks.

All four asserted by test.

---

## 5. What would change the answer

1. **A cheaper boundary.** Today the snapshot/rebuild phases dominate, capping
   the parallelisable slice at ~10%. This is the same finding as TASK-18 and is
   the single blocker for both experiments.
2. **Genuinely heavier per-row validation** — regex, deep containers, expensive
   constraints — where the detached slice would be large enough for Amdahl to
   work in our favour. The current scalar checks are a handful of comparisons.
3. **Batches far larger than 10,000** with amortised marshalling, e.g. an
   arrow-style columnar hand-off that avoids building a Python `dict` per row.

**Reproduce:**

```
python -c "import sys; sys.path.insert(0,'.'); \
    from benchmarks.native_validation import load_native, parallel_grid; \
    print(parallel_grid(load_native(build=False)))"
python -m pytest tests/compatibility/test_parallel_validation.py -q
```
