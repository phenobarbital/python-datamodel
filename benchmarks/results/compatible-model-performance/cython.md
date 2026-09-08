# FEAT-2 — Cython acceptance evidence (TASK-16)

**Verdict: FAIL. AC5 is not met, and AC6 cannot be signed off.**
**This task remains INCOMPLETE.** Its own acceptance criteria say so plainly:
*"If thresholds fail, this task remains incomplete pending compatible
remediation or reviewed spec change; a negative optimization result is not a
waiver."*

Compatibility, however, is perfect, and the dispatch budgets pass. The problem
is purely one of magnitude: the optimization works, it just is not big enough.

---

## 1. Headline

| gate | required | measured | status |
|---|---|---|---|
| **AC5** construction improvement (Employee raw & native) | ≥ 20% | **10.63% / 10.95%** | ❌ **FAIL** |
| **AC6** representative regression, median | ≤ 5% | `class_creation` **+4.91%**, CI upper **+5.72%** | ❌ **FAIL** (CI exceeds limit) |
| **AC6** representative regression, p95 | ≤ 5% | `assignment` p95 **+11.77%** | ❌ **FAIL** |
| **AC3** generic dispatch budget | ≤ 3 / ≤ 3 / 0 per build | **2.0 / 2.0 / 0.0** | ✅ PASS |
| **AC1/AC2/AC4/AC7** compatibility | zero divergence | **0 divergences everywhere** | ✅ PASS |

The AC5 shortfall is **not** a measurement artifact. The run resolves a 20%
effect comfortably (worst resolvable effect 1.50%), so ~11% is a real result.

---

## 2. Measurement quality

This matters more than the numbers, because the numbers are only worth what the
protocol is worth.

| property | value |
|---|---|
| protocol shortfalls | **none** (8 paired processes, 30 batches, 1000 warm-up ops) |
| duration | 494.8 s |
| calibration spread | **8.2%** → quiet machine |
| suspect processes | **0 of 16** |
| same-source control floor | **0.95%** |
| spurious verdicts from *identical* code | **0** |
| worst resolvable effect | 1.50% |
| can resolve AC5 (20%) / AC6 (5%) | yes / yes |

The control ran two independently built worktrees of the **same** reference
commit against each other. It produced **zero** spurious verdicts this time, and
puts the cross-build noise floor at 0.95% — so every effect reported below that
size is noise, and everything above it is real.

---

## 3. Full results

Ratio < 1.0 means the candidate is faster. Intervals are 95%.

| workload | reference ns | candidate ns | ratio | change | verdict |
|---|---|---|---|---|---|
| `unconstrained_native` | 19,739 | 16,617 | 0.8417 | **−15.8%** | improvement |
| `unconstrained_raw` | 24,076 | 20,651 | 0.8634 | **−13.7%** | improvement |
| `constrained_valid` | 15,302 | 13,627 | 0.8842 | **−11.6%** | improvement |
| `wide_native` | 139,864 | 123,862 | 0.8846 | **−11.5%** | improvement |
| `wide_raw` | 149,527 | 132,998 | 0.8861 | **−11.4%** | improvement |
| `employee_native` | 31,147 | 27,737 | 0.8905 | **−11.0%** | improvement |
| `employee_raw` | 37,352 | 33,217 | 0.8937 | **−10.6%** | improvement |
| `invalid_input` | 34,762 | 31,612 | 0.9073 | −9.3% | improvement |
| `client_nested` | 21,051 | 19,346 | 0.9173 | −8.3% | improvement |
| `callback_hooks` | 20,380 | 19,136 | 0.9438 | −5.6% | improvement |
| `container_full` | 80,480 | 76,740 | 0.9577 | −4.2% | improvement |
| `json_warm` | 14,540 | 14,576 | 1.0018 | +0.2% | inconclusive |
| `to_dict` | 11,431 | 11,500 | 1.0121 | +1.2% | regression |
| `assignment` | 315.6 | 320.1 | 1.0143 | +1.4% | regression |
| `class_creation` | 273,049 | 285,818 | 1.0491 | **+4.9%** | regression |

**11 of 15 workloads improved**, several by more than 10%. The optimization is
real and broad. It is simply about half the size AC5 demands.

---

## 4. Why AC5 fails

The TASK-13 gate removed the generic `_validation_` dispatch for exactly-typed
supported scalars — and it removed it *completely*: `unconstrained_native`
reaches the generic dispatch **zero** times per build, and Employee reaches it
exactly twice (its two non-scalar fields, `List[str]` and `Optional[Employee]`).

So the dispatch elimination is finished; there is no more of it to win. The
~11% it bought is what that dispatch actually cost. Reaching 20% requires
attacking what remains:

* per-field **conversion** work in `converters.pyx`;
* the `_dc_method_setattr_` path — 11 Python-level calls per Employee build,
  each doing a `startswith`/`endswith` pair and an **O(n) list membership scan**;
* the per-build `list(__columns__.items())` snapshot.

The last two were profiled in TASK-15 and **rejected as unsafe**, with evidence:
a live `items()` view breaks a callback that mutates `__columns__` mid-build
(tolerated on both builds today), and a membership set goes stale because
`__fields__` is public and mutated in place. Those verdicts stand; see
`structural.json`.

---

## 5. Why AC6 fails, and what would fix it

### `class_creation` +4.91% (CI upper +5.72%)

The point estimate is under 5%, but the interval is not, so ≤5% cannot be
*claimed*. This one is **understood and probably cheap to fix**:

`build_field_policy` (TASK-11) runs at class creation and costs **2,300 ns per
field**. It is called from **two** sites:

* `abstract.py:356` — in `_initialize_fields`, per newly declared field;
* `abstract.py:443` — in `__new__`, over the **final** column set.

For an 8-field class that is ~36.8 µs of the ~65 µs regression measured in
isolation (reference 481–490 µs vs candidate 545–554 µs), and **about half of it
is redundant**: the `__new__` loop rebuilds from the final field set, which
TASK-11 deliberately made authoritative so that cache hits and inheritance are
handled correctly. The earlier call is then pure duplicated work.

A second, smaller cost: `build_field_policy` allocates a `frozenset` per field
even when the field has no constraints at all.

**Not applied here.** Modifying production sources is explicitly out of scope
for TASK-16. This is a grounded recommendation for the gate owner
(TASK-11/TASK-13 scope) or a follow-up task, not a change smuggled into an
evidence task.

### `assignment` p95 +11.77%

The median is only +1.4%, so this is upper-tail behaviour rather than a
systematic slowdown. It needs explaining before AC6 can be signed off; the raw
per-batch samples for it are embedded in `cython.json` under `raw`.

---

## 6. Compatibility — unblemished

| check | result |
|---|---|
| differential corpus (45 cases, 2 isolated builds) | **0 divergences** |
| real `asyncdb.models` consumer (31 tests, 18 cases, 6 models) | **0 divergences** |
| adversarial mutation / hook / generic-fallback parity (18 tests) | **0 divergences** |
| repository suite | **675 passed, 2 skipped, 0 failed** |
| generic dispatch budget, 20,000 builds/workload | 2.0 / 2.0 / **0.0** |

Not one behavioural difference from 0.10.21 has been found by any instrument
built for this feature. Whatever is decided about the thresholds, the
*compatibility* half of the specification is met.

---

## 7. Frozen comparison point

The candidate is frozen as the optimized-Cython baseline for TASK-17–TASK-20,
**despite** the AC5 shortfall — those experiments must beat *this*, not the
0.10.21 reference, or they are measuring the Cython work a second time.

* candidate commit: recorded in `cython.json` → `frozen_candidate.commit`
* reference: `d932c720e9e36bbacdaca2b1a2af0688f2636c40` (0.10.21)
* extension sha256 digests for both: `cython.json` → `frozen_candidate.binaries`
  / `reference_binaries`

---

## 8. What has to happen next

This task cannot be closed as-is. The options, in the order I would rank them:

1. **Apply the `class_creation` remediation** (drop the redundant
   `abstract.py:356` policy build; consider skipping the `frozenset` allocation
   when a field has no constraints) and re-run this protocol. That plausibly
   clears AC6's median gate. **It will not move AC5.**
2. **Decide AC5 deliberately.** ~11% is a real, broad, compatible improvement
   with zero behavioural change. Either fund further optimization work, or take
   a *reviewed* spec change to the 20% threshold. What must not happen is the
   threshold being quietly relaxed to match the result — the acceptance criteria
   call that out by name.
3. **Investigate the `assignment` p95** before signing off AC6.

Raw per-process, per-batch samples for every number in this document are
embedded in `cython.json` under `raw.reference` / `raw.candidate`; allocation
and lifetime observations are in `diagnostics`, collected in a separate pass and
never while a timing was in progress.

**Reproduce:**

```
python benchmarks/model_performance.py --pin-cpu <cpu> \
    --control-root <second independently built worktree of d932c720> \
    --output <output>.json
python tests/compatibility/profile_validation.py --builds 20000
```
