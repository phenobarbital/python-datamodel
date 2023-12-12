from datetime import datetime
from typing import List, Optional
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


user = User(
    id='42',
    signup_ts='2032-06-21T12:00',
    address={
        "street": "Calle Mayor", "zipcode": 45510, "country": {"country": "Spain"}
    }
)
print(user)

@dataclass
class NavbarButton:
    href: AnyUrl

@dataclass
class Navbar:
    button: NavbarButton

navbar = Navbar(button=NavbarButton('https://example.com'))
print(navbar)

_end = datetime.now()
print(f'Pydantic End at: {_end - _started}')

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

user = User(
    id='42',
    signup_ts='2032-06-21T12:00',
    address={
        "street": "Calle Mayor", "zipcode": 45510, "country": {"country": "Spain"}
    }
)
print(user)

class HttpsUrl(AnyUrl):
    def __init__(self, url, scheme: str = 'https'):
        super(HttpsUrl, self).__init__(
            url=url,
            scheme=scheme
        )

class NavbarButton(BaseModel):
    href: HttpsUrl

class Navbar(BaseModel):
    button: NavbarButton

navbar = Navbar(button='https://example.com')
print(navbar)

_end = datetime.now()
print(f'BaseModel End at: {_end - _started}')
