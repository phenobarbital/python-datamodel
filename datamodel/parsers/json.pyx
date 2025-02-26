# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
"""
Module for JSON encoding and decoding using orjson with custom type handling.

This module provides the JSONContent class, which extends orjson's functionality to
support additional types (e.g., Decimal, datetime, custom Enum types, etc.), and a BaseEncoder
class as a drop-in replacement for json.dumps.
"""
import uuid
from pathlib import PosixPath, PurePath, Path
from datetime import datetime
from asyncpg.pgproto import pgproto
from psycopg2 import Binary
from cpython cimport PyErr_Clear
from cpython.object cimport (
    PyObject_IsInstance,
    PyObject_IsSubclass,
    PyObject_TypeCheck,
    PyObject_HasAttr,
    PyObject_GetAttr,
    PyCallable_Check
)
from dataclasses import _MISSING_TYPE, MISSING, InitVar
from typing import Any, Union
from decimal import Decimal
from enum import Enum, EnumType
import orjson
from ..exceptions cimport ParserError
from ..fields import Field


cdef inline bint is_callable(object obj):
    cdef int res = PyCallable_Check(obj)
    # PyCallable_Check normally returns 1 or 0, but if an error occurs,
    # assume it's not callable.
    return res != 0


cdef inline bint has_attribute(object obj, str name):
    cdef int result = PyObject_HasAttr(obj, name)
    if result < 0:
        PyErr_Clear()  # Clear any error that occurred
        return False
    return result != 0


cdef inline object get_attribute(object obj, str name):
    cdef object attr = PyObject_GetAttr(obj, name)
    if attr is None:
        PyErr_Clear()  # Clear any error that occurred
    return attr


cdef inline bint is_subclassof(object obj, object cls):
    cdef int res = PyObject_IsSubclass(obj, cls)
    if res < 0:
        PyErr_Clear()  # Clear error if subclass check fails
        return False
    return res != 0

cdef inline bint is_objid(object obj):
    return (
        getattr(obj, "__class__", None) is not None and
        obj.__class__.__module__ == "bson.objectid" and
        obj.__class__.__name__ == "ObjectId"
    )


ORJSON_DEFAULT_OPTIONS = (
    orjson.OPT_SERIALIZE_NUMPY |
    orjson.OPT_UTC_Z
    # orjson.OPT_NON_STR_KEYS
)


cdef class JSONContent:
    """
    A basic JSON encoder/decoder using orjson.

    This class provides methods to serialize Python objects to JSON strings and deserialize
    JSON strings back into Python objects, with custom handling for additional data types.
    """
    def __call__(self, object obj, **kwargs):
        return self.encode(obj, **kwargs)

    def default(self, object obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return str(obj)
        elif has_attribute(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, (PosixPath, PurePath, Path)):
            return str(obj)
        elif isinstance(obj, pgproto.UUID):
            return str(obj)
        elif isinstance(obj, uuid.UUID):
            return obj
        elif has_attribute(obj, "hex"):
            try:
                hex_method = get_attribute(obj, "hex")
                if is_callable(hex_method):
                    return hex_method()
            except AttributeError:
                return obj.hex
            if isinstance(obj, bytes):
                return obj.hex()
            else:
                return obj.hex
        elif has_attribute(obj, 'lower'): # asyncPg Range:
            up = obj.upper
            if isinstance(up, int):
                up = up - 1  # discrete representation
            return [obj.lower, up]
        elif has_attribute(obj, 'tolist'): # numpy array
            return obj.tolist()
        elif isinstance(obj, _MISSING_TYPE):
            return None
        elif obj is MISSING:
            return None
        elif PyObject_IsInstance(obj, type) and is_subclassof(obj, Enum):
            return [{'value': e.value, 'name': e.name} for e in obj]
        elif isinstance(obj, Enum):
            if has_attribute(obj, 'value'):
                return obj.value
            else:
                return obj.name
        elif isinstance(obj, Binary):  # Handle bytea column from PostgreSQL
            return str(obj)  # Convert Binary object to string
        elif is_objid(obj):
            return str(obj)
        elif isinstance(obj, Field):
            if has_attribute(obj, 'to_dict'):
                return obj.to_dict()
            return str(obj)
        elif has_attribute(obj, 'to_dict'):
            return obj.to_dict()
        elif has_attribute(obj, 'to_json'):
            # Return a JSON representation of the object.
            return orjson.Fragment(obj().encode())
        elif isinstance(obj, InitVar) or type(obj).__name__ == 'InitVar':
            # Handle InitVar explicitly
            return None
        raise TypeError(
            f'{obj!r} of Type {type(obj)} is not JSON serializable'
        )

    def encode(self, object obj, bint naive_utc = True, bint non_str_keys = False, **kwargs) -> str:
        """
        Custom default method for handling non-standard JSON serializable types.

        Supported types include Decimal, datetime, UUID, pathlib Paths, numpy arrays,
        custom Enums, asyncpg Ranges, and more.

        Parameters:
            obj: The object to convert to a JSON-compatible format.
            naive_utc (bool, optional): If True, convert datetime objects to naive UTC.
            non_str_keys (bool, optional): If True, use non-string keys for dictionaries.

        Returns:
            A JSON-serializable representation of `obj`.

        Raises:
            TypeError: If `obj` is not JSON serializable.
        """
        cdef int opt = ORJSON_DEFAULT_OPTIONS
        if naive_utc:
            opt |= orjson.OPT_NAIVE_UTC
        if non_str_keys:
            opt |= orjson.OPT_NON_STR_KEYS
        options = {
            "default": self.default,
            "option": opt
        }
        options.update(kwargs)
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
        """
        Class method to encode an object using a new JSONContent instance.
        """
        return cls().encode(obj, **kwargs)

    def decode(self, object obj):
        """
        Decode a JSON string into a Python object.

        Parameters:
            obj: A JSON string or bytes.

        Returns:
            The corresponding Python object.

        Raises:
            ParserError: If the JSON data is invalid.
        """
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
        """
        Class method to decode JSON data using a new JSONContent instance.
        """
        return cls().decode(obj, **kwargs)

cpdef str json_encoder(object obj, bint naive_utc = True, bint non_str_keys = False):
    """
    Encode an object to JSON using the default JSONContent encoder.
    """
    return JSONContent().dumps(obj, naive_utc=naive_utc, non_str_keys=non_str_keys)

cpdef object json_decoder(object obj):
    """
    Decode JSON data using the default JSONContent decoder.
    """
    return JSONContent().loads(obj)


cpdef object json_fragment(bytes obj):
    """
    Return a Orjson Fragment of an already-serialized JSON Document.
    """
    return orjson.Fragment(obj)


cdef class BaseEncoder:
    """
    Encoder replacement for json.dumps but using orjson,

    This is a drop-in replacement for json.dumps using orjson.
    """
    def __init__(self, *args, **kwargs):
        # Filter/adapt JSON arguments to ORJSON ones
        rjargs = ()
        rjkwargs = {}
        encoder = JSONContent(*rjargs, **rjkwargs)
        self.encode = encoder.__call__
