from datetime import datetime
from typing import Any
from datamodel import BaseModel, Column
from datamodel.exceptions import ValidationError


class User(BaseModel):
    user_id: int = Column(required=True, primary_key=True)
    name: str = Column(required=False)
    email: str = Column(required=False)
    created_at: datetime = Column(required=False, default=datetime.now())
    created_by: str = Column(required=False)

    class Meta:
        name = "users"
        as_objects = True
        schema = "public"
        strict = True
        connection = None
        frozen = False

class Group(BaseModel):
    group_id: int = Column(required=True, primary_key=True)
    name: str = Column(required=True)
    created_at: datetime = Column(required=False, default=datetime.now())
    created_by: str = Column(required=False)

    class Meta:
        name = "groups"
        schema = "public"
        strict = True
        connection = None
        frozen = False

class UserGroup(BaseModel):
    user_id: User = Column(required=True, primary_key=True)
    group_id: Group = Column(required=True, primary_key=True)
    created_at: datetime = Column(required=False, default=datetime.now())
    created_by: str = Column(required=False)

    class Meta:
        name = "user_groups"
        schema = "public"
        strict = True
        connection = None
        frozen = False


class UserAttributes(BaseModel):
    user_id: User = Column(required=True, primary_key=True)
    attributes: dict = Column(required=False, default_factory=dict)

    class Meta:
        name = "users_attributes"
        schema = "public"
        strict = True
        connection = None
        frozen = False
        as_objects = True


# Path: examples/validate_user.py
try:
    user = User(user_id=1, name="user1", email="email1")
    print(user)
except ValidationError as e:
    print(e.payload)

def create_user(name: str, value: Any, target_type: Any, *args, **kwargs):
    print('Target: ', target_type, value, name)
    args = {
        name: value,
        "name": "John Doe",
        "created_by": "John Doe",
    }
    return target_type(**args)

BaseModel.register_parser(User, create_user, 'user_id')

try:
    user_attributes = UserAttributes(user_id=1, attributes={"key": "value"})
    print(user_attributes)
    print('export user attributes')
    print(user_attributes.to_json())
except ValidationError as e:
    print(e.payload)

# UserAttributes.Meta.as_objects = True
# try:
#     user_attributes = UserAttributes(user_id=1, attributes={"key": "value"})
#     print(user_attributes)
# except ValidationError as e:
#     print(e.payload)
