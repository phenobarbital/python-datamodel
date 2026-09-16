"""Regression tests for CPython 3.14 Field doc compatibility.

Validates that Field/Column doc values survive model construction,
type conversion works via eager annotations, and inherited fields
retain their doc values across all supported interpreters.
"""
from datamodel import BaseModel
from datamodel.fields import Field, Column


class TestModelFieldInitialization:
    def test_model_with_eager_annotations(self):
        class FieldDocSmoke(BaseModel):
            __annotations__ = {"value": int}
            value = Column(default=0, doc="Example value")

        model = FieldDocSmoke(value="7")
        assert type(model.value) is int
        assert model.value == 7
        assert "value" in FieldDocSmoke.__columns__
        assert FieldDocSmoke.__columns__["value"].doc == "Example value"

    def test_model_field_doc_none(self):
        class NoneDocModel(BaseModel):
            __annotations__ = {"x": str}
            x = Column(default="hi")

        model = NoneDocModel()
        assert model.x == "hi"
        assert "x" in NoneDocModel.__columns__
        assert NoneDocModel.__columns__["x"].doc is None

    def test_standalone_field_doc(self):
        f = Field(doc="standalone")
        assert f.doc == "standalone"


class TestInheritedFieldDoc:
    def test_inherited_field_retains_doc(self):
        class ParentModel(BaseModel):
            __annotations__ = {"name": str}
            name = Column(default="", doc="Parent name")

        class ChildModel(ParentModel):
            __annotations__ = {"age": int}
            age = Column(default=0, doc="Child age")

        child = ChildModel(name="Alice", age=30)
        assert child.name == "Alice"
        assert child.age == 30
        assert ChildModel.__columns__["name"].doc == "Parent name"
        assert ChildModel.__columns__["age"].doc == "Child age"

    def test_overridden_field_doc(self):
        class BaseDoc(BaseModel):
            __annotations__ = {"label": str}
            label = Column(default="base", doc="Base label")

        class OverrideDoc(BaseDoc):
            __annotations__ = {"label": str}
            label = Column(default="override", doc="Override label")

        obj = OverrideDoc()
        assert obj.label == "override"
        assert OverrideDoc.__columns__["label"].doc == "Override label"
