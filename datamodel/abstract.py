from __future__ import annotations
import logging
from typing import Optional, Union, Any
from collections.abc import Callable
from collections import OrderedDict
import types
from dataclasses import dataclass, _FIELD, InitVar
from .parsers.json import JSONContent
from .fields import Field

class Meta:
    """
    Metadata information about Model.
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
        value = None if callable(value) else value
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
    strict: bool = False,
    frozen: bool = False
) -> Callable:
    """
    create_dataclass.
       Create a Dataclass from a simple Class
    """
    dc = dataclass(unsafe_hash=strict, repr=False, init=True, order=False, eq=True, frozen=frozen)(new_cls)
    setattr(dc, "__setattr__", _dc_method_setattr)
    # adding a properly internal json encoder:
    dc.__encoder__ = JSONContent
    dc.__valid__: bool = False
    return dc


class ModelMeta(type):
    """
    ModelMeta.
      MetaClass object to instanciate dataclasses as Models.
    """
    def __new__(cls, name, bases, attrs, **kwargs):
        """__new__ is a classmethod, even without @classmethod decorator"""
        cols = OrderedDict()
        if "__annotations__" in attrs:
            annotations = attrs.get('__annotations__', {})
            try:
                strict = attrs['Meta'].strict
            except (TypeError, AttributeError, KeyError):
                strict = False
            # set the slots of this class
            for field, _type in annotations.items():
                if field in attrs:
                    if isinstance(attrs.get(field), Field):
                        cols[field] = attrs.get(field)
                    else:
                        ds = attrs.get(field)
                        df = Field(required=False, type=_type, default=ds)
                        df.name = field
                        df.type = _type
                        cols[field] = df
                        attrs[field] = df
                        setattr(cls, field, df)
                else:
                    if strict is False and field not in attrs:
                        df = Field(type=_type, required=False, default=None)
                        df.name = field
                        df.type = _type
                        cols[field] = df
                        attrs[field] = df
                    else:
                        # add a new field, based on type
                        df = Field(type=_type, required=False, default=None)
                        df.name = field
                        df.type = _type
                        cols[field] = df
                        attrs[field] = df
                        setattr(cls, field, df)
            cls.__slots__ = tuple(cols.keys())
        attr_meta = attrs.pop("Meta", None)
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
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
                    logging.warning(f'Missing Meta Key: {key}, {e}')
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
            strict=new_cls.Meta.strict,
            frozen=frozen
        )
        cols = {
            k: v
            for k, v in dc.__dict__["__dataclass_fields__"].items()
            if v._field_type == _FIELD
        }
        dc.__columns__ = cols
        dc.__fields__ = list(cols.keys())
        return dc

    def __init__(cls, *args, **kwargs) -> None:
        cls.modelName = cls.__name__
        if cls.Meta.strict:
            cls.__frozen__ = cls.Meta.strict
        else:
            cls.__frozen__ = False
        # Initialized Data Model = True
        cls.__initialised__ = True
        cls.__errors__ = None
        super().__init__(*args, **kwargs)
