# cython: language_level=3, embedsignature=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from sys import version_info
from typing import (
    Optional,
    Union,
    Any
)
from functools import wraps
from collections.abc import Callable
from dataclasses import (
    _FIELD,
    MISSING,
    _MISSING_TYPE,
    _EMPTY_METADATA
)
from dataclasses import Field as ff
import _thread
from types import FunctionType, GenericAlias, MappingProxyType
from datamodel.types import (
    DB_TYPES
)


# Since most per-field metadata will be unused, create an empty
# read-only proxy that can be shared among all fields.
_EMPTY_METADATA = MappingProxyType({})


def fields(obj: Any):
    """Return a tuple describing the fields of this dataclass.

    Accepts a dataclass or an instance of one. Tuple elements are of
    type Field.
    """
    # Might it be worth caching this, per class?
    try:
        _fields = getattr(obj, '__dataclass_fields__')
    except AttributeError as exc:
        raise TypeError(
            'must be called with a dataclass type or instance'
        ) from exc
    # Exclude pseudo-fields.  Note that fields is sorted by insertion
    # order, so the order of the tuple is as the fields were defined.
    return tuple(f for f in _fields.values() if f._field_type is _FIELD)


# This function's logic is copied from "recursive_repr" function in
# reprlib module to avoid dependency.
def _recursive_repr(user_function):
    # Decorator to make a repr function return "..." for a recursive
    # call.
    repr_running = set()

    @wraps(user_function)
    def wrapper(self):
        key = id(self), _thread.get_ident()
        if key in repr_running:
            return '...'
        repr_running.add(key)
        try:
            result = user_function(self)
        finally:
            repr_running.discard(key)
        return result
    return wrapper


class Field(ff):
    """
    Field.
    description: Extending Field definition from Dataclass Field to DataModel.
    """

    __slots__ = (
        'name',
        'type',
        'default',
        'default_factory',
        'repr',
        'hash',
        'init',
        'compare',
        'metadata',
        'kw_only',
        'doc',
        'description',
        'validator',
        'schema_extra',
        'alias',
        'gt',
        'eq',
        'lt',
        'le',
        'ge',
        'is_dc',
        'is_primitive',
        'is_typing',
        'origin',
        'args',
        'type_args',
        'parser',
        '_field_type',
        '_type_category',
        '_typeinfo_',
        '_meta',
        '_inner_targs',
        '_typing_args',
        '_inner_origin',
        '_inner_type',
        '_inner_is_dc',
        '_inner_priv',
        '_required',
        '_nullable',
        '_primary',
        '_dbtype',
        '_alias',
        '_pattern',
        '_encoder_fn',
        '_default_callable',
    )

    def __init__(
        self,
        default: Optional[Union[Any, Callable]] = None,
        nullable: bool = True,
        required: bool = False,
        factory: Optional[Callable] = None,
        min: Union[int, float] = None,
        max: Union[int, float] = None,
        validator: Optional[Callable] = None,
        pattern: Optional[str] = None,
        alias: Optional[str] = None,
        kw_only: bool = False,
        metadata: Optional[MappingProxyType] = None,
        doc: Optional[str] = None,
        **kwargs,
    ):
        self.name = None
        self.type = None
        self._typeinfo_ = {}
        self._type_category = 'complex'
        self.parser: Optional[callable] = None
        self.is_dc: bool = False
        self.is_primitive: bool = False
        self._encoder_fn: Optional[callable] = None
        self.validator: Optional[callable] = None
        self._typing_args = None
        self._inner_targs = None
        self._inner_type = None
        self._inner_priv = None
        self._inner_is_dc = None
        self._inner_origin = None
        self._default_callable = None
        self.is_typing: bool = False
        self.type_args: Any = None
        self.origin: Any = None
        self.args: Any = None
        self.compare = kwargs.pop("compare", True)
        self.init = kwargs.pop("init", True)
        self.repr = kwargs.pop("repr", True)
        self.hash = kwargs.pop("hash", True)
        self.doc = doc
        self.default = default
        self._nullable = nullable
        self.kw_only = kw_only
        # set field type and dbtype
        self._field_type = None
        self._dbtype = kwargs.pop("db_type", None)
        self._required = required
        self.description = kwargs.pop('description', None)
        self._primary = kwargs.pop('primary_key', False)
        self._alias = alias
        self._pattern = pattern
        meta = {
            "required": required,
            "nullable": nullable,
            "primary": self._primary,
            "validator": validator,
            "alias": self._alias
        }
        _range = {}
        if min is not None:
            _range["min"] = min
        if max is not None:
            _range["max"] = max
        # representation:
        if required is True:
            self.init = True
        if self.init is False:
            self.repr = False
        metadata = (
            _EMPTY_METADATA if metadata is None else MappingProxyType(metadata)
        )
        self.metadata = metadata
        meta = {**meta, **metadata}
        ## Encoder, decoder and widget:
        meta["widget"] = kwargs.pop('widget', {})
        # Encoder and Decoder:
        meta["encoder"] = kwargs.pop('encoder', None)
        meta["decoder"] = kwargs.pop('decoder', None)
        # Future TODO: add more json-schema attributes
        self.schema_extra = kwargs.pop('schema_extra', None)
        ## field is read-only
        meta["readonly"] = bool(kwargs.pop('readonly', False))
        self._meta = {**meta, **_range, **kwargs}
        # assign metadata:
        self.metadata = self._meta
        self.default_factory = MISSING
        if default is None:
            ## Default Factory:
            default_factory = kwargs.get('default_factory', None)
            if factory is not None and default_factory is not None:
                raise ValueError(
                    "Cannot specify both factory and default_factory"
                )
            if factory is not None:
                self.default_factory = factory
                self.default = MISSING
            elif default_factory is not None:
                self.default_factory = default_factory
                if self.default_factory is not MISSING:
                    self.default = MISSING
        args = {
            "init": self.init,
            "repr": self.repr,
            "hash": self.hash,
            "compare": self.compare,
            "metadata": self._meta,
            "kw_only": self.kw_only
        }
        ff.__init__(
            self,
            default=self.default,
            default_factory=self.default_factory,
            **args
        )
        # set field type and dbtype
        self._field_type = self.type

    @_recursive_repr
    def __repr__(self):
        if self._alias is None:
            return (
                "Field("
                f"column={self.name!r}, "
                f"type={self.type!r}, "
                f"default={self.default!r})"
            )
        return (
            "Field("
            f"column={self.name!r}, "
            f"type={self.type!r}, "
            f"alias={self._alias!r}, "
            f"default={self.default!r})"
        )

    def get_metadata(self) -> dict:
        return self._meta

    def required(self) -> bool:
        return self._required

    def nullable(self) -> bool:
        return self._nullable

    def get_dbtype(self):
        return self._dbtype

    def to_dict(self):
        return {
            "name": self.name,
            "type": str(self.type),
            "default": self.default,
            "required": self._required,
            "primary": self._primary
        }

    def db_type(self):
        if self._dbtype is not None:
            if self._dbtype == "array":
                t = DB_TYPES[self.type]
                return f"{t}[]"
            else:
                return self._dbtype
        else:
            try:
                return DB_TYPES[self.type]
            except KeyError:
                return 'varchar'

    @property
    def typeinfo(self) -> dict:
        return self._typeinfo_

    @property
    def primary_key(self):
        return self._primary

    def __set_name__(self, owner, name):
        func = getattr(type(self.default), '__set_name__', None)
        if func:
            # There is a __set_name__ method on the descriptor, call
            # it.
            func(self.default, owner, name)

    __class_getitem__ = classmethod(GenericAlias)


def Column(
    default: Optional[Callable] = None,
    nullable: bool = True,
    required: bool = False,
    factory: Optional[Callable] = None,
    min: Union[int, float] = None,
    max: Union[int, float] = None,
    validator: Optional[Callable] = None,
    kw_only: bool = False,
    alias: Optional[str] = None,
    **kwargs
):
    """
      Column.
      DataModel Function that returns a Field() object
    """
    return Field(
        default=default,
        nullable=nullable,
        required=required,
        factory=factory,
        min=min,
        max=max,
        validator=validator,
        kw_only=kw_only,
        alias=alias,
        **kwargs,
    )
