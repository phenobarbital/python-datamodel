from typing import Optional, List
import pprint
from enum import Enum
from datetime import datetime, date
from dataclasses import is_dataclass
from datamodel import BaseModel, Field
from datamodel.types import Text
from datamodel.exceptions import ValidationError


pp = pprint.PrettyPrinter(width=41, compact=True)

class UserType(Enum):
    USER = 1  # , 'user'
    CUSTOMER = 2  # , 'customer'
    STAFF = 3  # , 'staff'
    MANAGER = 4  # , 'manager'
    ADMIN = 5  # , 'admin'
    ROOT = 10  # , 'superuser'

class NewUser(BaseModel):
    id: int
    name = 'John Doe'
    signup_ts: Optional[datetime] = None # TODO: optional[datetime] can also be converted to type.
    born: Optional[date] = None
    user_role: UserType = Field(required=False, default=UserType.USER)
    friends: List[int] = Field(default_factory=list)
    avatar: Text
    ## check for error: ValueError: mutable default <class 'list'> for field friends is not allowed: use default_factory

external_data = {
    'id': '123', 'signup_ts': '2017-06-01 12:22', 'born': '23-10-1978', 'friends': [1, '2', b'3'],
    "avatar": "https://avatars2.githubusercontent.com/u/2695287?s=460&v=4"
}
try:
    user = NewUser(**external_data)
except ValidationError as exc:
    print(exc.payload)
print(user)
#> User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
print(user.id, user.user_role)
#> 123
print('Is a Dataclass: ', is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)
print('Born is a date?: ', isinstance(user.born, date))

print('======= Schema ====')
pp.pprint(NewUser.schema(as_dict=False))
