import timeit
import uuid
import datetime
import rs_parsers
from datamodel.converters import (
    to_string,
    to_date,
    to_datetime,
    to_uuid,
    to_integer,
    to_float,
    to_decimal,
    # strtobool,
    to_boolean
)
from decimal import Decimal

# print('==== STRING TO BOOL =====')

# def ct_str_to_bool():
#     for _ in range(1, 10):
#         obj = strtobool('True')
#         obj = strtobool('False')
#         obj = strtobool('true')
#         obj = strtobool('false')
#         obj = strtobool('TRUE')
#         obj = strtobool('FALSE')
#         obj = strtobool('1')
#         obj = strtobool('0')
#         obj = strtobool('yes')
#         obj = strtobool('no')
#         obj = strtobool('YES')
#         obj = strtobool('NO')
#         assert isinstance(obj, bool)

# def rs_str_to_bool():
#     for _ in range(1, 10):
#         obj = rs_parsers.strtobool('True')
#         obj = rs_parsers.strtobool('False')
#         obj = rs_parsers.strtobool('true')
#         obj = rs_parsers.strtobool('false')
#         obj = rs_parsers.strtobool('TRUE')
#         obj = rs_parsers.strtobool('FALSE')
#         obj = rs_parsers.strtobool('1')
#         obj = rs_parsers.strtobool('0')
#         obj = rs_parsers.strtobool('yes')
#         obj = rs_parsers.strtobool('no')
#         obj = rs_parsers.strtobool('YES')
#         obj = rs_parsers.strtobool('NO')
#         assert isinstance(obj, bool)

# print('Test with Cython: ')
# time = timeit.timeit(ct_str_to_bool, number=100000)
# print(f"Execution time: {time:.6f} seconds")

# print('Test with Rust: ')
# time = timeit.timeit(rs_str_to_bool, number=100000)
# print(f"Execution time: {time:.6f} seconds")


print('======== BOOLEAN ======')

def ct_to_boolean():
    for _ in range(1, 10):
        obj = to_boolean('True')
        obj = to_boolean('False')
        obj = to_boolean('true')
        obj = to_boolean('false')
        obj = to_boolean('TRUE')
        obj = to_boolean('FALSE')
        obj = to_boolean('1')
        obj = to_boolean('0')
        obj = to_boolean('yes')
        obj = to_boolean('no')
        obj = to_boolean('YES')
        obj = to_boolean('NO')
        assert isinstance(obj, bool)


print('Test with Cython: ')
time = timeit.timeit(ct_to_boolean, number=100000)
print(f"Execution time: {time:.6f} seconds")

print('=========== STRINGS ============== ')

def ct_to_string():
    for _ in range(1, 10):
        obj = to_string(b'\x00')
        obj = to_string(1234)
        assert isinstance(obj, str)

print('Test with Cython: ')
time = timeit.timeit(ct_to_string, number=100000)
print(f"Execution time: {time:.6f} seconds")


def rs_to_string():
    for _ in range(1, 10):
        obj = rs_parsers.to_string(b'\x00')
        obj = rs_parsers.to_string(1234)
        assert isinstance(obj, str)

print('Test with Rust: ')
time = timeit.timeit(ct_to_string, number=100000)
print(f"Execution time: {time:.6f} seconds")

print('=========== DATES ============== ')

def ct_to_dates():
    for _ in range(1, 10):
        # obj = to_date(datetime.datetime.now())
        obj = to_date('2028-01-01')
        assert isinstance(obj, datetime.date)

print('Test with Cython: ')
time = timeit.timeit(ct_to_dates, number=100000)
print(f"Execution time: {time:.6f} seconds")


def rs_to_dates():
    for _ in range(1, 10):
        # obj = rs_parsers.to_date(datetime.datetime.now())
        obj = rs_parsers.to_date('2028-01-01')
        assert isinstance(obj, datetime.date)

print('Test with Rust: ')
time = timeit.timeit(rs_to_dates, number=100000)
print(f"Execution time: {time:.6f} seconds")


print('=========== DATETIMES ============== ')

def ct_to_datetimes():
    for _ in range(1, 10):
        # obj = to_datetime(datetime.datetime.now())
        obj = to_datetime('2028-01-01 12:00:00')
        assert isinstance(obj, datetime.datetime)

def rs_to_datetimes():
    for _ in range(1, 10):
        # obj = rs_parsers.to_datetime(datetime.datetime.now())
        obj = rs_parsers.to_datetime('2028-01-01 12:00:00')
        assert isinstance(obj, datetime.datetime)

print('Test with Cython: ')
time = timeit.timeit(ct_to_datetimes, number=100000)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust: ')
time = timeit.timeit(rs_to_datetimes, number=100000)
print(f"Execution time: {time:.6f} seconds")

print('================== UUID ======================')


def ct_uuid():
    for _ in range(1, 10):
        obj = to_uuid("550e8400-e29b-41d4-a716-446655440000")  # UUID object
        obj = to_uuid(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))  # Same UUID
        obj = to_uuid(lambda: "550e8400-e29b-41d4-a716-446655440000")  # Callable
        _ = to_uuid("not-a-uuid")  # None
        assert isinstance(obj, uuid.UUID)

def rs_uuid():
    for _ in range(1, 10):
        obj = rs_parsers.to_uuid_str("550e8400-e29b-41d4-a716-446655440000")  # UUID object
        obj = rs_parsers.to_uuid_str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))  # Same UUID
        obj = rs_parsers.to_uuid_str(lambda: "550e8400-e29b-41d4-a716-446655440000")  # Callable
        _ = rs_parsers.to_uuid_str("not-a-uuid")  # None
        assert isinstance(obj, uuid.UUID)

def rs_uuid_native():
    for _ in range(1, 10):
        obj = rs_parsers.to_uuid("550e8400-e29b-41d4-a716-446655440000")  # UUID object
        obj = rs_parsers.to_uuid(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))  # Same UUID
        obj = rs_parsers.to_uuid(lambda: "550e8400-e29b-41d4-a716-446655440000")  # Callable
        _ = rs_parsers.to_uuid("not-a-uuid")  # None
        assert isinstance(obj, uuid.UUID)

print('Test with Cython: ')
time = timeit.timeit(ct_uuid, number=10000)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust: ')
time = timeit.timeit(rs_uuid, number=10000)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust Native: ')
time = timeit.timeit(rs_uuid_native, number=10000)
print(f"Execution time: {time:.6f} seconds")


print('================== INTEGERS ======================')


def ct_integers():
    for _ in range(1, 10):
        obj = to_integer(42)  # ✅ 42
        obj = to_integer("100")  # ✅ 100
        obj = to_integer(lambda: "123")  # ✅ 123
        obj = to_integer(None)  # ✅ None
        try:
            _ = to_integer("invalid")  # ❌ Raises ValueError
        except ValueError:
            pass

def rs_integers():
    for _ in range(1, 10):
        obj = rs_parsers.to_integer(42)  # ✅ 42
        obj = rs_parsers.to_integer("100")  # ✅ 100
        obj = rs_parsers.to_integer(lambda: "123")  # ✅ 123
        obj = rs_parsers.to_integer(None)  # ✅ None
        try:
            _ = rs_parsers.to_integer("invalid")  # ❌ Raises ValueError
        except ValueError:
            pass

print('Test with Cython: ')
time = timeit.timeit(ct_integers, number=10000)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust: ')
time = timeit.timeit(rs_integers, number=10000)
print(f"Execution time: {time:.6f} seconds")


print('================== FLOATS ======================')


def ct_floats():
    for _ in range(1, 10):
        obj = to_float(3.14)  # ✅ 3.14
        obj = to_float("2.71")  # ✅ 2.71
        obj = to_float(lambda: "1.618")  # ✅ 1.618
        obj = to_float(None)  # ✅ None
        try:
            _ = to_float("invalid")  # ❌ Raises ValueError
        except ValueError:
            pass

def rs_floats():
    for _ in range(1, 10):
        obj = rs_parsers.to_float(3.14)  # ✅ 3.14
        obj = rs_parsers.to_float("2.71")
        obj = rs_parsers.to_float(lambda: "1.618")  # ✅ 1.618
        obj = rs_parsers.to_float(None)  # ✅ None
        try:
            _ = rs_parsers.to_float("invalid")  # ❌ Raises ValueError
        except ValueError:
            pass

print('Test with Cython: ')
time = timeit.timeit(ct_floats, number=10000)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust: ')
time = timeit.timeit(rs_floats, number=10000)
print(f"Execution time: {time:.6f} seconds")


print('============ DECIMALS =============================')


def ct_decimals():
    for _ in range(1, 10):
        obj = to_decimal(Decimal("10.5"))
        obj = to_decimal("100.1234")
        obj = to_decimal(lambda: "3.1415")
        obj = to_decimal(42.56)
        obj = to_decimal(None)
        try:
            _ = to_decimal("not-a-decimal")
        except ValueError:
            pass

def rs_decimals():
    for _ in range(1, 10):
        obj = rs_parsers.to_decimal(Decimal("10.5"))
        obj = rs_parsers.to_decimal("100.1234")
        obj = rs_parsers.to_decimal(lambda: "3.1415")
        obj = rs_parsers.to_decimal(42.56)
        obj = rs_parsers.to_decimal(None)
        try:
            _ = rs_parsers.to_decimal("not-a-decimal")
        except ValueError:
            pass

print('Test with Cython: ')
time = timeit.timeit(ct_decimals, number=100)
print(f"Execution time: {time:.6f} seconds")

print('Test with Rust: ')
time = timeit.timeit(rs_decimals, number=100)
print(f"Execution time: {time:.6f} seconds")
