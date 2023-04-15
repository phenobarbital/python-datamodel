# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=False, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import NewType
from datetime import (
    datetime,
    time,
    date,
    timedelta
)
from uuid import UUID
from decimal import Decimal


uint64 = NewType('uint64', int)  # uint64
uint64_min = 0
uint64_max = (1 << 64) - 1


DB_TYPES: dict = {
    bool: "boolean",
    int: "integer",
    # int64: "bigint",
    uint64: "bigint",
    float: "float",
    str: "character varying",
    bytes: "byte",
    list: "Array",
    tuple: "Array",
    Decimal: "numeric",
    date: "date",
    datetime: "timestamp without time zone",
    time: "time",
    timedelta: "timestamp without time zone",
    UUID: "uuid",
    dict: "jsonb",
    type(None): None
}


MODEL_TYPES: dict = {
    "boolean": bool,
    "integer": int,
    "bigint": uint64,
    "float": float,
    "character varying": str,
    "string": str,
    "varchar": str,
    "byte": bytes,
    "bytea": bytes,
    "Array": list,
    "hstore": dict,
    "character varying[]": list,
    "numeric": Decimal,
    "date": date,
    "timestamp with time zone": datetime,
    "time": time,
    "timestamp without time zone": datetime,
    "uuid": UUID,
    "json": dict,
    "jsonb": dict,
    "text": str,
    "serial": int,
    "bigserial": int,
    "inet": str
}


JSON_TYPES: dict = {
    bool: "boolean",
    int: "integer",
    uint64: "long",
    float: "number",
    str: "string",
    bytes: "byte",
    list: "array",
    dict: "object",
    Decimal: "number",
    date: "date",
    datetime: "datetime",
    time: "time",
    timedelta: "timedelta",
    UUID: "uuid"
}


### Declaration of New Types:
Text: str = NewType('Text', str)


def default_dict():
    """Return a default empty string usable into Dataclasses.
    """
    return {}


def default_string():
    """Return a default string.
    """
    return ''
