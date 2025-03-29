from typing import Optional, List, Dict, Tuple, Set, Union, Any
from datetime import datetime, date
import uuid
from dataclasses import dataclass
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


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

if __name__ == "__main__":
    try:
        user = User(**external_data)
        print(user)
    except ValidationError as e:
        print(e.payload)
