
import uuid
from datetime import datetime
from typing import Union, List, Optional
from dataclasses import dataclass, fields, is_dataclass
import pytest
import orjson
from bson import ObjectId
import asyncpg.pgproto.pgproto as pgproto
from datamodel import Field, BaseModel, Column
from datamodel.exceptions import ValidationError


def to_objid(value):
    return ObjectId(value.encode('ascii'))

class Dataset(BaseModel):
    _id: ObjectId = Field(encoder=to_objid)
    name: str = Field(required=True)

def auto_uid():
    return uuid.uuid4()


@dataclass
class Point:
    x: int = Field(default=0, min=0, max=10)
    y: int = Field(default=0, min=0, max=10)
    c: float = Field(default=10, init=False)


@pytest.fixture
def point_fixture():
    """Return a sample `Point` object."""
    return Point(x=10, y=10)


def test_point_creation(point_fixture):
    a = point_fixture
    assert a.x == 10
    assert a.y == 10
    assert a.c == 10.0
    # Check dataclass
    assert is_dataclass(a), "Point should be a dataclass"
    # Check fields
    flds = fields(a)
    assert len(flds) == 3
    names = [f.name for f in flds]
    assert "x" in names
    assert "y" in names
    assert "c" in names

# Example "intSum" interface
class intSum:
    def get_coordinate(self):
        return (self.x, self.y)

class newPoint(BaseModel, intSum):
    x: int = Field(default=0, min=0, max=10)
    y: Union[int, None] = Field(default=0, min=0, max=10)


@pytest.mark.parametrize("as_objects", [True, False])
def test_newpoint_creation(as_objects):
    newPoint.Meta.as_objects = as_objects

    a = newPoint(x=10, y=10)
    assert is_dataclass(a), "newPoint should be a dataclass"
    assert a.get_coordinate() == (10, 10)
    flds = fields(a)
    assert len(flds) == 2
    assert a.x == 10
    assert a.y == 10


class coordinate(BaseModel):
    latitude: float
    longitude: float

    def get_location(self) -> tuple:
        return self.latitude, self.longitude


@pytest.mark.parametrize("as_objects", [True, False])
def test_coordinate_creation(as_objects):
    coordinate.Meta.as_objects = as_objects

    c = coordinate(latitude=18.1, longitude=22.1)
    assert is_dataclass(c)
    assert c.latitude == 18.1
    assert c.longitude == 22.1
    assert c.get_location() == (18.1, 22.1)


class Country(BaseModel):
    country: str = Field(required=True)
    code: str = Field(min=0, max=2)


def default_number():
    return "6"


def default_rect():
    return [0, 0, 0, 0]


def valid_zipcode(field, value, *args, **kwargs):
    return value == 45510


class Address(BaseModel):
    id: uuid.UUID = Field(default=auto_uid)
    street: str = Field(required=True)
    number: str = Field(factory=default_number)
    zipcode: int = Field(required=False, default=1010, validator=valid_zipcode)
    location: Optional[coordinate]
    country: Union[Country, None] = Field(required=False)
    box: List[Optional[newPoint]]
    rect: List[int] = Field(factory=default_rect)
    prueba: str = Field(required=False)


@pytest.mark.parametrize("as_objects", [True, False])
def test_address_model(as_objects):
    Address.Meta.as_objects = as_objects

    addr = Address(
        street="Beato Juan de Avila",
        location=(18.1, 22.1),
        zipcode=45510,
        box=[(2, 10), (4, 8)],
        rect=[1, 2, 3, 4]
    )
    assert addr.street == "Beato Juan de Avila"
    assert addr.zipcode == 45510, "Should pass the valid_zipcode check"
    assert is_dataclass(addr)
    if as_objects:
        assert isinstance(addr.location, coordinate), "location should be a coordinate object"
        assert addr.location.get_location() == (18.1, 22.1)
    else:
        if isinstance(addr.location, coordinate):
            assert addr.location.get_location() == (18.1, 22.1)
        else:
            assert addr.location == (18.1, 22.1)


def auto_uuid(*args, **kwargs):
    return uuid.uuid4()


def def_age():
    return 18


class Account(BaseModel):
    provider: str = Column(required=True, default="dummy")
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default="")
    phone: Union[str, list] = Column(required=False, default="")

    def set_address(self, address: str):
        self.address = address


class Actor(BaseModel):
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    age: int = Column(default=def_age)
    name: str = Column(required=True)
    account: List[Account]
    enabled: bool = Column(required=False, default=True)

    def __str__(self) -> str:
        return f"<{self.name}: {self.userid}>"


@pytest.mark.parametrize("as_objects", [True, False])
def test_actor_with_accounts(as_objects):
    Actor.Meta.as_objects = as_objects

    user_data = {
        "userid": pgproto.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Jesus Lara",
        "account": [
            {"provider": "twilio", "phone": "+343317871"},
            {"provider": "email", "address": "jesuslara@jesuslara.com"},
            {"provider": "jabber", "address": "jesuslara@jesuslara.com"}
        ]
    }
    actor = Actor(**user_data)
    assert actor.name == "Jesus Lara"
    assert isinstance(actor.account, list)
    assert len(actor.account) == 3
    for acc in actor.account:
        if as_objects:
            assert isinstance(acc, Account)
        elif isinstance(acc, Account) and isinstance(actor.account, list):
            assert acc in actor.account
        else:
            assert isinstance(acc, dict)
            assert acc in user_data["account"]


@pytest.mark.parametrize("as_objects", [True, False])
def test_actor_with_accounts_validation(as_objects):
    Actor.Meta.as_objects = as_objects

    # Case 1: Missing required data (`name` is required)
    missing_data = {
        "userid": pgproto.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "account": [
            {"provider": "twilio", "phone": "+343317871"},
        ]
    }
    with pytest.raises(ValueError, match=r"Missing Required Field \*name\*"):
        Actor(**missing_data)

    # Case 2: Invalid field value (unconvertible type)
    invalid_data = {
        "userid": pgproto.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Invalid User",
        "account": [
            {"provider": "twilio", "phone": {"phone": 343317871}},  # Expecting a string for `phone`, provided a Dict
        ]
    }
    with pytest.raises(ValueError, match="Invalid type.*phone"):
        Actor(**invalid_data)

    # Case 3: Primitive type conversion failure (`enabled` in Account expects a bool)
    invalid_type_data = {
        "userid": pgproto.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Type Error User",
        "account": [
            {"provider": "twilio", "enabled": "Imposible to Convert to Boolean"},
        ]
    }
    with pytest.raises(ValidationError):
        Actor(**invalid_type_data)

    # Case 4: Valid data for `as_objects=True` and `as_objects=False`
    valid_data = {
        "userid": pgproto.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Valid User",
        "account": [
            {"provider": "twilio", "phone": "+343317871"},
            {"provider": "email", "address": "user@example.com"},
        ]
    }
    # Validate an Account:
    actor = Actor(**valid_data)
    assert actor.name == "Valid User"
    assert isinstance(actor.account, list)
    assert len(actor.account) == 2
    for acc in actor.account:
        if as_objects:
            assert isinstance(acc, Account)
        elif isinstance(acc, Account) and isinstance(actor.account, list):
            assert acc in actor.account
        else:
            assert isinstance(acc, dict)
