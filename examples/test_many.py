from typing import Optional, List
from datetime import datetime
import timeit
from datamodel import BaseModel, Field

external_user = {
    'id': '123',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3']
}

class Account(BaseModel):
    """
    Attributes for User Account
    """
    provider: str = Field(required=True, default='dummy')
    enabled: bool = Field(required=True, default=True)
    address: Optional[str] = Field(required=False, default='')


class User(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = Field(default_factory=list)
    # accounts: List[Account] = Field(default_factory=list)

user = User(**external_user)
print(user)
print(user.id)
print(type(user.signup_ts), user.signup_ts)

def create_user():
    for i in range(10):
        user = User(**external_user)


print('Test with DataModel: ')
time = timeit.timeit(create_user, number=100000)
print(f"Execution time: {time:.6f} seconds")
# runner.bench_func('datamodel', create_user2)
print(user, user.friends)
