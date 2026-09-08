# FEAT-2 — Cython acceptance evidence (TASK-16)

**Verdict: FAIL, blocked on AC5 alone.**
**This task remains INCOMPLETE.** Its own acceptance criteria say so:
*"If thresholds fail, this task remains incomplete pending compatible
remediation or reviewed spec change; a negative optimization result is not a
waiver."*

AC3, AC6 and every compatibility gate now pass. AC5 does not, and no further
remediation is going to close it — the mechanism it depends on is exhausted.

---

## 1. Headline

| gate | required | measured | status |
|---|---|---|---|
| **AC5** construction improvement (Employee raw & native) | ≥ 20% | **9.58% / 9.91%** | ❌ **FAIL** |
| **AC6** regression, median | ≤ 5% | worst: `class_creation` **+4.35%** (CI upper +4.64%) | ✅ **PASS** |
| **AC6** regression, p95 | ≤ 5% | worst overall **+4.54%** | ✅ **PASS** |
| **AC3** generic dispatch budget | ≤3 / ≤3 / 0 per build | **2.0 / 2.0 / 0.0** | ✅ PASS |
| **AC1/AC2/AC4/AC7** compatibility | zero divergence | **0 divergences everywhere** | ✅ PASS |

**11 of 15 workloads improved**, best 16.0%, median 9.9%.

---

## 2. This is the second acceptance run

The first run failed **both** AC5 and AC6. Between the two, three things
changed — and it is worth separating them, because only one was a performance
fix:

**a) The diagnosed `class_creation` remediation.** `build_field_policy` was
being called from two sites: `_initialize_fields` (per newly declared field)
and `ModelMeta.__new__` (over the final column set). The second is
authoritative by design, so the first was duplicated work at 2,300 ns per
field. Removed, along with a per-field empty-`frozenset` allocation.

**b) Two real correctness bugs, found by adversarial code review.** Both were
reproduced against the 0.10.21 reference before being fixed:

* **Policy eligibility could be spoofed by a custom metaclass.** Eligibility
  used `annotated_type in _BUILTIN_VALIDATORS` / `.get()`, which go through
  `__hash__`/`__eq__`. A metaclass returning `hash(float)` and claiming
  equality with `float` made an arbitrary class pass — and, since `abstract.py`
  resolves the validator the same way, collect the *real* `valid_float`, so
  even the validator-identity check passed. The gate then skipped validation
  entirely for a value the reference rejects. Eligibility is now decided by
  **identity** alone.
* **A guard removed in TASK-15 was not redundant.** `object.__setattr__`
  consults the type's data descriptors, so a `property` setter runs user code
  that may append its own name to `__fields__`. With the guard gone, a
  self-registering property raised `TypeError` where 0.10.21 accepted it.
  Restored, and TASK-15's "small measured improvement" retracted — that task is
  now a fully negative result.

**c) A deliberate ~1% performance cost for correctness.** The gate's diversion
check was `value is annotated_type`; the legacy path tests `value == _type`.
They coincide for the built-ins as shipped but not structurally, and the legacy
branch routes to `_field_checks_` (primary key / required / nullable). The gate
now mirrors `==`. That is a rich comparison per gated field, and it is most of
why Employee moved from 10.6% to 9.6%. I consider that a good trade and am
flagging it rather than burying it.

| | first run | this run |
|---|---|---|
| `employee_raw` | 10.63% | 9.58% |
| `employee_native` | 10.95% | 9.91% |
| `class_creation` | +4.91% (CI up 5.72%) | **+4.35% (CI up 4.64%)** |
| `assignment` | +1.43%, p95 +11.77% | inconclusive, p95 +1.81% |
| `to_dict` | +1.21% | inconclusive |
| AC5 / AC6 | FAIL / FAIL | FAIL / **PASS** |

---

## 3. Measurement quality

| property | value |
|---|---|
| protocol shortfalls | **none** (8 paired processes, 30 batches, 1000 warm-up ops) |
| duration | 486 s |
| calibration spread | **5.6%** → quiet machine |
| suspect processes | **0 of 16** |
| same-source control floor | **1.55%** |
| spurious verdicts from *identical* code | 3 |
| worst resolvable effect | 1.24% |

A 20% effect is comfortably resolvable, so the AC5 shortfall is a real result
and not a measurement limitation. `class_creation`'s +4.35% sits well above the
1.55% cross-build floor, so it is a real regression — just now within budget.

The control produced **3 spurious verdicts from provably identical code** this
run, which is the standing reminder that a confidence interval excluding 1.0 is
not by itself evidence at these magnitudes. Everything reported as passing or
failing above is far from that boundary.

---

## 4. Full results

| workload | reference ns | candidate ns | ratio | change | verdict |
|---|---|---|---|---|---|
| `unconstrained_native` | 19,862 | 16,646 | 0.8397 | **−16.0%** | improvement |
| `unconstrained_raw` | 24,064 | 20,665 | 0.8560 | **−14.4%** | improvement |
| `wide_native` | 139,675 | 124,090 | 0.8870 | **−11.3%** | improvement |
| `wide_raw` | 149,718 | 133,409 | 0.8904 | **−11.0%** | improvement |
| `constrained_valid` | 15,225 | 13,724 | 0.8974 | −10.3% | improvement |
| `employee_native` | 30,924 | 27,990 | 0.9009 | −9.9% | improvement |
| `employee_raw` | 37,264 | 33,851 | 0.9042 | −9.6% | improvement |
| `invalid_input` | 34,453 | 31,708 | 0.9083 | −9.2% | improvement |
| `client_nested` | 20,814 | 19,280 | 0.9224 | −7.8% | improvement |
| `callback_hooks` | 20,191 | 19,295 | 0.9530 | −4.7% | improvement |
| `container_full` | 78,733 | 77,062 | 0.9797 | −2.0% | improvement |
| `assignment` | 315.1 | 317.3 | 1.0042 | +0.4% | inconclusive |
| `json_warm` | 14,184 | 14,400 | 1.0072 | +0.7% | inconclusive |
| `to_dict` | 11,327 | 11,416 | 1.0087 | +0.9% | inconclusive |
| `class_creation` | 272,975 | 284,352 | 1.0435 | **+4.4%** | regression |

---

## 5. Why AC5 cannot be remediated further on this path

The generic-dispatch elimination is **complete**, and the dispatch counter
proves it: `unconstrained_native` reaches `_validation_` **zero** times per
build, and Employee reaches it exactly twice — its two non-scalar fields,
`List[str]` and `Optional[Employee]`, which are ineligible by design. There is
no remaining dispatch to remove. ~10% is what that dispatch actually cost.

Reaching 20% means attacking what is left:

* per-field **conversion** in `converters.pyx`;
* the `_dc_method_setattr_` path — 11 Python-level calls per Employee build,
  each doing a `startswith`/`endswith` pair and an **O(n) list membership scan**;
* the per-build `list(__columns__.items())` snapshot.

The latter two were profiled in TASK-15 and **rejected as unsafe with
evidence**: a live `items()` view breaks a callback that mutates `__columns__`
mid-build (tolerated on both builds today), and a membership set goes stale
because `__fields__` is public and mutated in place — including, as the review
showed, by property setters. Those verdicts stand; see `structural.json`.

---

## 6. Compatibility — unblemished

| check | result |
|---|---|
| differential corpus (45 cases, two isolated builds) | **0 divergences** |
| real `asyncdb.models` 2.16.0 consumer (31 tests) | **0 divergences** |
| adversarial mutation / hook / generic-fallback parity (18 tests) | **0 divergences** |
| repository suite | **680 passed, 2 skipped, 0 failed** |
| generic dispatch budget, 20,000 builds/workload | 2.0 / 2.0 / **0.0** |

Both correctness gaps found by review were fixed *before* this run and each now
has a regression test. Notably, neither was caught by the existing suite —
nothing exercised a custom metaclass or a self-registering property setter.

---

## 7. Frozen comparison point

Frozen as the optimized-Cython baseline for TASK-17–TASK-20 **despite** the
AC5 shortfall: those experiments must beat *this*, not 0.10.21, or they will be
re-measuring the Cython work.

Commit and both environments' extension digests: `cython.json` →
`frozen_candidate`.

---

## 8. The decision required

Blocked on **AC5 only**. Three honest options:

1. **Fund further compatible optimization.** The remaining targets are listed in
   §5. The two cheapest are already ruled out on safety grounds, so this is real
   work, not tuning.
2. **Take a reviewed spec change to the 20% threshold.** ~10%, broad across 11
   of 15 workloads, with zero behavioural change and a fully characterized
   compatibility story, is a defensible release. What must not happen is the
   threshold being quietly lowered to match the result — the acceptance criteria
   name that failure mode explicitly, which is why this document says FAIL.
3. **Accept and carry forward.** TASK-17–20 measure against this frozen
   candidate regardless; a native backend may close the gap on its own.

**Reproduce:**

```
python benchmarks/model_performance.py --pin-cpu <cpu> \
    --control-root <second independently built worktree of d932c720> \
    --output <output>.json
python tests/compatibility/profile_validation.py --builds 20000
```
