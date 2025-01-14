from typing import Type, Union
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

# Define a basic user hierarchy.
class User(BaseModel):
    username: str = Field(required=True)
    email: str = Field(required=True)

class BasicUser(User):
    level: str = Field(default="basic")

class ProUser(User):
    level: str = Field(default="pro")
    perks: list = Field(default_factory=list)

# Employee model whose user_class field must be a type (class)
# that is either BasicUser or ProUser.
class Employee(BaseModel):
    # The type hint below means: user_class must be a type (class)
    # that is a subclass of either BasicUser or ProUser.
    user_class: type[BasicUser | ProUser] = Field(required=True)


try:
    # This should raise a ValidationError because the type hint
    # specifies that user_class must be a type (class), not an instance.
    user = BasicUser(username="user", email="email")
    employee = Employee(user_class=user)
    print(employee)
except ValidationError as e:
    print(e.payload)

try:
    # This should raise a ValidationError because the type hint
    # specifies that user_class must be a type (class), not an instance.
    user = User(username="user", email="email")
    employee = Employee(user_class=user)
    print(employee)
except ValidationError as e:
    print(e.payload)
