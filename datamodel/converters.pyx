# cython: language_level=3, embedsignature=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
import re
from typing import get_args, get_origin, Union, Optional, List, NewType, Literal
from collections.abc import Sequence, Mapping, Callable, Awaitable
import types
from dataclasses import _MISSING_TYPE, _FIELDS, fields
import ciso8601
import orjson
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

cdef bint is_empty(object value):
    cdef bint result = False
    if value is None:
        return True
    if PyObject_IsInstance(value, _MISSING_TYPE) or value == _MISSING_TYPE:
        result = True
    elif PyObject_IsInstance(value, str) and value == '':
        result = True
    elif PyObject_IsInstance(value, (int, float)) and value == 0:
        result = False
    elif PyObject_IsInstance(value, dict) and value == {}:
        result = False
    elif PyObject_IsInstance(value, (list, tuple, set)) and value == []:
        result = False
    elif PyObject_HasAttr(value, 'empty') and PyObject_GetAttr(value, 'empty') == False:
        result = False
    elif not value:
        result = True
    return result

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
        return rc.to_datetime(obj)
    except ValueError:
        pass
    try:
        return ciso8601.parse_datetime(obj)
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
    # dict: to_object,
    # list: to_object,
    # tuple: to_object,
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

cdef object _parse_dict_type(
    object field,
    object T,
    object data,
    object encoder,
    object args
):
    cdef object val_type = args[1]
    cdef dict new_dict = {}
    for k, v in data.items():
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
    cdef object converter = TYPE_PARSERS.get(key) or TYPE_PARSERS.get(arg_type)
    cdef object inner_type = field._inner_type or arg_type

    if data is None:
        return []   # short-circuit

    if not isinstance(data, (list, tuple)):
        data = [data]

    # If it's a dataclass
    if is_dc(inner_type):
        for d in data:
            if is_dc(d):
                result.append(d)
            if converter:
                result.append(
                    converter(field.name, d, inner_type, _parent)
                )
            else:
                if isinstance(d, dict):
                    result.append(inner_type(**d))
                elif isinstance(d, (list, tuple)):
                    result.append(inner_type(*d))
                else:
                    result.append(inner_type(d))
        return result
    elif converter:
        for item in data:
            result.append(
                converter(field.name, item, inner_type, _parent)
            )
    elif is_primitive(inner_type):
        try:
            result = rc.to_list(inner_type, data)
            # return data
        except Exception as e:
            raise ValueError(
                f"Error parsing list of {inner_type}: {e}"
            ) from e
    else:
        for item in data:
            result.append(
                _parse_typing(field, T=inner_type, data=item, encoder=encoder, as_objects=False)
            )
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
    if T == datetime.date:
        return to_date(data)
    if T == datetime.datetime:
        return to_datetime(data)
    if T == UUID:
        return to_uuid(data)
    elif is_dc(T):
        return _parse_dataclass_type(T, data)
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

    if name == 'Tuple' or field.origin == tuple:
        if isinstance(data, (list, tuple)):
            if len(data) == len(type_args):
                return tuple(
                    _parse_type(field, typ, datum, encoder, False)
                    for typ, datum in zip(type_args, data)
                )
            else:
                if len(type_args) == 2 and type_args[1] is Ellipsis:
                    # e.g. Tuple[str, ...]
                    return tuple(
                        _parse_type(field, type_args[0], datum, None, False)
                        for datum in data
                    )
        return tuple(data)

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
    else:
        # parse each item
        for item in data:
            result.append(
                _parse_type(field, arg_type, item, encoder, False)
            )
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

    for t in args:
        if PyObject_IsInstance(data, t):
            return data

    # e.g. Optional[T] is Union[T, NoneType]
    if origin == Union and type(None) in args:
        if data is None:
            return None
        # Pick the non-None type (assumes only two types in the Union)
        non_none_arg = args[0] if args[1] is type(None) else args[1]
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
        else:
            pass
    for arg_type in targs:
        # Iterate over all subtypes of Union:
        subtype_origin = get_origin(arg_type)
        try:
            if subtype_origin is list or subtype_origin is tuple:
                if isinstance(data, list):
                    return _parse_list_type(field, arg_type, data, encoder, targs)
                else:
                    error = f"Invalid type for {field_name}: Expected a list, got {type(data).__name__}"
                    continue
            elif subtype_origin is dict:
                if isinstance(data, dict):
                    return _parse_dict_type(field, arg_type, data, encoder, targs)
                else:
                    error = f"Invalid type for {field_name} Expected a dict, got {type(data).__name__}"
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
                    error = f"Invalid type for {field_name}: Expected a list, got {type(data).__name__}"
                    continue
            elif arg_type is dict:
                if isinstance(data, dict):
                    return _parse_dict_type(field, arg_type, data, encoder, targs)
                else:
                    error = f"Invalid type for {field_name} Expected a dict, got {type(data).__name__}"
                    continue
            elif subtype_origin is None:
                if isinstance(data, arg_type):
                    return data
                else:
                    # Not matching => record an error
                    error = f"Invalid type for {field_name}, Data {data!r} is not an instance of {arg_type}"
                    continue
            else:
                # fallback to builtin parse
                return _parse_typing(
                    field,
                    arg_type,
                    data,
                    encoder,
                    False
                )
        except ValueError as exc:
            error = f"{field.name}: {exc}"
        except Exception as exc:
            error = f"Parse Error on {field.name}, {arg_type}: {exc}"

    # If we get here, all union attempts failed
    raise ValueError(
        f"Invalid type for {field.name} with data={data}, error = {error}"
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
    elif origin is not None:
        # other advanced generics
        return data
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
    if origin is list and targs:
        if field._inner_type is not None:
            inner_type = field._inner_type
            inner_origin = field._inner_origin
            # Optionally, also use cached type arguments for the inner type.
        else:
            inner_type = targs[0]
            inner_origin = get_origin(inner_type)
    else:
        inner_type = None
        inner_origin = None

    inner_is_dc = field._inner_is_dc or is_dc(inner_type)

    if data is None:
        return None

    # Put more frequently cases first:
    if field.is_dc:
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
        elif isinstance(data, list):
            return _parse_union_type(
                field,
                T,
                name,
                data,
                encoder,
                origin,
                targs
            )
        else:
            return _parse_union_type(
                field,
                T,
                name,
                data,
                encoder,
                origin,
                targs
            )
    # Field type shortcuts
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
        else:
            return _parse_typing_type(
                field, T, name, data, encoder, origin, targs, as_objects
            )
    if origin is dict and isinstance(data, dict):
        return _parse_dict_type(field, T, data, encoder, targs)
    if origin is list:
        return _parse_list_type(field, T, data, encoder, targs, parent)
    if origin is not None:
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
    except AttributeError:
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
                    errors.update(_build_error(name, f"Error parsing *{name}* = *{value}*", ex))
                    continue
            elif field_category == 'primitive':
                try:
                    newval = parse_basic(_type, value, _encoder)
                    if newval != value:
                        obj.__dict__[name] = newval
                except ValueError as ex:
                    errors.update(_build_error(name, f"Error parsing {name}: ", ex))
                    continue
            elif field_category == 'type':
                # TODO: support multiple types
                pass
            elif field_category == 'dataclass':
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
            elif f.origin in (list, 'list') and f._inner_is_dc:
                if as_objects is True:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, obj)
                else:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, None)
                obj.__dict__[name] = newval
            elif field_category == 'typing':
                if f.is_dc:
                    # means that is_dataclass(T)
                    newval = _handle_dataclass_type(None, name, value, _type, as_objects, None)
                    obj.__dict__[name] = newval
                elif f.origin is Literal:
                    # e.g. Literal[...]
                    newval = _parse_literal_type(f, _type, value, _encoder)
                    obj.__dict__[name] = newval
                elif f.origin is list:
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
                # If the field is a Union and data is a list, use _parse_union_type.
                elif f.origin is Union:
                    # e.g. Optional[...] or Union[A, B]
                    if len(f.args) == 2 and type(None) in f.args:
                        # Handle Optional[...] that is Union[..., None] cases first:
                        if f._inner_priv:
                            # If Optional but non-None is a primitive
                            newval = _parse_builtin_type(f, f._inner_type, value, _encoder)
                        if f._inner_is_dc:
                            # non-None is a Optional Dataclass:
                            newval = _handle_dataclass_type(
                                None, name, value, f._inner_type, as_objects, None
                            )
                        obj.__dict__[name] = newval
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
                    except Exception as e:
                        raise ValueError(
                            f"Error parsing {f.origin}: {name}: {e}"
                        )
            elif isinstance(value, list) and type_args:
                if as_objects is True:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, obj)
                else:
                    newval = _handle_list_of_dataclasses(f, name, value, _type, None)
                obj.__dict__[name] = newval
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
            # then, call the validation process:
            if (error := _validation_(name, newval, f, _type, meta, field_category, as_objects)):
                errors[name] = error
        except ValueError as ex:
            if meta.strict is True:
                raise
            else:
                errors.update(_build_error(name, f"Wrong Value for {f.name}: {f.type}", ex))
                continue
        except AttributeError:
            raise
        except (TypeError, RuntimeError) as ex:
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
    # If the field has a cached validator, use it.
    if f.validator is not None:
        try:
            error = f.validator(f, name, value, _type)
            if error:
                err["error"] = error
                return err
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
