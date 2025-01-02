import uuid
from typing import Union, List, Optional
from dataclasses import fields, dataclass, is_dataclass
import pytest
import orjson
import asyncpg.pgproto.pgproto as pgproto
from datamodel import Field, BaseModel, Column
from datamodel.exceptions import ValidationError


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

def test_newpoint_creation():
    a = newPoint(x=10, y=10)
    assert is_dataclass(a), "newPoint should be a dataclass"
    # Check coords
    assert a.get_coordinate() == (10, 10)
    # Check fields
    flds = fields(a)
    assert len(flds) == 2
    assert a.x == 10
    assert a.y == 10


class coordinate(BaseModel, intSum):
    latitude: float
    longitude: float

    def get_location(self) -> tuple:
        return (self.latitude, self.longitude)


def test_coordinate_creation():
    c = coordinate(latitude=18.1, longitude=22.1)
    assert is_dataclass(c)
    assert c.latitude == 18.1
    assert c.longitude == 22.1
    assert c.get_location() == (18.1, 22.1)


class Country(BaseModel):
    country: str = Field(required=True)
    code: str = Field(min=0, max=2)


def default_number():
    return '6'

def default_rect():
    return [0, 0, 0, 0]

def valid_zipcode(field, value):
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


def test_address_model():
    addr = Address(
        street="Beato Juan de Avila",
        location=(18.1, 22.1),
        zipcode=45510,
        box=[(2, 10), (4, 8)],    # This should create newPoint objects
        rect=[1, 2, 3, 4]
    )
    assert addr.street == "Beato Juan de Avila"
    assert addr.zipcode == 45510, "Should pass the valid_zipcode check"
    assert is_dataclass(addr)
    # Check location is `coordinate`
    assert isinstance(addr.location, coordinate), "location should be a coordinate object"
    assert addr.location.get_location() == (18.1, 22.1)

    # JSON export
    j = addr.json()
    data = orjson.loads(j)
    data['country'] = {
        "country": "Spain",
        "code": "ES"
    }
    addr2 = Address(**data)
    assert addr2.country.country == "Spain"
    assert addr2.country.code == "ES"

    # from_json
    addr3 = Address.from_json(j)
    assert addr3.street == "Beato Juan de Avila"
    assert isinstance(addr3.location, coordinate)


def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

def def_age():
    return 18

class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Column(required=True, default='dummy')
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default='')
    phone: Union[str, list] = Column(required=False, default='')

    def set_address(self, address: str):
        self.address = address


class Actor(BaseModel):
    """
    Basic Actor (meta-definition), can be a Sender or a Recipient
    """
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    age: int = Column(default=def_age)
    name: str
    # account: Union[Account, List[Account]]
    account: List[Account]

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


def test_actor_with_accounts():
    user_data = {
        "userid": pgproto.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'),
        "name": "Jesus Lara",
        "account": [
            {
                "provider": "twilio",
                "phone": "+343317871"
            },
            {
                "provider": "email",
                "address": "jesuslara@jesuslara.com"
            },
            {
                "provider": "jabber",
                "address": "jesuslara@jesuslara.com"
            }
        ]
    }
    # Should not raise ValidationError
    actor = Actor(**user_data)
    assert actor.name == "Jesus Lara"
    assert isinstance(actor.account, list)
    assert len(actor.account) == 3
    for acc in actor.account:
        assert isinstance(acc, Account)
