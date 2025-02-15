# tests/test_default_behavior.py

import pytest
from typing import Optional, Dict, Mapping, Sequence, List, Callable, Union
from datetime import datetime
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

class DummyModel(BaseModel):
    # A field that accepts an optional dict
    dwh_scheduler: Optional[dict] = Field(required=False, db_type='jsonb')
    attributes: Optional[Dict[str, str]] = Field(required=False, db_type='jsonb')
    other_field: str = Field(required=True)
    example: Mapping[str, str | int] = Field(required=False)
    more_nested: Mapping[str, Union[str, int]] = Field(required=False)

    class Meta:

        strict = True
        remove_nulls = True

def test_empty_dict_kept():
    # When an empty dictionary is provided, it should remain {} (and not become None).
    data = {
        'other_field': 'test value',
        'dwh_scheduler': {},  # payload provides an empty dict
        'attributes': {"example": "value"},
        "example": {"a": "hello", "b": 123},
        "more_nested": {"a": "hello", "b": 123}
    }
    try:
        model = DummyModel(**data)
    except ValidationError as e:
        print(e.payload)  # Should not raise an error, as we're using strict and remove_nulls.
    # We expect that after processing, dwh_scheduler is still an empty dict.
    # (Depending on your implementation and remove_nulls logic, you might have to
    #  adjust whether an empty dict is considered "null" or not.)
    assert model.dwh_scheduler == {}, "Empty dict should be preserved, not replaced with None"
    assert model.attributes == {"example": "value"}, "Empty dict should be preserved, not replaced with None"

def test_none_value():
    # When a field is not provided, it should default to None.
    data = {
        'other_field': 'test value',
        # dwh_scheduler is missing from the payload
    }
    model = DummyModel(**data)
    assert model.dwh_scheduler is None, "Missing field should be None"

if __name__ == "__main__":
    pytest.main([__file__])
