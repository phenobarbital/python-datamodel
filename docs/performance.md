# Performance

This document describes the compatible performance work done in FEAT-2, what it
measured, what it changed, and — just as importantly — what it deliberately did
**not** change.

The guiding constraint throughout: **preserve the behaviour of python-datamodel
0.10.21 exactly, including its legacy quirks.** Every optimization here is one
that could be made without a single observable behavioural difference. Several
promising ones were rejected for exactly that reason, and they are documented
below rather than quietly dropped.

> **Release status: not yet certified.** See
> [Rollout prerequisites](#rollout-prerequisites). The performance work is
> complete and measured; platform certification is not.

---

## What got faster

Measured against the 0.10.21 engineering reference, built in isolation, using
the paired-process protocol described in [Methodology](#methodology):

| workload | improvement |
|---|---|
| all-unconstrained scalar model | **−16.0%** |
| unconstrained scalars, raw string input | **−14.4%** |
| 50-field model (native / raw) | **−11.3% / −11.0%** |
| constrained scalars | −10.3% |
| `Employee` native / raw (11 fields, ORM-shaped) | **−9.9% / −9.6%** |
| invalid input | −9.2% |
| nested model | −7.8% |
| custom hooks | −4.7% |
| container-heavy model | −2.0% |

**11 of 15 measured workloads improved.** Constructing models is the priority
this feature was scoped around — ORM hydration in particular — and that is where
the gains land.

### What got slower

| workload | change |
|---|---|
| cold class creation | **+4.4%** |
| `to_dict()` / `json()` / attribute assignment | within noise (inconclusive) |

Class creation is slower because a validation policy is now computed once per
field when a model class is defined. That cost is paid once per class, not per
instance, and buys the per-construction saving above. It is within the ≤5%
budget the specification sets.

---

## How it works

Before this change, every field of every model went through a generic
`_validation_` dispatch on every construction.

Now, when a model class is created, each field gets a small **precomputed
policy** recording what validation work it could possibly require. At
construction time — *after* parsing, *after* any user callback, at the same
boundary the old code used — a gate consults that policy. When a field's value
is an exactly-typed supported scalar and the field's cached validator and parser
are still the ones the policy recorded, the generic dispatch is skipped: the
type is already proven, so the built-in validator is known to accept it, and
only the live constraints remain.

Measured effect: an all-scalar model now reaches the generic dispatch **zero**
times per construction, and an 11-field `Employee` reaches it exactly **twice**
— its `List[str]` and `Optional[Employee]` fields, which are ineligible by
design.

### When the fast path is *not* taken

The gate declines — and the original code path runs, untouched — whenever
anything is not provably safe:

* the value is a **subclass** of the expected type (exact identity is required,
  never `isinstance`), including `bool` where `int` is expected;
* the value is **empty or `None`**, so presence, primary-key, `db_default` and
  nullable rules still run. Note `0` and `False` are *values*, not absence, and
  do take the fast path;
* the field's **validator or parser was replaced at runtime**;
* the field is not an exactly supported scalar — containers, unions, nested
  models, enums, `Decimal` constraints and everything else keep the original
  path.

Declining is always safe: it costs one dispatch and changes nothing.

### Constraints are read live

The policy records only *which* constraints exist, never their values. The gate
re-reads them from the field's metadata on every construction, so a constraint
added, changed or removed **after** the class was defined takes effect
immediately:

```python
class Late(BaseModel):
    v: int = Column(required=False)

    class Meta:
        strict = False

Late(v=99)                      # fine

field = Late.__columns__["v"]
field._meta["max"] = 10
field.metadata = field._meta

Late(v=99).get_errors()         # now reports the violation
```

---

## Compatibility

No behavioural difference from 0.10.21 has been found by any instrument built
for this feature:

| check | result |
|---|---|
| differential corpus (45 cases, two isolated builds) | **0 divergences** |
| real `asyncdb.models` 2.16.0 consumer (31 tests, 18 cases, 6 models) | **0 divergences** |
| adversarial mutation / hook / generic-fallback parity (18 tests) | **0 divergences** |
| serialization parity, incl. corpus and asyncdb models | **0 divergences** |
| repository suite | 772 passed |

**`asyncdb.models` compatibility is a first-class requirement**, not an
afterthought: the pinned `asyncdb` 2.16.0 distribution is installed against both
builds and its models are constructed, mutated, serialized and compared
field-by-field. `asyncdb.models.Model` subclasses `BaseModel` and additionally
uses `datamodel.abstract.Meta`, `datamodel.types.MODEL_TYPES` and
`datamodel.types.DB_TYPES`, so it exercises a wider surface than `BaseModel`
alone.

The **FEAT-001 platform matrix** (Linux x86_64 and Windows AMD64 × CPython
3.10–3.14) is preserved as a requirement; its current verification status is in
[Rollout prerequisites](#rollout-prerequisites).

---

## Experiments that did not ship

Three alternatives were built, measured, and **rejected on their numbers**. Each
has a full report under `benchmarks/results/compatible-model-performance/`.

### Sequential Rust executor — *retained Cython*

A bounded native validator was built and works, with zero parity mismatches on
what it accepts. It is not promotable:

* **Coverage:** it can run **0 of the 15** acceptance workloads. Every corpus
  model carries `Decimal`, `UUID`, temporal or container fields, all of which it
  declines by design.
* **Economics:** crossing the Python↔Rust boundary costs ~1,163 ns, **7.8% of a
  construction**, while the entire saving available from validation is ~9.9%. It
  must spend most of the prize to collect it.

### Bounded parallel execution — *retained sequential*

Correct and deterministic (identical to sequential under 16-way
oversubscription, ineligible rows kept in their own slots), but the best
throughput anywhere on a 1–10,000 row × 1–16 thread grid was **1.11×** against a
required 1.25×, with no crossover. Only ~10% of the work is parallelisable,
because the GIL-held snapshot and rebuild phases dominate — the same boundary
cost that blocked the sequential experiment.

### Serialization — *retained the current path*

Reusing one encoder instead of constructing one per `json()` call measured
**+1.69% / +0.20%** against a required 10%; encoder construction is only 0.38%
of the call. The change that *would* pay — skipping `dataclasses.asdict`'s
recursive copy, **77.4%** of `json()` — was rejected because a user's
`__deepcopy__` genuinely runs during `json()`, so removing the copy would
silently stop executing user code.

### Structural costs — *all candidates rejected*

Two further optimizations were profiled and rejected as unsafe, with
demonstrations rather than arguments: passing a live `__columns__.items()` view
instead of a snapshot breaks a callback that mutates `__columns__` mid-build
(which works today), and caching `__fields__` membership in a set goes stale
because `__fields__` is public and mutated in place — including by property
setters.

---

## Remaining costs

For anyone continuing this work, measured shares of an `Employee` construction /
`json()` call:

| cost | share | note |
|---|---|---|
| `dataclasses.asdict` deep copy | **77.4%** of `json()` | protected by `__deepcopy__` side effects |
| per-field conversion in `converters.pyx` | large | not attacked by this feature |
| `_dc_method_setattr_` | 11 Python-level calls per construction | `startswith`/`endswith` pair plus an O(n) list membership scan |
| per-build `list(__columns__.items())` snapshot | ~570 ns | load-bearing; see above |
| generic validation dispatch | **eliminated** for supported scalars | this feature |

---

## Methodology

Performance claims here use one protocol, and nothing else counts:

* **8 paired fresh processes**, alternating which build runs first, so a warm-up
  or thermal trend cannot favour one side;
* 1,000 warm-up operations, then **30 batches of 2,000 constructions**;
* the clock is read **twice per batch**, never around an individual constructor;
* input preparation happens outside the timed region;
* profiling and allocation counters are compiled out of release builds entirely
  and collected in a separate pass.

Crucially, every run includes a **same-source control**: two independently built
worktrees of the *same* reference commit measured against each other. The true
ratio there is 1.0 by construction, so whatever it reports is pure noise plus
binary-layout effects. It has measured a cross-build floor of **0.95–2.12%** and
has produced up to **3 spurious "regression" verdicts from provably identical
code**. That is why a confidence interval excluding 1.0 is *not*, by itself,
evidence at these magnitudes — and why nothing under ~2% is claimed here.

### Reproducing

```bash
# full acceptance protocol (needs a second, independently built worktree of the
# reference commit for the control)
python benchmarks/model_performance.py --pin-cpu <cpu> \
    --control-root <second build of d932c720> --output out.json

# generic dispatch budget, in a separate profiling build
python tests/compatibility/profile_validation.py --builds 20000

# differential parity against the reference build
python -m pytest tests/compatibility/ -q

# everything
python -m pytest tests/ -q
```

---

## Rollout prerequisites

**This work is not certified for release.** The performance and compatibility
gates pass; platform certification does not.

| prerequisite | status |
|---|---|
| Compatible speed-up, measured | ✅ done |
| Zero behavioural divergence from 0.10.21 | ✅ done |
| `asyncdb.models` consumer compatibility | ✅ verified on CPython 3.13 |
| Platform matrix, 10 cells | ❌ **1 of 10** |

Blocking items, in priority order:

1. **CPython 3.14 does not work at all** — and this is **pre-existing**, not
   caused by this feature. `dataclasses.Field.__init__` gained a required `doc`
   parameter in 3.14, and `datamodel/fields.pyx` does not pass it, so *every
   model definition* raises `TypeError`. Verified by building the 0.10.21
   reference against 3.14, where it fails identically. The declared support
   matrix currently promises a 3.14 that cannot declare a model. **Needs its own
   ticket.**
2. **Windows AMD64 evidence is absent** (5 of 10 cells) — needs the FEAT-001
   release workflow or an authorized CI runner.
3. **`asyncdb` verified on one interpreter only** — the pinned artifact is the
   cp313 wheel.
4. **`rs_parsers` is not built by an editable install**, so string→date
   conversion fails in a plain `pip install -e .` environment. Pre-existing and
   shared with the reference.

No consumer baseline approval has been supplied, and none is implied by this
document.

### A note on versioning

The specification and task set assume this work lands in **0.11.0**;
`datamodel/version.py` currently reads **0.12.0**. No version bump was
authorized, so the file is untouched. **The maintainer needs to reconcile which
release carries this work** — this document deliberately does not choose.

---

## Full evidence

Every number above is backed by a machine-readable report in
`benchmarks/results/compatible-model-performance/` — see the
[README](../benchmarks/results/compatible-model-performance/README.md) in that
directory for an index.
