import uuid
from pathlib import Path, PurePath, PosixPath
from datetime import datetime
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, InitVar
from psycopg2 import Binary
import pytest
import numpy as np
import orjson
from datamodel import Field
from datamodel.parsers.json import JSONContent, json_encoder, json_decoder


# --- Helper classes for tests ---

class FakeRange:
    """
    A fake asyncpg Range-like object.
    Expected to have attributes 'lower' and 'upper'.
    The JSONContent encoder subtracts 1 from upper if it is an int.
    """
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

class DummyField:
    """
    A dummy Field-like class for testing.
    The JSONContent encoder calls its to_dict() method.
    """
    def to_dict(self):
        return {"dummy": "value"}

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

# --- Tests for each type ---

def test_decimal():
    value = Decimal("3.14")
    result = json_encoder(value)
    parsed = orjson.loads(result)
    # Expect Decimal to be converted to float
    assert isinstance(parsed, float)
    assert parsed == 3.14

def test_decimal_large():
    value = Decimal("1E+100")
    result = json_encoder(value)
    parsed = orjson.loads(result)
    # Expect Decimal to be converted to float without overflow
    assert isinstance(parsed, float)
    assert parsed == float(Decimal("1E+100"))

def test_decimal_small():
    value = Decimal("1E-100")
    result = json_encoder(value)
    parsed = orjson.loads(result)
    # Expect Decimal to be converted to float without underflow
    assert isinstance(parsed, float)
    assert parsed == float(Decimal("1E-100"))

def test_datetime():
    dt = datetime(2025, 2, 15, 12, 0, 0)
    # If naive_utc is True, orjson produces ISO format with "T" and a trailing "Z"
    expected = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    result = json_encoder(dt, naive_utc=True)
    # Remove surrounding quotes from the encoded JSON string
    assert result.strip('"') == expected

def test_datetime_non_naive():
    dt = datetime(2025, 2, 15, 12, 0, 0)
    # Without the UTC options, orjson might return ISO format without the trailing "Z"
    expected = dt.strftime('%Y-%m-%dT%H:%M:%S')
    result = json_encoder(dt, naive_utc=False)
    assert result.strip('"') == expected

def test_isoformat_object():
    # Create a dummy object that is not a datetime instance but has isoformat()
    class Dummy:
        def isoformat(self):
            return "dummy-isoformat"
    dummy = Dummy()
    result = json_encoder(dummy)
    assert result.strip('"') == "dummy-isoformat"

def test_uuid():
    u = uuid.uuid4()
    result = json_encoder(u)
    # orjson supports uuid natively, so the output is the standard string
    assert result.strip('"') == str(u)

def test_pathlib():
    p = Path("/tmp/test")
    result = json_encoder(p)
    assert result.strip('"') == str(p)

    pp = PurePath("/tmp/test2")
    result2 = json_encoder(pp)
    assert result2.strip('"') == str(pp)

    pposix = PosixPath("/tmp/test3")
    result3 = json_encoder(pposix)
    assert result3.strip('"') == str(pposix)

def test_hex_callable():
    # Object with a callable hex() method
    class WithHex:
        def hex(self):
            return "deadbeef"
    wh = WithHex()
    result = json_encoder(wh)
    assert result.strip('"') == "deadbeef"

def test_hex_non_callable():
    # Object with a non-callable hex attribute
    class WithHexAttr:
        hex = "non-callable-hex"
    wha = WithHexAttr()
    result = json_encoder(wha)
    assert result.strip('"') == "non-callable-hex"

def test_bytes_hex():
    # Bytes objects have a hex() method that returns their hexadecimal representation.
    b_val = b'\x00\xff'
    result = json_encoder(b_val)
    # Expected: "00ff"
    assert result.strip('"') == "00ff"

def test_asyncpg_range():
    # Fake asyncpg Range object: returns [lower, upper-1]
    r = FakeRange(1, 10)
    result = json_encoder(r)
    parsed = orjson.loads(result)
    assert parsed == [r.lower, r.upper - 1]

def test_numpy_array():
    arr = np.array([1, 2, 3])
    result = json_encoder(arr)
    parsed = orjson.loads(result)
    assert parsed == [1, 2, 3]

def test_enum_member():
    # Test an enum member: should return its value.
    result = json_encoder(Color.RED)
    parsed = orjson.loads(result)
    assert parsed == Color.RED.value

def test_enum_type():
    # Passing an Enum type should return a list of dicts.
    result = json_encoder(Color)
    parsed = orjson.loads(result)
    expected = [{'value': member.value, 'name': member.name} for member in Color]
    assert parsed == expected

def test_binary():
    # Test psycopg2.Binary object: should return str(binary_obj)
    b_obj = Binary(b"binarydata")
    result = json_encoder(b_obj)
    expected = str(b_obj)
    assert result.strip('"') == expected

def test_field():
    # Test that a Field-like object is serialized via its to_dict() method.
    field_obj = DummyField()
    result = json_encoder(field_obj)
    parsed = orjson.loads(result)
    assert parsed == field_obj.to_dict()

def test_initvar():
    @dataclass
    class TestClass:
        myinit: InitVar
        myfield: str = Field()
    init_var = TestClass(myinit='test', myfield='myfield')
    result = json_encoder(init_var)
    parsed = orjson.loads(result)
    assert parsed == {'myfield': 'myfield'}

def test_encode_decode_roundtrip():
    """
    Test a round-trip encode/decode for a complex object containing all the types.
    """
    data = {
        "decimal": Decimal("2.718"),
        "datetime": datetime(2025, 2, 15, 12, 0, 0),
        "uuid": uuid.uuid4(),
        "path": Path("/tmp/roundtrip"),
        "numpy": np.array([4, 5, 6]),
        "enum_member": Color.GREEN,
        "enum_type": Color,
        "range": FakeRange(100, 200),
        "bytes": b'\x01\x02',
        "field": DummyField()
    }
    encoded = json_encoder(data)
    decoded = json_decoder(encoded)

    # Decimal -> float
    assert isinstance(decoded["decimal"], float)
    assert decoded["decimal"] == 2.718

    # Datetime -> string
    assert isinstance(decoded["datetime"], str)
    expected = data["datetime"].strftime('%Y-%m-%dT%H:%M:%SZ')
    assert decoded["datetime"] == str(expected)

    # UUID -> string
    assert isinstance(decoded["uuid"], str)
    assert decoded["uuid"] == str(data["uuid"])

    # Path -> string
    assert decoded["path"] == str(data["path"])

    # Numpy array -> list
    assert decoded["numpy"] == [4, 5, 6]

    # Enum member -> its value
    assert decoded["enum_member"] == Color.GREEN.value

    # Enum type -> list of dicts
    expected_enum_type = [
        {'value': member.value, 'name': member.name} for member in Color
    ]
    assert decoded["enum_type"] == expected_enum_type

    # Fake asyncpg Range -> [lower, upper-1]
    assert decoded["range"] == [data["range"].lower, data["range"].upper - 1]

    # Bytes -> hex string
    assert decoded["bytes"] == "0102"

    # Field -> dict via to_dict()
    assert decoded["field"] == DummyField().to_dict()
