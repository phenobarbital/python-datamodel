import logging
from typing import Optional, Union, Any
from collections.abc import Callable
from collections import OrderedDict
import types
from dataclasses import dataclass
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
    endpoint: str = ""


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


def create_dataclass(
    new_cls: Union[object, Any],
    strict: bool = False,
    frozen: bool = False
) -> Callable:
    """
    create_dataclass.
       Create a Dataclass from a simple Class.
    """
    dc = dataclass(
        unsafe_hash=strict,
        repr=False,
        init=True,
        order=False,
        eq=True,
        frozen=frozen
    )(new_cls)
    dc.__values__: dict = {}
    # adding a properly internal json encoder:
    dc.__encoder__: Any = JSONContent
    dc.__valid__: bool = False
    dc.__errors__: Union[list, None] = None
    dc.__frozen__: bool = strict
    dc.__initialised__: bool = False
    setattr(dc, "__setattr__", _dc_method_setattr_)
    dc.modelName = dc.__name__
    return dc


class ModelMeta(type):

    def __new__(cls, name, bases, attrs, **kwargs):
        cols = OrderedDict()
        strict = False
        if "__annotations__" in attrs:
            annotations = attrs.get('__annotations__', {})
            try:
                strict = attrs['Meta'].strict
            except (TypeError, AttributeError, KeyError):
                pass

            @staticmethod
            def _initialize_fields(attrs, annotations, strict):
                cols = OrderedDict()
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
                    attrs[field] = df
                return cols

            cols = _initialize_fields(attrs, annotations, strict)
        _columns = cols.keys()
        cls.__slots__ = tuple(_columns)
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
                    logging.warning(
                        f'Missing Meta Key: {key}, {e}'
                    )
        # adding a "class init method"
        try:
            new_cls.__model_init__(
                new_cls,
                name,
                attrs
            )
        except AttributeError:
            pass

        # Create the dataclass once
        dc = create_dataclass(
            new_cls,
            strict=new_cls.Meta.strict,
            frozen=frozen
        )
        dc.__columns__ = cols
        dc.__fields__ = list(_columns)
        return dc

    def __init__(cls, *args, **kwargs) -> None:
        # Initialized Data Model = True
        cls.__initialised__ = True
        cls.__errors__ = None
        super().__init__(*args, **kwargs)
