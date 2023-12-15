from typing import Union, List
import uuid
from datetime import datetime
from datamodel import BaseModel, Column


def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

def def_age():
    return 18

def is_employee(obj) -> str:
    if obj in ('Y', 'F'):
        return obj
    elif obj is True:
        return 'Y'
    else:
        return 'F'

class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Column(required=True, default='dummy')
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default='')
    phone: Union[str, list] = Column(required=False, default='')

    def set_address(self, address: str):
        self.address = address

class Actor(BaseModel):
    """
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    age: int = Column(default=def_age)
    name: str
    account: Union[Account, List[Account]]
    is_employee: str = Column(required=True, default='F', encoder=is_employee)
    created_at: datetime = Column(required=False, default=datetime.now)

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


user = {
    "name": "Jesus Lara",
    "is_employee": True,
    "account": [
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
user = Actor(**user)
print(f"User: ID: {user.userid}, Name: {user.name}, age: {user.age}, accounts: {user.account!r}, created: {user.created_at}")
print(f'Types: {type(user.created_at)}')
