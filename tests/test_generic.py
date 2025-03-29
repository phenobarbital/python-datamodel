from typing import Optional, List, Dict, Tuple, Set, Union, Any
from datetime import datetime, date
import uuid
from dataclasses import dataclass, is_dataclass
import pytest
from datamodel import BaseModel, Field


@dataclass
class Address:
    street: str
    zipcode: int
    coordinates: Optional[Tuple[float, float]] = None


@dataclass
class Tag:
    name: str
    value: str


def auto_uuid(*args, **kwargs):
    return uuid.uuid4()


class Account(BaseModel):
    """
    Attributes for using a Provider by a User (Actor)
    """
    class Meta:
        strict = True
        frozen = False

    provider: str = Field(required=True, default='dummy')
    enabled: bool = Field(required=True, default=True)
    # Testing the bare list type (which caused the original error)
    address: list = Field(required=False, default_factory=list)
    # Testing mixed type with Union
    phone: Union[str, list] = Field(required=False, default='')
    # Testing typed list
    contacts: List[str] = Field(required=False, default_factory=list)
    # Testing bare dict
    metadata: dict = Field(required=False, default_factory=dict)
    # Testing bare tuple
    config: tuple = Field(required=False, default_factory=tuple)


class User(BaseModel):
    """
    User model with various generic aliases
    """
    class Meta:
        strict = True
        frozen = False

    # Basic fields
    id: int
    uid: uuid.UUID = Field(primary_key=True, default=auto_uuid)
    name: str = 'John Doe'

    # Date/time fields
    signup_ts: Optional[datetime] = None
    born: Optional[date] = None
    # Generic alias fields
    friends: List[int] = Field(default_factory=list)  # Typed list
    roles: list = Field(default_factory=list)         # Bare list
    # Nested dataclass
    address: Optional[Address] = None
    # List of dataclasses
    accounts: List[Account] = Field(default_factory=list)
    # Dictionary with string keys and integer values
    scores: Dict[str, int] = Field(default_factory=dict)
    # Bare dictionary
    properties: dict = Field(default_factory=dict)
    # Tuple of strings
    nicknames: Tuple[str, ...] = Field(default_factory=tuple)
    # Bare tuple
    settings: tuple = Field(default_factory=tuple)
    # Set of strings
    permissions: Set[str] = Field(default_factory=set)
    # Bare set
    groups: set = Field(default_factory=set)
    # Dictionary with nested structure
    profile: Dict[str, Any] = Field(default_factory=dict)
    # List of tagged items (list of dataclasses)
    tags: List[Tag] = Field(default_factory=list)
    # Union type with primitive types
    status: Union[str, int, bool] = Field(default="active")
    # Creation timestamp
    created_at: datetime = Field(default=datetime.now)


# Test data
external_data = {
    'id': '123',
    'signup_ts': '2017-06-01 12:22',
    'born': '23-10-1978',
    'friends': [1, '2', '3'],
    'roles': ['admin', 'user', 'guest'],
    "address": {
        "street": "Calle Mayor",
        "zipcode": 45510,
        "coordinates": (40.416775, -3.703790)
    },
    "accounts": [
        {
            "provider": "twilio",
            "phone": "+343317871",
            "contacts": ["support", "sales"]
        },
        {
            "provider": "email",
            "address": ["user@example.com", "admin@example.com"],
            "metadata": {"verified": True, "primary": True}
        },
        {
            "provider": "jabber",
            "address": ["user@jabber.org"],
            "config": ("encrypted", "auto-login")
        }
    ],
    "scores": {
        "math": 95,
        "science": 88,
        "history": 75
    },
    "properties": {
        "premium": True,
        "notification_settings": {"email": True, "sms": False}
    },
    "nicknames": ("Johnny", "JD", "Doe"),
    "settings": ("dark_mode", "compact_view", "notifications_enabled"),
    "permissions": ["read", "write", "delete"],
    "groups": ["developers", "testers", "admins"],
    "profile": {
        "bio": "Python developer",
        "links": {
            "github": "https://github.com/johndoe",
            "linkedin": "https://linkedin.com/in/johndoe"
        },
        "skills": ["Python", "Django", "FastAPI"]
    },
    "tags": [
        {"name": "language", "value": "python"},
        {"name": "framework", "value": "django"}
    ],
    "status": "active"
}


@pytest.fixture
def user():
    return User(**external_data)


def test_is_dataclass(user):
    """Test that the user object is a dataclass"""
    assert is_dataclass(user)


def test_basic_fields(user):
    """Test basic field types"""
    assert user.id == 123
    assert isinstance(user.id, int)
    assert user.name == 'John Doe'
    assert isinstance(user.uid, uuid.UUID)


def test_datetime_fields(user):
    """Test datetime and date fields"""
    assert str(user.signup_ts) == '2017-06-01 12:22:00'
    dt = datetime(2017, 6, 1, 12, 22, 00)
    assert isinstance(user.signup_ts, datetime)
    assert dt == user.signup_ts

    assert str(user.born) == '1978-10-23'
    dt = date(1978, 10, 23)
    assert isinstance(user.born, date)
    assert dt == user.born


def test_list_fields(user):
    """Test various list type fields"""
    # Typed list
    assert len(user.friends) == 3
    assert all(isinstance(f, int) for f in user.friends)

    # Bare list
    assert len(user.roles) == 3
    assert user.roles == ['admin', 'user', 'guest']


def test_address_nested_dataclass(user):
    """Test nested dataclass field"""
    assert type(user.address) == Address
    assert is_dataclass(user.address)
    assert user.address.street == "Calle Mayor"
    assert user.address.zipcode == 45510
    assert user.address.coordinates == (40.416775, -3.703790)


def test_accounts_list_of_dataclasses(user):
    """Test list of dataclasses field"""
    assert len(user.accounts) == 3
    assert all(isinstance(account, Account) for account in user.accounts)

    # Check individual accounts
    twilio_account = next(acc for acc in user.accounts if acc.provider == 'twilio')
    assert twilio_account.phone == "+343317871"
    assert twilio_account.contacts == ["support", "sales"]

    email_account = next(acc for acc in user.accounts if acc.provider == 'email')
    assert email_account.address == ["user@example.com", "admin@example.com"]
    assert email_account.metadata == {"verified": True, "primary": True}

    jabber_account = next(acc for acc in user.accounts if acc.provider == 'jabber')
    assert jabber_account.address == ["user@jabber.org"]
    assert jabber_account.config == ("encrypted", "auto-login")


def test_dict_fields(user):
    """Test dictionary fields"""
    # Typed dict
    assert user.scores["math"] == 95
    assert user.scores["science"] == 88
    assert user.scores["history"] == 75

    # Bare dict
    assert user.properties["premium"] is True
    assert user.properties["notification_settings"]["email"] is True
    assert user.properties["notification_settings"]["sms"] is False


def test_tuple_fields(user):
    """Test tuple fields"""
    # Typed tuple
    assert user.nicknames == ("Johnny", "JD", "Doe")

    # Bare tuple
    assert user.settings == ("dark_mode", "compact_view", "notifications_enabled")


def test_set_fields(user):
    """Test set fields"""
    # Typed set
    assert user.permissions == {"read", "write", "delete"}

    # Bare set
    assert user.groups == {"developers", "testers", "admins"}


def test_nested_dict_field(user):
    """Test nested dictionary field"""
    assert user.profile["bio"] == "Python developer"
    assert user.profile["links"]["github"] == "https://github.com/johndoe"
    assert user.profile["links"]["linkedin"] == "https://linkedin.com/in/johndoe"
    assert user.profile["skills"] == ["Python", "Django", "FastAPI"]


def test_list_of_dataclasses_field(user):
    """Test list of dataclasses field"""
    assert len(user.tags) == 2
    assert all(isinstance(tag, Tag) for tag in user.tags)

    language_tag = next(tag for tag in user.tags if tag.name == "language")
    assert language_tag.value == "python"

    framework_tag = next(tag for tag in user.tags if tag.name == "framework")
    assert framework_tag.value == "django"


def test_union_field(user):
    """Test union field"""
    assert user.status == "active"


def test_created_at_field(user):
    """Test created_at field"""
    assert isinstance(user.created_at, datetime)


def test_bare_container_types():
    """Test creating a user with bare container types"""
    # This tests creating instances with various bare container types
    # which should not cause IndexError
    user_data = {
        'id': 456,
        'roles': [],              # Empty bare list
        'properties': {},         # Empty bare dict
        'settings': (),           # Empty bare tuple
        'groups': set(),          # Empty bare set
        'accounts': [
            {
                'provider': 'test',
                'address': [],    # Empty bare list in nested object
                'metadata': {},   # Empty bare dict in nested object
                'config': ()      # Empty bare tuple in nested object
            }
        ]
    }

    # This should not raise an IndexError
    user = User(**user_data)

    assert user.id == 456
    assert user.roles == []
    assert user.properties == {}
    assert user.settings == ()
    assert user.groups == set()
    assert len(user.accounts) == 1
    assert user.accounts[0].address == []
    assert user.accounts[0].metadata == {}
    assert user.accounts[0].config == ()


def test_modification_of_container_types(user):
    """Test modifying container type fields"""
    # Add to lists
    user.roles.append('supervisor')
    assert 'supervisor' in user.roles

    # Add to dict
    user.properties['theme'] = 'light'
    assert user.properties['theme'] == 'light'

    # Add to set
    user.groups.add('managers')
    assert 'managers' in user.groups

    # Can't add to tuple (immutable), but we can test reassignment
    new_nicknames = user.nicknames + ('J',)
    user.nicknames = new_nicknames
    assert user.nicknames[-1] == 'J'
