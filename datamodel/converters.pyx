# cython: language_level=3, embedsignature=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
import re
from typing import get_args, get_origin, Union, Optional, List, NewType, Literal, Any, Set
from collections.abc import Sequence, Mapping, Callable, Awaitable
import types
from dataclasses import _MISSING_TYPE, _FIELDS, fields
import ciso8601
import orjson
from pathlib import PurePath, Path
from decimal import Decimal, InvalidOperation
from libc.stdio cimport sprintf, snprintf
from libc.stdlib cimport malloc, free
from cpython.mem cimport PyMem_Malloc, PyMem_Free
cimport cython
from cpython cimport datetime
from cpython.object cimport (
    PyObject_IsInstance,
    PyObject_IsSubclass,
    PyObject_HasAttr,
    PyObject_GetAttr,
    PyObject_SetAttr,
    PyObject_Call,
    PyObject_TypeCheck,
    PyCallable_Check
)
from cpython.ref cimport PyObject
from uuid import UUID
import asyncpg.pgproto.pgproto as pgproto
from .functions import is_iterable, is_primitive
from .validation import _validation
from .validation cimport _validate_constraints
from .fields import Field
# New converter:
import datamodel.rs_parsers as rc

cdef struct ColumnDef:
    const char* name
    PyObject* field

cdef bint is_dc(object obj):
    """Returns True if obj is a dataclass or an instance of a
    dataclass."""
    cls = obj if isinstance(obj, type) and not isinstance(obj, types.GenericAlias) else type(obj)
    return PyObject_HasAttr(cls, '__dataclass_fields__')

cdef bint is_typing(object obj):
    return PyObject_HasAttr(obj, '__module__') and obj.__module__ == 'typing'

cdef bint is_empty(object value):
    """
    Determines if a value should be considered empty.

    Enhanced to handle different container types properly, including:
    - None
    - Empty strings
    - Empty lists, tuples, sets
    - _MISSING_TYPE (used in default value checks)

    Returns True if the value is considered empty, False otherwise.
    """
    # None is always empty
    if value is None:
        return True

    # Field default missing markers
    if PyObject_IsInstance(value, _MISSING_TYPE) or value == _MISSING_TYPE:
        return True

    # Empty strings are considered empty
    if PyObject_IsInstance(value, str) and value == '':
        return True

    if PyObject_IsInstance(value, dict) and value == {}:
        return False

    if PyObject_IsInstance(value, (tuple, list, set)) and len(value) == 0:
        return True

    # Special case for containers: empty containers are NOT considered empty
    # because they are valid initialized values
    if PyObject_IsInstance(value, (list, tuple, set)):
        return False  # Return False even for empty containers

    # Numeric values of 0 are not considered empty
    if PyObject_IsInstance(value, (int, float)) and value == 0:
        return False

    # Objects with explicit "empty" attribute
    if PyObject_HasAttr(value, 'empty') and PyObject_GetAttr(value, 'empty') == False:
        return False

    # Fallback to Python's truthiness
    if not value:
        return True

    # Default: not empty
    return False

cpdef bint has_attribute(object obj, object attr):
    """Returns True if obj has the attribute attr."""
    return PyObject_HasAttr(obj, attr)

cpdef str to_string(object obj):
    """
    Returns a string version of an object.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, bytes):
        try:
            return obj.decode()
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode bytes: {e}") from e
    if isinstance(obj, (int, float, Decimal)):
        # its a number
        return str(obj)
    if callable(obj):
        # its a function callable returning a value
        try:
            val = obj()
            # Recursively call to_string on that result:
            return to_string(val)
        except Exception:
            pass
    # For any other arbitrary type, explicitly fail:
    raise ValueError(
        f"Cannot convert object of type {type(obj).__name__} to string."
    )

cpdef object to_uuid(object obj):
    """Returns a UUID version of a str column.
    """
    if isinstance(obj, pgproto.UUID):
        # If it's asyncpg's UUID, convert by casting to string first
        return UUID(str(obj))
    if isinstance(obj, UUID):
        # already an uuid
        return obj
    elif callable(obj):
        # its a function callable returning a value
        try:
            return UUID(obj())
        except:
            pass
    try:
        return UUID(str(obj))
    except ValueError:
        return None


cpdef str slugify_camelcase(str obj):
    """slugify_camelcase.

    Converting CamelCase into a spaced version, but don’t double-space
    if the string already contains spaces or uppercase letters follow
    existing spaces.
    """
    if not obj:
        return obj

    slugified = [obj[0]]
    for i in range(1, len(obj)):
        c = obj[i]
        # Condition: if c is uppercase AND the previous character isn't a space,
        # insert a space before it.
        if c.isupper() and not slugified[-1].isspace():
            slugified.append(' ')
        slugified.append(c)
    return ''.join(slugified)


cpdef datetime.date to_date(object obj):
    """to_date.

    Returns obj converted to date.
    """
    if obj is None:
        return None
    elif obj == _MISSING_TYPE:
        return None
    if isinstance(obj, datetime.date):
        return obj
    elif isinstance(obj, (datetime.datetime, datetime.timedelta)):
        return obj.date()
    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")
    # Handle Unix epoch via Rust's `to_timestamp`
    if isinstance(obj, (int, float)):
        try:
            return rc.to_timestamp(obj).date()
        except ValueError:
            pass
    # using rust todate function
    try:
        return rc.to_date(obj)
    except ValueError:
        pass
    # Fallback to Cython-native ciso8601 parsing
    try:
        return ciso8601.parse_datetime(obj).date()
    except ValueError:
        pass
        raise ValueError(
            f"Can't convert invalid data *{obj}* to date"
        )


cpdef datetime.datetime to_datetime(object obj):
    """to_datetime.

    Returns obj converted to datetime.
    """
    if obj is None:
        return None
    elif obj == _MISSING_TYPE:
        return None
    if isinstance(obj, datetime.datetime):
        return obj
    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")
    # Handle Unix epoch via Rust's `to_timestamp`
    if isinstance(obj, (int, float)):
        try:
            return rc.to_timestamp(obj)
        except ValueError:
            pass
    try:
        return ciso8601.parse_datetime(obj)
    except ValueError:
        pass
    try:
        return rc.to_datetime(obj)
    except ValueError:
        raise ValueError(
            f"Can't convert invalid data *{obj}* to datetime"
        )


cpdef object to_integer(object obj):
    """to_integer.

    Returns object converted to integer.
    """
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj
    if isinstance(obj, unicode):
        obj = obj.encode("ascii")
    if isinstance(obj, bytes):
        try:
            return int(obj)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid conversion to Integer of {obj}"
            ) from e
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    else:
        try:
            return int(obj)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid conversion to Integer of {obj}"
            ) from e

cpdef object to_float(object obj):
    """to_float.

    Returns object converted to float.
    """
    if isinstance(obj, (float, Decimal)):
        return obj
    elif isinstance(obj, _MISSING_TYPE):
        return None
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    else:
        try:
            return float(obj)
        except (TypeError, ValueError):
            return None

cpdef object to_decimal(object obj):
    """to_decimal.

    Returns a Decimal version of object.
    """
    if obj is None:
        return None
    if isinstance(obj, Decimal):
        return obj
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    else:
        try:
            return Decimal(obj)
        except InvalidOperation as ex:
            raise ValueError(
                f"Invalid Decimal conversion of {obj}"
            ) from ex
        except (TypeError, ValueError):
            return None

TIMEDELTA_RE = re.compile(r"(-)?(\d{1,3}):(\d{1,2}):(\d{1,2})(?:.(\d{1,6}))?")

cdef int _convert_second_fraction(s):
    if not s:
        return 0
    # Pad zeros to ensure the fraction length in microseconds
    s = s.ljust(6, "0")
    return int(s[:6])

cpdef object to_timedelta(object obj):

    if obj is None:
        return None
    if isinstance(obj, datetime.timedelta):
        return obj

    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")

    m = TIMEDELTA_RE.match(obj)
    if not m:
        return obj

    try:
        groups = list(m.groups())
        groups[-1] = _convert_second_fraction(groups[-1])
        negate = -1 if groups[0] else 1
        hours, minutes, seconds, microseconds = groups[1:]
        tdelta = (
                datetime.timedelta(
                    hours=int(hours),
                    minutes=int(minutes),
                    seconds=int(seconds),
                    microseconds=int(microseconds),
                )
                * negate
        )
        return tdelta
    except ValueError:
        raise ValueError(
            f"Invalid timedelta Object: {obj}"
        )

TIME_RE = re.compile(r"(\d{1,2}):(\d{1,2}):(\d{1,2})(?:.(\d{1,6}))?")

cpdef object to_time(object obj):
    """to_time.

    Returns obj converted to datetime.time.
    """
    if obj is None:
        return None
    if isinstance(obj, datetime.time):
        return obj
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    else:
        try:
            return datetime.time(*map(int, obj.split(':')))
        except (ValueError, TypeError):
            pass
        m = TIME_RE.match(obj)
        if not m:
            return obj
        try:
            groups = list(m.groups())
            groups[-1] = _convert_second_fraction(groups[-1])
            hours, minutes, seconds, microseconds = groups
            return datetime.time(
                hour=int(hours),
                minute=int(minutes),
                second=int(seconds),
                microsecond=int(microseconds),
            )
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid Time/Timestamp Object {obj}: {e}"
            )


cpdef object strtobool(str val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1', 'T'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0', 'none', 'null'):
        return False
    else:
        raise ValueError(
            f"Invalid truth value for **'{val}'**"
        )

cpdef object to_boolean(object obj):
    """to_boolean.

    Convert and returns any object value to boolean version.
    """
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")
    if isinstance(obj, str):
        return strtobool(obj)
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    else:
        return bool(obj)

cpdef object to_object(object obj):
    if obj is None:
        return None
    if isinstance(obj, (list, dict,tuple)):
        return obj
    elif callable(obj):
        # its a function callable returning a value
        try:
            return obj()
        except:
            pass
    elif isinstance(obj, str):
        try:
            return orjson.loads(obj)
        except (TypeError, ValueError):
            return None
    else:
        raise ValueError(
            f"Can't convert invalid data {obj} to Object"
        )

cpdef bytes to_bytes(object obj):
    """
    Convert the given object to bytes.

    - If the object is already bytes, return it directly.
    - If the object is a string, encode it (using UTF-8).
    - If the object is callable, call it and convert its result.
    - Otherwise, attempt to convert the object to bytes.
    If conversion fails, raise a ValueError.
    """
    if obj is None:
        raise ValueError("Cannot convert None to bytes")

    # 1. If already bytes, return as is.
    if isinstance(obj, bytes):
        return obj

    # 2. If it's a string, encode it to bytes.
    elif isinstance(obj, str):
        return obj.encode("utf-8")

    # 3. If it's callable, attempt to call it and convert its result.
    elif callable(obj):
        try:
            result = obj()
            # Recursively convert the result.
            return to_bytes(result)
        except Exception as e:
            raise ValueError("Failed to convert callable to bytes: %s" % e)

    # 4. Try converting the object into bytes using Python's built-in conversion.
    try:
        return bytes(obj)
    except Exception as e:
        raise ValueError("Invalid conversion to bytes: %s" % e)

cdef bint is_callable(object value) nogil:
    """
    Check if `value` is callable by calling Python's callable(...)
    but reacquire the GIL inside.
    """
    with gil:
        return callable(value)


# Encoder List:
encoders = {
    str: to_string,
    UUID: to_uuid,
    pgproto.UUID: to_uuid,
    bool: to_boolean,
    int: to_integer,
    float: to_float,
    datetime.date: to_date,
    datetime.datetime: to_datetime,
    datetime.timedelta: to_timedelta,
    datetime.time: to_time,
    Decimal: to_decimal,
    bytes: to_bytes,
    Path: lambda obj: Path(obj) if isinstance(obj, str) else obj
}


# Maps a type to a conversion callable
cdef dict TYPE_PARSERS = {}


cpdef object register_parser(object _type, object parser_func):
    """register_parser.

    Register a new Parser function for a given type.

    Parameters:
    _type (type): The type for which the parser function is registered.
    parser_func (function): The parser function to convert the given type.
    """
    TYPE_PARSERS[_type] = parser_func


## Parsing Functions
cdef object _parse_set_type(
    object field,
    object T,
    object data,
    object encoder,
    object args,
    object _parent = None
):
    """
    Parse a set of items to a typing type.
    """
    cdef object arg_type = args[0] if args else Any
    cdef set result = set()
    cdef tuple key = (arg_type, field.name)
    cdef object converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(arg_type)
    cdef object inner_type = field._inner_type if hasattr(field, '_inner_type') else arg_type
    cdef bint is_typing_set = hasattr(inner_type, '__origin__') and inner_type.__origin__ is set

    if data is None:
        return set()   # short-circuit

    # If data is not already a collection, put it in a list for processing
    if not isinstance(data, (list, tuple, set)):
        data = [data]

    # If it's a dataclass
    if is_dc(inner_type):
        for d in data:
            if is_dc(d):
                result.add(d)
            elif converter:
                result.add(
                    converter(field.name, d, inner_type, _parent)
                )
            elif isinstance(d, dict):
                result.add(inner_type(**d))
            elif isinstance(d, (list, tuple)):
                result.add(inner_type(*d))
            else:
                result.add(inner_type(d))
        return result
    elif is_typing_set:
        # If we're dealing with typing.Set[str] or similar
        inner_element_type = get_args(inner_type)[0] if get_args(inner_type) else Any
        # If the inner type is a set, we need to process it differently
        try:
            for item in data:
                if isinstance(item, str):
                    # String items are individual elements
                    result.add(item)
                elif isinstance(item, (list, tuple, set)):
                    # Process each element in collections
                    for element in item:
                        # Convert the element to the inner type if needed
                        if inner_element_type in encoders and not isinstance(element, inner_element_type):
                            converted = encoders[inner_element_type](element)
                            result.add(converted)
                        else:
                            result.add(element)
                else:
                    # Single non-string item
                    result.add(item)
        except Exception as e:
            raise ValueError(
                f"Error parsing set item of {inner_type}: {e}"
            ) from e
    elif converter:
        for item in data:
            result.add(
                converter(field.name, item, inner_type, _parent)
            )
    elif is_primitive(inner_type):
        # Process each item with appropriate converters
        for item in data:
            try:
                # If a specific encoder exists for this type, use it
                if encoder:
                    processed_item = encoder(item)
                else:
                    # Otherwise try to use builtin converters
                    processed_item = _parse_builtin_type(field, inner_type, item, None)
                result.add(processed_item)
            except Exception as e:
                raise ValueError(
                    f"Error parsing set item of {inner_type}: {e}"
                ) from e
    else:
        for item in data:
            result.add(
                _parse_typing(field, T=inner_type, data=item, encoder=encoder, as_objects=False)
            )
    return result

cdef object _parse_dict_type(
    object field,
    object T,
    object data,
    object encoder,
    object args
):
    cdef object key_type = args[0]  # First arg is key type
    cdef object val_type = args[1]  # Second arg is value type
    cdef dict new_dict = {}
    cdef object val_origin, val_args

    # Check if we have type args (Dict[K, V])
    if not args or len(args) < 2:
        return data  # If no type arguments, return as is

    # Get origin and args of value type to check if it's a nested Dict
    val_origin = get_origin(val_type)
    val_args = get_args(val_type)

    # Process each key-value pair
    for k, v in data.items():
        # Convert the key if needed
        if key_type == str and not isinstance(k, str):
            k = str(k)
        elif key_type == int and isinstance(k, str):
            try:
                k = int(k)
            except (ValueError, TypeError):
                pass

        # If value type is a nested Dict
        if val_origin is dict and val_args:
            if isinstance(v, dict):
                # Recursively process nested dict
                new_dict[k] = _parse_dict_type(field, val_type, v, encoder, val_args)
            else:
                # Not a dict but should be - create empty dict
                new_dict[k] = {}
        # If value type is a primitive type
        elif is_primitive(val_type):
            if val_type == int and isinstance(v, str):
                try:
                    new_dict[k] = int(v)
                except (ValueError, TypeError):
                    new_dict[k] = v
            elif val_type == float and isinstance(v, str):
                try:
                    new_dict[k] = float(v)
                except (ValueError, TypeError):
                    new_dict[k] = v
            elif val_type == bool and isinstance(v, str):
                try:
                    new_dict[k] = to_boolean(v)
                except (ValueError, TypeError):
                    new_dict[k] = v
            elif val_type in encoders:
                try:
                    new_dict[k] = encoders[val_type](v)
                except (ValueError, TypeError):
                    new_dict[k] = v
            else:
                new_dict[k] = v
        # Other non-primitive types
        else:
            new_dict[k] = _parse_typing(field, val_type, v, encoder, False)

    return new_dict

cdef object _parse_list_type(
    object field,
    object T,
    object data,
    object encoder,
    object args,
    object _parent = None
):
    """
    Parse a list of items to a typing type.
    """
    cdef object arg_type = args[0]
    cdef list result = []
    cdef tuple key = (arg_type, field.name)
    cdef object converter
    cdef object inner_type = field._inner_type or arg_type
    cdef bint is_optional = False
    cdef object origin = field._inner_origin or get_origin(T)
    cdef tuple type_args = field._typing_args or get_args(T)

    # Debug information if needed
    # print(f"_parse_list_type: field={field.name}, T={T}, data={data}, args={args}")

    if data is None:
        return []   # short-circuit

    # Compute the Inner Type:
    if hasattr(field, '_inner_type') and field._inner_type is not None:
        inner_type = field._inner_type
    # Then try to get it from the type's args
    elif type_args and len(type_args) > 0:
        inner_type = type_args[0]
    # Finally try to get it from args parameter
    elif args and isinstance(args, (list, tuple)) and len(args) > 0:
        if hasattr(args[0], '__origin__') and args[0].__origin__ is list and hasattr(args[0], '__args__'):
            # This is typing.List[T]
            arg_type = args[0]
            inner_type = arg_type.__args__[0] if arg_type.__args__ else Any
        else:
            inner_type = args[0]
    else:
        inner_type = Any

    if not isinstance(data, (list, tuple)):
        data = [data]

    # Get the converter if available
    key = (inner_type, field.name)
    converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(arg_type)

    # If it's a dataclass
    if is_dc(inner_type):
        for d in data:
            try:
                if is_dc(d):
                    result.append(d)
                elif converter:
                    result.append(
                        converter(field.name, d, inner_type, _parent)
                    )
                elif isinstance(d, dict):
                    result.append(inner_type(**d))
                elif isinstance(d, (list, tuple)):
                    result.append(inner_type(*d))
                else:
                    result.append(inner_type(d))
            except Exception as e:
                # Propagate the error with more context
                raise ValueError(
                    f"Error creating {inner_type.__name__} from {d}: {e}"
                ) from e
        return result
    elif is_typing(inner_type):
        if isinstance(data, list):
            result = _parse_list_typing(
                field,
                type_args,
                data,
                encoder,
                origin,
                args,
                None
            )
    elif converter:
        for item in data:
            result.append(
                converter(field.name, item, inner_type, _parent)
            )
    elif is_primitive(inner_type):
            try:
                for item in data:
                    if encoder:
                        result.append(encoder(item))
                    if inner_type == int and isinstance(item, str):
                        result.append(int(item))
                    elif inner_type == float and isinstance(item, str):
                        result.append(float(item))
                    else:
                        if inner_type in encoders:
                            result.append(encoders[inner_type](item))
                        else:
                            result.append(
                                _parse_builtin_type(field, inner_type, item, None)
                            )
            except Exception as e:
                try:
                    result = rc.to_list(inner_type, data)
                    # return data
                except Exception as e:
                    raise ValueError(
                        f"Error parsing list of {inner_type}: {e}"
                    ) from e
    elif inner_type is Any:
        # If no type is specified, return the list as-is
        return data
    else:
        # Default: process each item with _parse_typing
        for item in data:
            result.append(
                _parse_typing(field, T=inner_type, data=item, encoder=encoder, as_objects=False)
            )
    return result

cdef object _parse_tuple_type(
    object field,
    object T,
    object data,
    object encoder,
    object args
):
    """
    Parse a tuple of items to their respective types.
    Handles both heterogeneous tuples (Tuple[T1, T2, ...]) and
    homogeneous tuples (Tuple[T, ...])
    """
    cdef tuple result = ()

    # Handle empty data
    if data is None:
        return None

    # Ensure data is in tuple form
    if not isinstance(data, (list, tuple)):
        data = (data,)

    # Check for homogeneous tuple with ellipsis: Tuple[T, ...]
    if len(args) == 2 and args[1] is Ellipsis:
        # All elements should be of type args[0]
        element_type = args[0]
        result = tuple(
            _parse_builtin_type(field, element_type, item, encoder)
            if is_primitive(element_type) else
            _parse_type(field, element_type, item, encoder, False)
            for item in data
        )
    # Handle heterogeneous tuple: Tuple[T1, T2, ...]
    elif len(args) > 0:
        # Validate tuple length
        if len(data) != len(args):
            raise ValueError(
                f"Tuple length mismatch for {field.name}: expected {len(args)}, got {len(data)}"
            )

        # Convert each element according to its type
        converted_elements = []
        for i, (item_type, item) in enumerate(zip(args, data)):
            try:
                if is_primitive(item_type):
                    converted_elements.append(_parse_builtin_type(field, item_type, item, encoder))
                else:
                    converted_elements.append(_parse_type(field, item_type, item, encoder, False))
            except Exception as e:
                raise ValueError(
                    f"Error parsing tuple element {i} of {field.name}: {e}"
                )

        result = tuple(converted_elements)
    else:
        # No type args, just return the tuple
        result = tuple(data)

    return result

cdef object _parse_dataclass_type(object T, object data):
    if isinstance(data, dict):
        return T(**data)
    elif isinstance(data, (list, tuple)):
        return T(*data)
    else:
        return T(data)

cdef object _parse_builtin_type(object field, object T, object data, object encoder):
    if encoder is not None:
        try:
            return encoder(data)
        except ValueError as e:
            raise ValueError(f"Error parsing type {T}, {e}")
    if T == str:
        return to_string(data)
    if T == int:
        return to_integer(data)
    if T == float:
        return to_float(data)
    if T == datetime.date:
        return to_date(data)
    if T == datetime.datetime:
        return to_datetime(data)
    if T == UUID:
        return to_uuid(data)
    elif is_dc(T):
        return _parse_dataclass_type(T, data)
    elif T == Path:
        if isinstance(data, str):
            return Path(data)
        elif isinstance(data, Path):
            return data
        else:
            try:
                return Path(str(data))
            except:
                raise ValueError(f"Cannot convert {data} to Path")
    elif T == dict:
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected dict, got {type(data).__name__}"
            )
        return data
    elif T == list:
        if not isinstance(data, (list, tuple)):
            data = [data]
        return data
    else:
        # Try encoders dict:
        try:
            if field._encoder_fn is None:
                field._encoder_fn = encoders[T]
            return field._encoder_fn(data)
        except KeyError:
            # attempt direct construction:
            if isinstance(T, type):
                try:
                    if isinstance(data, dict):
                        return T(**data)
                    elif isinstance(data, (list, tuple)):
                        return T(*data)
                    elif isinstance(data, str):
                        return T(data)
                except (TypeError, ValueError):
                    pass
            return data
        except (TypeError) as e:
            raise TypeError(f"Error type {T}: {e}") from e
        except (ValueError) as e:
            raise ValueError(
                f"Error parsing type {T}: {e}"
            ) from e

cpdef object parse_basic(object T, object data, object encoder = None):
    """parse_basic.

    Parse a value to primitive types as str or int.
    --- (int, float, str, bool, bytes)
    """
    if T == str:
        if isinstance(data, str):
            return data
        elif data is not None:
            return str(data)
    if T == int:
        if isinstance(data, int):
            return data
        elif data is not None:
            return int(data)
    if T == bytes:
        if data is not None:
            return bytes(data)
    if T == UUID or T == pgproto.UUID:
        return to_uuid(data)
    if T == bool:
        if isinstance(data, bool):
            return data
    # function encoder:
    if encoder:
        if is_callable(encoder):
            # using a function encoder:
            try:
                return encoder(data)
            except TypeError as e:
                raise TypeError(
                    f"Type Error for Encoder {encoder!s} for type {T}: {e}"
                ) from e
            except ValueError as e:
                raise ValueError(
                    f"Error parsing type {T}, {e}"
                )
            except AttributeError as e:
                if data is None:
                    return None
                raise AttributeError(
                    f"Attribute Error for Encoder {encoder!s} for type {T}: {e}"
                ) from e
    # Using the encoders for basic types:
    try:
        return encoders[T](data)
    except KeyError:
        pass
    except TypeError as e:
        raise TypeError(f"Error type {T}: {e}") from e
    except ValueError as e:
        raise ValueError(
            f"Error parsing type {T}: {e}"
        ) from e


cdef object _parse_typing_type(
    object field,
    object T,
    object name,
    object data,
    object encoder,
    object origin,
    object args,
    object as_objects=False
):
    """
    Handle field_type='typing' scenario.
    """
    cdef tuple type_args = getattr(T, '__args__', ())

    if field.origin in {dict, Mapping} or name in {'Dict', 'Mapping'}:
        if isinstance(data, dict):
            if type_args:
                # e.g. Dict[K, V]
                return {k: _parse_type(field, type_args[1], v, None, False) for k, v in data.items()}
            return data
        else:
            raise TypeError(f"Expected dict, got {type(data).__name__}")

    if field.origin is tuple or name == 'Tuple' or field.origin == tuple:
        if isinstance(data, (list, tuple)):
            if len(type_args) == 2 and type_args[1] is Ellipsis:
                # Homogeneous tuple: e.g. Tuple[float, ...]
                return tuple(
                    _parse_type(field, type_args[0], datum, None, False)
                    for datum in data
                )
            elif len(data) == len(type_args):
                # Heterogeneous tuple: Convert each element to its corresponding type
                return tuple(
                    _parse_type(field, typ, datum, encoder, False)
                    for typ, datum in zip(type_args, data)
                )
            elif len(type_args) > 0:
                # Length mismatch but we have type arguments - try to convert what we can
                error = f"Tuple length mismatch for {field.name}: expected {len(type_args)}, got {len(data)}"
                raise ValueError(error)
        # If we can't process it, just return as-is
        return tuple(data) if not isinstance(data, tuple) else data

    if name in {'List', 'Sequence'} or field.origin in {list, Sequence}:
        if not isinstance(data, (list, tuple)):
            data = [data]
        return _parse_list_typing(
            field,
            type_args,
            data,
            encoder,
            origin,
            args,
            as_objects=as_objects
        )

    # handle None, Optional, Union:
    if name is None or name in ('Optional', 'Union'):
        return _parse_optional_union(field, T, data, encoder, origin, args)

    return data

cdef object _parse_list_typing(
    object field,
    tuple type_args,
    object data,
    object encoder,
    object origin,
    object args,
    object as_objects=False,
    dict typeinfo=None
):
    """
    Handle List[T] logic, trying to reduce overhead from repeated lookups.
    """
    cdef list result = []
    cdef list processed_sublist = []
    cdef list out = []
    cdef object arg_type = type_args[0] if type_args else None
    cdef object arg_module = getattr(arg_type, '__module__', None)
    cdef bint is_nested_typing = (arg_module == 'typing')

    # If no type args, we can't proceed with further logic
    if not type_args:
        return data

    if is_nested_typing:
        # nested typing: e.g. List[List[Foo]] or List[Optional[Foo]] etc.
        try:
            subT = arg_type.__args__[0]
            if is_dc(subT):
                for x in data:
                    result.append(_instantiate_dataclass(subT, x))
                return result
            elif field._inner_origin is list:
                inner_type = subT
                for sublist in data:
                    if not isinstance(sublist, (list, tuple)):
                        # Convert single items to lists if needed
                        sublist = [sublist]
                    processed_sublist = []
                    for item in sublist:
                        # Convert each item to the expected inner type
                        if is_primitive(inner_type):
                            if inner_type == int and isinstance(item, str):
                                processed_sublist.append(int(item))
                            elif inner_type == float and isinstance(item, str):
                                processed_sublist.append(float(item))
                            else:
                                processed_sublist.append(item)
                        else:
                            processed_sublist.append(_parse_type(field, inner_type, item, encoder, False))
                    result.append(processed_sublist)
                return result
            # Handle List[Optional[T]] or List[Union[...]]
            elif field._inner_origin is Union:
                for item in data:
                    processed_item = _parse_typing(field, arg_type, item, encoder, False)
                    result.append(processed_item)
                return result
            else:
                # fallback
                return data
        except AttributeError:
            return data
    elif arg_type is not None and is_dc(arg_type):
        # build list of dataclasses
        for d in data:
            result.append(_instantiate_dataclass(arg_type, d))
        return result
    elif is_primitive(arg_type):
        # For simple primitive types, don't create nested lists
        result = []
        for item in data:
            # Convert the item to the expected type
            if arg_type == int and isinstance(item, str):
                result.append(int(item))
            elif arg_type == float and isinstance(item, str):
                result.append(float(item))
            elif arg_type == str:
                result.append(str(item))
            elif arg_type == bool:
                result.append(to_boolean(item))
            else:
                result.append(item)
        return result
    else:
        for item in data:
            if type(item) is arg_type:
                result.append(item)
            else:
                # Convert the item to the expected type
                a = _parse_type(field, arg_type, item, encoder, False)
                result.append(a)
    return result

cdef object _instantiate_dataclass(object cls, object val):
    """
    Helper for instantiating a dataclass.
    """
    if is_dc(val):
        return val
    if isinstance(val, dict):
        return cls(**val)
    elif isinstance(val, (list, tuple)):
        return cls(*val)
    else:
        return cls(val)

cdef object _parse_optional_union(
    object field,
    object T,
    object data,
    object encoder,
    object origin,
    object args
):
    """
    Handle Optional or Union logic.
    """
    cdef object non_none_arg
    cdef object t = args[0] if args else None
    cdef bint matched = False

    # Safety check to avoid null pointer dereference
    if args is None or len(args) == 0:
        return data

    # Early exit for None values in Optional types
    if data is None and type(None) in args:
        return None

    for t in args:
        if t is not type(None) and PyObject_IsInstance(data, t):
            # For container types, we still need to process their contents
            if t in (list, dict, set, tuple) or get_origin(t) in (list, dict, set, tuple):
                # Continue to process contents
                pass
            else:
                return data

    # e.g. Optional[T] is Union[T, NoneType]
    if origin == Union and type(None) in args:
        # Pick the non-None type (assumes only two types in the Union)
        non_none_arg = args[0] if args[1] is type(None) else args[1]
        if non_none_arg is None:
            # If only None type is in the Union, return None
            return None
        non_none_origin = get_origin(non_none_arg)
        if non_none_origin is list:
            # Distinguish between typing.List and list
            if hasattr(non_none_arg, '__module__') and non_none_arg.__module__ == 'typing':
                # It's typing.List - use _parse_list_typing
                return _parse_list_typing(
                    field,
                    get_args(non_none_arg),
                    data,
                    encoder,
                    non_none_origin,
                    get_args(non_none_arg),
                    None
                )
            else:
                # It's a plain list - use _parse_list_type
                return _parse_list_type(
                    field,
                    non_none_arg,
                    data,
                    encoder,
                    get_args(non_none_arg),
                    None
                )
        else:
            return _parse_type(
                field,
                T=non_none_arg,
                data=data,
                encoder=encoder,
                as_objects=False
            )
    # Remove None from args.
    args = tuple(t for t in args if t is not type(None))
    # If there are no non-None types left, simply return data.
    if not args:
        return data

    for t in args:
        if isinstance(data, t):
            matched = True
            break
    if not matched:
        raise ValueError(
            f"Invalid type for *{field.name}* with {type(data)}, expected {T}"
        )
    try:
        if is_dc(t):
            if isinstance(data, dict):
                return t(**data)
            elif isinstance(data, (list, tuple)):
                return t(*data)
            else:
                try:
                    return t(data)
                except Exception:
                    return data
        elif callable(t):
            return data
        return data
    except KeyError:
        pass
    return data

cdef object _parse_union_type(
    object field,
    object T,
    object name,
    object data,
    object encoder,
    object origin,
    object targs
):
    """
    Attempt each type in the Union until one parses successfully
    or raise an error if all fail.
    If T is Optional[...] (i.e. a Union with NoneType), unwrap it.
    """
    cdef str field_name = field.name
    cdef str error = None
    cdef object non_none_arg = None
    cdef tuple inner_targs = None
    cdef bint is_typing = False
    cdef bint has_list_type = False
    cdef list errors = []  # Collect all errors to report if all types fail


    # First, check for None in Optional types
    if type(None) in targs and data is None:
        return None

    # If the union includes NoneType, unwrap it and use only the non-None type.
    if origin == Union and type(None) in targs:
        for arg in targs:
            if arg is not type(None):
                non_none_arg = arg
                break
        is_typing = hasattr(non_none_arg, '__module__') and non_none_arg.__module__ == 'typing'

        if non_none_arg is not None and is_typing is True:
            # Invoke the parse_typing_type
            field.args = get_args(non_none_arg)
            field.origin = get_origin(non_none_arg)
            if isinstance(data, list):
                return _parse_typing(
                    field,
                    non_none_arg,
                    data,
                    encoder,
                    False
                )

    # First check for dataclasses in the union
    for arg_type in targs:
        subtype_origin = field._inner_origin or get_origin(arg_type)
        if is_dc(arg_type):
            if isinstance(data, dict):
                try:
                    return arg_type(**data)
                except Exception as exc:
                    errors.append(f"Failed to create dataclass {arg_type.__name__} from dict: {exc}")
                    continue
            elif isinstance(data, arg_type):
                return data
            else:
                # For string inputs, don't accept them as dataclasses
                if isinstance(data, (str, int, float, bool)):
                    errors.append(f"Cannot convert {type(data).__name__} to {arg_type.__name__}")
                    continue
                try:
                    return arg_type(data)
                except Exception as exc:
                    errors.append(f"Failed to create {arg_type.__name__} from {type(data).__name__}: {exc}")
                    continue
        else:
            if is_primitive(arg_type):
                if isinstance(data, arg_type):
                    return data
                continue
            elif subtype_origin is list or subtype_origin is tuple:
                if isinstance(data, list):
                    try:
                        return _parse_list_type(field, arg_type, data, encoder, targs)
                    except ValueError as exc:
                        errors.append(str(exc))
                        continue
                else:
                    errors.append(f"Invalid type for {field_name}: Expected a list, got {type(data).__name__}")
                    continue
            elif subtype_origin is set:
                if isinstance(data, (list, tuple)):
                    return set(data)
                elif isinstance(data, set):
                    return data
                else:
                    try:
                        return _parse_set_type(field, T, data, encoder, targs, None)
                    except Exception as exc:
                        errors.append(f"Invalid type for {field_name}: Expected a set, got {type(data).__name__}")
                        continue
            elif subtype_origin is frozenset:
                if isinstance(data, (list, tuple)):
                    return frozenset(data)
                elif isinstance(data, frozenset):
                    return data
                else:
                    errors.append(f"Invalid type for {field_name}: Expected a frozenset, got {type(data).__name__}")
                    continue
            elif subtype_origin is list and field._inner_is_dc == True and isinstance(data, list):
                return _handle_list_of_dataclasses(field, field_name, data, T, None)
            elif subtype_origin is dict:
                if isinstance(data, dict):
                    return _parse_dict_type(field, arg_type, data, encoder, targs)
                else:
                    errors.append(
                        f"Invalid type for {field_name} Expected a dict, got {type(data).__name__}"
                    )
                    continue
            elif arg_type is list:
                if isinstance(data, list):
                    if arg_type is str:
                        # Ensure all elements in the list are strings
                        if all(isinstance(item, str) for item in data):
                            return data
                    else:
                        return _parse_list_type(field, arg_type, data, encoder, targs)
                else:
                    errors.append(
                        f"Invalid type for {field_name}: Expected a list, got {type(data).__name__}"
                    )
                    continue
            elif arg_type is dict:
                if isinstance(data, dict):
                    return _parse_dict_type(field, arg_type, data, encoder, targs)
                else:
                    errors.append(
                        f"Invalid type for {field_name} Expected a dict, got {type(data).__name__}"
                    )
                    continue
            elif subtype_origin is None:
                try:
                    if is_dc(arg_type):
                        return _handle_dataclass_type(field, name, data, arg_type, False, None)
                    elif arg_type in encoders:
                        return _parse_builtin_type(field, arg_type, data, encoder)
                    elif isinstance(data, arg_type):
                        return data
                    else:
                        # Not matching => record an error
                        errors.append(
                            f"Invalid type for {field_name}, Data {data!r} is not an instance of {arg_type}"
                        )
                        continue
                except ValueError as exc:
                    errors.append(f"{field.name}: {exc}")
                    continue
            else:
                try:
                    # fallback to builtin parse
                    return _parse_typing(
                        field,
                        arg_type,
                        data,
                        encoder,
                        False
                    )
                except ValueError as exc:
                    errors.append(f"{field.name}: {exc}")
                    continue
                except Exception as exc:
                    errors.append(f"Parse Error on {field.name}, {arg_type}: {exc}")
                    continue

    # If we get here, all union attempts failed
    if errors:
        error_msg = f"All Union types failed for {field_name}. Errors: " + "; ".join(errors)
        raise ValueError(error_msg)
    else:
        raise ValueError(
            f"Invalid type for {field_name} with data={data}, no matching type found"
        )

cdef object _parse_type(
    object field,
    object T,
    object data,
    object encoder=None,
    object as_objects=False,
):
    """
    Parse a value to a typing type.
    """
    # local cdef variables:
    cdef object origin = get_origin(T)
    cdef object targs = get_args(T)
    cdef object name = getattr(T, '_name', None)  # T._name or None if not present
    cdef object sub = None     # for subtypes, local cache
    cdef object result = None
    cdef object isdc = is_dc(T)

    if data is None:
        return None

    if isdc:
        return _handle_dataclass_type(None, name, data, T, as_objects, None)
    # Field type shortcuts
    elif origin is dict and isinstance(data, dict):
        return _parse_dict_type(field, T, data, encoder, targs)
    elif origin is list:
        return _parse_list_type(field, T, data, encoder, targs)
    elif origin is tuple:
        return _parse_tuple_type(field, T, data, encoder, targs)
    elif origin is set:
        # Handle Sets - convert lists to sets
        if isinstance(data, (list, tuple)):
            return set(data)  # Convert list/tuple to set
        elif isinstance(data, set):
            return data
        else:
            return {data} if data is not None else set()  # Wrap single value in set
    elif origin is frozenset:
        # Handle Frozensets - convert lists to frozensets
        if isinstance(data, (list, tuple)):
            return frozenset(data)  # Convert list/tuple to frozenset
        elif isinstance(data, frozenset):
            return data
        else:
            return frozenset([data]) if data is not None else frozenset()  # Wrap single value in frozenset
    elif origin is not None:
        if T in (int, float, str, bool) or T in encoders:
            return _parse_builtin_type(field, T, data, encoder)
        return data
    elif T is set:
        # Handle bare 'set' type
        if isinstance(data, (list, tuple)):
            return set(data)  # Convert list/tuple to set
        elif isinstance(data, set):
            return data
        else:
            return {data} if data is not None else set()
    else:
        # fallback to builtin parse
        result = _parse_builtin_type(field, T, data, encoder)
        return result

cdef object _parse_typing(
    object field,
    object T,
    object data,
    object encoder=None,
    object as_objects=False,
    object parent=None,
):
    """
    Parse a value to a typing type.
    """
    # local cdef variables:
    cdef object origin, targs
    cdef object name = getattr(T, '_name', None)  # T._name or None if not present
    cdef object sub = None     # for subtypes, local cache
    cdef object result = None
    cdef object inner_type = None
    cdef bint inner_is_dc = 0 # field._inner_is_dc or is_dataclass(inner_type)

    if data is None:
        return None  # no data, short-circuiting

    # Use cached values only if T is exactly the field's declared type.
    if T == field.type:
        origin = field.origin
        targs = field.args
    elif field._inner_type and field._inner_type == inner_type:
        origin = field._inner_origin
        targs = field._inner_args
    else:
        origin = get_origin(T)
        targs = get_args(T)

    # For generic (typing) fields, reuse cached inner type info if available.
    if origin in (list, set, frozenset) and targs:
        if field._inner_type is not None:
            inner_type = field._inner_type
            inner_origin = field._inner_origin
            # Optionally, also use cached type arguments for the inner type.
        else:
            inner_type = targs[0] if targs else Any
            inner_origin = get_origin(inner_type)
    else:
        inner_type = None
        inner_origin = None

    inner_is_dc = field._inner_is_dc or is_dc(inner_type)

    # Put more frequently cases first:
    if field.is_dc or is_dc(T):
        return _handle_dataclass_type(None, name, data, T, as_objects, None)

    # If the field is a Union and data is a list, use _parse_union_type.
    if origin is Union:
        # e.g. Optional[...] or Union[A, B]
        if len(targs) == 2 and type(None) in targs:
            # Handle Optional[...] that is Union[..., None] cases first:
            if field._inner_priv:
                # If Optional but non-None is a primitive
                return _parse_builtin_type(field, field._inner_type, data, encoder)
            elif field._inner_is_dc:
                # non-None is a Optional Dataclass:
                return _handle_dataclass_type(None, name, data, field._inner_type, as_objects, None)
            else:
                real_type = targs[0] if targs[1] is type(None) else targs[1]
                # Recursively parse the real_type exactly as if it weren't wrapped in Optional[…].
                return _parse_typing(field, real_type, data, encoder, as_objects, parent)
        else:
            try:
                return _parse_union_type(
                    field,
                    T,
                    name,
                    data,
                    encoder,
                    origin,
                    targs
                )
            except Exception as e:
                raise ValueError(
                    f"Union parsing error for {field.name}: {e}"
                ) from e
    # Other Field types
    if field._type_category == 'typing':
        # For example, if the origin is list and the inner type is a dataclass,
        # use _handle_dataclass_type on each element.
        if origin is list:
            if inner_is_dc:
                return _parse_list_type(field, T, data, encoder, targs, parent)
            else:
                return _parse_typing_type(
                    field, T, name, data, encoder, origin, targs, as_objects
                )
        elif origin is set:
            if targs and targs[0] is not Any:
                if isinstance(data, (list, tuple)):
                    result = set()
                    for item in data:
                        converted_item = _parse_type(field, targs[0], item, encoder, False)
                        result.add(converted_item)
                    return result
                elif isinstance(data, set):
                    # Already a set, just validate/convert the elements
                    result = set()
                    for item in data:
                        converted_item = _parse_type(field, targs[0], item, encoder, False)
                        result.add(converted_item)
                    return result
                else:
                    # Single value, convert and wrap in a set
                    converted_item = _parse_type(field, targs[0], data, encoder, False)
                    return {converted_item} if data is not None else set()
            else:
                # Untyped set, just convert to a set without validating elements
                if isinstance(data, (list, tuple)):
                    return set(data)
                elif isinstance(data, set):
                    return data
                else:
                    return {data} if data is not None else set()
        else:
            return _parse_typing_type(
                field, T, name, data, encoder, origin, targs, as_objects
            )
    # Handle container types with proper recursive processing
    # List types
    elif origin is list:
        return _parse_list_type(field, T, data, encoder, targs, parent)

    # Set types
    elif origin is set:
        return _parse_set_type(field, T, data, encoder, targs, parent)

    # FrozenSet types - process as set, then convert to frozenset
    elif origin is frozenset:
        try:
            # Convert to set first if needed
            if isinstance(data, (list, tuple, set)):
                set_data = set(data)
            elif isinstance(data, frozenset):
                set_data = data
            else:
                set_data = {data} if data is not None else set()

            # Process as a set
            processed_set = _parse_set_type(field, T, set_data, encoder, targs, parent)

            # Convert back to frozenset
            return frozenset(processed_set)
        except Exception as e:
            # Be resilient to errors
            if isinstance(data, frozenset):
                return data
            elif isinstance(data, (set, list, tuple)):
                return frozenset(data)
            else:
                return frozenset({data}) if data is not None else frozenset()
    # Dict types
    elif origin is dict and isinstance(data, dict):
        return _parse_dict_type(field, T, data, encoder, targs)
    elif origin is not None:
        # other advanced generics
        return data
    else:
        # fallback to builtin parse
        return _parse_builtin_type(field, T, data, encoder)

cdef object _parse_literal_type(
    object field,
    object T,
    object data,
    object encoder
):
    """
    _parse_literal_type parses a typing.Literal[...] annotation.

    :param field: A Field object (or similar) containing metadata
    :param T: The full annotated type (e.g. typing.Literal['text/plain', 'text/html']).
    :param data: The input value to check.
    :param encoder: Optional encoder (not usually used for literal).
    :return: Returns 'data' if it matches one of the literal choices, otherwise raises ValueError.
    """

    # Each element in `targs` is a valid literal value, e.g. a string, int, etc.
    # If data is exactly in that set, it's valid.
    cdef tuple targs = field.args
    cdef tuple i
    for arg in targs:
        if data == arg:
            return data

    # If we get here, data didn't match any literal value
    raise ValueError(
        f"Literal parse error for field '{field.name}': "
        f"value={data!r} is not one of {targs}"
    )

cdef object _handle_dataclass_type(
    object field,
    str name,
    object value,
    object _type,
    object as_objects = False,
    object parent = None
):
    """
    _handle_dataclass_type.

    Process a field that is annotated as SomeDataclass.
    If there's a registered converter for the dataclass, call it;
    otherwise, build the dataclass using default logic.
    """
    cdef tuple key = (_type, name)
    cdef object converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(_type)
    cdef bint isdc = field.is_dc if field else is_dc(_type)
    cdef object field_metadata = field.metadata if field else {}
    cdef str alias = field_metadata.get('alias')

    if value is None or is_dc(value):
        return value
    if PyObject_IsInstance(value, dict):
        try:
            # If alias exists, adjust the key passed to the dataclass
            if alias:
                # if alias exists on type, preserve the alias:
                if alias not in value and name in value:
                    value = value.copy()
                    value[alias] = value.pop(name)
            # convert the dictionary to the dataclass
            return _type(**value)
        except TypeError:
            # Ensure keys are strings
            value = {str(k): v for k, v in value.items()}
            if alias:
                value = value.copy()
                value[name] = value.pop(alias, None)
            return _type(**value)
        except ValueError:
            # replace in "value" dictionary the current "name" for "alias"
            if alias:
                value = value.copy()
                value[alias] = value.pop(name, None)
            return _type(**value)
        except Exception as exc:
            raise ValueError(
                f"Invalid value for {name}:{_type} == {value}, error: {exc}"
            )
    try:
        if PyObject_IsInstance(value, (list, tuple)):
            return _type(*value)
        else:
            # If a converter exists for this type, use it:
            if converter:
                return converter(name, value, _type, parent)
            if as_objects:
                # If alias exists, adjust the key passed to the dataclass
                if not alias:
                    alias = name
                # convert the list to the dataclass
                return _type(**{alias: value})
            if PyObject_IsInstance(value, (int, str, UUID)):
                return value
            if isdc:
                if not alias:
                    alias = name
                return _type(**{alias: value})
            else:
                return _type(value)
    except Exception as exc:
        raise ValueError(
            f"Invalid value for {name}:{_type} == {value}, error: {exc}"
        )

cdef object _handle_list_of_dataclasses(
    object field,
    str name,
    object value,
    object _type,
    object parent = None
):
    """
    _handle_list_of_dataclasses.

    Process a list field that is annotated as List[SomeDataclass].
    If there's a registered converter for the sub-dataclass, call it;
    otherwise, build the sub-dataclass using default logic.
    """
    try:
        sub_type = _type.__args__[0]
        if is_dc(sub_type):
            key = (sub_type, name)
            converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(_type)
            new_list = []
            for item in value:
                if converter:
                    new_list.append(converter(name, item, sub_type, parent))
                elif isinstance(item, dict):
                    new_list.append(sub_type(**item))
                else:
                    new_list.append(item)
            return new_list
    except ValueError:
        raise
    except AttributeError:
        pass
    return value

# Helper function to handle sets of dataclasses
cdef object _handle_set_of_dataclasses(
    object field,
    str name,
    object value,
    object _type,
    object parent = None
):
    """
    _handle_set_of_dataclasses.

    Process a set field that is annotated as Set[SomeDataclass].
    If there's a registered converter for the sub-dataclass, call it;
    otherwise, build the sub-dataclass using default logic.
    """
    try:
        sub_type = _type.__args__[0]
        if is_dc(sub_type):
            key = (sub_type, name)
            converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(_type)
            new_set = set()
            for item in value:
                if converter:
                    new_set.add(converter(name, item, sub_type, parent))
                elif isinstance(item, dict):
                    new_set.add(sub_type(**item))
                else:
                    new_set.add(item)
            return new_set
    except (AttributeError, IndexError):
        pass
    return value

cdef object _handle_default_value(
    object obj,
    str name,
    object value,
    object default_func,
    object default_is_callable
):
    """Handle default value of fields."""
    # If value is callable, try calling it directly
    if PyCallable_Check(value):
        try:
            new_val = value()
        except TypeError:
            try:
                new_val = default_func()
            except TypeError:
                new_val = None
        setattr(obj, name, new_val)
        return new_val

    # If f.default is callable and value is None
    if default_is_callable and value is None:
        try:
            new_val = default_func()
        except (AttributeError, RuntimeError, TypeError):
            new_val = None
        setattr(obj, name, new_val)
        return new_val

    # If there's a non-missing default and no value
    if not isinstance(default_func, _MISSING_TYPE) and value is None:
        setattr(obj, name, default_func)
        return default_func

    # Otherwise, return value as-is
    return value

cdef dict _build_error(str name, str message, object exp):
    """
    _build_error.

    Build a tuple containing an error message and the name of the field.
    """
    cdef str error_message = message + name + ", Error: " + str(exp)
    return {name: error_message}

cpdef dict processing_fields(object obj, list columns):
    """
    Process the fields (columns) of a dataclass object.

    For each field, if a custom parser is attached (i.e. f.parser is not None),
    it is used to convert the value. Otherwise, the standard conversion logic
    (parse_basic, parse_typing, etc.) is applied.
    """
    cdef object new_val
    cdef object _encoder = None
    cdef object _default = None
    cdef object _type = None
    cdef object meta = obj.Meta
    cdef bint as_objects = meta.as_objects
    cdef bint no_nesting = meta.no_nesting
    cdef tuple type_args = ()
    # Error handling
    cdef dict errors = {}
    # Type Information
    cdef dict _typeinfo = {}
    # Column information:
    cdef tuple c_col
    cdef str name
    cdef object f
    cdef object value
    cdef object newval

    for c_col in columns:
        name = c_col[0]
        f = c_col[1]
        value = getattr(obj, name)
        # Use the precomputed field type category:
        field_category = f._type_category

        if field_category == 'descriptor':
            # Handle descriptor-specific logic
            try:
                value = f.__get__(obj, type(obj))  # Get the descriptor value
                PyObject_SetAttr(obj, name, value)
            except Exception as e:
                errors.update(_build_error(name, f"Descriptor Error on {name}: ", e))
            continue

        # get type and default:
        _type = f.type
        _default = f.default
        typeinfo = f.typeinfo # cached info (e.g., type_args, default_callable)
        type_args = f.type_args
        try:
            metadata = f.metadata
        except AttributeError:
            metadata = PyObject_GetAttr(f, "metadata")

        # _default_callable = typeinfo.get('default_callable', False)
        # Check if object is empty
        if is_empty(value) and not PyObject_IsInstance(value, list):
            if _type == str and value is not "":
                value = f.default_factory if PyObject_IsInstance(_default, (_MISSING_TYPE)) else _default
            # PyObject_SetAttr(obj, name, value)
            obj.__dict__[name] = value
        if _default is not None:
            value = _handle_default_value(obj, name, value, _default, f._default_callable)
        try:
            _encoder = metadata.get('encoder')
            newval = value

            if f.parser is not None:
                # If a custom parser is attached to Field, use it
                try:
                    newval = f.parser(value)
                    if newval != value:
                        obj.__dict__[name] = newval
                except Exception as ex:
                    errors.update(
                        _build_error(name, f"Error parsing *{name}* = *{value}*", ex)
                    )
            elif field_category == 'primitive':
                try:
                    newval = parse_basic(_type, value, _encoder)
                    if newval != value:
                        obj.__dict__[name] = newval
                except ValueError as ex:
                    errors.update(
                        _build_error(name, f"Error parsing {name}: ", ex)
                    )
            elif field_category == 'type':
                # TODO: support multiple types
                pass
            elif field_category == 'dataclass':
                try:
                    if no_nesting is False:
                        if as_objects is True:
                            newval = _handle_dataclass_type(
                                f, name, value, _type, as_objects, obj
                            )
                        else:
                            newval = _handle_dataclass_type(
                                f, name, value, _type, as_objects, None
                            )
                        if newval!= value:
                            # PyObject_SetAttr(obj, name, newval)
                            obj.__dict__[name] = newval
                except ValueError:
                    raise
                except Exception as ex:
                    errors.update(
                        _build_error(name, f"Error parsing Dataclass: {name}: ", ex)
                    )
                    continue
            elif f.origin in (list, 'list') and f._inner_is_dc:
                try:
                    if as_objects is True:
                        newval = _handle_list_of_dataclasses(f, name, value, _type, obj)
                    else:
                        newval = _handle_list_of_dataclasses(f, name, value, _type, None)
                    obj.__dict__[name] = newval
                except ValueError:
                    raise
                except Exception as ex:
                    errors.update(
                        _build_error(name, f"Error handling list of dataclasses at {name}: ", ex)
                    )
                    continue
            # Handle set of dataclasses
            elif f.origin in (set, 'set') and getattr(f, '_inner_is_dc', False):
                try:
                    if as_objects is True:
                        newval = _handle_set_of_dataclasses(f, name, value, _type, obj)
                    else:
                        newval = _handle_set_of_dataclasses(f, name, value, _type, None)
                    obj.__dict__[name] = newval
                except ValueError:
                    raise
                except Exception as ex:
                    errors.update(
                        _build_error(name, f"Error handling set of dataclasses at {name}: ", ex)
                    )
                    continue
            elif field_category == 'typing':
                if f.is_dc:
                    try:
                        # means that is_dataclass(T)
                        newval = _handle_dataclass_type(None, name, value, _type, as_objects, None)
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error handling dataclass {name}: ", ex))
                        continue
                elif f.origin is Literal:
                    try:
                        # e.g. Literal[...]
                        newval = _parse_literal_type(f, _type, value, _encoder)
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing Literal {name}: ", ex))
                        continue
                elif f.origin is list:
                    try:
                        # Other typical case is when is a List of primitives.
                        if f._inner_priv:
                            newval = _parse_list_type(
                                f,
                                _type,
                                value,
                                _encoder,
                                f.args,
                                obj
                            )
                        else:
                            try:
                                newval = _parse_typing(
                                    f,
                                    _type,
                                    value,
                                    _encoder,
                                    as_objects,
                                    obj
                                )
                            except Exception as e:
                                raise ValueError(
                                    f"Error parsing List: {name}: {e}"
                                )
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(
                            _build_error(name, f"Error parsing List {name}: ", ex)
                        )
                        continue
                elif f.origin is set:
                    try:
                        if isinstance(value, list):
                            newval = set(value)  # Simple conversion for bare set
                        elif f._inner_priv is True:
                            # is a primitive typing Set.
                            newval = _parse_set_type(
                                f,
                                _type,
                                value,
                                _encoder,
                                f.args,
                                obj
                            )
                        else:
                            try:
                                newval = _parse_typing(
                                    f,
                                    _type,
                                    value,
                                    _encoder,
                                    as_objects,
                                    obj
                                )
                            except Exception as e:
                                raise ValueError(
                                    f"Error parsing Set: {name}: {e}"
                                )
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing Set: ", ex))
                        continue
                # FrozenSet type
                elif f.origin is frozenset:
                    try:
                        if value is not None:
                            # Convert to set first if needed
                            set_value = value if isinstance(value, (set, frozenset)) else set(value) if isinstance(value, (list, tuple)) else {value}
                            newval = frozenset(_parse_set_type(
                                f,
                                _type,
                                set_value,
                                _encoder,
                                f.args,
                                obj
                            ))
                        else:
                            newval = frozenset()
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing FrozenSet {name}: ", ex))
                        continue
                elif f.origin is tuple:
                    try:
                        newval = _parse_tuple_type(f, _type, value, _encoder, f.args)
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing Tuple {name}: ", ex))
                        continue
                # If the field is a Union and data is a list, use _parse_union_type.
                elif f.origin is Union:
                    try:
                        if len(f.args) == 2 and type(None) in f.args:
                            # e.g. Optional[...] or Union[A, B]
                            if value is None:
                                newval = None
                            elif f._inner_priv:
                                # If Optional but non-None is a primitive
                                newval = _parse_builtin_type(f, f._inner_type, value, _encoder)
                            elif f._inner_is_dc:
                                # non-None is a Optional Dataclass Optional[dataclass]
                                newval = _handle_dataclass_type(
                                    None, name, value, f._inner_type, as_objects, None
                                )
                            elif f._inner_origin is list:
                                if f._inner_type.__module__ == 'typing':
                                    newval = _parse_list_typing(
                                        f,
                                        f._typing_args,
                                        value,
                                        _encoder,
                                        f._inner_origin,
                                        f._typing_args,
                                        obj
                                    )
                                else:
                                    newval = _parse_list_type(
                                        f,
                                        f._inner_type,
                                        value,
                                        _encoder,
                                        f._inner_targs,
                                        obj
                                    )
                            elif f._inner_origin is dict and not isinstance(value, dict) and value is not None:
                                newval = _parse_dict_type(f, f._inner_type, value, _encoder, f.args)
                            else:
                                try:
                                    newval = _parse_typing(f, f._inner_type, value, _encoder, as_objects, obj)
                                except ValueError:
                                    raise
                                except Exception as e:
                                    raise ValueError(
                                        f"Error parsing Optional: {name}: {e}"
                                    )
                        else:
                            newval = _parse_typing(
                                f,
                                _type,
                                value,
                                _encoder,
                                as_objects,
                                obj
                            )
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing Union {name}: ", ex))
                        continue
                else:
                    try:
                        newval = _parse_typing(
                            f,
                            _type,
                            value,
                            _encoder,
                            as_objects,
                            obj
                        )
                        obj.__dict__[name] = newval
                    except ValueError:
                        raise
                    except Exception as ex:
                        errors.update(_build_error(name, f"Error parsing Typing: ", ex))
                        continue
            elif isinstance(value, list) and type_args:
                if as_objects is True:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, obj)
                else:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, None)
                obj.__dict__[name] = newval
            elif field_category == 'set':
                try:
                    newval = _parse_set_type(
                        f,
                        _type,
                        value,
                        _encoder,
                        type_args,
                        obj
                    )
                    obj.__dict__[name] = newval
                except ValueError:
                    raise
                except Exception as ex:
                    errors.update(_build_error(name, f"Error parsing Set: ", ex))
                    continue
            else:
                # fallback to builtin parse
                try:
                    newval = _parse_typing(
                        f,
                        _type,
                        value,
                        _encoder,
                        as_objects,
                        obj
                    )
                    obj.__dict__[name] = newval
                except ValueError:
                    raise
                except Exception as ex:
                    errors.update(_build_error(name, f"Error parsing Typing: ", ex))
                    continue
            # then, call the validation process:
            if (error := _validation_(name, newval, f, _type, meta, field_category, as_objects)):
                errors[name] = error
        except (TypeError, ValueError) as ex:
            _case = ex.__class__.__name__
            if meta.strict is True:
                raise
            else:
                errors.update(_build_error(name, f"{_case}: at {f.name}: {f.type}", ex))
                continue
        except AttributeError:
            raise
        except Exception as ex:
            errors.update(_build_error(name, f"Wrong Type for {f.name}: {f.type}", ex))
            continue
    # Return Errors (if any)
    return errors

cdef object _validation_(
    str name,
    object value,
    object f,
    object _type,
    object meta,
    str field_category,
    bint as_objects = False
):
    """
    _validation_.
    TODO: cover validations as length, not_null, required, max, min, etc
    """
    cdef object val_type = type(value)
    cdef str error = None
    cdef dict err = {
        "field": name,
        "value": value,
        "error": None
    }

    if val_type == type or value == _type or is_empty(value):
        try:
            _field_checks_(f, name, value, meta)
            return None
        except (ValueError, TypeError):
            raise

    if isinstance(value, set):
        # Just validate that all elements match the expected type if specified
        if hasattr(f, '_inner_type') and f._inner_type is not None and not is_empty(value):
            inner_type = f._inner_type
            # For primitive types, we can use isinstance
            if inner_type in (str, int, float, bool):
                for item in value:
                    if not isinstance(item, inner_type):
                        err["error"] = f"Set item {item} is not of expected type {inner_type.__name__}"
                        return err
        return None

    # If the field has a cached validator, use it.
    if f.validator is not None:
        try:
            error = f.validator(f, name, value, _type)
            if error:
                err["error"] = error
                return err
            else:
                # calling validation_constraints:
                if _type in (str, int, float):
                    return _validate_constraints(f, name, value, _type, val_type)
            return None
        except ValueError:
            raise
    else:
        # capturing other errors from validator:
        return _validation(f, name, value, _type, val_type, field_category, as_objects)

cdef object _field_checks_(object f, str name, object value, object meta):
    # Validate Primary Key
    cdef object metadata = f.metadata
    try:
        if metadata.get('primary', False) is True:
            if 'db_default' in metadata:
                pass
            else:
                raise ValueError(
                    f":: Missing Primary Key *{name}*"
                )
    except KeyError:
        pass
    # Validate Required
    try:
        if metadata.get('required', False) is True and meta.strict is True:
            if 'db_default' in metadata:
                return
            if value is not None:
                return  # If default value is set, no need to raise an error
            raise ValueError(
                f":: Missing Required Field *{name}*"
            )
    except ValueError:
        raise
    except KeyError:
        return
    # Nullable:
    try:
        if metadata.get('nullable', True) is False and meta.strict is True:
            raise ValueError(
                f":: *{name}* Cannot be null."
            )
    except ValueError:
        raise
    except KeyError:
        return
    return


cpdef parse_type(object field, object T, object data, object encoder = None):
    cdef object origin = get_origin(T)
    cdef tuple args = None
    cdef str type_name = getattr(T, '_name', None)
    cdef object type_args = getattr(T, '__args__', None)
    cdef dict typeinfo = getattr(T, '_typeinfo_', None)

    if isinstance(T, NewType):
        # change type if is a NewType object.
        T = T.__supertype__

    # Check if the data is already of the correct type
    if isinstance(data, T):
        return data

    if field._type_category == 'typing':
        args = type_args or ()
        if type_name == 'Dict' and isinstance(data, dict):
            if args:
                return {k: parse_type(field, type_args[1], v) for k, v in data.items()}

        elif type_name == 'List':
            if not isinstance(data, (list, tuple)):
                data = [data]
            arg_type = args[0]
            if arg_type.__module__ == 'typing': # nested typing
                try:
                    t = arg_type.__args__[0]
                    if is_dc(t):
                        result = []
                        for x in data:
                            if isinstance(x, dict):
                                result.append(t(**x))
                            elif isinstance(x, (list, tuple)):
                                result.append(t(*x))
                            else:
                                result.append(t())
                        return result
                    else:
                        return data
                except AttributeError:
                    return data # data -as is-
            elif is_dc(arg_type):
                if isinstance(data, list):
                    result = []
                    for d in data:
                        # is already a dataclass:
                        if is_dc(d):
                            result.append(d)
                        elif isinstance(d, list):
                            result.append(arg_type(*d))
                        elif isinstance(d, dict):
                            result.append(arg_type(**d))
                        else:
                            result.append(arg_type(d))
                return result
            else:
                result = []
                if is_iterable(data):
                    for item in data:
                        # escalar value:
                        converted_item = parse_type(field, arg_type, item, encoder)
                        result.append(converted_item)
                    return result
                return data
        elif type_name is None or type_name in ('Optional', 'Union'):
            args = get_args(T)
            # Handling Optional types
            if origin == Union and type(None) in args:
                if data is None:
                    return None
                # Determine the non-None type.
                non_none_arg = args[0] if args[1] is type(None) else args[1]
                if non_none_arg == list:
                    field.args = args
                    field.origin = get_origin(non_none_arg)
                    if isinstance(data, (list, str, dict)):
                        return _parse_builtin_type(field, non_none_arg, data, encoder)
                    else:
                        raise ValueError(f"Unsupported type for List in Optional: {type(data)}")
                # If the non-None type is exactly dict, return the dict as is.
                if non_none_arg is dict:
                    return data
                # Otherwise, recursively parse using the non-None type.
                field.args = args
                field.origin = get_origin(non_none_arg)
                return parse_type(field, non_none_arg, data, encoder)
            try:
                t = args[0]
                if is_dc(t):
                    if isinstance(data, dict):
                        data = t(**data)
                    elif isinstance(data, (list, tuple)):
                        data = t(*data)
                    else:
                        ## is already a dataclass, returning
                        return data
                elif callable(t):
                    if t.__module__ == 'typing': # nested typing
                        # there is also a nested typing:
                        if t._name == 'List' and isinstance(data, list):
                            arg = t.__args__[0]
                            if is_dc(arg):
                                result = []
                                for x in data:
                                    if isinstance(x, dict):
                                        result.append(arg(**x))
                                    else:
                                        result.append(arg(*x))
                                return result
                        return data
                    else:
                        try:
                            if t == str:
                                return data
                            fn = encoders[t]
                            try:
                                if data is not None:
                                    data = fn(data)
                            except TypeError as ex:
                                pass
                            except (ValueError, RuntimeError) as exc:
                                raise ValueError(
                                    f"Model: Error parsing {T}, {exc}"
                                )
                        except KeyError:
                            pass
                return data
            except KeyError:
                pass
    elif origin is dict and isinstance(data, dict):
        return _parse_dict_type(field, T, data, encoder, args)
    elif origin is list:
        return _parse_list_type(field, T, data, encoder, args)
    elif origin is not None:
        # Other typing constructs can be handled here
        return data
    else:
        return _parse_builtin_type(field, T, data, encoder)
