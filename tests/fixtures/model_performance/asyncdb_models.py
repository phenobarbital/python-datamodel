"""Real ``asyncdb.models`` consumer fixtures for FEAT-2 (TASK-10).

Spec §8 records the user's resolved requirement verbatim: *"schema examples in
examples/ folder and asyncdb.models (that uses under-the-hood python-datamodel)
requires strict compat."*  This module supplies the ``asyncdb`` half.

What makes this corpus meaningful
=================================

Every model below subclasses the **real** :class:`asyncdb.models.Model` from
the pinned distribution recorded in :mod:`asyncdb_manifest.json`.  Nothing here
re-implements or fakes it: a stand-in would only prove that *our* stand-in is
stable, which is not the compatibility question.  ``asyncdb.models.Model``
derives from ``datamodel.BaseModel`` and additionally reaches into
``datamodel.types.MODEL_TYPES``/``DB_TYPES`` and ``datamodel.abstract.Meta`` --
so it exercises a *wider* public surface than ``BaseModel`` alone, which is
exactly why it is the load-bearing consumer for this feature.

The driver boundary
===================

``Model``'s database methods (``insert``/``update``/``select``/...) are all
``async`` and require a live connection, so they are **out of scope** here: the
task forbids production database access.  What is in scope is everything
reachable without I/O, which is where a compatibility break would actually bite:

* construction / hydration from raw (all-string) and already-typed rows,
* type coercion, defaults, required and null handling,
* primary keys, ``db_type`` metadata and ``Model.model()`` DDL rendering,
* nested relations, aliases, assignment, ``to_dict()`` and ``json()``,
* the error type, message and payload for malformed rows.

``set_connection()`` is exercised against an inert stub object so the
connection *slot* is covered without opening a socket.  ``get_connection()``
is deliberately not called: it imports a driver module and would build a real
client.

Availability is a hard gate, not a skip
=======================================

If the pinned distribution is missing, :data:`ASYNCDB_AVAILABLE` is ``False``
and :data:`ASYNCDB_IMPORT_ERROR` records why.  ``test_asyncdb_models.py`` turns
that into a **failure** of the required integration gate -- per the task, a
missing dependency must never be able to report success.

Determinism
===========

No clock, randomness, filesystem, network or database access happens while a
case is built.  Timestamps and UUIDs are frozen constants shared with the main
corpus, so a row built in the reference process is byte-identical to the same
row built in the candidate process.
"""
# NOTE: deliberately no ``from __future__ import annotations``.
# Under PEP 563 every annotation becomes a string, and datamodel
# resolves ``field.type`` as a real object -- model definition then
# fails with "Expected type, got str". ``models.py`` omits it for the
# same reason; ``test_asyncdb_models.py`` pins this so it cannot be
# reintroduced by a well-meaning cleanup.

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

# --- frozen inputs (shared vocabulary with the main corpus) ----------------

FROZEN_NOW = datetime(2024, 3, 17, 12, 30, 45)
FROZEN_DATE = date(2024, 3, 17)
FROZEN_UUID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

#: Populated on a successful import; consumed by the manifest test so the
#: recorded pin and the module actually in use can never drift apart.
ASYNCDB_VERSION: Optional[str] = None
ASYNCDB_FILE: Optional[str] = None
ASYNCDB_IMPORT_ERROR: Optional[str] = None

try:  # pragma: no cover - the failure path is asserted by the gate test
    import asyncdb as _asyncdb
    from asyncdb.models import Column, Field, Model, is_missing  # noqa: F401
    from datamodel.types import DB_TYPES  # noqa: F401  (asyncdb mutates this)

    ASYNCDB_AVAILABLE = True
    ASYNCDB_VERSION = getattr(_asyncdb, "__version__", None)
    ASYNCDB_FILE = getattr(_asyncdb, "__file__", None)
except Exception as exc:  # noqa: BLE001 - any import failure must be recorded
    ASYNCDB_AVAILABLE = False
    ASYNCDB_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    Model = object  # type: ignore[assignment,misc]


ALL_MODELS: Tuple[str, ...] = (
    "DbUser",
    "DbEmployee",
    "DbDepartment",
    "DbStaffing",
    "DbAliasedRow",
    "DbPresence",
)


if ASYNCDB_AVAILABLE:

    class DbUser(Model):
        """The plainest possible table model: scalars, a PK and defaults."""

        user_id: int = Column(primary_key=True, required=True, db_type="integer")
        name: str = Column(required=True, db_type="varchar")
        email: str = Column(required=False, default="n/a", db_type="varchar")
        active: bool = Column(required=False, default=True, db_type="boolean")

        class Meta:
            name = "users"
            schema = "public"
            strict = True

    class DbEmployee(Model):
        """Wider row: temporal, numeric-precision and bounded columns.

        The ``hire_date``/``created_at`` columns are the interesting ones: they
        are the string->date/datetime conversions that route through
        ``converters.pyx`` and the ``rs_parsers`` backend, i.e. the code path
        most likely to change under this feature.
        """

        employee_id: str = Column(primary_key=True, required=True, db_type="uuid")
        first_name: str = Column(required=True, db_type="varchar")
        last_name: str = Column(required=True, db_type="varchar")
        age: int = Column(required=False, min=18, max=99, db_type="integer")
        salary: Decimal = Column(required=False, db_type="numeric")
        hire_date: date = Column(required=False, db_type="date")
        created_at: datetime = Column(required=False, db_type="timestamp")
        tags: List[str] = Column(required=False, default_factory=list)

        class Meta:
            name = "employees"
            schema = "hr"
            strict = True

    class DbDepartment(Model):
        department_id: int = Column(primary_key=True, required=True, db_type="integer")
        title: str = Column(required=True, db_type="varchar")

        class Meta:
            name = "departments"
            schema = "hr"
            strict = True

    class DbStaffing(Model):
        """Nested relation: a model-typed column hydrated from a plain dict."""

        staffing_id: int = Column(primary_key=True, required=True, db_type="integer")
        department: DbDepartment = Column(required=False)
        headcount: int = Column(required=False, default=0, db_type="integer")

        class Meta:
            name = "staffing"
            schema = "hr"
            strict = True
            as_objects = True

    class DbAliasedRow(Model):
        """A column whose wire name differs from its attribute name."""

        row_id: int = Column(primary_key=True, required=True, db_type="integer")
        label: str = Column(required=False, alias="lbl", db_type="varchar")

        class Meta:
            name = "aliased"
            schema = "public"
            strict = True

    class DbPresence(Model):
        """Required / nullable / default interactions."""

        pk: int = Column(primary_key=True, required=True, db_type="integer")
        must_be_present: str = Column(required=True, db_type="varchar")
        nullable_column: Optional[str] = Column(
            required=False, nullable=True, default=None, db_type="varchar"
        )
        defaulted: int = Column(required=False, default=7, db_type="integer")

        class Meta:
            name = "presence"
            schema = "public"
            strict = True


class StubConnection:
    """An inert stand-in for a driver connection.

    ``set_connection()`` only stores the object on ``Meta``; nothing here is
    awaited or dialled, so the connection *slot* is covered with no I/O. This
    fakes the **driver boundary**, never ``asyncdb.models.Model`` itself.
    """

    __slots__ = ("closed",)

    def __init__(self) -> None:
        self.closed = False

    def __repr__(self) -> str:
        return "<StubConnection>"


EXPECT_OK = "ok"
EXPECT_ERROR = "error"


@dataclass(frozen=True)
class AsyncDBCase:
    """One observed asyncdb-consumer behaviour."""

    name: str
    model_name: str
    build: Callable[[], Dict[str, Any]]
    expect: str = EXPECT_OK
    tags: Tuple[str, ...] = ()
    notes: str = ""
    #: True when the row parses a date/datetime **from a string**, which needs
    #: the ``rs_parsers`` extension present (see the main corpus for the gap).
    requires_rust_parsers: bool = False

    def resolve_model(self) -> type:
        """Resolve by *name*, never by captured class object.

        The child process imports this module under whichever ``datamodel``
        build it is testing, so a class captured at definition time would
        belong to the wrong build.
        """
        return globals()[self.model_name]


# ---------------------------------------------------------------------------
# Row builders.  Each returns brand-new mutables on every call.
# ---------------------------------------------------------------------------


def _user_raw() -> Dict[str, Any]:
    """All-string row, as a DB driver hands back untyped text."""
    return {"user_id": "42", "name": "Ada Lovelace", "email": "ada@example.org",
            "active": "true"}


def _user_native() -> Dict[str, Any]:
    """Already-typed row, as a typed driver hands back."""
    return {"user_id": 42, "name": "Ada Lovelace", "email": "ada@example.org",
            "active": True}


def _user_defaults() -> Dict[str, Any]:
    """Only the required columns: defaults must fill the rest."""
    return {"user_id": 7, "name": "Grace Hopper"}


def _user_missing_required() -> Dict[str, Any]:
    return {"email": "nobody@example.org"}


def _user_bad_type() -> Dict[str, Any]:
    return {"user_id": "not-an-integer", "name": "Broken Row"}


def _employee_raw() -> Dict[str, Any]:
    return {
        "employee_id": FROZEN_UUID,
        "first_name": "Alan",
        "last_name": "Turing",
        "age": "41",
        "salary": "12345.67",
        "hire_date": "2024-03-17",
        "created_at": "2024-03-17T12:30:45",
        "tags": ["research", "logic"],
    }


def _employee_native() -> Dict[str, Any]:
    return {
        "employee_id": FROZEN_UUID,
        "first_name": "Alan",
        "last_name": "Turing",
        "age": 41,
        "salary": Decimal("12345.67"),
        "hire_date": FROZEN_DATE,
        "created_at": FROZEN_NOW,
        "tags": ["research", "logic"],
    }


def _employee_below_min_age() -> Dict[str, Any]:
    return {
        "employee_id": FROZEN_UUID,
        "first_name": "Too",
        "last_name": "Young",
        "age": 7,
    }


def _employee_partial() -> Dict[str, Any]:
    """Optional columns omitted entirely -- the common SELECT-subset shape."""
    return {"employee_id": FROZEN_UUID, "first_name": "Ada", "last_name": "Byron"}


def _department_native() -> Dict[str, Any]:
    return {"department_id": 3, "title": "Research"}


def _staffing_nested_dict() -> Dict[str, Any]:
    return {
        "staffing_id": 100,
        "department": {"department_id": 3, "title": "Research"},
        "headcount": 12,
    }


def _staffing_nested_missing() -> Dict[str, Any]:
    return {"staffing_id": 101}


def _aliased_by_attribute() -> Dict[str, Any]:
    return {"row_id": 1, "label": "by-attribute"}


def _aliased_by_alias() -> Dict[str, Any]:
    return {"row_id": 2, "lbl": "by-alias"}


def _presence_full() -> Dict[str, Any]:
    return {"pk": 1, "must_be_present": "here", "nullable_column": "value",
            "defaulted": 99}


def _presence_defaults() -> Dict[str, Any]:
    return {"pk": 2, "must_be_present": "here"}


def _presence_explicit_none() -> Dict[str, Any]:
    return {"pk": 3, "must_be_present": "here", "nullable_column": None}


def _presence_missing_required() -> Dict[str, Any]:
    return {"pk": 4}


CASES: Tuple[AsyncDBCase, ...] = (
    AsyncDBCase("db_user_raw", "DbUser", _user_raw, tags=("scalar", "raw"),
                notes="untyped driver row; every value arrives as str"),
    AsyncDBCase("db_user_native", "DbUser", _user_native, tags=("scalar", "native"),
                notes="typed driver row"),
    AsyncDBCase("db_user_defaults", "DbUser", _user_defaults, tags=("default",),
                notes="omitted optional columns fall back to defaults"),
    AsyncDBCase("db_user_missing_required", "DbUser", _user_missing_required,
                expect=EXPECT_ERROR, tags=("error", "required"),
                notes="both required columns absent"),
    AsyncDBCase("db_user_bad_type", "DbUser", _user_bad_type,
                expect=EXPECT_ERROR, tags=("error", "coercion"),
                notes="uncoercible primary key"),
    AsyncDBCase("db_employee_raw", "DbEmployee", _employee_raw,
                tags=("wide", "raw", "temporal"), requires_rust_parsers=True,
                notes="string date/datetime conversion via converters.pyx"),
    AsyncDBCase("db_employee_native", "DbEmployee", _employee_native,
                tags=("wide", "native", "temporal")),
    AsyncDBCase("db_employee_below_min_age", "DbEmployee", _employee_below_min_age,
                expect=EXPECT_ERROR, tags=("error", "constraint", "characterization"),
                notes="VERIFIED against the reference build: min= IS enforced on "
                      "an int column and raises ValidationError. Note the "
                      "contrast with the main corpus, where min/max on a *str* "
                      "field are silently ignored -- so 'constraints are not "
                      "enforced' is false in general and must not be "
                      "generalised from the str case."),
    AsyncDBCase("db_employee_partial", "DbEmployee", _employee_partial,
                tags=("default", "partial")),
    AsyncDBCase("db_department", "DbDepartment", _department_native, tags=("scalar",)),
    AsyncDBCase("db_staffing_nested", "DbStaffing", _staffing_nested_dict,
                tags=("nested", "as_objects"),
                notes="dict hydrated into a nested Model under as_objects"),
    AsyncDBCase("db_staffing_nested_missing", "DbStaffing", _staffing_nested_missing,
                tags=("nested", "default")),
    AsyncDBCase("db_aliased_by_attribute", "DbAliasedRow", _aliased_by_attribute,
                tags=("alias",)),
    AsyncDBCase("db_aliased_by_alias", "DbAliasedRow", _aliased_by_alias,
                tags=("alias",),
                notes="supplied under the wire alias rather than the attribute"),
    AsyncDBCase("db_presence_full", "DbPresence", _presence_full, tags=("presence",)),
    AsyncDBCase("db_presence_defaults", "DbPresence", _presence_defaults,
                tags=("presence", "default")),
    AsyncDBCase("db_presence_explicit_none", "DbPresence", _presence_explicit_none,
                tags=("presence", "null"),
                notes="explicit None for a nullable column"),
    AsyncDBCase("db_presence_missing_required", "DbPresence",
                _presence_missing_required, expect=EXPECT_ERROR,
                tags=("error", "required")),
)

CASES_BY_NAME: Dict[str, AsyncDBCase] = {case.name: case for case in CASES}


def case_names() -> Tuple[str, ...]:
    return tuple(case.name for case in CASES)


def cases_with_tag(tag: str) -> Tuple[AsyncDBCase, ...]:
    return tuple(case for case in CASES if tag in case.tags)


__all__ = (
    "ALL_MODELS",
    "ASYNCDB_AVAILABLE",
    "ASYNCDB_FILE",
    "ASYNCDB_IMPORT_ERROR",
    "ASYNCDB_VERSION",
    "CASES",
    "CASES_BY_NAME",
    "EXPECT_ERROR",
    "EXPECT_OK",
    "FROZEN_DATE",
    "FROZEN_NOW",
    "FROZEN_UUID",
    "AsyncDBCase",
    "StubConnection",
    "case_names",
    "cases_with_tag",
)
