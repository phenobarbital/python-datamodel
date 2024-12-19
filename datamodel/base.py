from typing import Any, Optional
import inspect
import logging
# Dataclass
from dataclasses import (
    _FIELD,
    _MISSING_TYPE
)
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from .converters import parse_basic, parse_type
from .fields import Field
from .validation import (
    _validation,
    is_callable,
    is_empty,
    is_dataclass,
    is_primitive
)
from .exceptions import ValidationError
from .abstract import ModelMeta, Meta
from .models import ModelMixin


class BaseModel(ModelMixin, metaclass=ModelMeta):
    """
    BaseModel.
    Base Model for all DataModels.
    """
    Meta = Meta

    def __post_init__(self) -> None:
        """
        Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        errors = {}
        columns = list(self.__columns__.items())

        def process_field(item: tuple):
            name, f = item
            try:
                value = getattr(self, name)
                error = self._process_field_(name, value, f)
                return name, error
            except Exception as e:
                # Capture the exception in an error dictionary
                return name, {"error": str(e)}

        if self.Meta.concurrent is True:
            with ThreadPoolExecutor() as executor:
                results = executor.map(process_field, columns)
            for name, error in results:
                if error:
                    errors[name] = error
        else:
            for name, f in columns:
                try:
                    value = getattr(self, name)
                    if (error := self._process_field_(name, value, f)):
                        errors[name] = error
                except RuntimeError as err:
                    logging.exception(err)

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

    def _handle_default_value(self, value, f, name) -> Any:
        # Calculate default value
        if is_callable(value):
            if value.__module__ != 'typing':
                try:
                    new_val = value()
                except TypeError:
                    try:
                        new_val = f.default()
                    except TypeError:
                        new_val = None
                setattr(self, name, new_val)
        elif is_callable(f.default) and value is None:
            # Set the default value first
            try:
                new_val = f.default()
            except (AttributeError, RuntimeError):
                new_val = None
            setattr(self, name, new_val)
            value = new_val  # Return the new value
        elif not isinstance(f.default, _MISSING_TYPE) and value is None:
            setattr(self, name, f.default)
            value = f.default
        return value

    def _handle_dataclass_type(self, value, _type):
        try:
            if hasattr(self.Meta, 'no_nesting'):
                return value
            if value is None or is_dataclass(value):
                return value
            if isinstance(value, dict):
                return _type(**value)
            if isinstance(value, list):
                return _type(*value)
            return value if isinstance(value, (int, str, UUID)) else _type(value)
        except Exception as exc:
            raise ValueError(
                f"Invalid value for {_type}: {value}, error: {exc}"
            )

    def _handle_list_of_dataclasses(self, value, _type):
        try:
            sub_type = _type.__args__[0]
            if is_dataclass(sub_type):
                return [
                    sub_type(
                        **item
                    ) if isinstance(item, dict) else item for item in value
                ]
        except AttributeError:
            pass
        return value

    def _process_field_(
        self,
        name: str, value: Any, f: Field
    ) -> Optional[dict[Any, Any]]:
        _type = f.type
        _encoder = f.metadata.get('encoder')
        new_val = value
        if is_empty(value):
            new_val = f.default_factory if isinstance(
                f.default, (_MISSING_TYPE)
            ) else f.default
            setattr(self, name, new_val)

        if f.default is not None:
            value = self._handle_default_value(value, f, name)

        if is_primitive(_type):
            try:
                if value is not None:
                    new_val = parse_basic(f.type, value, _encoder)
                return self._validation_(name, new_val, f, _type)
            except (TypeError, ValueError) as ex:
                raise ValueError(
                    f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                ) from ex
        elif inspect.isclass(_type) and _type.__module__ == 'typing':
            new_val = parse_type(_type, value, _encoder)
            return self._validation_(name, new_val, f, _type)
        elif isinstance(value, list) and hasattr(_type, '__args__'):
            new_val = self._handle_list_of_dataclasses(value, _type)
            return self._validation_(name, new_val, f, _type)
        elif is_dataclass(_type):
            new_val = self._handle_dataclass_type(value, _type)
            return self._validation_(name, new_val, f, _type)
        else:
            try:
                new_val = parse_type(f.type, value, _encoder)
            except (TypeError, ValueError) as ex:
                raise ValueError(
                    f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                ) from ex
            # Then validate the value
            return self._validation_(name, new_val, f, _type)

    def _field_checks_(self, f: Field, name: str, value: Any) -> None:
        # Validate Primary Key
        try:
            if f.metadata['primary'] is True:
                if 'db_default' in f.metadata:
                    pass
                else:
                    raise ValueError(
                        f"::{self.modelName}:: Missing Primary Key *{name}*"
                    )
        except KeyError:
            pass
        # Validate Required
        try:
            if f.metadata["required"] is True and self.Meta.strict is True:
                if 'db_default' in f.metadata:
                    return
                if value is not None:
                    return  # If default value is set, no need to raise an error
                raise ValueError(
                    f"::{self.modelName}:: Missing Required Field *{name}*"
                )
        except KeyError:
            return
        # Nullable:
        try:
            if f.metadata["nullable"] is False and self.Meta.strict is True:
                raise ValueError(
                    f"::{self.modelName}:: *{name}* Cannot be null."
                )
        except KeyError:
            return
        return

    def _validation_(
        self,
        name: str,
        value: Any,
        f: Field, _type: Any
    ) -> Optional[dict[Any, Any]]:
        """
        _validation_.
        TODO: cover validations as length, not_null, required, max, min, etc
        """
        val_type = type(value)
        # Set the current Value
        setattr(self, name, value)

        if val_type == type or value == _type or is_empty(value):
            try:
                self._field_checks_(f, name, value)
                return None
            except (ValueError, TypeError):
                raise
        else:
            # capturing other errors from validator:
            return _validation(f, name, value, _type, val_type)

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
