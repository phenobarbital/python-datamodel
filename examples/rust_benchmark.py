"""Benchmark: building a python-datamodel dataclass-like model 100 times.

Instantiates a `BaseModel` subclass N times from raw (string) input so the
type-coercion pipeline — now backed by the Rust `rs_parsers` extension — is
exercised on every field, and reports the elapsed time.

Run with::

    python examples/rust_benchmark.py [iterations]
"""
import sys
import uuid
from dataclasses import dataclass, fields as dc_fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from statistics import mean, median
from time import perf_counter_ns
from typing import List, Optional

import datamodel.rs_parsers as rc
from datamodel import BaseModel, Column

try:
    import pydantic
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic.dataclasses import dataclass as pydantic_dataclass

    HAS_PYDANTIC = True
except ImportError:  # pragma: no cover - optional comparison
    HAS_PYDANTIC = False


ITERATIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
NS_PER_MS = 1_000_000


class Employee(BaseModel):
    """A simple dataclass-like model covering the common converters."""

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


@dataclass
class PlainEmployee:
    """stdlib dataclass baseline: no validation, no type coercion."""

    employee_id: uuid.UUID
    name: str
    email: str
    age: int
    salary: Decimal
    rating: float
    active: bool
    hired_at: date
    updated_at: datetime
    skills: List[str]
    manager: Optional[str] = None


if HAS_PYDANTIC:

    class PydanticEmployee(PydanticBaseModel):
        """pydantic BaseModel: validates + coerces, but is NOT a dataclass."""

        employee_id: uuid.UUID
        name: str
        email: str = ''
        age: int = pydantic.Field(ge=18, le=99)
        salary: Decimal
        rating: float = 0.0
        active: bool = True
        hired_at: date
        updated_at: datetime
        skills: List[str] = pydantic.Field(default_factory=list)
        manager: Optional[str] = None

    @pydantic_dataclass
    class PydanticDCEmployee:
        """pydantic's dataclass flavour: real dataclass, validated fields."""

        employee_id: uuid.UUID
        name: str
        age: int
        salary: Decimal
        hired_at: date
        updated_at: datetime
        skills: List[str]
        email: str = ''
        rating: float = 0.0
        active: bool = True
        manager: Optional[str] = None


# Raw payload: every value arrives as a string, exactly as it would from
# JSON, a CSV row or a database driver without native types.
PAYLOAD = {
    "employee_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Jesus Lara",
    "email": "jesuslara@jesuslara.com",
    "age": "42",
    "salary": "85000.50",
    "rating": "4.75",
    "active": "true",
    "hired_at": "2020-03-15",
    "updated_at": "2026-09-08T10:30:00",
    "skills": ["python", "rust", "cython"],
    "manager": "Ada Lovelace",
}

# Same data, pre-converted: what the stdlib dataclass needs to receive.
NATIVE_PAYLOAD = {
    "employee_id": uuid.UUID(PAYLOAD["employee_id"]),
    "name": PAYLOAD["name"],
    "email": PAYLOAD["email"],
    "age": 42,
    "salary": Decimal("85000.50"),
    "rating": 4.75,
    "active": True,
    "hired_at": date(2020, 3, 15),
    "updated_at": datetime(2026, 9, 8, 10, 30),
    "skills": PAYLOAD["skills"],
    "manager": PAYLOAD["manager"],
}


def timeit(label: str, factory, iterations: int = ITERATIONS) -> dict:
    """Run `factory` `iterations` times, returning per-call timings in ms."""
    samples = []
    for _ in range(iterations):
        start = perf_counter_ns()
        factory()
        samples.append((perf_counter_ns() - start) / NS_PER_MS)
    total = sum(samples)
    return {
        "label": label,
        "iterations": iterations,
        "total_ms": total,
        "avg_ms": mean(samples),
        "median_ms": median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
        "first_ms": samples[0],
        "ops_per_sec": iterations / (total / 1000) if total else float('inf'),
    }


def report(result: dict) -> None:
    # A first call that dwarfs the median is lazy-import / warm-up cost, not
    # the steady-state price of the operation: mark it so avg is read with care.
    warm = " *" if result['first_ms'] > 10 * result['median_ms'] else ""
    print(
        f"{result['label']:<34}"
        f"{result['total_ms']:>10.3f}"
        f"{result['avg_ms']:>11.4f}"
        f"{result['median_ms']:>11.4f}"
        f"{result['min_ms']:>10.4f}"
        f"{result['max_ms']:>10.4f}"
        f"{result['ops_per_sec']:>14,.0f}"
        f"{warm}"
    )


FOOTNOTE = "  * first call dominated by one-time warm-up — read the median column."


def main() -> int:
    print("=" * 100)
    print("python-datamodel — model construction benchmark")
    print("=" * 100)
    print(f"Python           : {sys.version.split()[0]}")
    print(f"Rust rs_parsers  : {'ENABLED' if rc.HAS_RUST else 'DISABLED (pure fallback)'}")
    print(f"pydantic         : {pydantic.VERSION if HAS_PYDANTIC else 'not installed'}")
    print(f"Iterations       : {ITERATIONS}")
    print()

    # Sanity check + warm-up (first instantiation builds the model metadata).
    employee = Employee(**PAYLOAD)
    print("Sample instance:")
    print(f"  {employee}")
    print(f"  employee_id : {employee.employee_id!r} ({type(employee.employee_id).__name__})")
    print(f"  age         : {employee.age!r} ({type(employee.age).__name__})")
    print(f"  salary      : {employee.salary!r} ({type(employee.salary).__name__})")
    print(f"  active      : {employee.active!r} ({type(employee.active).__name__})")
    print(f"  hired_at    : {employee.hired_at!r} ({type(employee.hired_at).__name__})")
    print(f"  updated_at  : {employee.updated_at!r} ({type(employee.updated_at).__name__})")
    print()

    header = (
        f"{'benchmark':<34}{'total ms':>10}{'avg ms':>11}"
        f"{'median ms':>11}{'min ms':>10}{'max ms':>10}{'ops/sec':>14}"
    )
    print(header)
    print("-" * len(header))

    model_raw = timeit(
        "BaseModel (raw str -> coerced)",
        lambda: Employee(**PAYLOAD),
    )
    report(model_raw)

    model_native = timeit(
        "BaseModel (already-typed input)",
        lambda: Employee(**NATIVE_PAYLOAD),
    )
    report(model_native)

    plain = timeit(
        "stdlib @dataclass (no checks)",
        lambda: PlainEmployee(**NATIVE_PAYLOAD),
    )
    report(plain)

    if HAS_PYDANTIC:
        pyd = timeit(
            "pydantic BaseModel (raw str)",
            lambda: PydanticEmployee(**PAYLOAD),
        )
        report(pyd)

        pyd_dc = timeit(
            "pydantic @dataclass (raw str)",
            lambda: PydanticDCEmployee(**PAYLOAD),
        )
        report(pyd_dc)

    serialize = timeit(
        "Employee.json() serialization",
        employee.json,
    )
    report(serialize)

    print("-" * len(header))
    print(FOOTNOTE)
    print(
        f"\nTotal for {ITERATIONS} BaseModel builds from raw input: "
        f"{model_raw['total_ms']:.3f} ms "
        f"({model_raw['avg_ms'] * 1000:.1f} µs per instance)"
    )
    print(
        f"Coercion overhead vs already-typed input: "
        f"{model_raw['avg_ms'] - model_native['avg_ms']:+.4f} ms/instance"
    )
    print(
        f"Validation overhead vs stdlib dataclass : "
        f"{model_native['avg_ms'] / plain['avg_ms']:.1f}x slower "
        f"(stdlib does no type checking)"
    )
    if HAS_PYDANTIC:
        ratio = pyd['median_ms'] / model_raw['median_ms']
        verdict = "faster" if ratio > 1 else "slower"
        print(
            f"datamodel vs pydantic BaseModel (median): "
            f"{max(ratio, 1 / ratio):.2f}x {verdict}"
        )
        dc_ratio = pyd_dc['median_ms'] / model_raw['median_ms']
        dc_verdict = "faster" if dc_ratio > 1 else "slower"
        print(
            f"datamodel vs pydantic @dataclass (median): "
            f"{max(dc_ratio, 1 / dc_ratio):.2f}x {dc_verdict}"
        )

        # --- dataclass compatibility ------------------------------------
        print()
        print("Dataclass compatibility (dataclasses.is_dataclass / fields):")
        for label, cls in (
            ("datamodel BaseModel", Employee),
            ("stdlib @dataclass", PlainEmployee),
            ("pydantic BaseModel", PydanticEmployee),
            ("pydantic @dataclass", PydanticDCEmployee),
        ):
            ok = is_dataclass(cls)
            try:
                nfields = len(dc_fields(cls))
                detail = f"{nfields} fields via dataclasses.fields()"
            except TypeError as exc:
                detail = f"dataclasses.fields() -> TypeError: {exc}"
            print(f"  {label:<22} is_dataclass={str(ok):<5}  {detail}")

    # --- Rust converters, called directly -------------------------------
    print()
    print("Rust-backed converters (direct calls, same iteration count):")
    print(header)
    print("-" * len(header))
    report(timeit("rc.to_date('2020-03-15')", lambda: rc.to_date("2020-03-15")))
    report(timeit("rc.to_datetime(iso8601)", lambda: rc.to_datetime("2026-09-08T10:30:00")))
    report(timeit("rc.to_uuid_obj(str)", lambda: rc.to_uuid_obj(PAYLOAD["employee_id"])))
    report(timeit("rc.to_integer('42')", lambda: rc.to_integer("42")))
    report(timeit("rc.to_float('4.75')", lambda: rc.to_float("4.75")))
    report(timeit("rc.to_decimal('85000.50')", lambda: rc.to_decimal("85000.50")))
    report(timeit("rc.to_boolean('true')", lambda: rc.to_boolean("true")))
    print("-" * len(header))
    print(FOOTNOTE)

    print()
    print("Same conversions via the Python stdlib, for reference:")
    print(header)
    print("-" * len(header))
    report(timeit("date.fromisoformat", lambda: date.fromisoformat("2020-03-15")))
    report(timeit("datetime.fromisoformat", lambda: datetime.fromisoformat("2026-09-08T10:30:00")))
    report(timeit("uuid.UUID(str)", lambda: uuid.UUID(PAYLOAD["employee_id"])))
    report(timeit("int('42')", lambda: int("42")))
    report(timeit("float('4.75')", lambda: float("4.75")))
    report(timeit("Decimal('85000.50')", lambda: Decimal("85000.50")))
    print("-" * len(header))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
