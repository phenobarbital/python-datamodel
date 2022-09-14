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
        '_nullable'
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
    default: Optional[Callable] = None,
    nullable: bool = True,
    required: bool = False,
    factory: Optional[Callable] = None,
    min: Union[int, float, Decimal] = None,
    max: Union[int, float, Decimal] = None,
    validator: Optional[Union[Callable, None]] = None,
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
        **kwargs,
    )
