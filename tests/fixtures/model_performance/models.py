"""Model declarations for the FEAT-2 compatibility corpus.

Every model here is a faithful adaptation of an existing, verified schema in
this repository.  Provenance is recorded in ``PROVENANCE`` and asserted by
``tests/compatibility/test_fixture_corpus.py`` so a future edit cannot quietly
drift away from the shape whose behaviour we are pinning.

Nothing in this module executes at import time beyond class creation: the
adapted examples were rewritten instead of imported precisely because several
``examples/*.py`` modules run benchmarks, build models and print at module
scope (see ``examples_manifest.json``).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from datamodel import BaseModel, Column, Field

# ---------------------------------------------------------------------------
# Frozen values.  Nothing in the corpus may call ``datetime.now()``,
# ``uuid.uuid4()`` or any other nondeterministic factory while a case is built.
# ---------------------------------------------------------------------------

FROZEN_NOW = datetime(2026, 9, 8, 10, 30, 0)
FROZEN_TODAY = date(2026, 9, 8)
FROZEN_UUID = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")


def frozen_now() -> datetime:
    """Deterministic stand-in for ``datetime.now`` used as a field default."""
    return FROZEN_NOW


def frozen_today() -> date:
    """Deterministic stand-in for ``date.today`` used as a field default."""
    return FROZEN_TODAY


# ---------------------------------------------------------------------------
# 1. Employee -- verbatim port of examples/rust_benchmark.py:35-51
# ---------------------------------------------------------------------------


class Employee(BaseModel):
    """The proposal's benchmark model, ported field-for-field.

    Adapted from ``examples/rust_benchmark.py:35-51``.  All eleven
    declarations, their defaults and the ``age`` bounds are preserved exactly;
    only the surrounding benchmark driver was left behind.
    """

    employee_id: uuid.UUID = Column(required=True, primary_key=True)
    name: str = Column(required=True)
    email: str = Column(required=False, default='')
    age: int = Column(required=True, min=18, max=99)
    salary: Decimal = Column(required=True)
    rating: float = Column(default=0.0)
    active: bool = Column(default=True)
    hired_at: date = Column(required=True)
    updated_at: datetime = Column(required=False)
    skills: List[str] = Column(default_factory=list)
    manager: Optional[str] = Column(required=False, default=None)


# ---------------------------------------------------------------------------
# 2. Scalar models -- the AC3 dispatch-count fixtures
# ---------------------------------------------------------------------------


class UnconstrainedScalars(BaseModel):
    """Supported scalars with *no* constraints and no custom callbacks.

    This is the fixture AC3 requires to reach **zero** generic ``_validation_``
    dispatches once the gate lands.  Keep it free of ``min``/``max``/
    ``pattern``/``validator`` and of container or union annotations.
    """

    an_int: int = Column(required=True)
    a_str: str = Column(required=True)
    a_float: float = Column(required=True)
    a_bool: bool = Column(required=True)
    a_decimal: Decimal = Column(required=True)
    a_uuid: uuid.UUID = Column(required=True)
    a_date: date = Column(required=True)
    a_datetime: datetime = Column(required=True)


class ConstrainedScalars(BaseModel):
    """Every legacy constraint source that ``_validate_constraints`` executes.

    Bounds are **inclusive** in ``datamodel/validation.pyx:427,437`` even though
    the message reads "greater than"/"less than"; the corpus pins the
    predicate and the message together.

    ``sized_str`` is deliberately declared with ``min``/``max`` even though the
    reference build **ignores** them for ``str`` (verified: ``"a"`` and a
    21-character value both construct successfully).  Spec §1 lists "making
    previously ignored constraints active" as an explicit non-goal, so this
    field pins the *ignoring* -- a gate that starts enforcing string length
    here would be a behaviour change, not a fix.
    """

    bounded_int: int = Column(required=True, min=18, max=99)
    bounded_float: float = Column(required=True, min=0.0, max=10.0)
    bounded_decimal: Decimal = Column(required=True, min=Decimal("0"), max=Decimal("1000"))
    sized_str: str = Column(required=True, min=2, max=12)
    patterned_str: str = Column(required=True, pattern=r"^[A-Z]{2}-\d{4}$")


# ---------------------------------------------------------------------------
# 3. Wide model -- 50 fields
# ---------------------------------------------------------------------------


def _wide_annotations() -> Dict[str, Any]:
    """Build the 50 field declarations of :class:`WideModel`.

    The rotation is deliberate and stable: ten repetitions of the same
    five-type cycle, so per-field costs stay comparable across runs while the
    model still exercises more than one converter.
    """
    annotations: Dict[str, Any] = {}
    namespace: Dict[str, Any] = {}
    cycle = (
        ("int_", int, 0),
        ("str_", str, ''),
        ("float_", float, 0.0),
        ("bool_", bool, False),
        ("dec_", Decimal, Decimal("0")),
    )
    for index in range(10):
        for prefix, kind, default in cycle:
            name = f"{prefix}{index}"
            annotations[name] = kind
            namespace[name] = Column(required=False, default=default)
    return annotations, namespace


_WIDE_ANNOTATIONS, _WIDE_NAMESPACE = _wide_annotations()

WideModel = type(
    "WideModel",
    (BaseModel,),
    {
        "__doc__": "A 50-field model used to measure per-field scaling.",
        "__annotations__": _WIDE_ANNOTATIONS,
        "__module__": __name__,
        **_WIDE_NAMESPACE,
    },
)

WIDE_FIELD_NAMES: Tuple[str, ...] = tuple(_WIDE_ANNOTATIONS)


# ---------------------------------------------------------------------------
# 4. Nested / ORM-like relationships -- adapted from tests/test_converter.py:6-24
# ---------------------------------------------------------------------------


class Organization(BaseModel):
    """Adapted from ``tests/test_converter.py:6-12``."""

    org_id: int = Field(primary_key=True)
    name: str

    class Meta:
        strict = True


class Client(BaseModel):
    """Adapted from ``tests/test_converter.py:14-24``.

    Keeps the ``alias="org_id"`` on a *model-typed* field together with
    ``as_objects = True``, which is the ORM-hydration shape asyncdb relies on.
    """

    client_id: int = Field(primary_key=True)
    client_name: str
    status: bool = Field(required=True)
    orgid: Organization = Field(required=False, alias="org_id")
    org_name: str = Field(required=False)

    class Meta:
        name: str = 'clients'
        strict: bool = True
        as_objects: bool = True


class Address(BaseModel):
    """Small nested value object."""

    street: str = Column(required=True)
    zipcode: int = Column(required=False, default=0)


class Account(BaseModel):
    """Nested model reached through a typed container."""

    provider: str = Column(required=True, default='dummy')
    address: Optional[Address] = Column(required=False, default=None)


class BigContainer(BaseModel):
    """Typed containers: list/dict/tuple/mapping/union of nested models."""

    name: str = Column(required=True)
    addresses: List[Address] = Column(required=False, default_factory=list)
    accounts: List[Account] = Column(required=False, default_factory=list)
    tags: List[str] = Column(required=False, default_factory=list)
    attributes: Dict[str, Any] = Column(required=False, default_factory=dict)
    directives: Tuple[float, float] = Column(required=False)
    supported: Tuple[float, ...] = Column(required=False)
    example: Mapping[str, Union[str, int]] = Column(required=False)


# ---------------------------------------------------------------------------
# 5. Aliases -- model-level and field-level
# ---------------------------------------------------------------------------


class AliasedRecord(BaseModel):
    """Alias resolution happens in ``ModelMeta.__call__`` before ``__init__``."""

    record_id: int = Column(required=True, primary_key=True, alias="id")
    display_name: str = Column(required=True, alias="displayName")
    plain: str = Column(required=False, default='')


# ---------------------------------------------------------------------------
# 6. Presence rules -- required / primary / nullable / db_default / defaults
# ---------------------------------------------------------------------------


class PresenceRules(BaseModel):
    """Pins ``_field_checks_`` behaviour (``converters.pyx:2372``).

    Two verified asymmetries live here and must survive any gate:

    * ``0``/``False``/``[]`` are **values**, not absences, and construct fine.
    * ``not_nullable`` (``nullable=False``) rejects the *empty string* with
      ``ValueError: :: *not_nullable* Cannot be null.`` but silently falls back
      to its default when given an explicit ``None``.  That asymmetry is the
      reference behaviour; the corpus pins it rather than tidying it up.
    """

    pk: int = Column(required=True, primary_key=True)
    required_str: str = Column(required=True)
    nullable_str: Optional[str] = Column(required=False, nullable=True, default=None)
    not_nullable: str = Column(required=False, nullable=False, default='x')
    zero_int: int = Column(required=False, default=0)
    false_bool: bool = Column(required=False, default=False)
    empty_str: str = Column(required=False, default='')
    empty_list: List[str] = Column(required=False, default_factory=list)
    with_db_default: datetime = Column(required=False, db_default='now()', default=frozen_now)


# ---------------------------------------------------------------------------
# 7. Custom callbacks -- cached f.validator vs. metadata callback
# ---------------------------------------------------------------------------

#: Append-only log of callback invocations.  A case that observes callbacks
#: must reset this first; ``cases.py`` does so through ``reset_hook_events``.
hook_events: List[Tuple[str, Any]] = []


def reset_hook_events() -> None:
    """Clear the shared callback log between independent cases."""
    del hook_events[:]


def no_empty_tag(field: Any, value: Any, annotated_type: Any, val_type: Any) -> bool:
    """A user validator on a *container* field, which really is invoked.

    ``validation.pyx:488`` calls ``fn(F, value, annotated_type, val_type)`` and
    treats a literal ``False`` return as a failure.  It is only reached when
    ``f.validator`` is ``None`` -- i.e. for types absent from
    ``validation.validators`` -- which is why this sits on ``List[str]``.
    """
    hook_events.append(("no_empty_tag", list(value) if value is not None else value))
    if value is None:
        return True
    return all(item != "" for item in value)


def never_called_validator(field: Any, value: Any, annotated_type: Any,
                           val_type: Any) -> bool:
    """A user validator on a **primitive**, which the reference never invokes.

    ``abstract.py:257`` caches ``validators[int]`` into ``f.validator``, and
    ``converters.pyx:2354`` takes that branch instead of ``_validation``.  The
    metadata callback is therefore dead code for ``int``/``str``/``float`` and
    friends.  Pinning it stops a "unified callback" refactor from quietly
    starting to call it.
    """
    hook_events.append(("never_called_validator", value))
    return False


def scaling_encoder(value: Any) -> Any:
    """A user encoder on a ``float`` field, which really is invoked.

    ``parse_basic`` (``converters.pyx:964``) consults ``encoder`` only after its
    ``str``/``int``/``bytes``/``UUID``/``bool`` short-circuits, so ``float`` is
    one of the types that actually reaches it.
    """
    hook_events.append(("scaling_encoder", value))
    return float(value) * 2


def never_called_encoder(value: Any) -> Any:
    """A user encoder on a ``str`` field, which the reference never invokes.

    ``parse_basic`` returns early for ``str`` before the encoder branch.
    """
    hook_events.append(("never_called_encoder", value))
    return str(value).upper()


class CallbackModel(BaseModel):
    """Both callback routes, plus both dead-callback quirks, side by side.

    ``converters.pyx:2354`` routes the cached primitive validator separately
    from ``validation.pyx:488``'s metadata callback; spec §2 rule 7 forbids
    merging them.  Every field below was verified against the reference build:
    the two ``live_*`` fields do invoke their callback, the two ``dead_*``
    fields do not.
    """

    live_tags: List[str] = Column(required=False, default_factory=list,
                                  validator=no_empty_tag)
    live_scaled: float = Column(required=False, default=0.0,
                                encoder=scaling_encoder)
    dead_validator: int = Column(required=False, default=0,
                                 validator=never_called_validator)
    dead_encoder: str = Column(required=False, default='',
                               encoder=never_called_encoder)
    untouched: int = Column(required=False, default=1)


class CallableModel(BaseModel):
    """Adapted from ``tests/test_valid_callables.py:8-10``."""

    callback: Callable[[int], str] = Field(required=True)
    async_result: Awaitable[int] = Field(required=True)


# ---------------------------------------------------------------------------
# 8. Descriptors and model hooks
# ---------------------------------------------------------------------------


class IntConversionDescriptor:
    """Adapted from ``tests/test_descriptors.py:6-20``."""

    def __init__(self, *, default):
        self._default = default

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, int(value))


class StringTrimDescriptor:
    """Adapted from ``tests/test_descriptors.py:23-36``."""

    def __init__(self, *, default=""):
        self._default = default

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, value.strip() if isinstance(value, str) else value)


class DescriptorModel(BaseModel):
    """Descriptor-typed attributes must always take the legacy path."""

    quantity_on_hand: IntConversionDescriptor = IntConversionDescriptor(default=100)
    description: StringTrimDescriptor = StringTrimDescriptor(default="No description")


class HookModel(BaseModel):
    """A model whose ``__post_init__`` extends the base implementation.

    Adapted from the ``super().__post_init__()`` pattern in
    ``examples/test_datadriver.py:8-45`` without that module's top-level code.
    """

    name: str = Column(required=True)
    normalized: str = Column(required=False, default='')

    def __post_init__(self) -> None:
        hook_events.append(("pre_post_init", self.name))
        super(HookModel, self).__post_init__()
        self.normalized = self.name.strip().lower()
        hook_events.append(("post_post_init", self.normalized))


# ---------------------------------------------------------------------------
# 9. Native / type-system boundaries
# ---------------------------------------------------------------------------


class Boundaries(BaseModel):
    """The compatibility boundaries listed in spec §2 (Rust experiments).

    ``bool`` is an ``int`` subclass and ``validation.pyx:28`` accepts it, so a
    fast path narrowing that acceptance is a regression.

    Two boundaries were verified to *reject* in the reference build, and the
    corpus records the rejection rather than the spec's optimistic reading:

    * a ``date`` supplied to a ``datetime`` field raises
      ``Error parsing *a_datetime* ... argument must be str`` -- the
      ``validation.pyx:59`` leniency applies to the validator, which conversion
      never reaches;
    * a ``str`` *subclass* supplied to a ``str`` field raises
      ``Expected str, got <Subclass>``.

    Both are pinned as EXPECT_ERROR cases in ``cases.py``.
    """

    big_int: int = Column(required=False, default=0)
    small_int: int = Column(required=False, default=0)
    precise_decimal: Decimal = Column(required=False, default=Decimal("0"))
    unicode_text: str = Column(required=False, default='')
    raw_bytes: bytes = Column(required=False, default=b'')
    a_datetime: datetime = Column(required=False, default=frozen_now)
    an_id: uuid.UUID = Column(required=False, default=None)


class StrSubclass(str):
    """A ``str`` subclass with an observable ``__eq__``."""

    comparisons: List[Any] = []

    def __eq__(self, other):  # pragma: no cover - exercised through models
        type(self).comparisons.append(other)
        return str.__eq__(self, other)

    def __ne__(self, other):  # pragma: no cover - exercised through models
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    __hash__ = str.__hash__


class IntSubclass(int):
    """An ``int`` subclass; ``validation.pyx:28`` must keep accepting it."""


# ---------------------------------------------------------------------------
# Registry + provenance
# ---------------------------------------------------------------------------

ALL_MODELS: Tuple[type, ...] = (
    Employee,
    UnconstrainedScalars,
    ConstrainedScalars,
    WideModel,
    Organization,
    Client,
    Address,
    Account,
    BigContainer,
    AliasedRecord,
    PresenceRules,
    CallbackModel,
    CallableModel,
    DescriptorModel,
    HookModel,
    Boundaries,
)

#: model name -> source location it was adapted from.
PROVENANCE: Dict[str, str] = {
    "Employee": "examples/rust_benchmark.py:35-51",
    "UnconstrainedScalars": "new (spec AC3 zero-dispatch fixture)",
    "ConstrainedScalars": "new (datamodel/validation.pyx:307-460 constraint sources)",
    "WideModel": "new (spec §4 '50-field models')",
    "Organization": "tests/test_converter.py:6-12",
    "Client": "tests/test_converter.py:14-24",
    "Address": "new (nested value object)",
    "Account": "new (nested model behind a container)",
    "BigContainer": "examples/test_qsmodel.py:38-68 (container/tuple/mapping shapes)",
    "AliasedRecord": "new (datamodel/abstract.py:516 alias-before-constructor)",
    "PresenceRules": "new (datamodel/converters.pyx:2372 _field_checks_)",
    "CallbackModel": "new (converters.pyx:2354 vs validation.pyx:488 routes)",
    "CallableModel": "tests/test_valid_callables.py:8-10",
    "DescriptorModel": "tests/test_descriptors.py:6-42",
    "HookModel": "examples/test_datadriver.py:8-45 (super().__post_init__ pattern)",
    "Boundaries": "new (spec §2 native compatibility boundaries)",
}

#: The exact Employee declaration ported above, pinned so a drift is caught.
EMPLOYEE_FIELD_SPEC: Tuple[Tuple[str, str], ...] = (
    ("employee_id", "UUID"),
    ("name", "str"),
    ("email", "str"),
    ("age", "int"),
    ("salary", "Decimal"),
    ("rating", "float"),
    ("active", "bool"),
    ("hired_at", "date"),
    ("updated_at", "datetime"),
    ("skills", "List[str]"),
    ("manager", "Optional[str]"),
)
