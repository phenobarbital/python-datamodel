import uuid
from typing import Union, List, Optional
from dataclasses import dataclass, fields, is_dataclass, field
import asyncpg.pgproto.pgproto as pgproto
import orjson
from datamodel import Field, BaseModel, Column
from datamodel.exceptions import ValidationError


def auto_uid():
    return uuid.uuid4()

@dataclass
class Point:
    x: int = Field(default=0, min=0, max=10)
    y: int = Field(default=0, min=0, max=10)
    c: float = Field(default=10, init=False)


a = Point(x=10, y=10)
print(a)
print(fields(a))
print('IS a Dataclass?: ', is_dataclass(a))

class intSum(object):
    def get_coordinate(self):
        return (self.x, self.y)

# or using Model:
class newPoint(BaseModel, intSum):
    x: int = Field(default=0, min=0, max=10)
    y: Union[int, None] = Field(default=0, min=0, max=10)

try:
    p = newPoint(x=10, y=10)
except ValidationError as e:
    print(e.payload)

print(p)
print(fields(p), ' Coords: ', p.x, p.y, type(p.x), type(p.y))
print('IS a Dataclass?: ', is_dataclass(p))
print(p.get_coordinate())

class coordinate(BaseModel, intSum):
    latitude: float
    longitude: float

    def get_location(self) -> tuple:
        return (self.latitude, self.longitude)


class Country(BaseModel):
    country: str = Field(required=True)
    code: str = Field(min=0, max=2)

def default_number():
    return '6'

def default_rect():
    return [0,0,0,0]

def valid_zipcode(field, value):
    return value == 45510

class Address(BaseModel):
    id: uuid.UUID = Field(default_factory=auto_uid)
    street: str = Field(required=True)
    number: str = Field(factory=default_number)
    zipcode: int = Field(required=False, default=1010, validator=valid_zipcode)
    location: Optional[coordinate]
    country: Union[Country, None] = Field(required=False)
    box: List[Optional[newPoint]]
    rect: List[int] = Field(factory=default_rect)
    prueba: str = Field(required=False)

try:
    addr = Address(
        street="Beato Juan de Avila",
        location=(18.1, 22.1),
        zipcode=45510,
        box=[(2, 10), (4, 8)],
        rect=[1, 2, 3, 4]
    )
except ValidationError as e:
    print('==')
    print(e.payload)
    print('==')

print(addr)
print('IS a Dataclass?: ', is_dataclass(addr))

print(addr.location.get_location())
print('== Export to JSON ==')
print(addr.json())
b = addr.json()
data = orjson.loads(b)
data['country'] = {
    "country": "Spain",
    "code": "ES"
}
addr2 = Address(**data)
print(addr2)
print('== Using "from-json" method ==')
addr3 = Address.from_json(b)
print(addr3)
print('=== PRINTING MODEL === ')
print(Address.model())


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
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    age: int = Column(default=def_age)
    name: str = Column(required=True)
    account: List[Account]

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


user = {
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
try:
    user = Actor(**user)
    print(user)
    print('Accounts: ', user.account)
except ValidationError as e:
    print(e.payload)
