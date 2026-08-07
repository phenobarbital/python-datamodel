from typing import Optional
from datamodel import BaseModel, Field
from datetime import datetime


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
    signup_ts: datetime = Field(default=datetime.now)
    address: Optional[Address]


if __name__ == '__main__':
    spain = Country(country='Spain')
    print(spain, spain.code)

    user = User(
        id='42',
        signup_ts='2032-06-21T12:00',
        address={
            "street": "Calle Mayor", "zipcode": 45510, "country": {"country": "Spain"}
        }
    )
    # print(user, type(user.signup_ts), user.address.country.code)
    print(user)
