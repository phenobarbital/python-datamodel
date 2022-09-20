from __future__ import annotations
import inspect
import types
from typing import (
    Optional,
    Union,
    Any
)
import logging
from collections.abc import Callable
# Dataclass
from dataclasses import (
    dataclass,
    is_dataclass,
    _FIELD,
    asdict,
    make_dataclass,
    _MISSING_TYPE
)
from orjson import OPT_INDENT_2
from datamodel.fields import Field
from datamodel.types import JSON_TYPES
from datamodel.converters import parse_type
from datamodel.validation import validator
from .parsers import DefaultEncoder


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
    dsn: Optional[str] = None
    datasource: Optional[str] = None
    connection: Optional[Callable] = None

def set_connection(cls, conn: Callable):
    cls.connection = conn


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
    dc.__encoder__ = DefaultEncoder()
    dc.__valid__: bool = False
    return dc


class ModelMeta(type):
    """
    ModelMeta.
      MetaClass object to create dataclasses for modeling DataModels.
    """
    __fields__: list

    Meta = Meta

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
                    logging.warning(e)
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

    def to_dict(self):
        return asdict(self)

    def json(self, **kwargs):
        encoder = self.__encoder__
        if len(kwargs) > 0: # re-configure the encoder
            encoder = DefaultEncoder(**kwargs)
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

    def __post_init__(self) -> None:
        """
         Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        for _, f in self.__columns__.items():
            value = getattr(self, f.name)
            key = f.name
            if 'encoder' in f.metadata:
                encoder = f.metadata['encoder']
            else:
                encoder = None
            # print(f'FIELD {key} = {value}', 'TYPE : ', f.type, type(f.type))
            if isinstance(f.type, types.MethodType):
                raise TypeError(
                    f"DataModel: Wrong type for Column {key}: {f.type}"
                )
            elif is_dataclass(f.type): # is already a dataclass
                if isinstance(value, dict):
                    new_val = f.type(**value)
                    setattr(self, key, new_val)
            else:
                try:
                    if f.type.__module__ == 'typing':  # a typing extension
                        new_val = parse_type(f.type, value, encoder)
                        setattr(self, key, new_val)
                        continue
                except AttributeError as e:
                    raise TypeError(
                        f"DataModel: Wrong type for {key}: {f.type}, error: {e}"
                    ) from e
                if isinstance(value, list):
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
                elif new_val:= parse_type(f.type, value, encoder):
                    # be processed by _parse_type
                    setattr(self, key, new_val)
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
            value = getattr(self, f.name)
            annotated_type = f.type
            val_type = type(value)
            # Fix values of Data:
            if hasattr(f, 'default') and self.is_callable(value):
                try:
                    if value.__module__ != 'typing':
                        try:
                            new_val = value()
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
            # first: check primary and required:
            if val_type == type or value == annotated_type or value is None:
                if f.metadata['primary'] is True:
                    raise ValueError(
                        f"Missing Primary Key *{name}*"
                    )
                if f.metadata["required"] is True and self.Meta.strict is True:
                    raise ValueError(
                        f"Missing Required Field *{name}*"
                    )
                elif f.metadata["nullable"] is False and self.Meta.strict is True:
                    raise ValueError(
                        f"Missing Field *{name}* when Nullable is False."
                    )
            else:
                # capturing other errors from validator:
                error = validator(f, name, value)
                if error:
                    errors[name] = error
        if errors:
            print("=== ERRORS ===")
            print(errors)
            object.__setattr__(self, "__valid__", False)
        else:
            object.__setattr__(self, "__valid__", True)

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

    @classmethod
    def from_json(cls, obj: str) -> dataclass:
        try:
            decoded = cls.__encoder__.loads(obj)
            return cls(**decoded)
        except ValueError as e:
            raise RuntimeError(
                "DataModel: Invalid string (JSON) data for decoding: {e}"
            ) from e

    @classmethod
    def from_dict(cls, obj: dict) -> dataclass:
        try:
            return cls(**obj)
        except ValueError as e:
            raise RuntimeError(
                "DataModel: Invalid Dictionary data for decoding: {e}"
            ) from e

    @classmethod
    def model(cls, dialect: str = "json") -> Any:
        """model.

        Return the json-version of current Model.
        Returns:
            str: string (json) version of model.
        """
        result = None
        clsname = cls.__name__
        schema = cls.Meta.schema
        table = cls.Meta.name if cls.Meta.name else clsname.lower()
        columns = cls.columns(cls).items()
        if dialect == 'json':
            cols = {}
            for _, field in columns:
                key = field.name
                _type = field.type
                if _type.__module__ == 'typing':
                    # TODO: discover real value of typing
                    if _type._name == 'List':
                        t = 'list'
                    elif _type._name == 'Dict':
                        t = 'dict'
                    else:
                        try:
                            t = _type.__args__[0]
                            t = t.__name__
                        except (AttributeError, ValueError):
                            t = 'object'
                else:
                    try:
                        t = JSON_TYPES[_type]
                    except KeyError:
                        t = 'object'
                cols[key] = {"name": key, "type": t}
            doc = {
                "name": clsname,
                "description": cls.__doc__.strip("\n").strip(),
                "table": table,
                "schema": schema,
                "fields": cols,
            }
            result = cls.__encoder__.dumps(doc, option=OPT_INDENT_2)
        return result
