import pytest
from dataclasses import dataclass
from datamodel import BaseModel


# First descriptor: Integer conversion
class IntConversionDescriptor:
    def __init__(self, *, default):
        self._default = default

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, int(value))


# Second descriptor: String trimming
class StringTrimDescriptor:
    def __init__(self, *, default=""):
        self._default = default

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, value.strip() if isinstance(value, str) else value)


# BaseModel integration
@dataclass
class InventoryItem(BaseModel):
    quantity_on_hand: IntConversionDescriptor = IntConversionDescriptor(default=100)
    description: StringTrimDescriptor = StringTrimDescriptor(default="No description")


# Test cases
@pytest.fixture
def inventory_item():
    return InventoryItem()


def test_int_conversion_descriptor_default(inventory_item):
    # Default value check
    assert inventory_item.quantity_on_hand == 100


def test_int_conversion_descriptor_set_value(inventory_item):
    # Assigning float, should convert to int
    inventory_item.quantity_on_hand = 20.75
    assert inventory_item.quantity_on_hand == 20

    # Assigning integer, should remain as integer
    inventory_item.quantity_on_hand = 42
    assert inventory_item.quantity_on_hand == 42


def test_string_trim_descriptor_default(inventory_item):
    # Default value check
    assert inventory_item.description == "No description"


def test_string_trim_descriptor_set_value(inventory_item):
    # Assigning string with extra spaces
    inventory_item.description = "   Trimmed String   "
    assert inventory_item.description == "Trimmed String"

    # Assigning integer, should not modify
    inventory_item.description = 123
    assert inventory_item.description == 123


def test_combined_descriptors(inventory_item):
    # Test both descriptors together
    inventory_item.quantity_on_hand = 15.5
    inventory_item.description = "   Combined Test   "
    assert inventory_item.quantity_on_hand == 15
    assert inventory_item.description == "Combined Test"
