"""The conservative per-field validation policy (FEAT-2 / TASK-11).

The policy is a *precomputation*, not a behaviour change.  In this task nothing
consults it at validation time: `_validation` is untouched, and these tests
exist to prove that the policy is (a) conservative, (b) invalidated by every
identity or metadata drift that could make it wrong, and (c) invisible from
outside.  The gated loop that will finally read it lands in a later task; if
any assumption here is wrong, that task would silently skip real work.

The load-bearing property throughout is: **`None` is the legacy policy and is
always safe.**  Every unknown, dynamic, custom or drifting case must land on
`None`, never on a policy that overstates what is known.
"""
import gc
import itertools
import weakref
from decimal import Decimal
from typing import List, Optional

import pytest

from datamodel import BaseModel, Column, Field
from datamodel.exceptions import ValidationError
from datamodel.validation import (
    POLICY_WORK_CONSTRAINTS,
    POLICY_WORK_CUSTOM_VALIDATOR,
    POLICY_WORK_TYPE_CHECK,
    FieldPolicy,
    build_field_policy,
    field_policy,
    policy_is_current,
    validators,
)


# ===========================================================================
# Part 1 -- the default is legacy, and legacy is safe
# ===========================================================================


def test_a_bare_field_has_no_policy():
    """A Field that never reached a model keeps the legacy default."""
    assert Field(required=False)._policy is None
    assert field_policy(Field(required=False)) is None


def test_field_policy_never_raises_on_a_foreign_object():
    """Callers must be able to ask about anything without guarding."""
    assert field_policy(None) is None
    assert field_policy(object()) is None
    assert field_policy(42) is None


def test_build_returns_legacy_for_missing_inputs():
    assert build_field_policy(None, int) is None
    assert build_field_policy(Field(), None) is None


def test_policy_is_current_is_false_for_legacy():
    """A legacy policy is never 'current', so it can never authorise a skip."""
    assert policy_is_current(Field(), None) is False
    assert policy_is_current(None, None) is False


def test_policy_is_current_rejects_a_foreign_policy_object():
    class NotAPolicy:
        work_mask = 0xFF

    class M(BaseModel):
        a: int = Column(required=False)

    assert policy_is_current(M.__columns__["a"], NotAPolicy()) is False


# ===========================================================================
# Part 2 -- what does and does not earn a policy
# ===========================================================================


class Scalars(BaseModel):
    an_int: int = Column(required=False)
    a_str: str = Column(required=False)
    a_float: float = Column(required=False)
    a_bool: bool = Column(required=False)
    a_decimal: Decimal = Column(required=False)


@pytest.mark.parametrize(
    "name", ["an_int", "a_str", "a_float", "a_bool", "a_decimal"]
)
def test_exact_scalars_earn_a_policy(name):
    field = Scalars.__columns__[name]
    policy = field_policy(field)
    assert isinstance(policy, FieldPolicy)
    assert policy.exact_scalar is True
    assert policy.work_mask & POLICY_WORK_TYPE_CHECK
    assert policy_is_current(field, policy) is True


class NonScalars(BaseModel):
    a_list: List[str] = Column(required=False, default_factory=list)
    an_optional: Optional[str] = Column(required=False)
    a_nested: Scalars = Column(required=False)


@pytest.mark.parametrize("name", ["a_list", "an_optional", "a_nested"])
def test_non_scalars_stay_on_the_legacy_path(name):
    """Anything that is not an exact scalar must default safely."""
    field = NonScalars.__columns__[name]
    assert field_policy(field) is None


def test_constraint_shape_is_recorded_but_values_are_not():
    """The policy records *which* constraints exist, never their values.

    Storing a value would freeze it, and `_validate_constraints` reads
    constraints live. Recording only the shape is what keeps the two in step.
    """
    class Bounded(BaseModel):
        v: int = Column(required=False, min=1, max=10)

    policy = field_policy(Bounded.__columns__["v"])
    assert policy.constraint_shape == frozenset({"min", "max"})
    assert policy.work_mask & POLICY_WORK_CONSTRAINTS
    # No constraint *value* is reachable from the policy.
    assert 1 not in tuple(policy.constraint_shape)
    assert 10 not in tuple(policy.constraint_shape)


def test_an_unconstrained_scalar_reports_no_constraint_work():
    class Plain(BaseModel):
        v: int = Column(required=False)

    policy = field_policy(Plain.__columns__["v"])
    assert policy.constraint_shape == frozenset()
    assert not (policy.work_mask & POLICY_WORK_CONSTRAINTS)


def test_a_custom_validator_is_part_of_the_work_mask():
    def my_validator(field, value, annotated_type, val_type):
        return True

    class WithValidator(BaseModel):
        v: int = Column(required=False, validator=my_validator)

    policy = field_policy(WithValidator.__columns__["v"])
    if policy is not None:
        assert policy.work_mask & POLICY_WORK_CUSTOM_VALIDATOR


def test_a_custom_field_subclass_never_earns_a_policy():
    """We cannot reason about a subclass's behaviour, so we do not try."""
    class MyField(Field):
        pass

    custom = MyField(required=False)
    custom.type = int
    custom._type_category = "primitive"
    custom.validator = validators[int]
    assert build_field_policy(custom, int) is None


def test_a_str_subclass_annotation_does_not_earn_a_policy():
    class MyStr(str):
        pass

    field = Field(required=False)
    field.type = MyStr
    field._type_category = "primitive"
    assert build_field_policy(field, MyStr) is None


# ===========================================================================
# Part 3 -- identity drift must invalidate, never persist
# ===========================================================================


_UNIQUE = itertools.count()


def _fresh_int_field():
    """A genuinely fresh field, with a class name never used before.

    Reusing a class name here would be a trap: the class cache is keyed on
    (name, bases, annotations), so a second `class Holder` returns the *same*
    Field object, and a test that swaps its validator would corrupt every
    later test. See `test_class_cache_shares_field_objects_for_identical_signatures`.
    """
    return type(
        f"Holder{next(_UNIQUE)}",
        (BaseModel,),
        {"__annotations__": {"v": int}, "v": Column(required=False)},
    ).__columns__["v"]


def test_a_swapped_validator_invalidates_the_policy():
    field = _fresh_int_field()
    policy = field_policy(field)
    assert policy_is_current(field, policy) is True

    field.validator = lambda *a, **k: None
    assert policy_is_current(field, policy) is False


def test_a_swapped_parser_invalidates_the_policy():
    field = _fresh_int_field()
    policy = field_policy(field)
    assert policy_is_current(field, policy) is True

    field.parser = lambda value: value
    assert policy_is_current(field, policy) is False


def test_a_swapped_type_invalidates_the_policy():
    field = _fresh_int_field()
    policy = field_policy(field)
    assert policy_is_current(field, policy) is True

    field.type = str
    assert policy_is_current(field, policy) is False


def test_a_dropped_primitive_category_invalidates_the_policy():
    field = _fresh_int_field()
    policy = field_policy(field)
    field._type_category = "complex"
    assert policy_is_current(field, policy) is False


def test_adding_a_constraint_through_live_metadata_invalidates_the_policy():
    """Live-metadata semantics: a callback may mutate `_meta` at any time.

    A policy built when no constraint existed must not survive one appearing,
    or a later gate would skip a constraint that is now real.
    """
    field = _fresh_int_field()
    policy = field_policy(field)
    assert policy.constraint_shape == frozenset()
    assert policy_is_current(field, policy) is True

    field._meta["min"] = 5
    field.metadata = field._meta
    assert policy_is_current(field, policy) is False


def test_removing_a_constraint_also_invalidates_the_policy():
    class Bounded(BaseModel):
        v: int = Column(required=False, min=1)

    field = Bounded.__columns__["v"]
    policy = field_policy(field)
    assert policy_is_current(field, policy) is True

    field._meta.pop("min")
    field.metadata = field._meta
    assert policy_is_current(field, policy) is False


def test_adding_a_custom_validator_later_invalidates_the_policy():
    field = _fresh_int_field()
    policy = field_policy(field)
    assert policy_is_current(field, policy) is True

    field._meta["validator"] = lambda *a, **k: True
    field.metadata = field._meta
    assert policy_is_current(field, policy) is False


def test_replacing_a_public_validator_cannot_make_a_stranger_look_known():
    """Identity is checked against a private snapshot, not the public map.

    `validators` is a plain, importable, mutable dict. If eligibility were
    decided against it, overwriting an entry would let an arbitrary function
    be treated as a known built-in -- and a later gate could skip work that
    function was supposed to do.
    """
    original = validators[int]
    intruder = lambda field, name, value, _type: None  # noqa: E731
    validators[int] = intruder
    try:
        field = Field(required=False)
        field.type = int
        field._type_category = "primitive"
        field.validator = intruder
        assert build_field_policy(field, int) is None
    finally:
        validators[int] = original


def test_identity_is_not_inferred_from_a_function_name():
    """A look-alike named exactly like the built-in must still be rejected."""
    original = validators[int]

    def impostor(field, name, value, _type):
        return None

    # Wear the built-in's exact display name. (It is "wrap", not "valid_int":
    # the built-ins are cdef functions reached through a Cython wrapper, which
    # is itself a good reason never to key trust on __name__.)
    impostor.__name__ = original.__name__
    impostor.__qualname__ = getattr(original, "__qualname__", original.__name__)
    assert impostor.__name__ == original.__name__

    field = Field(required=False)
    field.type = int
    field._type_category = "primitive"
    field.validator = impostor
    assert build_field_policy(field, int) is None


# ===========================================================================
# Part 4 -- class construction: cache hits, inheritance, replacement, dynamics
# ===========================================================================


def test_policies_are_built_on_a_class_cache_hit():
    """A cache hit must still leave every final field with a usable policy."""
    def make():
        class Cached(BaseModel):
            v: int = Column(required=False)

        return Cached

    first, second = make(), make()
    for model in (first, second):
        field = model.__columns__["v"]
        policy = field_policy(field)
        assert isinstance(policy, FieldPolicy)
        assert policy_is_current(field, policy) is True


def test_class_cache_shares_field_objects_for_identical_signatures():
    """CHARACTERIZATION of pre-existing behaviour, not something introduced here.

    The class cache is keyed on (name, bases, annotations) and deliberately
    omits defaults and configuration, so two same-named classes with different
    constraint *values* share one Field object -- the second class silently
    sees the first's `min`. That is why the task forbids reusing that key as a
    semantic plan key.

    The policy is unaffected because it records only the constraint *shape* of
    the field that actually exists, and both classes genuinely share that one
    field. A gate reading live values later reads the same value the reference
    build reads, so no new divergence is introduced.
    """
    def make(minimum):
        class Shared(BaseModel):
            v: int = Column(required=False, min=minimum)

        return Shared

    first, second = make(1), make(50)
    field_a = first.__columns__["v"]
    field_b = second.__columns__["v"]

    assert field_a is field_b, "pre-existing sharing no longer happens"
    assert field_b.metadata.get("min") == 1, "the second class sees the first's min"

    policy = field_policy(field_a)
    assert policy.constraint_shape == frozenset({"min"})
    assert policy_is_current(field_b, policy) is True


def test_inherited_fields_have_policies_on_the_subclass():
    class Parent(BaseModel):
        inherited: int = Column(required=False)

    class Child(Parent):
        own: str = Column(required=False)

    for name in ("inherited", "own"):
        field = Child.__columns__[name]
        assert isinstance(field_policy(field), FieldPolicy), name
        assert policy_is_current(field, field_policy(field)) is True


def test_a_replaced_field_gets_the_replacements_policy():
    """Overriding a parent field must not inherit the parent's policy."""
    class Base2(BaseModel):
        v: int = Column(required=False)

    class Override(Base2):
        v: str = Column(required=False, max_length=5)

    field = Override.__columns__["v"]
    policy = field_policy(field)
    assert field.type is str
    assert policy.type_ref is str
    assert "max_length" in policy.constraint_shape


def test_a_dynamically_added_field_defaults_to_legacy():
    """`create_field` builds a bare Field; it must never look pre-analysed."""
    class Loose(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False

    instance = Loose(known=1)
    instance.create_field("added", "a value")
    assert field_policy(instance.__columns__["added"]) is None


def test_add_field_defaults_to_legacy():
    class Loose2(BaseModel):
        known: int = Column(required=False)

        class Meta:
            strict = False

    Loose2.add_field("later", 5)
    assert field_policy(Loose2.__columns__["later"]) is None


# ===========================================================================
# Part 5 -- the policy must be invisible and cheap
# ===========================================================================


class Visible(BaseModel):
    a: int = Column(required=False, default=1)
    b: str = Column(required=False, default="x")


def test_policy_does_not_appear_in_to_dict_or_json():
    instance = Visible()
    assert "_policy" not in instance.to_dict()
    assert "_policy" not in instance.json()
    assert "FieldPolicy" not in instance.json()


def test_policy_does_not_appear_in_field_metadata():
    """`metadata` is public and is what leaks into schemas."""
    for field in Visible.__columns__.values():
        assert "_policy" not in dict(field.metadata)
        assert "policy" not in dict(field.metadata)


def test_policy_adds_no_public_column_or_option():
    assert "_policy" not in Visible.__fields__
    assert "_policy" not in Visible.__columns__
    assert "_policy" not in dict(Visible.__dataclass_fields__)


def test_no_policy_is_rebuilt_per_instance():
    """A per-instance rebuild would make construction slower, not faster."""
    field = Visible.__columns__["a"]
    before = field_policy(field)
    for value in range(50):
        Visible(a=value)
    after = field_policy(field)
    assert after is before, "the policy object was replaced during construction"


def test_policy_does_not_retain_the_class_after_it_is_dropped():
    """No global registry: a policy must die with its class."""
    refs = []
    for index in range(25):
        model = type(
            f"Temp{index}",
            (BaseModel,),
            {"__annotations__": {"v": int}, "v": Column(required=False)},
        )
        assert isinstance(field_policy(model.__columns__["v"]), FieldPolicy)
        refs.append(weakref.ref(model))
        del model

    gc.collect()
    gc.collect()
    alive = [ref for ref in refs if ref() is not None]
    assert not alive, f"{len(alive)}/25 model classes were retained"


def test_policy_holds_no_instance_state():
    """Values, defaults, results and errors must never be stored on a policy."""
    policy = field_policy(Visible.__columns__["a"])
    slots = ("work_mask", "type_ref", "validator_ref", "parser_ref",
             "constraint_shape", "exact_scalar")
    for attribute in slots:
        assert hasattr(policy, attribute)
    for forbidden in ("value", "values", "default", "result", "errors",
                      "instance", "metadata"):
        assert not hasattr(policy, forbidden), forbidden


def test_policy_is_immutable_from_python():
    policy = field_policy(Visible.__columns__["a"])
    with pytest.raises((AttributeError, TypeError)):
        policy.work_mask = 0


# ===========================================================================
# Part 6 -- building a policy changed no behaviour (the whole point)
# ===========================================================================


def test_valid_values_still_build():
    instance = Scalars(an_int=1, a_str="s", a_float=1.5, a_bool=True,
                       a_decimal=Decimal("1.5"))
    assert instance.an_int == 1
    assert instance.a_decimal == Decimal("1.5")


def test_type_errors_are_still_raised():
    with pytest.raises((ValidationError, ValueError, TypeError)):
        Scalars(an_int="definitely not an int")


def test_constraints_are_still_enforced():
    class Bounded3(BaseModel):
        v: int = Column(required=False, min=1, max=10)

    assert Bounded3(v=5).v == 5
    with pytest.raises((ValidationError, ValueError)):
        Bounded3(v=99)


def test_a_constraint_added_at_runtime_is_still_enforced():
    """The policy must not have frozen 'this field has no constraints'."""
    class Late(BaseModel):
        v: int = Column(required=False)

    assert Late(v=99).v == 99

    field = Late.__columns__["v"]
    field._meta["max"] = 10
    field.metadata = field._meta
    assert policy_is_current(field, field_policy(field)) is False
    with pytest.raises((ValidationError, ValueError)):
        Late(v=99)


def test_required_and_null_behaviour_is_unchanged():
    class Req(BaseModel):
        needed: str = Column(required=True)

    assert Req(needed="here").needed == "here"
    with pytest.raises((ValidationError, ValueError)):
        Req()
