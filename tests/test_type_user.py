# test_employee.py
from typing import Type, Union
import pytest
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

# NOTE: In your converters/validation modules you must support such fields by:
# - Checking that get_origin(annotated_type) is type.
# - Extracting get_args(annotated_type) and verifying that
#   the supplied value is a type and a subclass of one of the allowed types.

# Example test functions below:

def test_valid_employee_basic():
    """Test that an Employee can be created with BasicUser as its user_class."""
    emp = Employee(user_class=BasicUser)
    # Verify that the field user_class was correctly set to BasicUser
    assert emp.user_class is BasicUser

def test_valid_employee_pro():
    """Test that an Employee can be created with ProUser as its user_class."""
    emp = Employee(user_class=ProUser)
    assert emp.user_class is ProUser

def test_invalid_employee_team():
    """Test that assigning a type not allowed (TeamUser) raises a validation error."""
    with pytest.raises(ValidationError) as excinfo:
        Employee(user_class=User)
    errors = excinfo.value.payload
    # Check that the error mentions the 'user_class' field and the allowed types.
    assert "user_class" in errors
    error_message = errors["user_class"]["error"]
    assert "type" in error_message

# For manual testing when running this file directly:
if __name__ == "__main__":
    test_valid_employee_basic()
    test_valid_employee_pro()
    try:
        test_invalid_employee_team()
    except Exception as e:
        print("Expected error:", e)
