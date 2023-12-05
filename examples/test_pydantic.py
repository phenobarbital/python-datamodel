from datetime import datetime
import pyperf
from typing import List, Optional
from dataclasses import is_dataclass
from pydantic import BaseModel
import timeit

# runner = pyperf.Runner()
print('============= PYDANTIC =============')
class User(BaseModel):
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

print('Test with Pydantic: ')
time = timeit.timeit(create_user, number=10000)
print(f"Execution time: {time:.6f} seconds")

# runner.bench_func('pydantic', create_user)

print('============= Model =============')
# Basic Model:
from datamodel import Model, Field

class User(Model):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = Field(default_factory=list)

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = User(**external_data)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user1():
    for i in range(10):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        user = User(**external_data)

print('Test with Model: ')
time = timeit.timeit(create_user1, number=10000)
print(f"Execution time: {time:.6f} seconds")

# runner = pyperf.Runner()
# runner.bench_func('model', create_user1)

print('============= BaseModel =============')

from datamodel import BaseModel, Field
class NewUser(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = Field(default_factory=list)

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = NewUser(**external_data)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user2():
    for i in range(10):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        user = NewUser(**external_data)


print('Test with DataModel: ')
time = timeit.timeit(create_user2, number=10000)
print(f"Execution time: {time:.6f} seconds")
# runner.bench_func('datamodel', create_user2)
