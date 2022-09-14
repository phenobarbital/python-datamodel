import uuid
import datetime
from decimal import Decimal
import numpy as np


DB_TYPES: dict = {
    bool: "boolean",
    int: "integer",
    np.int64: "bigint",
    float: "float",
    str: "character varying",
    bytes: "byte",
    list: "Array",
    Decimal: "numeric",
    datetime.date: "date",
    datetime.datetime: "timestamp without time zone",
    datetime.time: "time",
    datetime.timedelta: "timestamp without time zone",
    uuid.UUID: "uuid",
    dict: "jsonb"
}

MODEL_TYPES = {
    "boolean": bool,
    "integer": int,
    "bigint": np.int64,
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
    "date": datetime.date,
    "timestamp with time zone": datetime.datetime,
    "time": datetime.time,
    "timestamp without time zone": datetime.datetime,
    "uuid": uuid.UUID,
    "json": dict,
    "jsonb": dict,
    "text": str,
    "serial": int,
    "bigserial": int,
    "inet": str,
}

JSON_TYPES = {
    bool: "boolean",
    int: "integer",
    np.int64: "integer",
    float: "float",
    str: "string",
    bytes: "byte",
    list: "list",
    Decimal: "decimal",
    datetime.date: "date",
    datetime.datetime: "datetime",
    datetime.time: "time",
    datetime.timedelta: "timedelta",
    uuid.UUID: "uuid",
}
