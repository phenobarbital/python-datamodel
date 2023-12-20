import pprint
from enum import Enum
from datamodel import BaseModel, Field

pp = pprint.PrettyPrinter(indent=4, compact=False)

class UserType(Enum):
    CUSTOMER = 'customer'
    STAFF = 'staff'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    ROOT = 'superuser'

class User(BaseModel):
    user_id: int = Field(required=False, primary_key=True, repr=False)
    first_name: str = Field(required=True, max=254, label="First Name", pattern="^\w*$")
    last_name: str = Field(required=True, max=254, label="Last Name")
    email: str = Field(required=False, max=254, label="User's Email")
    user_type: UserType = Field(required=False, default=UserType.CUSTOMER)

schema = User.schema(as_dict=False)
pp.pprint(schema)
