from typing import Optional, List, Union
from datetime import datetime, date
from dataclasses import dataclass
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

@dataclass
class Address:
    street: str
    zipcode: int


class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Field(required=True, default='dummy')
    enabled: bool = Field(required=True, default=True)
    address: Union[str, list] = Field(required=False, default='')
    phone: Union[str, list] = Field(required=False, default='')

class User(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    born: date = None
    friends: List[int] = Field(default_factory=list)
    address: Optional[Address]
    accounts: List[Account]
    created_at: datetime = Field(default=datetime.now)

external_data = {
    'id': '123',
    'signup_ts': '2017-06-01 12:22',
    'born': '23-10-1978',
    'friends': [1, '2', '3'],
    "address": {"street": "Calle Mayor", "zipcode": 45510},
    "accounts": [
        {
            "provider": "twilio",
            "phone": "+343317871"
        },
        {
            "provider": "email",
            "address": "jesuslara@jesuslara.com"
        },
        {
            "provider": "jabber",
            "address": "jesuslara@jesuslara.com"
        }
    ]
}
try:
    user = User(**external_data)
    print('USER> ', user)
    print('Types: ', type(user.created_at))
except ValidationError as exc:
    print(exc.payload)
