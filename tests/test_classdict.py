from typing import Optional
import pytest
from datamodel import Field
from datamodel.libs.mapping import ClassDict

class QueryObject(ClassDict):
    """Base Class for all options passed to Parsers.
    """
    source: Optional[str]
    driver: Optional[str]
    conditions: Optional[dict] = Field(default={})

def test_classdict_contains():
    # create a ClassDict
    c = ClassDict(a=1, b=2)

    # test if contains
    assert 'a' in c
    assert 'c' not in c

def test_classdict_del():
    # create a ClassDict
    c = ClassDict(a=1, b=2)

    # delete an item
    del c['a']

    # test if deleted
    assert 'a' not in c
    assert len(c) == 1

def test_classdict_sort():
    # create a ClassDict
    c = ClassDict(b=2, a=1)

    # sort by key
    c = dict(sorted(c.items()))

    # test if sorted
    assert list(c.keys()) == ['a', 'b']

def test_classdict_get_by_dict_syntax():
    # create a ClassDict
    c = ClassDict(a=1, b=2)

    # get an item by dict syntax
    assert c['a'] == 1

def test_classdict_get_by_object_syntax():
    # create a ClassDict
    c = ClassDict(a=1, b=2)

    # get an item by object syntax
    assert c.a == 1

def test_classdict_add():
    # create a ClassDict
    c = ClassDict(a=1, b=2)

    # add an item
    c['c'] = 3

    # test if added
    assert 'c' in c
    assert c['c'] == 3
