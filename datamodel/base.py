from collections.abc import Callable
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


TYPE_CONVERTERS = {}  # Maps a type to a conversion callable


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
        """Handle default value of fields."""
        # If value is callable, try calling it directly
        if is_callable(value):
            try:
                new_val = value()
            except TypeError:
                try:
                    new_val = f.default()
                except TypeError:
                    new_val = None
            setattr(self, name, new_val)
            return new_val

        # If f.default is callable and value is None
        if is_callable(f.default) and value is None:
            try:
                new_val = f.default()
            except (AttributeError, RuntimeError, TypeError):
                new_val = None
            setattr(self, name, new_val)
            return new_val

        # If there's a non-missing default and no value
        if not isinstance(f.default, _MISSING_TYPE) and value is None:
            setattr(self, name, f.default)
            return f.default

        # Otherwise, return value as-is
        return value

    @classmethod
    def register_converter(cls, target_type: Any, func: Callable, field_name: str = None):
        key = (target_type, field_name) if field_name else target_type
        TYPE_CONVERTERS[key] = func

    def _handle_dataclass_type(self, name: str, value: Any, _type: Any):
        try:
            if hasattr(self.Meta, 'no_nesting'):
                return value
            if value is None or is_dataclass(value):
                return value
            if isinstance(value, dict):
                return _type(**value)
            if isinstance(value, list):
                return _type(*value)
            else:
                # If a converter exists for this type, use it:
                key = (_type, name)
                converter = TYPE_CONVERTERS.get(key) or TYPE_CONVERTERS.get(_type)
                if converter:
                    return converter(name, value, _type)
                if getattr(self.Meta, 'as_objects', False) is True:
                    return _type(**{name: value})
                if isinstance(value, (int, str, UUID)):
                    return value
                if inspect.isclass(_type) and hasattr(_type, '__dataclass_fields__'):
                    return _type(**{name: value})
                else:
                    return _type(value)
        except Exception as exc:
            raise ValueError(
                f"Invalid value for {_type}: {value}, error: {exc}"
            )

    def _handle_list_of_dataclasses(self, name: str, value: Any, _type: Any):
        """
        _handle_list_of_dataclasses.

        Process a list field that is annotated as List[SomeDataclass].
        If there's a registered converter for the sub-dataclass, call it;
        otherwise, build the sub-dataclass using default logic.
        """
        try:
            sub_type = _type.__args__[0]
            if is_dataclass(sub_type):
                key = (sub_type, name)
                converter = TYPE_CONVERTERS.get(key) or TYPE_CONVERTERS.get(_type)
                new_list = []
                for item in value:
                    if converter:
                        new_list.append(converter(name, item, sub_type))
                    elif isinstance(item, dict):
                        new_list.append(sub_type(**item))
                    else:
                        new_list.append(item)
                return new_list
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
                f.default, (_MISSING_TYPE)) else f.default
            setattr(self, name, new_val)
            value = new_val

        if f.default is not None:
            value = self._handle_default_value(value, f, name)

        # Use the precomputed field type category:
        field_category = self.__field_types__.get(name, 'complex')
        try:
            if field_category == 'primitive':
                print('AQUI > ', _type, value, type(value))
                # if value is not None:
                new_val = parse_basic(_type, value, _encoder)
                return self._validation_(name, new_val, f, _type)
            elif field_category == 'dataclass':
                new_val = self._handle_dataclass_type(name, value, _type)
                return self._validation_(name, new_val, f, _type)
            elif field_category == 'typing':
                new_val = parse_type(_type, value, _encoder, field_category)
                return self._validation_(name, new_val, f, _type)
            elif isinstance(value, list) and hasattr(_type, '__args__'):
                new_val = self._handle_list_of_dataclasses(name, value, _type)
                return self._validation_(name, new_val, f, _type)
            else:
                new_val = parse_type(f.type, value, _encoder, field_category)
                return self._validation_(name, new_val, f, _type)
        except (TypeError, ValueError) as ex:
            raise ValueError(
                f"Wrong Type for {f.name}: {f.type}, error: {ex}"
            ) from ex

    def _field_checks_(self, f: Field, name: str, value: Any) -> None:
        # Validate Primary Key
        try:
            if f.metadata.get('primary', False) is True:
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
            if f.metadata.get('required', False) is True and self.Meta.strict is True:
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
            if f.metadata.get('nullable', True) is False and self.Meta.strict is True:
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
            field_type = self.__field_types__.get(name, 'complex')
            return _validation(f, name, value, _type, val_type, field_type)

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
