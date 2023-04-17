# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=False, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from sys import version_info
from typing import (
    Optional,
    Union,
    Any
)
from collections.abc import Callable
from dataclasses import Field as ff
from dataclasses import (
    _FIELD,
    MISSING,
    _MISSING_TYPE
)
from datamodel.types import (
    DB_TYPES
)


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


class Field(ff):
    """
    Field.
    description: Extending Field definition from Dataclass Field to DataModel.
    """
    __slots__ = (
        'name',
        'type',
        'description',
        'default',
        'default_factory',
        '_default_factory',
        '_default', # Private: default value
        'repr',
        'hash',
        'init',
        'compare',
        'metadata',
        '_meta',
        '_field_type',  # Private: not to be used by user code.
        '_required',
        '_nullable',
        '_primary',
        '_dbtype',
        '_alias',
        '_pattern'
    )

    def __init__(
        self,
        default: Optional[Callable] = None,
        nullable: bool = True,
        required: bool = False,
        factory: Optional[Callable] = None,
        min: Union[int, float] = None,
        max: Union[int, float] = None,
        validator: Optional[Callable] = None,
        pattern: Optional[str] = None,
        alias: Optional[str] = None,
        kw_only: bool = False,
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
            "primary": False,
            "validator": None
        }
        self._primary = False
        self._dbtype = None
        self._required = required
        self._nullable = nullable
        self.description = kwargs.get('description', None)
        self._primary = kwargs.get('primary_key', False)
        self._default = default
        self._alias = alias
        self._pattern = pattern
        meta['primary'] = self._primary
        if self._primary:
            del kwargs['primary_key']
        self._dbtype = kwargs.get("db_type", None)
        if self._dbtype:
            del kwargs["db_type"]
        _range = {}
        if min is not None:
            _range["min"] = min
        if max is not None:
            _range["max"] = max
        # representation:
        args["repr"] = kwargs.get("repr", True)
        try:
            del kwargs["repr"]
        except KeyError:
            pass
        args["init"] = kwargs.get("init", True)
        try:
            del kwargs["init"]
        except KeyError:
            pass
        if required is True:
            args["init"] = True
        if args["init"] is False:
            args["repr"] = False
        if validator is not None:
            meta["validator"] = validator
        metadata = kwargs.get("metadata", {})
        meta = {**meta, **metadata}
        if metadata:
            del kwargs["metadata"]
        ## Encoder, decoder and widget:
        meta["widget"] = kwargs.get('widget', {})
        if meta["widget"]:
            del kwargs['widget']
        # Encoder and Decoder:
        meta["encoder"] = kwargs.get('encoder', None)
        if meta["encoder"]:
            del kwargs['encoder']
        meta["decoder"] = kwargs.get('decoder', None)
        if meta["decoder"]:
            del kwargs['decoder']
        ## field is read-only
        try:
            meta["readonly"] = bool(kwargs['readonly'])
            del kwargs['readonly']
        except KeyError:
            meta["readonly"] = False
        self._meta = {**meta, **_range, **kwargs}
        args["metadata"] = self._meta
        self._default_factory = MISSING
        if default is not None:
            self._default = default
        else:
            ## Default Factory:
            default_factory = kwargs.get('default_factory', None)
            if factory is not None and default_factory is not None:
                raise ValueError(
                    "Cannot specify both factory and default_factory"
                )
            if factory is not None:
                self._default_factory = factory
                self._default = MISSING
            elif default_factory is not None:
                self._default_factory = default_factory
                if default is not None:
                    self._default = default
                    self._default_factory = MISSING
                else:
                    print(' == ESTE FALLO ACA >> ')
                    print(self._default, factory, nullable, self._default_factory)
                    if self._default_factory is not MISSING:
                        self._default = None
                    # if nullable is True: # Can be null
                    #     if factory is None:
                    #         factory = self._default_factory
                    #     self._default_factory = factory
            print('FACTORY > ', self._default_factory, self._default, kwargs.get('type'))
        # Calling Parent init
        if version_info.minor > 9:
            args["kw_only"] = kw_only
        super().__init__(
            default=self._default,
            default_factory=self._default_factory,
            **args
        )
        # set field type and dbtype
        self._field_type = self.type

    def __repr__(self):
        return (
            "Field("
            f"column={self.name!r}, "
            f"type={self.type!r}, "
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
    def primary_key(self):
        return self._primary


def Column(
    default: Optional[Callable] = None,
    nullable: bool = True,
    required: bool = False,
    factory: Optional[Callable] = None,
    min: Union[int, float] = None,
    max: Union[int, float] = None,
    validator: Optional[Callable] = None,
    kw_only: bool = False,
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
        **kwargs,
    )
