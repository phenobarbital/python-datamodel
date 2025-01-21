# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
"""
JSON Encoder, Decoder.
"""
import uuid
from pathlib import PosixPath, PurePath, Path
from datetime import datetime
from asyncpg.pgproto import pgproto
from psycopg2 import Binary
from dataclasses import _MISSING_TYPE, MISSING
from typing import Any, Union
from decimal import Decimal
from enum import Enum, EnumType
from ..exceptions cimport ParserError
from ..fields import Field
import orjson


cdef class JSONContent:
    """
    Basic Encoder using orjson
    """
    def __call__(self, object obj, **kwargs):
        return self.encode(obj, **kwargs)

    def default(self, object obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return str(obj)
        elif isinstance(obj, pgproto.UUID):
            return str(obj)
        elif isinstance(obj, uuid.UUID):
            return obj
        elif isinstance(obj, (PosixPath, PurePath, Path)):
            return str(obj)
        elif hasattr(obj, "hex"):
            if isinstance(obj, bytes):
                return obj.hex()
            else:
                return obj.hex
        elif hasattr(obj, 'lower'): # asyncPg Range:
            up = obj.upper
            if isinstance(up, int):
                up = up - 1  # discrete representation
            return [obj.lower, up]
        elif hasattr(obj, 'tolist'): # numpy array
            return obj.tolist()
        elif isinstance(obj, _MISSING_TYPE):
            return None
        elif obj is MISSING:
            return None
        elif isinstance(obj, (Enum, EnumType)):
            if obj is None:
                return None
            if hasattr(obj, 'value'):
                return obj.value
            else:
                return obj.name
        elif isinstance(obj, type) and issubclass(obj, Enum):
            return [{'value': e.value, 'name': e.name} for e in obj]
        elif isinstance(obj, Binary):  # Handle bytea column from PostgreSQL
            return str(obj)  # Convert Binary object to string
        elif isinstance(obj, Field):
            return obj.to_dict()
        raise TypeError(
            f'{obj!r} of Type {type(obj)} is not JSON serializable'
        )

    def encode(self, object obj, **kwargs) -> str:
        # decode back to str, as orjson returns bytes
        options = {
            "default": self.default,
            "option": orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY| orjson.OPT_UTC_Z | orjson.OPT_NON_STR_KEYS
        }
        if kwargs:
            options = {**options, **kwargs}
        try:
            return orjson.dumps(
                obj,
                **options
            ).decode('utf-8')
        except orjson.JSONEncodeError as ex:
            raise ParserError(
                f"Invalid JSON data: {ex}"
            )

    dumps = encode

    @classmethod
    def dump(cls, object obj, **kwargs):
        return cls().encode(obj, **kwargs)

    def decode(self, object obj):
        try:
            return orjson.loads(
                obj
            )
        except orjson.JSONDecodeError as ex:
            raise ParserError(
                f"Invalid JSON data: {ex}"
            )

    loads = decode

    @classmethod
    def load(cls, object obj, **kwargs):
        return cls().decode(obj, **kwargs)


cpdef str json_encoder(object obj):
    return JSONContent().dumps(obj)

cpdef object json_decoder(object obj):
    return JSONContent().loads(obj)


cdef class BaseEncoder:
    """
    Encoder replacement for json.dumps but using orjson
    """
    def __init__(self, *args, **kwargs):
        # Filter/adapt JSON arguments to ORJSON ones
        rjargs = ()
        rjkwargs = {}
        encoder = JSONContent(*rjargs, **rjkwargs)
        self.encode = encoder.__call__
