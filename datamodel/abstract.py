import contextlib
import logging
from typing import Optional, Any, List, Dict, get_args, get_origin, ClassVar
from types import GenericAlias
from collections import OrderedDict
from collections.abc import Callable
import types
from inspect import isclass
from dataclasses import dataclass, InitVar
from .parsers.json import JSONContent
from .converters import encoders, parse_basic, parse_type
from .fields import Field
from .functions import (
    is_dataclass,
    is_primitive
)

class Meta:
    """
    Metadata information about Model.

    Attributes:
    name: str = "" name of the model
    description: str = "" description of the model
    schema: str = "" schema of the model (optional)
    frozen: bool = False if the model (dataclass) is read-only (frozen state)
    strict: bool = True if the model (dataclass) should raise an error on invalid data.
    remove_null: bool = True if the model should remove null values from the data.
    validate_assignment: bool = True if the model should validate during assignment.
    """
    name: str = ""
    description: str = ""
    schema: str = ""
    frozen: bool = False
    strict: bool = True
    driver: str = None
    credentials: dict = Optional[dict]
    dsn: Optional[str] = None
    datasource: Optional[str] = None
    connection: Optional[Callable] = None
    remove_nulls: bool = False
    endpoint: str
    extra: str = 'forbid'  # could be 'allow', 'ignore', or 'forbid'
    validate_assignment: bool = False
    as_objects: bool = False
    no_nesting: bool = False
    alias_function: Optional[Callable] = None


def set_connection(cls, conn: Callable):
    cls.connection = conn


def _dc_method_setattr_(self, name: str, value: Any) -> None:
    """
    Simplified __setattr__ for dataclass-like objects.

    This version separates the known-field assignment (with optional validation)
    from the “extra field” assignment and uses a helper to perform conversion/validation.
    """
    # Ensure that the __values__ dict is present.
    if not hasattr(self, '__values__'):
        object.__setattr__(self, '__values__', {})

    # Check whether we are assigning to a known field.
    if name in self.__fields__:
        # Save the initial value (only once).
        self.__values__.setdefault(name, value)

        # If assignment validation is active, convert the value.
        if self.Meta.validate_assignment:
            value = _validate_field_assignment(self, name, value)
        object.__setattr__(self, name, value)
        return

    # If the class is frozen, do not allow new attributes.
    if self.Meta.frozen:
        raise TypeError(
            f"Cannot add new attribute {name!r} on {self.modelName} "
            "(the class is frozen)"
        )

    # For extra attributes, store them as usual.
    # (Note: here we “neutralize” any callable value to None if needed.)
    object.__setattr__(self, name, None if callable(value) else value)
    if name == '__values__':
        return

    # If the field isn’t known yet:
    if name not in self.__fields__:
        # In strict mode, we don’t allow unknown fields.
        if self.Meta.strict:
            return False

        # Otherwise, check the "extra" policy.
        extra_policy = self.Meta.extra
        if extra_policy == 'forbid':
            raise TypeError(f"Field {name!r} is not allowed on {self.modelName}")
        elif extra_policy == 'ignore':
            return

        # Dynamically create a new Field for the unknown attribute.
        try:
            new_field = Field(required=False, default=value)
            new_field.name = name
            new_field.type = type(value)
            # (Optionally, you might attach a parser here if validation is on.)
            self.__columns__[name] = new_field
            self.__fields__.append(name)
            object.__setattr__(self, name, value)
        except Exception as err:
            logging.exception(err, stack_info=True)
            raise


def _validate_field_assignment(self, name: str, value: Any) -> Any:
    """
    Helper that applies field conversion/validation based on cached field info.

    If you cache the parser (or the type-category) on the Field during model creation,
    this helper could simply call that parser.
    """
    field_obj = self.__columns__[name]
    # _type = field_obj.type
    # _encoder = field_obj.metadata.get('encoder')
    # Retrieve the field category (pre‐computed at class creation)
    # field_category = self.__field_types__.get(name, 'complex')
    try:
        return field_obj.parser(value) if field_obj.parser else value
    except Exception as e:
        raise TypeError(
            f"Cannot assign {value!r} to field {name!r}: {e}"
        ) from e


class ModelMeta(type):
    """ModelMeta.

    Metaclass for DataModels, convert any Model into a dataclass-compatible object.
    """
    __columns__: Dict
    __fields__: List
    __field_types__: List
    __aliases__: Dict

    def __new__(cls, name, bases, attrs, **kwargs):  # noqa
        cols = OrderedDict()
        strict = False
        cls.__field_types__ = {}
        cls.__typing_args__ = {}
        cls.__aliases__ = {}
        _types = {}
        _typing_args = {}
        aliases = {}

        if "__annotations__" in attrs:
            annotations = attrs.get('__annotations__', {})
            with contextlib.suppress(TypeError, AttributeError, KeyError):
                strict = attrs['Meta'].strict

            @staticmethod
            def _initialize_fields(attrs, annotations, strict):
                cols = OrderedDict()
                _types_local = {}
                _typing_args = {}
                aliases = {}
                for field, _type in annotations.items():
                    if isinstance(_type, InitVar) or _type == InitVar:
                        # Skip InitVar fields;
                        # they should not be part of the dataclass instance
                        continue
                    origin = get_origin(_type)
                    if origin is ClassVar:
                        continue

                    # Check if the field's default value is a descriptor
                    default_value = attrs.get(field, None)
                    is_descriptor = any(
                        hasattr(default_value, method)
                        for method in ("__get__", "__set__", "__delete__")
                    )
                    # Handle the descriptor field
                    if is_descriptor:
                        default_value._type_category = 'descriptor'
                        cols[field] = default_value
                        _types_local[field] = 'descriptor'
                        continue

                    if isinstance(_type, Field):
                        _type = _type.type
                    df = attrs.get(
                        field,
                        Field(type=_type, required=False, default=None)
                    )
                    if df is not None and isinstance(df, Field):
                        alias = df.metadata.get("alias", None)
                        if alias:
                            aliases[alias] = field
                    if not isinstance(df, Field):
                        df = Field(required=False, type=_type, default=df)
                    df.name = field
                    df.type = _type
                    try:
                        df._encoder_fn = encoders[_type]
                    except (TypeError, KeyError):
                        df._encoder_fn = None

                    # Cache reflection info so we DON’T need to call
                    # get_origin/get_args repeatedly:
                    args = get_args(_type)
                    _default = df.default
                    _is_dc = is_dataclass(_type)
                    _is_prim = is_primitive(_type)
                    _is_alias = isinstance(_type, GenericAlias)
                    _is_typing = hasattr(_type, '__module__') and _type.__module__ == 'typing'  # noqa

                    # Store the type info in the field object:
                    df.is_dc = _is_dc
                    df.is_primitive = _is_prim
                    df.is_typing = _is_typing
                    df.origin = origin
                    df.args = args
                    df.type_args = getattr(_type, '__args__', None)

                    df._typeinfo_ = {
                        "default_callable": callable(_default)
                    }

                    # check type of field:
                    if _is_prim:
                        df.parser = lambda value, _type=_type, _encoder=df.metadata.get('encoder'): parse_basic(_type, value, _encoder)
                        _type_category = 'primitive'
                    elif origin == type:
                        _type_category = 'type'
                    elif _is_dc:
                        _type_category = 'dataclass'
                    elif _is_typing:  # noqa
                        _type_category = 'typing'
                    elif isclass(_type):
                        _type_category = 'class'
                    elif _is_alias:
                        _type_category = 'typing'
                    else:
                        # TODO: making parser for complex types
                        _type_category = 'complex'
                    _types_local[field] = _type_category
                    df._type_category = _type_category

                    # Store them in a dict keyed by field name:
                    _typing_args[field] = (origin, args)
                    # Assign the field object to the attrs so dataclass can pick it up
                    attrs[field] = df
                    cols[field] = df
                return cols, _types_local, _typing_args, aliases

            # Initialize the fields
            cols, _types, _typing_args, aliases = _initialize_fields(
                attrs, annotations, strict
            )
        else:
            # if no __annotations__, cols is empty:
            cols = OrderedDict()

        _columns = cols.keys()
        cls.__slots__ = tuple(_columns)

        # Pop Meta before creating the class so we can assign it after
        attr_meta = attrs.pop("Meta", None)
        # Create the class
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)

        # Attach Meta class
        new_cls.Meta = attr_meta or getattr(new_cls, "Meta", Meta)
        new_cls.__dataclass_fields__ = cols
        new_cls.__typing_args__ = _typing_args
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
        dc.__field_types__ = _types
        dc.__aliases__ = aliases
        dc.__typing_args__ = _typing_args
        dc.modelName = dc.__name__

        # Override __setattr__ method
        setattr(dc, "__setattr__", _dc_method_setattr_)
        return dc

    def __init__(cls, *args, **kwargs) -> None:
        # Initialized Data Model = True
        cls.__initialised__ = True
        cls.__errors__ = None
        super().__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        #    rename any kwargs that match an alias ONLY if there are aliases defined.
        alias_func = getattr(cls.Meta, "alias_function", None)
        if callable(alias_func):
            new_kwargs = {}
            for k, v in kwargs.items():
                new_k = alias_func(k)
                new_kwargs[new_k] = v
            kwargs = new_kwargs
        if cls.__aliases__:
            new_kwargs = {}
            for k, v in kwargs.items():
                if k in cls.__aliases__:
                    real_field = cls.__aliases__[k]
                    new_kwargs[real_field] = v
                else:
                    new_kwargs[k] = v
            kwargs = new_kwargs
        return super().__call__(*args, **kwargs)
