from datetime import datetime, date
from typing import List, Optional, Dict, Union
from dataclasses import is_dataclass
import timeit
from pydantic import BaseModel


external_user = {
    'id': '123',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3'],
    "accounts": [
        {
            "provider": "twilio",
            "address": "+34343434"
        },
        {
            "provider": "email",
            "address": "test@example.com"
        }
    ],
    "attributes": {
        "age": 23,
        "height": 1.78
    }
}

print('============= PYDANTIC =============')

class Account(BaseModel):
    """
    Attributes for User Account
    """
    provider: str = 'dummy'
    enabled: bool = True
    address: Optional[str]

class User(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = []
    accounts: List[Account] = []
    attributes: Dict[str, Union[int, float]] = {}

user = User(**external_user)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user():
    for i in range(10):
        user = User(**external_user)

print('Test with Pydantic: ')
time = timeit.timeit(create_user, number=1000)
print(f"Execution time: {time:.6f} seconds")

# runner.bench_func('pydantic', create_user)

print(' ============ ClassDict =============')
from datamodel.libs.mapping import ClassDict
# from datamodel.libs.mutables import ClassDict

class User(ClassDict):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = []

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = User(**external_data)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user():
    for i in range(10):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        user = User(**external_data)

print('Test with ClassDict: ')
time = timeit.timeit(create_user, number=1000)
print(f"Execution ClassDict: {time:.6f} seconds")

print('============= Model =============')
# Basic Model:
from datamodel import Model, Field

class Account(BaseModel):
    """
    Attributes for User Account
    """
    provider: str = Field(required=True, default='dummy')
    enabled: bool = Field(required=True, default=True)
    address: Optional[str] = Field(required=False, default='')

class User(Model):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = Field(default_factory=list)
    accounts: List[Account] = Field(default_factory=list)
    attributes: Dict[str, Union[int, float]] = Field(default_factory=dict)

user = User(**external_user)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user1():
    for i in range(10):
        user = User(**external_user)

print('Test with Model: ')
time = timeit.timeit(create_user1, number=1000)
print(f"Execution time: {time:.6f} seconds")

print('============= BaseModel =============')

external_user = {
    'id': '123',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3'],
    'born': '1978-10-23',
    "accounts": [
        {
            "provider": "twilio",
            "address": "+34343434"
        },
        {
            "provider": "email",
            "address": "test@example.com"
        }
    ],
    "attributes": {
        "age": 23,
        "height": 1.78
    }
}

from datamodel import BaseModel, Field


class Account(BaseModel):
    """
    Attributes for User Account
    """
    provider: str = Field(required=True, default='dummy')
    enabled: bool = Field(required=True, default=True)
    address: Optional[str] = Field(required=False, default='')


class NewUser(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    born: Optional[date] = None
    friends: List[int] = Field(default_factory=list)
    accounts: List[Account] = Field(default_factory=list)
    attributes: Dict[str, Union[int, float]] = Field(default_factory=dict)

user = NewUser(**external_user)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user2():
    for i in range(10):
        user = NewUser(**external_user)


print('Test with DataModel: ')
time = timeit.timeit(create_user2, number=1000)
print(f"Execution time: {time:.6f} seconds")
# runner.bench_func('datamodel', create_user2)
print(user, user.friends)

print('============= BaseModel (Caching) =============')

user = NewUser(**external_user)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)
print(type(user.born), user.born)

def create_user3():
    for i in range(10):
        user = NewUser(**external_user)


print('Test with DataModel: ')
time = timeit.timeit(create_user3, number=1)
print(f"Execution time: {time:.6f} seconds")
# runner.bench_func('datamodel', create_user2)
print(user, user.friends)
