import logging
from typing import Optional, Any, List, Dict
from collections.abc import Callable
from collections import OrderedDict
import types
import numbers
from inspect import isclass
from dataclasses import dataclass, is_dataclass
from .parsers.json import JSONContent
from .fields import Field


class Meta:
    """
    Metadata information about Model.

    Attributes:
    name: str = "" name of the model
    description: str = "" description of the model
    schema: str = "" schema of the model (optional)
    app_label: str = "" app label of the model (optional)
    frozen: bool = False if the model (dataclass) is read-only (frozen state)
    strict: bool = True if the model (dataclass) should raise an error on invalid data.
    remove_null: bool = True if the model should remove null values from the data.
    concurrent: bool = True if processing fields should be called concurrently.
    """
    name: str = ""
    description: str = ""
    schema: str = ""
    app_label: str = ""
    frozen: bool = False
    strict: bool = True
    driver: str = None
    credentials: dict = Optional[dict]
    dsn: Optional[str] = None
    datasource: Optional[str] = None
    connection: Optional[Callable] = None
    remove_nulls: bool = False
    endpoint: str = ""
    concurrent: bool = False


def set_connection(cls, conn: Callable):
    cls.connection = conn


def _dc_method_setattr_(
    self,
    name: str,
    value: Any,
) -> None:
    """
    _dc_method_setattr_.
    Method for overwrite the "setattr" on Dataclasses.

    """
    # Initialize __values__ if it doesn't exist
    if not hasattr(self, '__values__'):
        object.__setattr__(self, '__values__', {})

    # Check if the attribute is a field
    if name in self.__fields__:
        # Only store the initial value:
        if name not in self.__values__:
            # Store the initial value in __values__
            self.__values__[name] = value

    if self.Meta.frozen is True and name not in self.__fields__:
        raise TypeError(
            f"Cannot add New attribute {name} on {self.modelName}, "
            "This DataClass is frozen (read-only class)"
        )
    else:
        value = None if callable(value) else value
        object.__setattr__(self, name, value)
        if name == '__values__':
            return
        if name not in self.__fields__:
            if self.Meta.strict is True:
                return False
            try:
                # create a new Field on Model.
                f = Field(required=False, default=value)
                f.name = name
                f.type = type(value)
                self.__columns__[name] = f
                self.__fields__.append(name)
                setattr(self, name, value)
            except Exception as err:
                logging.exception(err, stack_info=True)
                raise

def is_primitive(t) -> bool:
    return t in (int, float, bool, str, bytes)

class ModelMeta(type):
    """ModelMeta.

    Metaclass for DataModels, convert any Model into a dataclass-compatible object.
    """
    __columns__: Dict
    __fields__: List
    __field_types__: List

    def __new__(cls, name, bases, attrs, **kwargs):  # noqa
        cols = OrderedDict()
        strict = False
        cls.__field_types__ = {}

        if "__annotations__" in attrs:
            annotations = attrs.get('__annotations__', {})
            try:
                strict = attrs['Meta'].strict
            except (TypeError, AttributeError, KeyError):
                pass

            @staticmethod
            def _initialize_fields(attrs, annotations, strict):
                cols = OrderedDict()
                _types = {}
                for field, _type in annotations.items():
                    if isinstance(_type, Field):
                        _type = _type.type
                    df = attrs.get(
                        field,
                        Field(type=_type, required=False, default=None)
                    )
                    if not isinstance(df, Field):
                        df = Field(required=False, type=_type, default=df)
                    df.name = field
                    df.type = _type
                    cols[field] = df
                    # check type of field:
                    if is_primitive(_type):
                        _types[field] = 'primitive'
                    elif is_dataclass(_type):
                        _types[field] = 'dataclass'
                    else:
                        # Additional checks for typing can be done here:
                        if hasattr(_type, '__module__') and _type.__module__ == 'typing':  # noqa
                            _types[field] = 'typing'
                        elif isclass(_type):
                            _types[field] = 'class'
                        else:
                            _types[field] = 'complex'
                    # Assign the field object to the attrs so dataclass can pick it up
                    attrs[field] = df
                return cols, _types

            # Initialize the fields
            cols, _types = _initialize_fields(attrs, annotations, strict)
            cls.__field_types__ = _types

        _columns = cols.keys()
        cls.__slots__ = tuple(_columns)

        # Pop Meta before creating the class so we can assign it after
        attr_meta = attrs.pop("Meta", None)
        # Create the class
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)

        # Attach Meta class
        new_cls.Meta = attr_meta or getattr(new_cls, "Meta", Meta)
        new_cls.__dataclass_fields__ = cols
        if not new_cls.Meta:
            new_cls.Meta = Meta
        new_cls.Meta.set_connection = types.MethodType(
            set_connection, new_cls.Meta
        )
        try:
            frozen = new_cls.Meta.frozen
        except AttributeError:
            new_cls.Meta.frozen = False
            frozen = False

        # mix values from Meta to an existing Meta Class
        new_cls.Meta.__annotations__ = Meta.__annotations__
        for key, _ in Meta.__annotations__.items():
            if not hasattr(new_cls.Meta, key):
                try:
                    setattr(new_cls.Meta, key, None)
                except AttributeError as e:
                    logging.warning(
                        f'Missing Meta Key: {key}, {e}'
                    )

        # If there's a __model_init__ method, call it
        try:
            new_cls.__model_init__(
                new_cls,
                name,
                attrs
            )
        except AttributeError:
            pass

        # Now that fields are in attrs, decorate the class as a dataclass
        dc = dataclass(
            unsafe_hash=strict,
            repr=False,
            init=True,
            order=False,
            eq=True,
            frozen=frozen
        )(new_cls)
        # Set additional attributes:
        dc.__columns__ = cols
        dc.__fields__ = list(_columns)
        dc.__values__ = {}
        dc.__encoder__ = JSONContent
        dc.__valid__ = False
        dc.__errors__ = None
        dc.__frozen__ = strict
        dc.__initialised__ = False
        dc.modelName = dc.__name__

        # Override __setattr__ method
        setattr(dc, "__setattr__", _dc_method_setattr_)
        return dc

    def __init__(cls, *args, **kwargs) -> None:
        # Initialized Data Model = True
        cls.__initialised__ = True
        cls.__errors__ = None
        super().__init__(*args, **kwargs)
