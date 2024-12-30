from typing import Optional, List, Union
from datetime import datetime, date
import uuid
from dataclasses import dataclass, is_dataclass
from datamodel import BaseModel, Field

@dataclass
class Address:
    street: str
    zipcode: int

def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

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
    uid: uuid.UUID = Field(primary_key=True, default=auto_uuid)
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    born: Optional[date] = None
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
user = User(**external_data)


def test_is_dataclass():
    assert is_dataclass(user)

def test_userid():
    assert user.id == 123
    assert isinstance(user.id, int)
    assert user.name == 'John Doe'
    assert isinstance(user.uid, uuid.UUID)

def test_signup():
    assert str(user.signup_ts) == '2017-06-01 12:22:00'
    dt = datetime(2017, 6, 1, 12, 22, 00)
    assert isinstance(user.signup_ts, datetime)
    assert dt == user.signup_ts

def test_borndate():
    assert str(user.born) == '1978-10-23'
    dt = date(1978, 10, 23)
    assert isinstance(user.born, date)
    assert dt == user.born

def test_friend():
    assert len(user.friends) == 3

def test_address():
    assert type(user.address) == Address
    assert is_dataclass(user.address)
    assert user.address.street == "Calle Mayor"
    assert user.address.zipcode == 45510

def test_accounts():
    assert len(user.accounts) > 0
    assert len(user.accounts) == 3
    assert isinstance(user.accounts[0], Account)
    assert is_dataclass(user.accounts[0])
    for account in user.accounts:
        if account.provider == 'twilio':
            assert account.phone == "+343317871"
        if account.provider == 'jabber':
            assert account.address == "jesuslara@jesuslara.com"

def test_created_at():
    assert isinstance(user.created_at, datetime)
