from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
import asyncio

# Pydantic
_started = datetime.now()
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass
_end = datetime.now()

print(f'Pydantic Loaded at: {_end - _started}')

@dataclass
class Country:
    country: str
    code: str = 'ES'
    iso_code: str = '+34'

@dataclass
class Address:
    street: str
    zipcode: int
    country: Country

@dataclass
class User:
    id: int
    name: str = 'John Doe'
    signup_ts: datetime = None
    address: Optional[Address] = None

@dataclass
class Employee:
    employee_id: UUID
    user: User
    joined_date: datetime = datetime.now()

user = Employee(
    employee_id=uuid4(),
    user=User(
        id='42',
        signup_ts='2032-06-21T12:00',
        address={
            "street": "Calle Mayor", "zipcode": 45510, "country": {"country": "Spain"}
        }
    )
)
print(user)

# # @dataclass
# # class NavbarButton:
# #     href: AnyUrl

# # @dataclass
# # class Navbar:
# #     button: NavbarButton

# # navbar = Navbar(button=NavbarButton('https://example.com'))
# # print(navbar)

_end = datetime.now()
print(f'Pydantic End at: {_end - _started}')

## Tortoise ORM
_started = datetime.now()
from tortoise.models import Model
from tortoise import fields
from tortoise import Tortoise
_end = datetime.now()
print(f'Tortoise Loaded at: {_end - _started}')

class Country(Model):
    country: str = fields.CharField(pk=True, max_length=255)
    code: str = fields.CharField(max_length=2, default='ES')
    iso_code: str = fields.CharField(max_length=4, default='+34')

class Address(Model):
    street: str = fields.CharField(max_length=255)
    zipcode: int = fields.IntField(default=45510)
    country: Country = fields.ForeignKeyField(
        'models.Country', related_name='addresses'
    )

class User(Model):
    id: int = fields.IntField(pk=True)
    name: str = fields.CharField(max_length=255, default='John Doe')
    signup_ts: datetime = fields.DatetimeField(null=True)
    address: Optional[Address] = fields.ForeignKeyField(
        'models.Address', related_name='users', null=True
    )

class Employee(Model):
    employee_id: UUID = fields.UUIDField(pk=True)
    user: User = fields.ForeignKeyField(
        'models.User',
        related_name='employees'
    )
    joined_date: datetime = fields.DatetimeField(
        null=True, default=datetime.now()
    )

async def create_employee():
    await Tortoise.init(
        db_url='sqlite://:memory:',
        modules={'models': ['__main__']}
    )
    await Tortoise.generate_schemas()

    # Create Country, Address, and User instances
    country = await Country.create(country='Spain')
    address = await Address.create(street='Calle Mayor', zipcode=45510, country=country)
    user = await User.create(
        id=42,
        signup_ts=datetime(2032, 6, 21, 12, 0),
        address=address
    )
    # Create Employee and associate with User
    employee = await Employee.create(employee_id=uuid4(), user=user)

    await Tortoise.close_connections()

    return employee

employee = asyncio.run(create_employee())
print(employee)

_end = datetime.now()
print(f'Tortoise End at: {_end - _started}')


## BaseModel
_started = datetime.now()
from datamodel import BaseModel, Field
from dataclasses import dataclass

_end = datetime.now()
print(f'BaseModel Loaded at: {_end - _started}')

def country_iso_code():
    return '+34'

class Country(BaseModel):
    country: str
    code: str = Field(default='ES')
    iso_code: str = Field(default=country_iso_code)

class Address(BaseModel):
    street: str
    zipcode: int
    country: Country

class User(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: datetime = None
    address: Optional[Address]

class Employee(User):
    employee_id: UUID
    joined_date: datetime = datetime.now()

user = Employee(
    id='42',
    employee_id=uuid4(),
    signup_ts='2032-06-21T12:00',
    address={
        "street": "Calle Mayor", "zipcode": 45510, "country": {"country": "Spain"}
    }
)
print(user)

# # class HttpsUrl(AnyUrl):
# #     def __init__(self, url, scheme: str = 'https'):
# #         super(HttpsUrl, self).__init__(
# #             url=url,
# #             scheme=scheme
# #         )

# # class NavbarButton(BaseModel):
# #     href: HttpsUrl

# # class Navbar(BaseModel):
# #     button: NavbarButton

# # navbar = Navbar(button='https://example.com')
# # print(navbar)

_end = datetime.now()
print(f'BaseModel End at: {_end - _started}')
