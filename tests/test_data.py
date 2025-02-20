from typing import Optional, List, Union
from datetime import datetime, date
from dataclasses import dataclass
import pytest
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

    class Meta:
        as_objects = True
        strict = True

@pytest.fixture
def external_data():
    """Fixture providing the external data to be used in multiple tests."""
    return {
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

def test_user_model_success(external_data):
    """Test that a User object is created correctly with valid external data."""
    try:
        user = User(**external_data)
    except ValidationError as exc:
        pytest.fail(
            f"User creation should succeed, but ValidationError occurred: {exc.payload}"
        )

    # Basic attribute checks:
    assert user.id == 123
    assert user.name == 'John Doe'
    assert user.signup_ts == datetime(2017, 6, 1, 12, 22)
    assert user.born == date(1978, 10, 23)
    assert user.friends == [1, 2, 3]

    # Check the address is the correct dataclass object:
    assert user.address is not None
    assert user.address.street == "Calle Mayor"
    assert user.address.zipcode == 45510

    # Check accounts
    assert len(user.accounts) == 3
    # 1st account
    assert user.accounts[0].provider == "twilio"
    assert user.accounts[0].phone == "+343317871"
    assert user.accounts[0].enabled is True
    # 2nd account
    assert user.accounts[1].provider == "email"
    assert user.accounts[1].address == "jesuslara@jesuslara.com"
    # 3rd account
    assert user.accounts[2].provider == "jabber"
    assert user.accounts[2].address == "jesuslara@jesuslara.com"

    # created_at should default to a datetime
    assert isinstance(user.created_at, datetime)

def test_user_model_validation_error():
    """Demonstrate that missing/invalid data leads to ValidationError."""
    invalid_data = {
        # 'id' is missing
        'signup_ts': 'invalid-date-format',
        'friends': 'not a list',  # also invalid type
        "accounts": []
    }
    with pytest.raises(ValueError) as excinfo:
        User(**invalid_data)
    # We expect ValueError, now we can inspect `excinfo.value` if needed.
    assert "id" in str(excinfo.value)
