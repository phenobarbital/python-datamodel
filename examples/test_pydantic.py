from datetime import datetime
from typing import List, Optional
from dataclasses import is_dataclass
from pydantic import BaseModel
import timeit


class User(BaseModel):
    id: int
    name = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = []

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = User(**external_data)
print(user)
#> User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
print(user.id)
#> 123
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user():
    for i in range(100):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        user = User(**external_data)


print('Test with Pydantic: ')
time = timeit.timeit(create_user, number=10000)
print(f"Execution time: {time:.6f} seconds")
# runner = pyperf.Runner()
# runner.bench_func('pydantic', create_user)

from datamodel import BaseModel, Field

class NewUser(BaseModel):
    id: int
    name = 'John Doe'
    signup_ts: Optional[datetime] = None # TODO: optional[datetime] can also be converted to type.
    friends: List[int] = Field(default_factory=list)
    ## check for error: ValueError: mutable default <class 'list'> for field friends is not allowed: use default_factory

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = NewUser(**external_data)
print(user)
#> User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
print(user.id)
#> 123
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user2():
    for i in range(100):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        user = NewUser(**external_data)


print('Test with DataModel: ')
time = timeit.timeit(create_user2, number=10000)
print(f"Execution time: {time:.6f} seconds")
# runner.bench_func('datamodel', create_user2)
