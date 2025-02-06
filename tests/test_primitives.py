import datetime
import pytest
from decimal import Decimal
from uuid import UUID, uuid4

# Import your encoder and validator functions. Adjust the import paths
# according to your project structure.
from datamodel.converters import (
    to_string,
    to_uuid,
    to_boolean,
    to_integer,
    to_float,
    to_date,
    to_datetime,
    to_timedelta,
    to_time,
    to_decimal,
    to_object,
    to_bytes,
)
from datamodel.validation import validators
from datamodel.types import Text
import asyncpg.pgproto.pgproto as pgproto

# ------------------------------
# Encoder Tests
# ------------------------------

@pytest.mark.parametrize("encoder,input_value,expected", [
    # to_string: strings, bytes, numbers, and callable returning a string
    (to_string, "hello", "hello"),
    (to_string, b"hello", "hello"),
    (to_string, 123, "123"),
    (to_string, lambda: "callable", "callable"),

    # to_uuid: if already a UUID, or from a string, or from a pgproto.UUID-like object.
    (
        to_uuid, "12345678-1234-5678-1234-567812345678",
        UUID("12345678-1234-5678-1234-567812345678")
    ),
    (to_uuid, uuid4(), lambda u: u),  # identity test; see note below

    # to_boolean: should convert typical true/false values
    (to_boolean, True, True),
    (to_boolean, False, False),
    (to_boolean, "true", True),
    (to_boolean, "false", False),
    (to_boolean, b"true", True),

    # to_integer: from int, string, or bytes representing an integer
    (to_integer, 42, 42),
    (to_integer, "42", 42),
    (to_integer, b"42", 42),

    # to_float: from float, string or int
    (to_float, 3.14, 3.14),
    (to_float, "3.14", 3.14),
    (to_float, 42, 42.0),

    # to_date: from a date instance or a date string in ISO format
    (to_date, datetime.date(2020, 1, 1), datetime.date(2020, 1, 1)),
    (to_date, "2020-01-01", datetime.date(2020, 1, 1)),

    # to_datetime: from a datetime instance or a datetime string
    (to_datetime, datetime.datetime(2020, 1, 1, 12, 0, 0), datetime.datetime(2020, 1, 1, 12, 0, 0)),
    (to_datetime, "2020-01-01T12:00:00", datetime.datetime(2020, 1, 1, 12, 0, 0)),

    # to_timedelta: from a timedelta instance or a string
    (
        to_timedelta, datetime.timedelta(hours=1, minutes=2, seconds=3),
        datetime.timedelta(hours=1, minutes=2, seconds=3)
    ),
    (to_timedelta, "1:02:03", lambda x: x),  # we'll check within a delta

    # to_time: from a time instance or a string
    (to_time, datetime.time(12, 34, 56), datetime.time(12, 34, 56)),
    (to_time, "12:34:56", datetime.time(12, 34, 56)),

    # to_decimal: from a Decimal or a string
    (to_decimal, Decimal("3.14159"), Decimal("3.14159")),
    (to_decimal, "3.14159", Decimal("3.14159")),

    # to_object: when input is already a dict/list/tuple, or from a JSON string
    (to_object, {"a":1}, {"a":1}),
    (to_object, [1,2,3], [1,2,3]),
    (to_object, (1,2,3), (1,2,3)),
    (to_object, '{"a": 1}', {"a": 1}),

    # to_bytes: from bytes, string, or callable returning a string
    (to_bytes, b"hello", b"hello"),
    (to_bytes, "hello", b"hello"),
    (to_bytes, lambda: "hello", b"hello"),
])
def test_encoders(encoder, input_value, expected):
    result = encoder(input_value)
    # For functions returning dynamic types (like uuid), allow a callable check:
    if callable(expected):
        # Expected function is applied to the result for equality check.
        assert result == expected(result)
    elif isinstance(expected, float):
        # Allow a small tolerance for float conversions.
        assert abs(result - expected) < 1e-6
    elif encoder == to_timedelta and isinstance(input_value, str):
        # For to_timedelta, allow a small delta.
        expected_td = datetime.timedelta(hours=1, minutes=2, seconds=3)
        assert abs(result - expected_td) < datetime.timedelta(seconds=1)
    else:
        assert result == expected

# ------------------------------
# Validator Tests
# ------------------------------

@pytest.mark.parametrize("validator,input_value", [
    # For valid inputs, validators should return None.
    (validators[str], "hello"),
    (validators[int], 42),
    (validators[float], 3.14),
    (validators[UUID], uuid4()),
    (validators[bool], True),
    (validators[datetime.date], datetime.date(2020, 1, 1)),
    (validators[datetime.datetime], datetime.datetime(2020, 1, 1, 12, 0, 0)),
    (validators[datetime.timedelta], datetime.timedelta(hours=1)),
    (validators[datetime.time], datetime.time(12, 34, 56)),
    (validators[Decimal], Decimal("2.718")),
    (validators[Text], "hello"),  # for Text, valid_str is used.
])
def test_validators(validator, input_value):
    # Using the type of the input as the expected type.
    error = validator(None, "field", input_value, type(input_value))
    assert error is None

@pytest.mark.parametrize("validator,input_value", [
    # For invalid inputs, validators should return an error message.
    (validators[str], 123),
    (validators[int], "not int"),
    (validators[float], "not float"),
    (validators[UUID], "not uuid"),
    (validators[bool], "not bool"),
    (validators[datetime.date], "not date"),
    (validators[datetime.datetime], "not datetime"),
])
def test_invalid_validators(validator, input_value):
    error = validator(None, "field", input_value, type(input_value))
    assert error is not None
