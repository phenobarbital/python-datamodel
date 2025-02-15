import uuid
from datetime import date, datetime, time
from decimal import Decimal

from datamodel import BaseModel, Column, Field
from datamodel.exceptions import ValidationError


def auto_now_add():
    return uuid.uuid4()

def is_employee(obj) -> str:
    if obj in ('Y', 'F'):
        return obj
    elif obj is True:
        return 'Y'
    else:
        return 'F'

class Contact(BaseModel):
    account: str = ''
    value: str = ''

class User(BaseModel):
    """
    User Basic Structure
    """
    id: uuid.UUID = Column(
        primary_key=True,
        required=True,
        default=auto_now_add,
        db_default='uuid_generate_v4()'
    )
    firstname: str = Field(required=True)
    lastname: str = Field(required=True)
    name: str = Column(required=True, default='John Doe')
    age: int = Column(default=18, required=True)
    salary: Decimal = Column(default=10.0)
    in_time: time = Column(default='15:00')
    out_time: time = Column(default='23:00')
    birth: date = Column(required=False)
    is_employee: str = Column(required=True, default='F', encoder=is_employee)
    size: float
    signup_ts: datetime = Column(default=datetime.now(), db_default='now()')
    contacts: Contact = Column(required=False)

    class Meta:
        strict: bool = True


# Error on empy user:
try:
    u = User(firstname='Jesus', lastname='Lara', birth='Egg')
except ValidationError as ex:
    print('Valid Error: ', ex)
except TypeError as ex:
    print(ex)
except ValueError as ex:
    print(ex)

### creates a new user:
try:
    jesus = User(
        firstname='Jesus',
        lastname='Lara',
        age='Hola',
        salary=1500.25,
        size=185.28,
        birth='1978-10-23',
        in_time='11:00:00.000',
        out_time='23:59:00.000',
        is_employee=True
    )
    print(jesus)
except ValidationError as ex:
    print('Validation for bad Age > ', ex)
    print(ex.payload)

# try to adding a missing keyword:
try:
    jesus = User(airport=True)
except ValidationError as ex:
    print(ex)
except TypeError as ex:
    print(ex)

class Animal(BaseModel):
    name: str
    specie: str
    age: int

try:
    animal = Animal(**{
        "name": "Human",
        "specie": "Homo Sapiens",
        "age": "otra cosa"
    })
except ValidationError as ex:
    print(ex)
    print(ex.payload)
except TypeError as ex:
    print(ex)
except ValueError as ex:
    print(ex)
