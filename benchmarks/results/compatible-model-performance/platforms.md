# FEAT-2 — Platform / interpreter matrix (TASK-21)

## Status: **NOT CERTIFIED** — 1 of 10 required cells has passing evidence

AC12 requires real test evidence from ten cells (Linux x86_64 and Windows
AMD64 × CPython 3.10–3.14). One cell passes. **Release certification is
blocked.**

The most important qualifier, stated up front: **no failure found here is
attributable to FEAT-2.** Every one is reproduced on the 0.10.21 reference. But
a cell that fails for a pre-existing reason still has no passing evidence, so it
still blocks AC12. "Not our fault" is not "certified".

---

## 1. The matrix

| platform | CPython | status | tests | rs_parsers | asyncdb |
|---|---|---|---|---|---|
| linux-x86_64 | 3.10 | ❌ fail | 1 collection error | absent | unverified |
| linux-x86_64 | 3.11 | ❌ fail | 1 collection error | absent | unverified |
| linux-x86_64 | 3.12 | ❌ fail | 1 collection error | absent | unverified |
| linux-x86_64 | **3.13** | ✅ **pass** | **772 passed, 0 failed** | built | **verified** |
| linux-x86_64 | 3.14 | ❌ fail | 29 collection errors | absent | unverified |
| windows-amd64 | 3.10–3.14 | ⛔ unavailable | — | — | — |

Windows cells are recorded as **unavailable**, never as skipped. The aggregator
treats `unavailable` exactly like a failure for certification purposes.

---

## 2. Release blockers

### BLOCKER-1 (high) — **CPython 3.14 does not work at all**

`dataclasses.Field.__init__` gained a required `doc` parameter in Python 3.14.
`datamodel/fields.pyx` does not pass it, so **every model definition** raises:

```
TypeError: Field.__init__() missing 1 required positional argument: 'doc'
```

29 test modules fail at collection. This is **pre-existing**: I built the
0.10.21 reference against CPython 3.14 and it fails identically, and the
`ff.__init__` call site is byte-identical between the two builds.

The consequence matters for the release: **the FEAT-001 release matrix claims
CPython 3.10–3.14 support, and 3.14 is completely non-functional.** Wheels may
build and import, but no model can be declared. This needs its own ticket
against `fields.pyx`; fixing it is outside FEAT-2's scope.

### BLOCKER-2 (medium) — Windows AMD64 evidence entirely absent

Five of ten cells. No Windows runner exists in this environment; it needs the
FEAT-001 release workflow or an authorized CI runner.

### BLOCKER-3 (medium) — asyncdb verified on one interpreter only

The pinned asyncdb 2.16.0 artifact is the **cp313** wheel, so real consumer
compatibility is verified for CPython 3.13 only. AC12 requires it per cell.

### BLOCKER-4 (low) — `rs_parsers` is not built by an editable install

`uv pip install -e .` does not build the Rust extension, so
`converters.pyx:199,236` dereference `rc.to_date`/`rc.to_datetime` on a module
that defines only `HAS_RUST = False`, and every string→date conversion fails.
This is the gap TASK-7 characterized and TASK-8 confirmed is **shared with the
reference**; building `rs_parsers` makes the suite fully green. It affects
test-environment setup rather than shipped wheels, but it is why 3.10/3.11/3.12
show a collection error instead of a clean run.

---

## 3. What the passing cell demonstrates

`linux-x86_64 / CPython 3.13`, built from source fingerprint `fde1d97b71c0…`:

* **772 passed, 0 failed**, 2 skipped — the full repository suite, not an
  import smoke test;
* `rs_parsers` present (`HAS_RUST=True`);
* real **asyncdb 2.16.0** consumer installed and its compatibility suite green;
* the **experimental native module is absent** from a normally installed
  environment — confirming the `rs_core` work from TASK-17/19 did not leak into
  the package, and that default construction works without it.

---

## 4. Why this aggregator cannot be talked into a green tick

The matrix logic is the deliverable here as much as the numbers, so it is tested
against every way the evidence could be inadequate. It refuses to certify when:

* a required cell was **never run** (each of the ten checked individually);
* a cell is **unavailable** — explicitly *"this is incomplete certification, not
  a skip"*;
* a cell's tests **failed**;
* a cell's evidence is an **import-only smoke test** (a wheel that merely
  imports proves nothing about behaviour — the acceptance criteria say so, and
  `tests_passed == 0` is treated as no evidence);
* a cell was built from a **different source fingerprint** than the others
  (stale artifact reference);
* a cell did not verify the **real asyncdb consumer**.

An empty report yields exactly ten problems, and a fully clean matrix does
certify — the positive control exists, so `certified` is not hard-wired to
False.

---

## 5. What is needed to certify

1. **Fix CPython 3.14** (`Field.__init__` must pass `doc`), or remove 3.14 from
   the declared support matrix. Currently the matrix promises something that
   does not work.
2. **Run the Windows AMD64 cells** on the FEAT-001 release workflow.
3. **Provide asyncdb artifacts** for each interpreter, or build it from source
   per cell, so consumer compatibility is verified per cell rather than once.
4. **Build `rs_parsers`** in each test environment (the manifest's `reproduce`
   steps), so the Linux 3.10–3.12 cells run clean.

Until then AC12 remains blocked, and this task is **not** marked verified.

**Reproduce:**

```
python -m pytest tests/compatibility/test_matrix_runner.py -q   # aggregator logic
python -c "import sys; sys.path.insert(0,'.'); \
    from tests.compatibility.matrix import run_cell; print(run_cell('3.13'))"
```
