from typing import List, Union
import pytest
from dataclasses import is_dataclass
from datamodel import BaseModel


class Foo(BaseModel):
    value: Union[List[int], int]


class Bar(BaseModel):
    foo: Union[Foo, List[Foo]]


def test_nested_dataclasses():
    f = Foo(value=[1, 2])
    instance = Bar(foo=f)
    assert is_dataclass(instance)

    # Assert that the instances are valid
    assert instance.is_valid()

    ### check Foo value:
    assert instance.foo.value == [1, 2]

    # Assert that the instances are equal
    assert instance == Bar(foo=Foo(value=[1, 2]))

    # Assert that Foo and Bar are dataclasses
    assert isinstance(f, BaseModel)
    assert isinstance(instance, BaseModel)
