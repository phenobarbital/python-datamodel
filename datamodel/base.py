from collections.abc import Callable
from typing import Any
# Dataclass
from dataclasses import (
    _FIELD,
)
from .converters import process_attributes, register_converter
from .fields import Field
from .exceptions import ValidationError
from .abstract import ModelMeta
from .models import ModelMixin


TYPE_CONVERTERS = {}


class BaseModel(ModelMixin, metaclass=ModelMeta):
    """
    BaseModel.
    Base Model for all DataModels.
    """

    def __post_init__(self) -> None:
        """
        Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        columns = list(self.__columns__.items())

        errors = process_attributes(self, columns)
        # errors = {}
        # for name, f in columns:
        #     try:
        #         value = getattr(self, name)
        #         if (error := self._process_field_(name, value, f)):
        #             errors[name] = error
        #     except RuntimeError as err:
        #         logging.exception(err)

        if errors:
            if self.Meta.strict is True:
                raise ValidationError(
                    f"""{self.modelName}: There are errors in Model. \
                        Hint: please check the "payload" attribute in the exception.""",
                    payload=errors
                )
            self.__errors__ = errors
            object.__setattr__(self, "__valid__", False)
        else:
            object.__setattr__(self, "__valid__", True)

    @classmethod
    def register_converter(
        cls,
        target_type: Any,
        func: Callable,
        field_name: str = None
    ):
        key = (target_type, field_name) if field_name else target_type
        register_converter(key, func)

    @classmethod
    def add_field(cls, name: str, value: Any = None) -> None:
        if cls.Meta.strict is True:
            raise TypeError(
                f'Cannot create a new field {name} on a Strict Model.'
            )
        if name != '__errors__':
            f = Field(required=False, default=value)
            f.name = name
            f.type = type(value)
            f._field_type = _FIELD
            cls.__columns__[name] = f
            cls.__dataclass_fields__[name] = f

    def create_field(self, name: str, value: Any) -> None:
        """create_field.
        create a new Field on Model (when strict is False).
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        Raises:
            TypeError: when try to create a new field on an Strict Model.
        """
        if self.Meta.strict is True:
            raise TypeError(
                f'Cannot create a new field {name} on a Strict Model.'
            )
        if name != '__errors__':
            f = Field(required=False, default=value)
            f.name = name
            f.type = type(value)
            f._field_type = _FIELD
            self.__columns__[name] = f
            self.__dataclass_fields__[name] = f
            setattr(self, name, value)

    def set(self, name: str, value: Any) -> None:
        """set.
        Alias for Create Field.
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        """
        if name not in self.__columns__:
            if name != '__errors__' and self.Meta.strict is False:
                self.create_field(name, value)
        else:
            setattr(self, name, value)

    def get_errors(self):
        return self.__errors__
