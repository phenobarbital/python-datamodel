from __future__ import annotations
import types
import inspect
import typing
from typing import (
    Optional,
    Union,
    Any
)
import logging
from collections.abc import Callable, Iterable, Mapping
from decimal import Decimal
# Dataclass
from dataclasses import Field as ff
from dataclasses import (
    dataclass,
    is_dataclass,
    _FIELD,
    asdict,
    MISSING,
    InitVar,
    make_dataclass,
    _MISSING_TYPE
)
import six
from .encoders import DefaultEncoder


class Meta:
    """
    Metadata information about Model.
    """
    name: str = ""
    schema: str = ""
    app_label: str = ""
    frozen: bool = False
    strict: bool = True
    driver: str = None
    credentials: dict = Optional[dict]
    dsn:  Union[None, str] = None
    datasource: Union[None, str] = None
    connection = None

    @classmethod
    def set_connection(cls, conn: Callable):
        cls.connection = conn

@dataclass
class ValidationError:
    """
    Class for Error validation on DataModels.
    """
    field: str
    value: Optional[Union[str, Any]]
    error: str
    value_type: Any
    annotation: type
    exception: Optional[Exception]


class Field(ff):
    """
    Field.
    description: Extending Field definition from Dataclass Field to DataModel.
    """
    def __init__(
        self,
        default: Optional[Union[Iterable, Mapping, Any]] = None,
        nullable: Optional[bool] = True,
        required: Optional[bool] = False,
        factory: Callable[..., Any] = None,
        min: Union[int, float, Decimal] = None,
        max: Union[int, float, Decimal] = None,
        validator: Optional[Union[Callable, None]] = None,
        **kwargs,
    ):
        args = {
            "init": True,
            "repr": True,
            "hash": True,
            "compare": True,
            "metadata": None,
        }
        try:
            args["compare"] = kwargs["compare"]
            del kwargs["compare"]
        except KeyError:
            pass
        meta = {
            "required": required,
            "nullable": nullable,
            "validator": None
        }
        self._required = required
        self._nullable = nullable
        if 'description' in kwargs:
            self.description = kwargs['description']
        else:
            self.description = None
        _range = {}
        if min is not None:
            _range["min"] = min
        if max is not None:
            _range["max"] = max
        try:
            args["repr"] = kwargs["repr"]
            del kwargs["repr"]
        except KeyError:
            args["repr"] = True
        try:
            args["init"] = kwargs["init"]
            del kwargs["init"]
        except KeyError:
            args["init"] = True
        if required is True:
            args["init"] = True
        if args["init"] is False:
            args["repr"] = False
        if validator is not None:
            meta["validator"] = validator
        try:
            meta = {**meta, **kwargs["metadata"]}
            del kwargs["metadata"]
        except (KeyError, TypeError):
            pass
        self._meta = {**meta, **_range, **kwargs}
        args["metadata"] = self._meta
        self._default_factory = MISSING
        if default is not None:
            self._default = default
        else:
            self._default = None
            if nullable is True: # Can be null
                if not factory:
                    factory = _MISSING_TYPE
                self._default_factory = factory
        # Calling Parent init
        super(Field, self).__init__(
            default=self._default,
            default_factory=self._default_factory,
            **args
        )
        # set field type and dbtype
        self._field_type = self.type

    def __repr__(self):
        return (
            "Field("
            f"column={self.name!r},"
            f"type={self.type!r},"
            f"default={self.default!r})"
        )

    def required(self) -> bool:
        return self._required

    def nullable(self) -> bool:
        return self._nullable

def Column(
    *,
    default: Optional[Union[Iterable, Mapping, Any]] = None,
    nullable: Optional[bool] = True,
    required: Optional[bool] = False,
    factory: Callable[..., Any] = None,
    min: Union[int, float, Decimal] = None,
    max: Union[int, float, Decimal] = None,
    validator: Optional[Union[Callable, None]] = None,
    **kwargs,
):
    """
      Column.
      DataModel Function that returns a Field() object
    """
    if factory is None:
        factory = MISSING
    if default is not None and factory is not MISSING:
        raise ValueError(
            f"Cannot specify both default: {default} and factory: {factory}"
        )
    return Field(
        default=default,
        nullable=nullable,
        required=required,
        factory=factory,
        min=min,
        max=max,
        validator=validator,
        **kwargs,
    )

def _dc_method_setattr(
            self,
            name: str,
            value: Any,
        ) -> None:
    """
    _dc_method_setattr.
    Method for overwrite the "setattr" on Dataclasses.
    """
    if self.Meta.frozen is True and name not in self.__fields__:
        raise TypeError(
            f"Cannot add New attribute {name} on {self.modelName}, "
            "This DataClass is frozen (read-only class)"
        )
    else:
        object.__setattr__(self, name, value)
        if name not in self.__fields__:
            if self.Meta.strict is True:
                logging.warning(
                    f"Warning: *{name}* doesn't exists on {self.modelName}"
                )
            else:
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


def create_dataclass(
    new_cls: Union[object, Any],
    frozen: bool = False
) -> Callable:
    """
    create_dataclass.
       Create a Dataclass from a simple Class
    """
    dc = dataclass(unsafe_hash=True, init=True, frozen=frozen)(new_cls)
    setattr(dc, "__setattr__", _dc_method_setattr)
    # adding a properly internal json encoder:
    dc.__encoder__ = DefaultEncoder(
        sort_keys=False
    )
    dc.__valid__: bool = False
    return dc


class ModelMeta(type):
    """
    ModelMeta.
      MetaClass object to create dataclasses for modeling DataModels.
    """
    __fields__: list

    def __new__(cls, name, bases, attrs, **kwargs):
        """__new__ is a classmethod, even without @classmethod decorator"""
        cols = []
        if "__annotations__" in attrs:
            annotations = attrs["__annotations__"]
            for field, _type in annotations.items():
                # print(f"Field: {field}, Type: {_type}")
                if field in attrs:
                    df = attrs[field]
                    if isinstance(df, Field):
                        setattr(cls, field, df)
                    else:
                        df = Field(factory=_type, required=False, default=df)
                        df.name = field
                        df.type = _type
                        setattr(cls, field, df)
                else:
                    # add a new field, based on type
                    df = Field(factory=_type, required=False)
                    df.name = field
                    df.type = _type
                    setattr(cls, field, df)
                cols.append(field)
            # set the slots of this class
            cls.__slots__ = tuple(cols)
        attr_meta = attrs.pop("Meta", None)
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        new_cls.Meta = attr_meta or getattr(new_cls, "Meta", Meta)
        if not new_cls.Meta:
            new_cls.Meta = Meta
        frozen = False
        # adding a "class init method"
        try:
            new_cls.__model_init__(
                new_cls,
                name,
                attrs
            )
        except AttributeError:
            pass
        dc = create_dataclass(
            new_cls,
            frozen=frozen
        )
        cols = {
            k: v
            for k, v in dc.__dict__["__dataclass_fields__"].items()
            if v._field_type == _FIELD
        }
        dc.__columns__ = cols
        dc.__fields__ = tuple(cols.keys())
        return dc

    def __init__(cls, *args, **kwargs) -> None:
        cls.modelName = cls.__name__
        if cls.Meta.strict:
            cls.__frozen__ = cls.Meta.strict
        else:
            cls.__frozen__ = False
        # Initialized Data Model = True
        cls.__initialised__ = True
        super(ModelMeta, cls).__init__(*args, **kwargs)



class BaseModel(metaclass=ModelMeta):
    """
    Model.

    Base Model for all DataModels.
    """
    Meta = Meta

    def __unicode__(self):
        return str(__class__)

    def columns(self):
        return self.__columns__

    def get_fields(self):
        return self.__fields__

    def column(self, name):
        return self.__columns__[name]

    def dict(self):
        return asdict(self)

    def json(self, **kwargs):
        encoder = self.__encoder__
        if len(kwargs) > 0: # re-configure the encoder
            encoder = DefaultEncoder(sort_keys=False, **kwargs)
        return encoder(asdict(self))

    def is_valid(self):
        return bool(self.__valid__)

    def create_field(self, name: str, value: Any) -> None:
        """create_field.
        create a new Field on Model (when strict is False).
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        """
        f = Field(required=False, default=value)
        f.name = name
        f.type = type(value)
        self.__columns__[name] = f
        setattr(self, name, value)

    def set(self, name: str, value: Any) -> None:
        """set.
        Alias for Create Field.
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        """
        if name not in self.__columns__:
            self.create_field(name, value)
        else:
            setattr(self, name, value)

    def _parse_type(self, F, data) -> object:
        _type = F.type
        if _type.__module__ == 'typing':
            args = None
            try:
                args = _type.__args__
            except AttributeError:
                pass
            if _type._name == 'Dict' and isinstance(data, dict):
                return {k: self._parse_type(F.type.__args__[1], v) for k, v in data.items()}
            elif _type._name == 'List' and isinstance(data, list):
                arg = args[0]
                if arg.__module__ == 'typing': # nested typing
                    try:
                        t = arg.__args__[0]
                        if is_dataclass(t):
                            return [t(*x) for x in data]
                        else:
                            return data
                    except AttributeError:
                        return data # data -as is-
                elif is_dataclass(arg):
                    return [arg(*x) for x in data]
                else:
                    return data
            elif _type._name is None:
                if isinstance(_type.__origin__, type(Union)):
                    t = args[0]
                    if is_dataclass(t):
                        # print('AQUI ', F, args, _type.__origin__, t)
                        # print(data, type(data))
                        if isinstance(data, dict):
                            data = t(**data)
                        elif isinstance(data, (list, tuple)):
                            data = t(*data)
                        else:
                            data = None
                    # F.type = args[0]
                    return data
                else:
                    pass
        else:
            return data

    def __post_init__(self) -> None:
        """
         Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        for _, f in self.__columns__.items():
            value = getattr(self, f.name)
            key = f.name
            # print(f'FIELD {key} = {value}')
            if is_dataclass(f.type): # is already a dataclass
                if isinstance(value, dict):
                    new_val = f.type(**value)
                    setattr(self, key, new_val)
            elif f.type.__module__ == 'typing':  # a typing extension
                new_val = self._parse_type(f, value)
                setattr(self, key, new_val)
            elif isinstance(value, list):
                try:
                    sub_type = f.type.__args__[0]
                    if is_dataclass(sub_type):
                        # for every item
                        items = []
                        for item in value:
                            try:
                                if isinstance(item, dict):
                                    items.append(sub_type(**item))
                                else:
                                    items.append(item)
                            except (TypeError, AttributeError):
                                continue
                        setattr(self, key, items)
                except AttributeError:
                    setattr(self, key, value)
            elif value is None:
                is_missing = isinstance(f.default, _MISSING_TYPE)
                setattr(self, key, f.default_factory if is_missing else f.default)
            else:
                continue
        try:
            self._validation()
        except RuntimeError as err:
            logging.exception(err)

    def is_callable(self, value) -> bool:
        is_missing = (value == _MISSING_TYPE)
        return callable(value) if not is_missing else False

    def _validation(self) -> None:
        """
        _validation.
        TODO: cover validations as length, not_null, required, max, min, etc
        """
        errors = {}
        for _, f in self.__columns__.items():
            name = f.name
            val = self.__dict__[name]
            if hasattr(f, 'default') and self.is_callable(val):
                try:
                    if val.__module__ != 'typing':
                        try:
                            new_val = val()
                        except TypeError:
                            try:
                                new_val = f.default()
                            except TypeError:
                                new_val = None
                        setattr(self, name, new_val)
                except TypeError as e:
                    print(e)
                    logging.warning(
                        f'{self.modelName}: Missing *Column* {f} with name {name}'
                    )
                    setattr(self, name, None)
            # first check: data type hint
            val = self.__dict__[name]
            val_type = type(val)
            annotated_type = f.type
            if val_type == type or val == annotated_type or val is None:
                # data not provided
                if f.metadata["required"] is True and self.Meta.strict is True:
                    errors[name] = ValidationError(
                        field=name,
                        value=None,
                        value_type=val_type,
                        error="Field Required",
                        annotation=annotated_type,
                        exception=None,
                    )
                elif f.metadata['nullable'] is False:
                    errors[name] = ValidationError(
                        field=name,
                        value=None,
                        value_type=val_type,
                        error="Not Null",
                        annotation=annotated_type,
                        exception=None,
                    )
            else:
                try:
                    instance = self._is_instanceof(val, annotated_type)
                    if not instance:
                            errors[name] = ValidationError(
                                field=name,
                                value=val,
                                error="Validation Exception",
                                value_type=val_type,
                                annotation=annotated_type,
                                exception=None,
                            )
                except (TypeError) as e:
                    errors[name] = ValidationError(
                        field=name,
                        value=val,
                        error="Validation Exception",
                        value_type=val_type,
                        annotation=annotated_type,
                        exception=e,
                    )
                ## calling validator:
                if 'validator' in f.metadata:
                    if f.metadata['validator'] is not None:
                        fn = f.metadata['validator']
                        if self.is_callable(fn):
                            try:
                                result = fn(f, val)
                                if result is False:
                                    errors[name] = ValidationError(
                                        field=name,
                                        value=val,
                                        error=f"Validator: {result}",
                                        value_type=val_type,
                                        annotation=annotated_type,
                                        exception=None,
                                    )
                            except (ValueError, AttributeError, TypeError) as e:
                                errors[name] = ValidationError(
                                    field=name,
                                    value=val,
                                    error="Validator Exception",
                                    value_type=val_type,
                                    annotation=annotated_type,
                                    exception=e,
                                )
        if errors:
            print("=== ERRORS ===")
            print(errors)
            object.__setattr__(self, "__valid__", False)
        else:
            object.__setattr__(self, "__valid__", True)

    def _is_instanceof(self, value: Any, annotated_type: type) -> bool:
        if annotated_type.__module__ == 'typing':
            return True # TODO: validate subscripted generic (typing extensions)
        else:
            try:
                return isinstance(value, annotated_type)
            except (AttributeError, TypeError, ValueError) as e:
                logging.error(e)
                raise

    @classmethod
    def make_model(cls, name: str, schema: str = "public", fields: list = None):
        parent = inspect.getmro(cls)
        obj = make_dataclass(name, fields, bases=(parent[0],))
        m = Meta()
        m.name = name
        m.schema = schema
        m.app_label = schema
        obj.Meta = m
        return obj
