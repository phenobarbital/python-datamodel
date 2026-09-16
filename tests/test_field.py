from dataclasses import _MISSING_TYPE, asdict, dataclass, replace
from dataclasses import fields as dc_fields

import pytest
from datamodel.fields import Column, Field
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
    email: str | None = Field(default=None)
    bio: str | None = Field(default='')
    attributes: dict | None = Column(default_factory=default_dict)


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


@pytest.mark.parametrize("doc_val,expected", [
    (None, None),
    ("", ""),
    ("field documentation", "field documentation"),
    ("Multi\nline", "Multi\nline"),
])
def test_field_doc_values(doc_val, expected):
    if doc_val is None:
        f = Field()
    else:
        f = Field(doc=doc_val)
    assert f.doc == expected


def test_field_doc_omitted():
    f = Field()
    assert f.doc is None


@pytest.mark.parametrize("doc_val,expected", [
    (None, None),
    ("column doc", "column doc"),
    ("", ""),
])
def test_column_doc_forwarding(doc_val, expected):
    if doc_val is None:
        c = Column()
    else:
        c = Column(doc=doc_val)
    assert isinstance(c, Field)
    assert c.doc == expected


def test_doc_with_default_factory():
    f = Field(factory=list, doc="has factory")
    assert f.doc == "has factory"
    assert f.default_factory is list
    v1 = f.default_factory()
    v2 = f.default_factory()
    assert v1 == v2 == []
    assert v1 is not v2

    with pytest.raises(ValueError, match="Cannot specify both"):
        Field(factory=list, default_factory=dict)


def test_dataclass_field_doc():
    @dataclass
    class DocDataclass:
        name: str = Field(default="anon", doc="The name")
        count: int = Column(default=0, doc="A counter")

    obj = DocDataclass()
    assert obj.name == "anon"
    assert obj.count == 0

    flds = dc_fields(obj)
    assert len(flds) == 2
    assert flds[0].name == "name"
    assert flds[1].name == "count"

    d = asdict(obj)
    assert d == {"name": "anon", "count": 0}

    obj2 = replace(obj, name="Bob", count=5)
    assert obj2.name == "Bob"
    assert obj2.count == 5
