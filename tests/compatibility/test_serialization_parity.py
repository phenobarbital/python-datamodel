"""Serialization parity across the reference and candidate (FEAT-2 / TASK-20).

TASK-20 measured two candidate optimizations for `json()` and took **neither**:

* reusing one encoder instance instead of building one per call — measured at
  **+1.69% / +0.20%** against AC10's required **≥10%**;
* skipping `dataclasses.asdict`'s recursive deep copy, which is **76.8%** of
  `json()` — rejected because a user's `__deepcopy__` genuinely runs during
  `json()`, so removing the copy is an observable behaviour change.

Production serialization is therefore **unchanged**, and this file's job is to
keep it that way: every observable of `to_dict()` and `json()` is compared
between the rebuilt 0.10.21 reference and the candidate, in separate processes
bound to their own compiled artifacts.

The harness is TASK-14's; the oracle is the reference build.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.test_mutation_parity import assert_parity  # noqa: E402

SERIALIZATION_REPORT = (
    Path(__file__).resolve().parents[2] / "benchmarks" / "results"
    / "compatible-model-performance" / "serialization.json"
)


# ===========================================================================
# Part 1 -- output content and type
# ===========================================================================


SCALAR_SCENARIOS = {
    "scalar_round_trip": '''
def run():
    from decimal import Decimal
    from datetime import date, datetime
    import uuid
    class M(BaseModel):
        i: int = Column(required=False, default=0)
        s: str = Column(required=False, default="x")
        f: float = Column(required=False, default=0.0)
        b: bool = Column(required=False, default=False)
        d: Decimal = Column(required=False)
        u: uuid.UUID = Column(required=False)
        when: date = Column(required=False)
        stamp: datetime = Column(required=False)
        class Meta:
            strict = False
    instance = M(i=7, s="hello", f=1.5, b=True, d=Decimal("12345.6789"),
                 u=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
                 when=date(2024, 3, 17), stamp=datetime(2024, 3, 17, 12, 30, 45))
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict()),
            "json_type": describe(type(instance.json()).__name__)}
''',
    "decimal_extremes": '''
def run():
    from decimal import Decimal
    class M(BaseModel):
        d: Decimal = Column(required=False)
        class Meta:
            strict = False
    out = {}
    for label, raw in (("large", "1" * 28), ("small", "0.0000000000000000000000000001"),
                       ("negative", "-99999999999999999999.99"), ("zero", "0")):
        instance = M(d=Decimal(raw))
        out[label] = {"json": attempt(lambda i=instance: i.json()),
                      "to_dict": attempt(lambda i=instance: i.to_dict())}
    return out
''',
    "null_and_defaults": '''
def run():
    from typing import Optional
    class M(BaseModel):
        present: str = Column(required=False, default="here")
        missing: Optional[str] = Column(required=False, default=None)
        class Meta:
            strict = False
    instance = M()
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict()),
            "remove_nulls": attempt(lambda: instance.to_dict(remove_nulls=True))}
''',
    "unicode_payload": '''
def run():
    class M(BaseModel):
        s: str = Column(required=False, default="")
        class Meta:
            strict = False
    return {"accents": attempt(lambda: M(s="ünïcödé").json()),
            "cjk": attempt(lambda: M(s="\\u65e5\\u672c\\u8a9e").json()),
            "emoji": attempt(lambda: M(s="\\U0001f600").json()),
            "quotes": attempt(lambda: M(s='he said "hi"').json())}
''',
}


CONTAINER_SCENARIOS = {
    "nested_dataclass": '''
def run():
    class Inner(BaseModel):
        v: int = Column(required=False, default=0)
        class Meta:
            strict = False
    class Outer(BaseModel):
        inner: Inner = Column(required=False)
        label: str = Column(required=False, default="x")
        class Meta:
            strict = False
    instance = Outer(inner={"v": 3}, label="outer")
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict()),
            "nested_is_dict": attempt(
                lambda: type(instance.to_dict()["inner"]).__name__)}
''',
    "containers": '''
def run():
    from typing import Dict, List
    class M(BaseModel):
        items: List[str] = Column(required=False, default_factory=list)
        mapping: Dict[str, int] = Column(required=False, default_factory=dict)
        class Meta:
            strict = False
    instance = M(items=["a", "b"], mapping={"k": 1})
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict())}
''',
    "to_dict_copy_independence": '''
def run():
    class M(BaseModel):
        items: list = Column(required=False, default_factory=list)
        class Meta:
            strict = False
    instance = M(items=[1, 2, 3])
    first = instance.to_dict()
    first["items"].append(99)
    return {"original_untouched": describe(instance.items),
            "second_call": attempt(lambda: instance.to_dict()),
            "fresh_each_call": describe(instance.to_dict() is not instance.to_dict())}
''',
    "exclusion_set_is_not_mutated_across_calls": '''
def run():
    class M(BaseModel):
        a: int = Column(required=False, default=1)
        b: int = Column(required=False, default=2)
        class Meta:
            strict = False
    instance = M()
    caller_set = {"a"}
    first = attempt(lambda: instance.to_dict(exclude=caller_set))
    return {"first": first,
            "caller_set_after": describe(sorted(caller_set)),
            "second": attempt(lambda: instance.to_dict(exclude=caller_set))}
''',
}


HOOK_SCENARIOS = {
    "deepcopy_side_effect_is_preserved": '''
def run():
    from typing import Any
    events = []
    class Tracked:
        def __init__(self, value):
            self.value = value
        def __deepcopy__(self, memo):
            events.append("deepcopy")
            return Tracked(self.value)
    class M(BaseModel):
        payload: Any = Column(required=False)
        class Meta:
            strict = False
    instance = M(payload=Tracked(1))
    events.clear()
    to_dict_result = attempt(lambda: type(instance.to_dict()["payload"]).__name__)
    after_to_dict = len(events)
    events.clear()
    json_result = attempt(lambda: instance.json())
    after_json = len(events)
    return {"to_dict": to_dict_result, "deepcopy_calls_to_dict": describe(after_to_dict),
            "json": json_result, "deepcopy_calls_json": describe(after_json)}
''',
    "custom_encoder_on_a_field": '''
def run():
    class M(BaseModel):
        v: float = Column(required=False, default=0.0,
                          encoder=lambda value: float(value))
        class Meta:
            strict = False
    instance = M(v=2)
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict())}
''',
    "enum_conversion": '''
def run():
    import enum
    class Colour(enum.Enum):
        RED = "red"
    class M(BaseModel):
        colour: Colour = Column(required=False)
        class Meta:
            strict = False
    instance = M(colour=Colour.RED)
    return {"json": attempt(lambda: instance.json()),
            "to_dict": attempt(lambda: instance.to_dict()),
            "convert_enums": attempt(lambda: instance.to_dict(convert_enums=True))}
''',
    "per_call_options_are_dropped": '''
def run():
    import orjson
    class M(BaseModel):
        b: int = Column(required=False, default=2)
        a: int = Column(required=False, default=1)
        class Meta:
            strict = False
    instance = M()
    return {"default": attempt(lambda: instance.json()),
            "sorted": attempt(lambda: instance.json(option=orjson.OPT_SORT_KEYS)),
            "indent": attempt(lambda: instance.json(indent=2))}
''',
}


def test_scalar_serialization_parity():
    assert_parity(SCALAR_SCENARIOS)


def test_container_and_copy_parity():
    """AC7: public to_dict copy behaviour must be identical on both builds."""
    assert_parity(CONTAINER_SCENARIOS)


def test_hook_and_option_parity():
    """AC2/AC10: custom hooks, deepcopy and per-call options unchanged."""
    assert_parity(HOOK_SCENARIOS)


def test_corpus_models_serialize_identically():
    """Every benchmark corpus model, through both builds."""
    assert_parity({
        "corpus_serialization": '''
def run():
    import sys
    from tests.fixtures.model_performance import cases as C
    out = {}
    for case in C.CASES:
        if case.expect != "ok" or case.requires_rust_parsers:
            continue
        model = case.resolve_model()
        try:
            instance = model(**case.build())
        except BaseException as exc:
            out[case.name] = {"build_error": type(exc).__name__}
            continue
        out[case.name] = {"json": attempt(lambda i=instance: i.json()),
                          "to_dict": attempt(lambda i=instance: i.to_dict())}
    return out
''',
    })


def test_asyncdb_consumer_models_serialize_identically():
    """The real downstream consumer, not a proxy."""
    assert_parity({
        "asyncdb_serialization": '''
def run():
    from tests.fixtures.model_performance import asyncdb_models as fx
    if not fx.ASYNCDB_AVAILABLE:
        raise RuntimeError("asyncdb missing: %s" % fx.ASYNCDB_IMPORT_ERROR)
    out = {}
    for case in fx.CASES:
        if case.expect != "ok" or case.requires_rust_parsers:
            continue
        model = case.resolve_model()
        instance = model(**case.build())
        out[case.name] = {"json": attempt(lambda i=instance: i.json()),
                          "to_dict": attempt(lambda i=instance: i.to_dict())}
    return out
''',
    })


# ===========================================================================
# Part 2 -- the recorded decision
# ===========================================================================


def test_serialization_report_exists_and_retains_the_current_path():
    import json

    assert SERIALIZATION_REPORT.is_file(), f"{SERIALIZATION_REPORT} is missing"
    report = json.loads(SERIALIZATION_REPORT.read_text(encoding="utf-8"))

    assert report["decision"] in {"retain_current", "promote_candidate"}
    gate = report["promotion_gate"]
    assert gate["required_warm_json_improvement_pct"] == 10.0
    if report["decision"] == "retain_current":
        assert gate["met"] is False
        assert report["production_changed"] is False
    for candidate in report["candidates"]:
        assert candidate["verdict"].startswith("REJECTED")
        assert candidate.get("measured") is not None


def test_the_report_records_where_the_time_actually_goes():
    """A report that only said 'no' would not help the next attempt."""
    import json

    report = json.loads(SERIALIZATION_REPORT.read_text(encoding="utf-8"))
    breakdown = report["cost_breakdown"]
    assert breakdown["as_dict_share_pct"] > 50, (
        "the dominant cost should be recorded so a future attempt starts there"
    )
    assert breakdown["encoder_construction_share_pct"] < 1.0
