"""Tests for PEP 604 (X | Y) union type syntax support."""
import pytest
from datamodel import BaseModel, Field


class Address(BaseModel):
    street: str
    city: str


class Person(BaseModel):
    name: str
    age: int | None = None
    score: float | None = None
    address: Address | None = None
    tags: list[str] | None = None


class MultiUnion(BaseModel):
    value: int | str = "default"


class NestedOptional(BaseModel):
    addresses: list[Address] | None = None


class TestPep604BasicConstruction:
    def test_none_defaults(self):
        p = Person(name="Alice")
        assert p.name == "Alice"
        assert p.age is None
        assert p.address is None
        assert p.tags is None

    def test_explicit_none(self):
        p = Person(name="Alice", age=None, address=None)
        assert p.age is None
        assert p.address is None

    def test_with_values(self):
        p = Person(name="Bob", age=30, score=9.5)
        assert p.age == 30
        assert p.score == 9.5


class TestPep604TypeCoercion:
    def test_str_to_int(self):
        p = Person(name="Bob", age="25")
        assert p.age == 25
        assert isinstance(p.age, int)

    def test_str_to_float(self):
        p = Person(name="Bob", score="3.14")
        assert p.score == 3.14
        assert isinstance(p.score, float)

    def test_int_to_float(self):
        p = Person(name="Bob", score=10)
        assert isinstance(p.score, (int, float))


class TestPep604NestedDataclass:
    def test_dict_to_dataclass(self):
        p = Person(
            name="Carol",
            address={"street": "123 Main St", "city": "Springfield"}
        )
        assert isinstance(p.address, Address)
        assert p.address.street == "123 Main St"
        assert p.address.city == "Springfield"

    def test_dataclass_passthrough(self):
        addr = Address(street="456 Elm", city="Shelbyville")
        p = Person(name="Dave", address=addr)
        assert isinstance(p.address, Address)
        assert p.address is addr

    def test_none_address(self):
        p = Person(name="Eve", address=None)
        assert p.address is None


class TestPep604ListOptional:
    def test_list_with_values(self):
        p = Person(name="Frank", tags=["a", "b", "c"])
        assert p.tags == ["a", "b", "c"]

    def test_list_none(self):
        p = Person(name="Grace")
        assert p.tags is None


class TestPep604MultiUnion:
    def test_int_value(self):
        m = MultiUnion(value=42)
        assert m.value == 42

    def test_str_value(self):
        m = MultiUnion(value="hello")
        assert m.value == "hello"

    def test_default_value(self):
        m = MultiUnion()
        assert m.value == "default"


class TestPep604NestedOptionalList:
    def test_list_of_dicts_to_dataclasses(self):
        n = NestedOptional(
            addresses=[
                {"street": "1st Ave", "city": "NYC"},
                {"street": "2nd Ave", "city": "LA"},
            ]
        )
        assert isinstance(n.addresses, list)
        assert len(n.addresses) == 2
        assert all(isinstance(a, Address) for a in n.addresses)

    def test_none(self):
        n = NestedOptional()
        assert n.addresses is None


class TestPep604Schema:
    def test_schema_int_or_none(self):
        schema = Person.schema(as_dict=True)
        assert schema["properties"]["age"]["type"] == "integer"

    def test_schema_address_or_none(self):
        schema = Person.schema(as_dict=True)
        assert schema["properties"]["address"]["type"] == "object"
        assert "$ref" in schema["properties"]["address"]


class TestPep604BackwardCompatibility:
    """Ensure traditional typing.Optional and typing.Union still work."""

    def test_optional_still_works(self):
        from typing import Optional

        class Classic(BaseModel):
            name: str
            age: Optional[int] = None

        c = Classic(name="Test", age="42")
        assert c.age == 42

    def test_union_still_works(self):
        from typing import Union

        class Classic(BaseModel):
            name: str
            value: Union[int, str] = "x"

        c = Classic(name="Test", value=123)
        assert c.value == 123
