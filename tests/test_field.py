from typing import Optional
from dataclasses import dataclass, _MISSING_TYPE
import pytest
from datamodel.fields import Field, Column
from datamodel.types import default_dict


def test_field_defaults():
    f = Field()
    assert f.default is None
    assert isinstance(f.default_factory, _MISSING_TYPE)
    assert f.required() is False
    assert f.nullable() is True
    assert f.primary_key is False
    assert f.db_type() == 'varchar'

def test_field_metadata():
    f = Field(
        nullable=False,
        primary_key=True,
        db_type='integer',
        metadata={'description': 'my field'}
    )
    assert f.nullable() is False
    assert f.primary_key is True
    assert f.db_type() == 'integer'
    assert f._meta['description'] == 'my field'

def test_field_repr():
    f = Field()
    print(f'{f!r}')
    assert repr(f) == "Field(column=None, type=None, default=None)"

def test_default_value():
    f = Field(default='value')
    assert f.default == 'value'
    f = Field(default_factory=dict)
    assert f.default_factory == dict

def test_field_type():
    f:str = Field(unknown_arg='value')
    assert f.get_metadata()['unknown_arg'] == 'value'
    print(f.type)
    f.type == str


@dataclass
class Person:
    name: str
    age: int = Column(default=0)
    email: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default='')
    attributes: Optional[dict] = Column(default_factory=default_dict)


def test_person():
    person = Person(name="John")
    assert person.age == 0
    assert person.email is None
    assert person.bio == ''
    assert person.attributes == {}

    person = Person(name="Mary", age=30, email="mary@example.com", bio="A bio", attributes={"hair_color": "blonde"})
    assert person.name == "Mary"
    assert person.age == 30
    assert person.email == "mary@example.com"
    assert person.bio == "A bio"
    assert person.attributes == {"hair_color": "blonde"}

    with pytest.raises(ValueError):
        p1 = Column(default=None, factory=dict, default_factory=default_dict)
        person = Person(name="Bob", attributes=p1)

    age_field = Column(default=0, factory=int)
    person = Person(name="Bob", age=age_field)
