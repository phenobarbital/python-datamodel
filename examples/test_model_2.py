from typing import Optional
from datetime import datetime
import pprint
from enum import Enum
from datamodel import BaseModel, Column
from datamodel.types import Text


pp = pprint.PrettyPrinter(width=41, compact=True)

def IdentityField():
    return Column(required=False, primary_key=True, db_default='auto', repr=False)

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
    first_name: Text = Column(required=True, max=254, label="First Name", pattern="^\w*$")
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
    avatar: Text = Column(max=512, repr=False)
    associate_id: str = Column(required=False, repr=False)
    group_id: list[int] = Column(required=False)
    groups: list = Column(required=False)
    programs: list = Column(required=False)
    attributes: Optional[dict] = Column(required=False, default_factory=dict)
    address: Address = Column(required=False)

    class Meta:
        name = 'users'
        schema = 'public'
        strict = True


class UserIdentity(BaseModel):
    user_id: User = Column(required=True)
    auth_provider: str = Column(required=True, default="BasicAuth")
    uid: str = Column(required=True, comment="User Id on Auth Backend")
    auth_data: Optional[dict] = Column(required=False, default_factory=dict)
    attributes: Optional[dict] = Column(required=False, default_factory=dict)
    created_at: datetime = Column(required=False, default=datetime.now())

    class Meta:
        name = "user_identities"
        schema = "public"
        strict = True
        connection = None


class Company(BaseModel):

    company_id: int = IdentityField()
    company_name: str = Column(required=True)
    identity_id: UserIdentity = Column(
        required=True, fk="identity_id|display_name", api="user_identity", label="user identities"
    )
    description: Text = Column(required=False)
    is_prospect: bool = Column(required=False, default=True,)
    website: str = Column(required=False)
    phone: str = Column(required=False)
    address: str = Column(required=False)
    city: str = Column(required=False)
    state_code: str = Column(required=False)
    country_code: str = Column(required=False)
    zipcode: str = Column(required=False)
    observation: Text = Column(required=False)
    created_at: datetime = Column(required=False, default=datetime.now(), repr=False)

    class Meta:
        name = "companies"
        schema = "public"
        strict = True
        connection = None


### Nested Models: schema
### Getting the JSON-Schema Object for this Model:
schema = Company.schema(as_dict=False)
print(schema)
### also, a sample
# pp.pprint(Company.sample())
