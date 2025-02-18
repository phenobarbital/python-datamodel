import cProfile
from typing import Optional, List
from dataclasses import is_dataclass
from datetime import datetime
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

class NewUser(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: List[int] = Field(default_factory=list)

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
try:
    user = NewUser(**external_data)
except ValidationError as e:
    print(e.payload)
print(user)
print(user.id)
print(is_dataclass(user))
print(type(user.signup_ts), user.signup_ts)

def create_user2():
    for i in range(100):
        external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
        try:
            user = NewUser(**external_data)
        except ValidationError as e:
            print(e.payload)

print('Test with DataModel: ')
cProfile.run("create_user2()", sort="cumulative")
