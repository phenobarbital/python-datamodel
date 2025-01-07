# tests/test_alias_function.py
import pytest
from datamodel import BaseModel, Field
from datamodel.aliases import to_snakecase

class Store(BaseModel):
    # Fields (with normal pythonic names)
    email_address: str
    status: str
    store_id: int = Field(primary_key=True)

    class Meta:
        strict = True
        as_objects = True
        # The function that transforms keys (e.g., EmailAddress -> email_address)
        alias_function = to_snakecase

class User(BaseModel):
    email_address: str = Field(alias='emailAddress')

def test_alias_function_store():
    """Ensure that the alias_function (to_snakecase) properly converts keys."""
    # We pass in uppercase/camelcase versions of the fields:
    store = Store(emailAddress="test@example.com", Status="ACTIVE", StoreId=123)
    # Now we verify that the model's actual attributes got populated correctly:
    assert store.email_address == "test@example.com"
    assert store.status == "ACTIVE"
    assert store.store_id == 123

    # Check the model's type and printing
    assert isinstance(store, Store)
    print(f"Created store: {store}")


def test_alias_simple_store():
    """Ensure that Alias on Field is properly managed."""
    # We pass in uppercase/camelcase versions of the fields:
    user = User(emailAddress="Test@Test")
    assert user.email_address == "Test@Test"

    # Check the model's type and printing
    assert isinstance(user, User)
