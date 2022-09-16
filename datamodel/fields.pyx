# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=False, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import (
    Optional,
    Union,
    Any
)
from decimal import Decimal
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
        '_dbtype'
    )

    def __init__(
        self,
        default: Optional[Callable] = None,
        nullable: bool = True,
        required: bool = False,
        factory: Optional[Callable] = None,
        min: Union[int, float, Decimal] = None,
        max: Union[int, float, Decimal] = None,
        validator: Optional[Union[Callable, None]] = None,
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
        if 'description' in kwargs:
            self.description = kwargs['description']
        else:
            self.description = None
        try:
            self._primary = kwargs["primary_key"]
            meta['primary'] = self._primary
            del kwargs["primary_key"]
        except KeyError:
            self._primary = False
        try:
            self._dbtype = kwargs["db_type"]
            del kwargs["db_type"]
        except KeyError:
            self._dbtype = None
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
        ## Encoder, decoder and widget:
        try:
            meta["widget"] = kwargs['widget']
            del kwargs['widget']
        except KeyError:
            meta["widget"] = {}
        try:
            meta["encoder"] = kwargs['encoder']
            del kwargs['encoder']
        except KeyError:
            meta["encoder"] = None
        try:
            meta["decoder"] = kwargs['decoder']
            del kwargs['decoder']
        except KeyError:
            meta["decoder"] = None
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
            kw_only=kw_only,
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
    min: Union[int, float, Decimal] = None,
    max: Union[int, float, Decimal] = None,
    validator: Optional[Union[Callable, None]] = None,
    kw_only: bool = False,
    **kwargs
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
        kw_only=kw_only,
        **kwargs,
    )
