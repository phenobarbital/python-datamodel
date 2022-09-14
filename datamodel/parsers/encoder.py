"""
JSON Encoders.
"""
import decimal
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import asyncpg
import numpy as np
from rapidjson import Encoder as JSONEncoder

class DefaultEncoder(JSONEncoder):
    """
    Basic Encoder using rapidjson
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return str(obj)
        elif isinstance(obj, timedelta):
            return str(obj)
        elif isinstance(obj, Enum):
            if not obj.value:
                return None
            else:
                return str(obj.value)
        elif isinstance(obj, uuid.UUID):
            try:
                return str(obj)
            except ValueError:
                if uobj := uuid.UUID(obj, version=4):
                    return str(uobj)
        elif isinstance(obj, decimal.Decimal):
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
        else:
            # return str(obj)
            raise TypeError(f"{obj!r} is not JSON serializable")

class BaseEncoder:
    """
    Encoder replacement for json.dumps using rapidjson
    """

    def __init__(self, *args, **kwargs):
        # Filter/adapt JSON arguments to RapidJSON ones
        rjargs = ()
        rjkwargs = {}
        encoder = DefaultEncoder(sort_keys=False, *rjargs, **rjkwargs)
        self.encode = encoder.__call__
