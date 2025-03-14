import pytest
from typing import Union, List, Dict, Optional
from dataclasses import dataclass
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class UnionStrDictModel(BaseModel):
    """
    This model has a field that can be either a string or a dict
    """
    data: Union[str, dict] = Field(required=True)


class UnionStrListModel(BaseModel):
    """
    This model has a field that can be either a string or a list of strings
    """
    items: Union[str, List[str]] = Field(required=True)


class ComplexUnionModel(BaseModel):
    """
    This model demonstrates a nested union inside a dict, and is optional
    e.g. Optional[Dict[str, Union[int, Dict[str, int]]]]
    """
    widget_location: Optional[Dict[str, Union[int, Dict[str, int]]]] = Field(required=False)


#
# Tests for Union[str, dict]
#

@pytest.mark.parametrize(
    "value",
    [
        "Hello World",
        {"key": "value", "another": 123},  # valid dict
    ],
    ids=["string_value", "dict_value"]
)
def test_union_str_dict_valid(value):
    model = UnionStrDictModel(data=value)
    assert model.data == value


@pytest.mark.parametrize(
    "value",
    [
        3.14,            # float is not str or dict
        ["not", "valid"] # list is not str or dict
    ],
    ids=["float_value", "list_value"]
)
def test_union_str_dict_invalid(value):
    with pytest.raises(ValueError):
        UnionStrDictModel(data=value)


#
# 3) Tests for Union[str, List[str]]
#

@pytest.mark.parametrize(
    "value",
    [
        "single string",
        ["list", "of", "strings"],
    ],
    ids=["string_value", "list_of_strings"]
)
def test_union_str_list_valid(value):
    m = UnionStrListModel(items=value)
    # check that it stored correctly
    assert m.items == value


@pytest.mark.parametrize(
    "value",
    [
        {"not": "valid"},
        ("single string",),  # tuple is not valid
    ],
    ids=["dict_value", "tuple_of_strings"]
)
def test_union_str_list_invalid(value):
    with pytest.raises(ValueError):
        UnionStrListModel(items=value)


#
# 4) Tests for Optional[Dict[str, Union[int, Dict[str, int]]]]
#    i.e. a nested union inside a dict, or None

def test_complex_union_model_valid_none():
    # Allowed to be None because of Optional
    m = ComplexUnionModel(widget_location=None)
    assert m.widget_location is None

def test_complex_union_model_valid_dict_all_ints():
    # Dict with only int values
    valid_val = {"foo": 10, "bar": 9999}
    m = ComplexUnionModel(widget_location=valid_val)
    assert m.widget_location == valid_val

def test_complex_union_model_valid_dict_mixed():
    # Some keys are int, some keys are dict[str, int]
    valid_val = {
        "timestamp": 1735573243363,
        "nested": {"x": 1, "y": 2},  # dict[str,int]
    }
    m = ComplexUnionModel(widget_location=valid_val)
    assert m.widget_location == valid_val

@pytest.mark.parametrize(
    "value",
    [
        "not_a_dict",                 # union expects dict or None
    ],
    ids=["not_a_dict"]
)
def test_complex_union_model_invalid(value):
    with pytest.raises(ValidationError):
        ComplexUnionModel(widget_location=value)
