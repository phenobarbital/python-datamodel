"""Lossless, type-tagged observations for the FEAT-2 differential runner.

The reference and the candidate run in *separate processes* against *separate
compiled artifacts*, so their results have to cross a process boundary before
they can be compared.  Plain ``json.dumps`` would destroy exactly the
distinctions this feature must preserve — ``True``/``1``, ``Decimal("1.0")``/
``"1.0"``, ``date``/``datetime``, ``bytes``/``str``, ``list``/``tuple``, a
``str`` subclass versus ``str`` — so every value is wrapped in a tag that
records its concrete class alongside a reversible rendering.

Object *identity* is recorded the only way it can be compared across processes:
as a relationship **within** one run.  Every mutable object seen during a run is
assigned a sequential reference number the first time it is encountered; seeing
the same number twice means "the same object appeared twice here".  Literal
memory addresses are never emitted.

Nothing in this module imports :mod:`datamodel`, so it behaves identically in
the reference child and the candidate child.
"""
from __future__ import annotations

import base64
import datetime as _dt
import decimal
import uuid
from typing import Any, Dict, Iterator, List, Optional, Tuple

#: Bumped whenever the observation format changes in a way that makes an old
#: recorded run incomparable with a new one.
FORMAT_VERSION = 1

#: Guard against pathological/recursive structures in a fixture.
MAX_DEPTH = 24


class Observer:
    """Builds tagged observations, tracking object identity within one run.

    A single :class:`Observer` must be used for everything observed in one
    process run, because reference numbers are only meaningful relative to each
    other.
    """

    def __init__(self) -> None:
        self._refs: Dict[int, int] = {}
        self._keepalive: List[Any] = []
        self._next = 0

    def _ref_for(self, value: Any) -> Tuple[int, bool]:
        """Return ``(reference_number, is_first_sight)`` for ``value``."""
        key = id(value)
        existing = self._refs.get(key)
        if existing is not None:
            return existing, False
        ref = self._next
        self._next += 1
        self._refs[key] = ref
        # Hold a strong reference so a temporary cannot be garbage-collected
        # and have its id() reused by a different object later in the run.
        self._keepalive.append(value)
        return ref, True

    # -- scalars ----------------------------------------------------------

    def observe(self, value: Any, depth: int = 0) -> dict:
        """Return a tagged, comparable observation of ``value``."""
        if depth > MAX_DEPTH:
            return {"k": "truncated", "cls": _cls(value)}

        if value is None:
            return {"k": "none"}

        # bool BEFORE int: bool is an int subclass and the whole point of this
        # corpus is that the two must never be normalised together.
        if isinstance(value, bool):
            return {"k": "bool", "cls": _cls(value), "v": bool(value)}
        if isinstance(value, int):
            # str() keeps arbitrary-precision integers exact across JSON.
            return {"k": "int", "cls": _cls(value), "v": str(int(value))}
        if isinstance(value, float):
            return {"k": "float", "cls": _cls(value), "v": repr(float(value))}
        if isinstance(value, decimal.Decimal):
            # str() preserves trailing zeros and exponent form; float() would not.
            return {"k": "decimal", "cls": _cls(value), "v": str(value)}
        if isinstance(value, str):
            return {"k": "str", "cls": _cls(value), "v": str(value)}
        if isinstance(value, (bytes, bytearray)):
            return {
                "k": "bytes",
                "cls": _cls(value),
                "v": base64.b64encode(bytes(value)).decode("ascii"),
            }
        if isinstance(value, uuid.UUID):
            return {"k": "uuid", "cls": _cls(value), "v": str(value)}
        # datetime BEFORE date: datetime is a date subclass.
        if isinstance(value, _dt.datetime):
            return {
                "k": "datetime",
                "cls": _cls(value),
                "v": value.isoformat(),
                "tz": None if value.tzinfo is None else str(value.tzinfo),
            }
        if isinstance(value, _dt.date):
            return {"k": "date", "cls": _cls(value), "v": value.isoformat()}
        if isinstance(value, _dt.time):
            return {"k": "time", "cls": _cls(value), "v": value.isoformat()}
        if isinstance(value, _dt.timedelta):
            return {"k": "timedelta", "cls": _cls(value),
                    "v": repr(value.total_seconds())}

        # -- containers and objects ---------------------------------------

        ref, first = self._ref_for(value)
        if not first:
            # Second sighting: this *is* the identity signal.
            return {"k": "seen", "ref": ref, "cls": _cls(value)}

        if isinstance(value, (list, tuple)):
            return {
                "k": "tuple" if isinstance(value, tuple) else "list",
                "cls": _cls(value),
                "ref": ref,
                "items": [self.observe(item, depth + 1) for item in value],
            }
        if isinstance(value, (set, frozenset)):
            # A set has no order, so sort by the rendered observation to get a
            # stable comparison without normalising element types.
            items = [self.observe(item, depth + 1) for item in value]
            items.sort(key=_stable_key)
            return {"k": "set", "cls": _cls(value), "ref": ref, "items": items}
        if isinstance(value, dict):
            return {
                "k": "dict",
                "cls": _cls(value),
                "ref": ref,
                "items": [
                    [self.observe(k, depth + 1), self.observe(v, depth + 1)]
                    for k, v in value.items()
                ],
            }

        fields = _dataclass_field_names(value)
        if fields is not None:
            return {
                "k": "model",
                "cls": _cls(value),
                "ref": ref,
                "fields": [
                    [name, self.observe(getattr(value, name, _MISSING), depth + 1)]
                    for name in fields
                ],
            }

        if callable(value):
            return {
                "k": "callable",
                "cls": _cls(value),
                "ref": ref,
                "name": getattr(value, "__qualname__", getattr(value, "__name__", "")),
            }

        return {"k": "object", "cls": _cls(value), "ref": ref, "repr": _safe_repr(value)}


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover - only reached on a bug
        return "<missing>"


_MISSING = _Missing()


def _cls(value: Any) -> str:
    """``module.QualName`` of ``value``'s *concrete* class."""
    kind = type(value)
    module = getattr(kind, "__module__", "?")
    name = getattr(kind, "__qualname__", getattr(kind, "__name__", "?"))
    return name if module in ("builtins", "?") else f"{module}.{name}"


def _safe_repr(value: Any) -> str:
    """``repr`` that can never raise and never leaks an address."""
    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - defensive
        return f"<unreprable {type(value).__name__}: {exc}>"
    return _strip_addresses(text)


def _strip_addresses(text: str) -> str:
    """Replace ``0x7f...`` addresses, which differ between processes."""
    out = []
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("0x", index):
            end = index + 2
            while end < length and text[end] in "0123456789abcdefABCDEF":
                end += 1
            if end > index + 2:
                out.append("0xADDR")
                index = end
                continue
        out.append(text[index])
        index += 1
    return "".join(out)


def _dataclass_field_names(value: Any) -> Optional[List[str]]:
    """Ordered field names if ``value`` is a dataclass *instance*, else None.

    ``dataclasses.fields`` is deliberately not imported at module scope so this
    module stays free of any import that a reference/candidate split could make
    behave differently; ``__dataclass_fields__`` is the same public protocol.
    """
    if isinstance(value, type):
        return None
    spec = getattr(value, "__dataclass_fields__", None)
    if spec is None:
        return None
    try:
        return list(spec.keys())
    except Exception:  # pragma: no cover - defensive
        return None


def _stable_key(observation: dict) -> str:
    return repr(sorted(observation.items(), key=lambda kv: kv[0]))


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


class Divergence:
    """One concrete difference between a reference and a candidate run."""

    __slots__ = ("path", "kind", "reference", "candidate")

    def __init__(self, path: str, kind: str, reference: Any, candidate: Any) -> None:
        self.path = path
        self.kind = kind
        self.reference = reference
        self.candidate = candidate

    def __repr__(self) -> str:
        return (
            f"Divergence({self.path!r}, {self.kind!r}, "
            f"reference={self.reference!r}, candidate={self.candidate!r})"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Divergence):
            return NotImplemented
        return (
            self.path == other.path
            and self.kind == other.kind
            and self.reference == other.reference
            and self.candidate == other.candidate
        )

    def __hash__(self) -> int:
        return hash((self.path, self.kind, repr(self.reference), repr(self.candidate)))

    def describe(self) -> str:
        return (
            f"{self.path}: {self.kind}\n"
            f"    reference: {self.reference!r}\n"
            f"    candidate: {self.candidate!r}"
        )


def compare(reference: Any, candidate: Any, path: str = "$") -> List[Divergence]:
    """All differences between two observations, deepest detail first.

    The returned paths are actionable: ``$.cases.employee_raw.fields[3].age.v``
    names the exact value that moved.
    """
    return list(_compare(reference, candidate, path))


def _compare(reference: Any, candidate: Any, path: str) -> Iterator[Divergence]:
    if isinstance(reference, dict) and isinstance(candidate, dict):
        yield from _compare_dicts(reference, candidate, path)
        return
    if isinstance(reference, list) and isinstance(candidate, list):
        if len(reference) != len(candidate):
            yield Divergence(path, "length", len(reference), len(candidate))
        for index, (left, right) in enumerate(zip(reference, candidate)):
            yield from _compare(left, right, f"{path}[{index}]")
        return
    if type(reference) is not type(candidate):
        yield Divergence(path, "type", _describe(reference), _describe(candidate))
        return
    if reference != candidate:
        yield Divergence(path, "value", reference, candidate)


def _compare_dicts(reference: dict, candidate: dict, path: str) -> Iterator[Divergence]:
    # An observation dict: report the tag mismatch first, it explains the rest.
    ref_kind, cand_kind = reference.get("k"), candidate.get("k")
    if ref_kind != cand_kind and (ref_kind is not None or cand_kind is not None):
        yield Divergence(path, "kind", ref_kind, cand_kind)
        return
    ref_cls, cand_cls = reference.get("cls"), candidate.get("cls")
    if ref_cls != cand_cls:
        yield Divergence(path, "class", ref_cls, cand_cls)

    if ref_kind == "model":
        yield from _compare_model(reference, candidate, path)
        return

    ref_keys, cand_keys = set(reference), set(candidate)
    for missing in sorted(ref_keys - cand_keys):
        yield Divergence(f"{path}.{missing}", "missing-in-candidate",
                         reference[missing], None)
    for added in sorted(cand_keys - ref_keys):
        yield Divergence(f"{path}.{added}", "missing-in-reference",
                         None, candidate[added])
    for key in sorted(ref_keys & cand_keys):
        if key == "cls":
            continue  # already reported above
        yield from _compare(reference[key], candidate[key], f"{path}.{key}")


def _compare_model(reference: dict, candidate: dict, path: str) -> Iterator[Divergence]:
    """Compare a model observation, reporting field *order* explicitly."""
    ref_fields = [name for name, _ in reference.get("fields", [])]
    cand_fields = [name for name, _ in candidate.get("fields", [])]
    if ref_fields != cand_fields:
        yield Divergence(f"{path}.__field_order__", "field-order",
                         ref_fields, cand_fields)

    ref_ref, cand_ref = reference.get("ref"), candidate.get("ref")
    if ref_ref != cand_ref:
        yield Divergence(f"{path}.ref", "identity", ref_ref, cand_ref)

    ref_by_name = dict(reference.get("fields", []))
    cand_by_name = dict(candidate.get("fields", []))
    for name in ref_fields:
        if name not in cand_by_name:
            continue  # already reported by field-order
        yield from _compare(ref_by_name[name], cand_by_name[name], f"{path}.{name}")


def _describe(value: Any) -> str:
    return f"{type(value).__name__}:{value!r}"
