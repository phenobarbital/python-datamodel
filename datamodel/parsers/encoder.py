"""
JSON Encoders.
"""
from dataclasses import _MISSING_TYPE, MISSING
import decimal
from typing import Any, Union
from decimal import Decimal
import asyncpg
import numpy as np
import orjson


class DefaultEncoder:
    """
    Basic Encoder using orjson
    """
    def __init__(self, **kwargs):
        # eventually take into consideration when serializing
        self.options = kwargs

    def __call__(self, obj, **kwargs) -> Any:
        return self.encode(obj, **kwargs)

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, Decimal):
            return str(obj)
        elif hasattr(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, asyncpg.Range):
            return [obj.lower, obj.upper]
        elif hasattr(obj, "hex"):
            return obj.hex
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif obj == _MISSING_TYPE:
            return None
        elif obj == MISSING:
            return None
        raise TypeError(f"{obj!r} is not JSON serializable")

    def encode(self, obj, **kwargs) -> str:
        # decode back to str, as orjson returns bytes
        options = {
            "default": self.default,
            "option": orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY| orjson.OPT_UTC_Z
        }
        if kwargs:
            options = {**options, **kwargs}
        return orjson.dumps(
            obj,
            **options
        ).decode('utf-8')

    dumps = encode

    def decode(self, obj) -> Union[dict, list]:
        return orjson.loads(
            obj
        )

    loads = decode

class BaseEncoder:
    """
    Encoder replacement for json.dumps using orjson
    """

    def __init__(self, *args, **kwargs):
        encoder = DefaultEncoder(*args, **kwargs)
        self.encode = encoder.__call__
