from typing import Optional
from datetime import datetime
from enum import Enum
from datamodel import BaseModel, Column


class Address(BaseModel):
    street_address: str
    postal_code: str


class UserType(Enum):
    CUSTOMER = 'customer'
    STAFF  = 'staff'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    ROOT = 'superuser'

class User(BaseModel):
    """Basic User Model for authentication."""

    user_id: int = Column(required=False, primary_key=True, repr=False)
    first_name: str = Column(required=True, max=254, label="First Name", pattern="^\w*$")
    last_name: str = Column(required=True, max=254, label="Last Name")
    email: str = Column(required=False, max=254, label="User's Email")
    password: str = Column(required=False, max=16, secret=True, widget='/properties/password')
    last_login: datetime = Column(required=False, format='YYYY-MM-DD', readonly=True)
    username: str = Column(required=False)
    user_type: UserType = Column(required=False)
    is_superuser: bool = Column(required=True, default=False, widget='/properties/toggle')
    is_active: bool = Column(required=True, default=True)
    is_new: bool = Column(required=True, default=True)
    is_staff: bool = Column(required=False, default=True)
    title: str = Column(equired=False, max=90)
    registration_key: str = Column(equired=False, max=512, repr=False, readonly=True)
    reset_pwd_key: str = Column(equired=False, max=512, repr=False, readonly=True)
    avatar: str = Column(max=512, repr=False)
    associate_id: str = Column(required=False, repr=False)
    group_id: list[int] = Column(required=False)
    groups: list = Column(required=False)
    programs: list = Column(required=False)
    attributes: Optional[dict] = Column(required=False, default_factory=dict)
    address: Address = Column(required=False)

    def __getitem__(self, item):
        return getattr(self, item)

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        name = 'users'
        schema = 'public'
        strict = True
        frozen = False


### Getting the JSON-Schema Object for this Model:
schema = User.schema()
print(schema)
