from __future__ import annotations
from typing import Any
# Dataclass
from dataclasses import asdict
from operator import attrgetter
from datamodel.fields import fields
from .abstract import ModelMeta, Meta


class ModelMixin:
    """Interface for shared methods on Model classes.
    """
    def __unicode__(self):
        return str(__class__)

    def columns(self):
        return self.__columns__

    @classmethod
    def get_columns(cls):
        return cls.__columns__

    def get_fields(self):
        return self.__fields__

    def __getitem__(self, item):
        return getattr(self, item)

    def column(self, name):
        return self.__columns__[name]

    def __repr__(self):
        nodef_f_vals = (
            (f.name, attrgetter(f.name)(self))
            for f in fields(self)
            if attrgetter(f.name)(self) != f.default
        )
        nodef_f_repr = ", ".join(f"{name}={value}" for name, value in nodef_f_vals)
        return f"{self.__class__.__name__}({nodef_f_repr})"

    def remove_nulls(self, obj: Any) -> dict[str, Any]:
        """Recursively removes any fields with None values from the given object."""
        if isinstance(obj, list):
            return [self.remove_nulls(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.remove_nulls(value) for key, value in obj.items() if value is not None}
        else:
            return obj

    def to_dict(self):
        if self.Meta.remove_nulls is True:
            return self.remove_nulls(asdict(self, dict_factory=dict))
        return asdict(self)


    def json(self, **kwargs):
        encoder = self.__encoder__(**kwargs)
        return encoder(asdict(self))

    to_json = json

class Model(ModelMixin, metaclass=ModelMeta):
    """Model.

    Basic dataclass-based Model.
    """
    Meta = Meta

    def __post_init__(self) -> None:
        """
        Post init method.
        Useful for making Post-validations of Model.
        """
