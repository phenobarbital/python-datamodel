from __future__ import annotations
from typing import Any
# Dataclass
from dataclasses import asdict as as_dict
from operator import attrgetter
from datamodel.fields import fields
from .abstract import ModelMeta, Meta
from .fields import Field

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

    @classmethod
    def get_column(cls, name: str) -> Field:
        try:
            return cls.__columns__[name]
        except KeyError:
            raise AttributeError(
                f"{cls.__name__} has no column {name}"
            )

    def get_fields(self):
        return self.__fields__

    def __getitem__(self, item):
        return getattr(self, item)

    def reset_values(self):
        try:
            self.__values__ = {}
        except AttributeError:
            pass

    def old_value(self, name: str) -> Any:
        """
        old_value.
        Get the old value of an attribute.
        Args:
            name (str): name of the attribute.
        Returns:
            Any: value of the attribute.
        """
        try:
            return self.__values__[name]
        except KeyError:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            )

    def column(self, name: str) -> Field:
        return self.__columns__[name]

    def __repr__(self) -> str:
        f_repr = ", ".join(f"{f.name}={getattr(self, f.name)}" for f in fields(self))
        return f"{self.__class__.__name__}({f_repr})"

    def remove_nulls(self, obj: Any) -> dict[str, Any]:
        """Recursively removes any fields with None values from the given object."""
        if isinstance(obj, list):
            return [self.remove_nulls(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                key: self.remove_nulls(value) for key, value in obj.items()
                if value is not None
            }
        else:
            return obj

    def to_dict(self):
        if self.Meta.remove_nulls is True:
            return self.remove_nulls(as_dict(self, dict_factory=dict))
        return as_dict(self)

    def json(self, **kwargs):
        encoder = self.__encoder__(**kwargs)
        return encoder(as_dict(self))

    to_json = json

    def is_valid(self) -> bool:
        """is_valid.

        returns True when current Model is valid under datatype validations.
        Returns:
            bool: True if current model is valid.
        """
        return bool(self.__valid__)

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
        self.__initialised__ = True
