from datetime import (
    datetime,
    time,
    date
)
import uuid
from decimal import Decimal
from datamodel import BaseModel, Column


def auto_now_add(*args, **kwargs):
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
    id: uuid.UUID = Column(primary_key=True, required=True, default=auto_now_add(), db_default='uuid_generate_v4()')
    firstname: str
    lastname: str
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
        name = 'users'
        schema = 'public'
        driver = 'pg'
        strict = False

u = User()
print(u.model(dialect='json'))

### creates a new user:
jesus = User(
    firstname='Jesus', lastname='Lara', age=43, salary=1500.25, size=185.28, birth='1978-10-23', in_time='11:00:00.000', out_time='23:59:00.000', is_employee=True
)
print(jesus)
b = jesus.json()
print('JSON ::')
print(b)
jlara = User.from_json(b)
print(jlara)
