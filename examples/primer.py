from typing import Union, Optional, List
import uuid
import orjson
from dataclasses import fields, is_dataclass
from datamodel import Field, BaseModel, Column


# 1.- basic Point example:

class intSum(object):
    def get_coordinates(self):
        return (self.latitude, self.longitude)

class Coordinate(BaseModel, intSum):
    latitude: float
    longitude: float

    def get_location(self) -> tuple:
        return (self.latitude, self.longitude)

a = Coordinate(latitude=10, longitude=10)
print('COORDINATE > ', a)
print(fields(a))
print('IS a Dataclass?: ', is_dataclass(a))
print(a.get_location(), a.get_coordinates())

# 2.- Basic User Example:

class Country(BaseModel):
    country: str = Field(required=True)
    code: str = Field(min=0, max=2)

def default_number():
    return '6'

def default_rect():
    return [0, 0, 0, 0]

def valid_zipcode(field, value):
    return value == 45510

def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

class Address(BaseModel):
    id: uuid.UUID = Column(default_factory=auto_uuid)
    street: str = Field(required=True)
    number: str = Field(factory=default_number)
    zipcode: int = Field(required=False, default=1010, validator=valid_zipcode)
    location: Optional[Coordinate]
    country: Union[Country, None] = Field(required=False)
    box: List[Optional[Coordinate]]
    rect: List[int] = Field(factory=default_rect)

addr = Address(
    street="Beato Juan de Avila",
    location=(18.1, 22.1),
    zipcode=45510,
    box=[(2, 10), (4, 8)],
    rect=[1, 2, 3, 4]
)
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

# 3.- User Account Example:

class Account(BaseModel):
    """
    User Account
    """
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    name: str
    enabled: bool = Column(required=True, default=True)
    address: Address = Column(required=False)
    phone: Union[str, list] = Column(required=False, default='')

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'

    def __post_init__(self) -> None:
        print('PRIMER')
        return super().__post_init__()



user = {
    "name": "Jesus Lara",
    "address": addr
    # "address": {
    #     "street": "Calle Beato Juan de Avila",
    #     "country": {
    #         "country": "Spain",
    #         "code": "ES"
    #     },
    #     "location": {
    #         "latitude": 10.0,
    #         "longitude": 10.0
    #     },
    #     "zipcode": 45510
    # }
}

user = Account(**user)
print('==== Printing User ====')
print(user)
