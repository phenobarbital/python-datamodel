from typing import Optional, List
from datetime import datetime, date
from dataclasses import is_dataclass
from datamodel import BaseModel, Field

class NewUser(BaseModel):
    id: int
    name = 'John Doe'
    signup_ts: Optional[datetime] = None # TODO: optional[datetime] can also be converted to type.
    born: Optional[date] = None
    friends: List[int] = Field(default_factory=list)
    ## check for error: ValueError: mutable default <class 'list'> for field friends is not allowed: use default_factory

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'born': '23-10-1978', 'friends': [1, '2', b'3']}
user = NewUser(**external_data)
print(user)
#> User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
print(user.id)
#> 123
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)
print(isinstance(user.born, date))
