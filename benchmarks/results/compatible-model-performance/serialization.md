# FEAT-2 — Serialization experiment: decision (TASK-20)

## Decision: **RETAIN THE CURRENT PATH**

AC10 requires **≥ 10% warm JSON improvement**. Two candidates were considered.
One is safe but worth almost nothing; the other would pay handsomely but is a
compatibility break. **No production file was modified.**

---

## 1. Where the time actually goes

`Employee(native).json()`, warm:

| component | ns | share |
|---|---|---|
| **`dataclasses.asdict`** (recursive deep copy) | 10,825 | **77.4%** |
| `orjson.dumps` via the encoder | 1,138 | 8.2% |
| **`JSONContent()` construction** | 53 | **0.38%** |
| total | 14,079 | 100% |

Cold vs warm, measured separately: `json()` **20,998 ns cold** / 14,079 ns warm;
`to_dict()` cold/warm likewise recorded in the JSON.

This breakdown is the useful output of the task. It says plainly that the
encoder is not the problem and `asdict` is.

---

## 2. Candidate A — reuse one encoder instead of building one per call

**REJECTED: measured, far below the gate.**

`json()` currently does `self.__encoder__(**kwargs)` on every call, building a
fresh `JSONContent`. Reusing a single instance when no per-call options are
given was measured end to end:

| model | current | candidate | improvement |
|---|---|---|---|
| `Employee` | 13,704 ns | 13,472 ns | **+1.69%** |
| `UnconstrainedScalars` | 12,393 ns | 12,368 ns | **+0.20%** |

Outputs identical. Against a required **10%**, this is not close — encoder
construction is 0.38% of the call, so that was always its ceiling.

Worth recording: this candidate would have been **safe**. `JSONContent` is a
`cdef` class with no instance state at all (no `__dict__`), so a shared instance
is *not* the "mutable encoder instance globally reused" the acceptance criteria
warn against. It simply buys nothing. A test now fails if instance state is ever
added to `JSONContent`, which would invalidate that reasoning.

---

## 3. Candidate B — skip the deep copy inside `json()`

**REJECTED: compatibility, demonstrated.**

This is the only candidate that could reach 10%: `asdict`'s recursive copy is
77.4% of `json()`. And the copy *looks* like pure waste — the intermediate dict
is handed to `orjson` and discarded immediately, so nothing can observe the
copied values.

Except that the copying itself is observable. A value with a custom
`__deepcopy__` has it invoked **exactly once during `json()`** — verified on
**both** builds:

```
to_dict()  -> __deepcopy__ calls: 1
json()     -> __deepcopy__ calls: 1
```

Skipping the copy would silently stop running user code. That is precisely the
"custom encoders, `__deepcopy__` and exclusion/null side effects" the task
requires be preserved, so the optimization is not available compatibly — no
matter how attractive 77% looks.

---

## 4. Parity — zero divergences

Every scenario executed in **two separate processes** bound to their own
compiled artifacts, with the rebuilt 0.10.21 reference as the oracle:

| area | result |
|---|---|
| scalars, Decimal extremes, Unicode, nulls/defaults | **0 divergences** |
| containers, copy independence, exclusion-set mutation | **0 divergences** |
| nested dataclasses, custom encoders, enums, `__deepcopy__` | **0 divergences** |
| every OK case in the benchmark corpus | **0 divergences** |
| every OK case in the real `asyncdb` 2.16.0 consumer corpus | **0 divergences** |

`to_dict()` still returns independent copies, and a caller's `exclude` set is
compared before and after to confirm it is not mutated across calls.

---

## 5. A pre-existing quirk, characterized not fixed

**`json(**kwargs)` silently ignores per-call options.** The kwargs are forwarded
to the encoder's *constructor* (`self.__encoder__(**kwargs)`), never to
`encode()`. `JSONContent` accepts and discards them, so:

```
json()                        -> {"b":2,"a":1}
json(option=OPT_SORT_KEYS)    -> {"b":2,"a":1}     # option dropped
json(indent=2)                -> {"b":2,"a":1}     # indent dropped
```

Verified identical on 0.10.21, so it is **not a regression**. Correcting it
would be new JSON semantics, which spec §1 puts out of scope, so it is pinned by
test instead — and any future encoder-caching attempt must reproduce it exactly.

It is worth flagging to the maintainer as a separate issue: a caller passing
`indent=2` today gets compact output and no error.

---

## 6. What would change the answer

1. **A way to preserve `__deepcopy__` side effects without copying everything** —
   for example copying only values that define `__deepcopy__`. That is a
   behavioural judgement call, not a pure optimization, and belongs in a spec
   change rather than a benchmark task.
2. **A serializer that walks the instance directly** instead of materialising an
   intermediate dict, which would attack the same 77% from a different angle
   while still invoking user hooks.
3. Neither is a "narrow traversal/temporary-object optimization", which is what
   this task was scoped to try.

**Reproduce:**

```
python -m pytest tests/test_json.py tests/compatibility/test_serialization_parity.py -q
```
