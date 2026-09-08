"""Generic-fallback parity for everything the gate declines (FEAT-2 / TASK-14).

The fast path deliberately covers a narrow slice: exactly-typed supported
scalars.  Everything else -- unions, literals, nested containers, dataclass
fields, callables, enums, typed subclasses -- must reach the untouched generic
``_validation_`` path and behave exactly as it did at 0.10.21.

That makes this file the complement of ``test_validation_fastpath.py``: that
one checks what the gate *takes over*, this one checks that what it *declines*
was left strictly alone.  Both matter, but a regression here would be the
quieter one, because none of these types were ever meant to change.

Every scenario runs in both builds and the two must agree; the harness lives in
``test_mutation_parity.py``.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.compatibility.test_mutation_parity import assert_parity  # noqa: E402


CONTAINER_SCENARIOS = {
    "typed_containers": '''
def run():
    from typing import Dict, List, Set, Tuple
    class M(BaseModel):
        items: List[str] = Column(required=False, default_factory=list)
        mapping: Dict[str, int] = Column(required=False, default_factory=dict)
        unique: Set[int] = Column(required=False, default_factory=set)
        pair: Tuple[int, str] = Column(required=False)
        class Meta:
            strict = False
    instance = M(items=["a", "b"], mapping={"k": 1}, unique={1, 2}, pair=(1, "x"))
    return {"items": attempt(lambda: instance.items),
            "mapping": attempt(lambda: instance.mapping),
            "unique": attempt(lambda: instance.unique),
            "pair": attempt(lambda: instance.pair),
            "to_dict": attempt(lambda: instance.to_dict())}
''',
    "container_with_wrong_inner_type": '''
def run():
    from typing import List
    class M(BaseModel):
        items: List[int] = Column(required=False, default_factory=list)
        class Meta:
            strict = False
    return {"good": attempt(lambda: M(items=[1, 2]).items),
            "mixed": attempt(lambda: M(items=[1, "two"]).items),
            "errors": attempt(lambda: (M(items=[1, "two"]).get_errors() or {}))}
''',
    "empty_containers": '''
def run():
    from typing import Dict, List
    class M(BaseModel):
        items: List[str] = Column(required=False, default_factory=list)
        mapping: Dict[str, int] = Column(required=False, default_factory=dict)
        class Meta:
            strict = False
    instance = M()
    return {"items": attempt(lambda: instance.items),
            "mapping": attempt(lambda: instance.mapping),
            "independent": attempt(lambda: M().items is not instance.items)}
''',
    "nested_containers": '''
def run():
    from typing import Dict, List
    class M(BaseModel):
        deep: Dict[str, List[int]] = Column(required=False, default_factory=dict)
        class Meta:
            strict = False
    return {"value": attempt(lambda: M(deep={"a": [1, 2]}).deep)}
''',
}

UNION_SCENARIOS = {
    "optional_and_union": '''
def run():
    from typing import Optional, Union
    class M(BaseModel):
        maybe: Optional[str] = Column(required=False)
        either: Union[int, str] = Column(required=False)
        class Meta:
            strict = False
    return {"none": attempt(lambda: M(maybe=None).maybe),
            "text": attempt(lambda: M(maybe="x").maybe),
            "union_int": attempt(lambda: M(either=1).either),
            "union_str": attempt(lambda: M(either="s").either),
            "union_bad": attempt(lambda: M(either=[1]).either)}
''',
    "literal_field": '''
def run():
    from typing import Literal
    class M(BaseModel):
        mode: Literal["a", "b"] = Column(required=False)
        class Meta:
            strict = False
    return {"allowed": attempt(lambda: M(mode="a").mode),
            "rejected": attempt(lambda: M(mode="zzz").mode),
            "errors": attempt(lambda: (M(mode="zzz").get_errors() or {}))}
''',
    "enum_field": '''
def run():
    import enum
    class Colour(enum.Enum):
        RED = "red"
        BLUE = "blue"
    class M(BaseModel):
        colour: Colour = Column(required=False)
        class Meta:
            strict = False
    return {"member": attempt(lambda: M(colour=Colour.RED).colour),
            "by_value": attempt(lambda: M(colour="red").colour),
            "unknown": attempt(lambda: M(colour="green").colour)}
''',
}

NESTED_MODEL_SCENARIOS = {
    "nested_dataclass_field": '''
def run():
    class Inner(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    class Outer(BaseModel):
        inner: Inner = Column(required=False)
        name: str = Column(required=False)
        class Meta:
            strict = False
    from_dict = attempt(lambda: Outer(inner={"v": 1}, name="x").inner)
    from_obj = attempt(lambda: Outer(inner=Inner(v=2), name="y").inner)
    return {"from_dict": from_dict, "from_obj": from_obj,
            "to_dict": attempt(lambda: Outer(inner={"v": 3}, name="z").to_dict())}
''',
    "nested_as_objects": '''
def run():
    class Inner(BaseModel):
        v: int = Column(required=False)
        class Meta:
            strict = False
    class Outer(BaseModel):
        inner: Inner = Column(required=False)
        class Meta:
            strict = False
            as_objects = True
    return {"value": attempt(lambda: Outer(inner={"v": 1}).inner),
            "json": attempt(lambda: Outer(inner={"v": 1}).json())}
''',
    "inherited_and_overridden_fields": '''
def run():
    class Parent(BaseModel):
        shared: int = Column(required=False)
        class Meta:
            strict = False
    class Child(Parent):
        shared: str = Column(required=False)
        own: int = Column(required=False)
        class Meta:
            strict = False
    return {"parent": attempt(lambda: Parent(shared=1).shared),
            "child_override": attempt(lambda: Child(shared="text", own=2).shared),
            "child_own": attempt(lambda: Child(shared="text", own=2).own),
            "columns": describe(sorted(Child.__columns__))}
''',
}

CALLABLE_SCENARIOS = {
    "callable_field": '''
def run():
    from collections.abc import Callable
    class M(BaseModel):
        fn: Callable = Column(required=False)
        class Meta:
            strict = False
    return {"with_function": attempt(lambda: M(fn=len).fn is len),
            "with_non_callable": attempt(lambda: M(fn=5).fn)}
''',
    "default_factory_is_not_shared": '''
def run():
    from typing import List
    class M(BaseModel):
        items: List[str] = Column(required=False, default_factory=list)
        class Meta:
            strict = False
    first, second = M(), M()
    first.items.append("mutated")
    return {"first": attempt(lambda: first.items),
            "second": attempt(lambda: second.items)}
''',
    "aliased_field": '''
def run():
    class M(BaseModel):
        value: str = Column(required=False, alias="wire_name")
        class Meta:
            strict = False
    return {"by_attribute": attempt(lambda: M(value="a").value),
            "by_alias": attempt(lambda: M(wire_name="b").value)}
''',
}

PARSE_FAILURE_SCENARIOS = {
    "failed_conversion_then_validation": '''
def run():
    from datetime import date
    class M(BaseModel):
        when: date = Column(required=False)
        after: int = Column(required=False, max=10)
        class Meta:
            strict = False
    instance = M(when="not-a-date", after=99)
    return {"errors": describe(sorted(instance.get_errors() or {})),
            "after": attempt(lambda: instance.after)}
''',
    "parse_error_ordering": '''
def run():
    from datetime import date
    class M(BaseModel):
        a: int = Column(required=False, max=10)
        b: date = Column(required=False)
        c: int = Column(required=False, max=10)
        class Meta:
            strict = False
    instance = M(a=99, b="nope", c=99)
    return {"error_keys": describe(sorted(instance.get_errors() or {}))}
''',
    "strict_parse_error_raises": '''
def run():
    from datetime import date
    class M(BaseModel):
        when: date = Column(required=False)
        class Meta:
            strict = True
    return {"result": attempt(lambda: M(when="not-a-date"))}
''',
}


def test_container_fallback_parity():
    assert_parity(CONTAINER_SCENARIOS)


def test_union_literal_and_enum_parity():
    assert_parity(UNION_SCENARIOS)


def test_nested_model_parity():
    assert_parity(NESTED_MODEL_SCENARIOS)


def test_callable_alias_and_factory_parity():
    assert_parity(CALLABLE_SCENARIOS)


def test_parse_failure_parity():
    """A failed conversion followed by validation must behave identically."""
    assert_parity(PARSE_FAILURE_SCENARIOS)


def test_mixed_fast_and_generic_fields_in_one_model():
    """The realistic case: a model where only some fields take the fast path.

    If the gate leaked state between fields -- reusing a decision, or skipping
    the wrong one -- a mixed model is where it would show.
    """
    scenarios = {
        "mixed_model": '''
def run():
    from decimal import Decimal
    from typing import List, Optional
    from datetime import date
    class M(BaseModel):
        scalar: int = Column(required=False)
        bounded: int = Column(required=False, max=10)
        text: str = Column(required=False)
        money: Decimal = Column(required=False)
        when: date = Column(required=False)
        items: List[str] = Column(required=False, default_factory=list)
        maybe: Optional[str] = Column(required=False)
        class Meta:
            strict = False
    good = M(scalar=1, bounded=5, text="t", money=Decimal("1.5"),
             when=date(2024, 3, 17), items=["a"], maybe="m")
    bad = M(scalar=1, bounded=99, text="t", money=Decimal("1.5"),
            when=date(2024, 3, 17), items=["a"], maybe="m")
    return {"good": attempt(lambda: good.to_dict()),
            "good_errors": describe(sorted(good.get_errors() or {})),
            "bad_errors": describe(sorted(bad.get_errors() or {})),
            "bad_scalar_survived": attempt(lambda: bad.scalar)}
''',
    }
    assert_parity(scenarios)
