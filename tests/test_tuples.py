import pytest
from datetime import datetime
from typing import Tuple, Optional, List, Mapping
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

# Example model including a heterogeneous tuple field and a homogeneous tuple field.
class TupleModel(BaseModel):
    # Heterogeneous tuple: first element string, second element int
    hetero: Tuple[str, int] = Field(required=True)
    # Homogeneous tuple: only floats allowed (any length)
    homo: Tuple[float, ...] = Field(required=True)
    # Optional homogeneous tuple
    optional_homo: Optional[Tuple[float, ...]] = Field(required=False)

def test_required_tuple_fields():
    payload = {
        "hetero": ("test", 123), # required field
    }
    with pytest.raises(ValueError):
        TupleModel(**payload)

def test_heterogeneous_tuple():
    payload = {
        "hetero": ("test", "123"),  # note the second element is a string that should be converted to int
    }
    instance = TupleModel(**payload, homo=(1.0, 2.0))  # provide homo field as floats
    assert isinstance(instance.hetero, tuple)
    # Check that the first element is a string and the second is an int
    h0, h1 = instance.hetero
    assert isinstance(h0, str)
    assert isinstance(h1, int)
    assert h0 == "test"
    assert h1 == 123

def test_homogeneous_tuple():
    payload = {
        "hetero": ("example", 10),
        "homo": ("3.14", 2.718, 1.414)  # these values should be converted to floats if necessary
    }
    instance = TupleModel(**payload)
    assert isinstance(instance.homo, tuple)
    for value in instance.homo:
        assert isinstance(value, float)
    assert instance.homo == (3.14, 2.718, 1.414)

def test_invalid_tuple_length():
    payload = {
        "hetero": ("test",),  # incorrect length
        "homo": (1.1, 2.2)
    }
    with pytest.raises(ValidationError):
        TupleModel(**payload)

def test_optional_tuple():
    payload = {
        "hetero": ("test", 123),
        "homo": (1.1, 2.2),
        "optional_homo": (1.1, 2.2)
    }
    instance = TupleModel(**payload)
    assert instance.optional_homo == (1.1, 2.2)


if __name__ == "__main__":
    pytest.main([__file__])
