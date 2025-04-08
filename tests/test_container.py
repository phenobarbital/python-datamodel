from typing import Optional, List, Dict, Tuple, Set, Union, Any, FrozenSet
import uuid
from datetime import datetime
from dataclasses import is_dataclass
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class ContainerTypesModel(BaseModel):
    """Model with different container types"""
    class Meta:
        strict = True
        frozen = False

    # Bare container types (without type arguments)
    bare_list: list = Field(default_factory=list)
    bare_dict: dict = Field(default_factory=dict)
    bare_tuple: tuple = Field(default_factory=tuple)
    bare_set: set = Field(default_factory=set)

    # Typed container types
    typed_list: List[int] = Field(default_factory=list)
    typed_dict: Dict[str, str] = Field(default_factory=dict)
    typed_tuple: Tuple[str, ...] = Field(default_factory=tuple)
    typed_set: Set[str] = Field(default_factory=set)

    # Nested container types
    nested_list: List[List[int]] = Field(default_factory=list)
    nested_dict: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    # Union types with containers
    union_list: Union[List[int], str] = Field(default=None)
    union_dict: Union[Dict[str, int], int] = Field(default=None)
    union_set: Union[Set[str], List[Set[str]]] = Field(default=None)

    # Optional container types
    optional_list: Optional[List[int]] = Field(default=None)
    optional_dict: Optional[Dict[str, int]] = Field(default=None)
    optional_set: Optional[Set[str]] = Field(default=None)

    # Empty containers - these should not fail
    empty_list: List[int] = Field(default_factory=list)
    empty_set: Set[str] = Field(default_factory=set)
    empty_dict: Dict[str, int] = Field(default_factory=dict)
    empty_tuple: Tuple[int, ...] = Field(default_factory=tuple)

    # FrozenSet (less common but should work)
    frozen_set: FrozenSet[str] = Field(default_factory=frozenset)


@pytest.fixture
def model_with_data():
    """Create a model with actual data"""
    return ContainerTypesModel(
        bare_list=["a", "b", 1, 2],
        bare_dict={"a": 1, "b": 2},
        bare_tuple=("x", "y", 1, 2),
        bare_set={"a", "b", "c"},

        typed_list=[1, 2, 3, 4],
        typed_dict={"a": "A", "b": "B"},
        typed_tuple=("x", "y", "z"),
        typed_set={"a", "b", "c"},

        nested_list=[[1, 2], [3, 4]],
        nested_dict={"a": {"x": 1, "y": 2}, "b": {"z": 3}},

        union_list=[1, 2, 3],
        union_dict={"a": 1, "b": 2},
        union_set={"a", "b", "c"},

        optional_list=[1, 2, 3],
        optional_dict={"a": 1, "b": 2},
        optional_set={"a", "b", "c"},

        frozen_set=frozenset(["x", "y", "z"])
    )


@pytest.fixture
def model_with_empty_data():
    """Create a model with all empty containers"""
    return ContainerTypesModel()


def test_model_creation():
    """Test that we can create a model with default values"""
    model = ContainerTypesModel()
    assert is_dataclass(model)

    # Check default empty containers
    assert model.bare_list == []
    assert model.bare_dict == {}
    assert model.bare_tuple == ()
    assert model.bare_set == set()


def test_model_with_data(model_with_data):
    """Test a model with various container data"""
    # Verify basic containers
    assert isinstance(model_with_data.bare_list, list)
    assert isinstance(model_with_data.bare_dict, dict)
    assert isinstance(model_with_data.bare_tuple, tuple)
    assert isinstance(model_with_data.bare_set, set)

    # Verify typed containers
    assert all(isinstance(x, int) for x in model_with_data.typed_list)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in model_with_data.typed_dict.items())
    assert all(isinstance(x, str) for x in model_with_data.typed_tuple)
    assert all(isinstance(x, str) for x in model_with_data.typed_set)

    # Verify nested structures
    assert all(isinstance(sublist, list) for sublist in model_with_data.nested_list)
    assert all(isinstance(subdict, dict) for subdict in model_with_data.nested_dict.values())

    # Verify union types
    assert isinstance(model_with_data.union_list, list)
    assert isinstance(model_with_data.union_dict, dict)
    assert isinstance(model_with_data.union_set, set)

    # Verify optional types
    assert isinstance(model_with_data.optional_list, list)
    assert isinstance(model_with_data.optional_dict, dict)
    assert isinstance(model_with_data.optional_set, set)

    # Verify frozen set
    assert isinstance(model_with_data.frozen_set, frozenset)


def test_empty_containers(model_with_empty_data):
    """Test a model with empty containers"""
    # All containers should be empty but initialized
    assert model_with_empty_data.empty_list == []
    assert model_with_empty_data.empty_set == set()
    assert model_with_empty_data.empty_dict == {}
    assert model_with_empty_data.empty_tuple == ()

    # Optional containers should be None
    assert model_with_empty_data.optional_list is None
    assert model_with_empty_data.optional_dict is None
    assert model_with_empty_data.optional_set is None


def test_modification_of_containers(model_with_empty_data):
    """Test modifying container fields"""
    # Add to bare containers
    model_with_empty_data.bare_list.append("new_item")
    assert "new_item" in model_with_empty_data.bare_list

    model_with_empty_data.bare_dict["new_key"] = "new_value"
    assert model_with_empty_data.bare_dict["new_key"] == "new_value"

    # Can't append to tuple, but we can reassign
    model_with_empty_data.bare_tuple = ("new_item",)
    assert model_with_empty_data.bare_tuple == ("new_item",)

    # Add to set
    model_with_empty_data.bare_set.add("new_item")
    assert "new_item" in model_with_empty_data.bare_set

    # Add to typed containers
    model_with_empty_data.typed_list.append(42)
    assert 42 in model_with_empty_data.typed_list

    model_with_empty_data.typed_dict["key"] = "value"
    assert model_with_empty_data.typed_dict["key"] == "value"

    model_with_empty_data.typed_set.add("element")
    assert "element" in model_with_empty_data.typed_set


def test_type_conversion():
    """Test type conversion for containers"""
    # Test converting types for list
    model = ContainerTypesModel(typed_list=["1", "2", "3"])  # Strings should convert to ints
    assert all(isinstance(x, int) for x in model.typed_list)
    assert model.typed_list == [1, 2, 3]

    # Test with mixed string/int input that should convert properly
    model = ContainerTypesModel(typed_list=[1, "2", 3])
    assert all(isinstance(x, int) for x in model.typed_list)
    assert model.typed_list == [1, 2, 3]


def test_union_type_behavior():
    """Test behavior with union types"""
    # Test union with string alternative
    try:
        model = ContainerTypesModel(union_list="not a list")
    except ValidationError as e:
        print(e.payload)
    assert model.union_list == "not a list"

    # Test union with proper list
    model = ContainerTypesModel(union_list=[1, 2, 3])
    assert model.union_list == [1, 2, 3]

    # Test union with set
    model = ContainerTypesModel(union_set="not a set")
    assert model.union_set == {'not a set'}

    model = ContainerTypesModel(union_set={"a", "b"})
    assert model.union_set == {"a", "b"}


def test_optional_containers():
    """Test behavior with optional containers"""
    # Default is None
    model = ContainerTypesModel()
    assert model.optional_list is None
    assert model.optional_set is None

    # Explicit None
    model = ContainerTypesModel(optional_list=None, optional_set=None)
    assert model.optional_list is None
    assert model.optional_set is None

    # With values
    model = ContainerTypesModel(optional_list=[1, 2], optional_set={"a", "b"})
    assert model.optional_list == [1, 2]
    assert model.optional_set == {"a", "b"}


def test_problematic_set_handling():
    """Test specifically focused on set handling which was causing issues"""
    class UserWithSets(BaseModel):
        groups: set = Field(default_factory=set)
        permissions: Set[str] = Field(default_factory=set)

    # Test with empty sets (default factory)
    user = UserWithSets()
    assert user.groups == set()
    assert user.permissions == set()

    # Test with provided data
    user = UserWithSets(groups={"admins", "users"}, permissions={"read", "write"})
    assert user.groups == {"admins", "users"}
    assert user.permissions == {"read", "write"}

    # Test modification
    user.groups.add("developers")
    assert "developers" in user.groups

    user.permissions.add("delete")
    assert "delete" in user.permissions


def test_nested_containers():
    """Test deeply nested container structures"""
    model = ContainerTypesModel(
        nested_list=[[1, 2], [3, "4"]],  # Note "4" should convert to 4
        nested_dict={
            "a": {"x": 1, "y": "2"},  # Note "2" should convert to 2
            "b": {"z": 3}
        }
    )

    # Check the nested structure is preserved
    assert model.nested_list[0] == [1, 2]
    assert model.nested_list[1] == [3, 4]  # "4" should convert to 4

    assert model.nested_dict["a"]["x"] == 1
    assert model.nested_dict["a"]["y"] == 2  # "2" converted to 2
    assert model.nested_dict["b"]["z"] == 3
