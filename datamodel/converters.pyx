# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
import re
from typing import get_args, get_origin, Union, Optional, List, NewType
from collections.abc import Sequence, Mapping, Callable, Awaitable
from dataclasses import _MISSING_TYPE, _FIELDS, fields
import ciso8601
import orjson
from decimal import Decimal, InvalidOperation
from cpython cimport datetime
from uuid import UUID
import asyncpg.pgproto.pgproto as pgproto
from cpython.ref cimport PyObject
from .functions import is_empty, is_dataclass, is_iterable, is_primitive
from .validation import _validation
from .fields import Field
# New converter:
import rs_parsers as rc


# Maps a type to a conversion callable
cdef dict TYPE_CONVERTERS = {}


cpdef object register_converter(object _type, object converter_func):
    """register_converter.

    Register a new converter function for a given type.
    """
    TYPE_CONVERTERS[_type] = converter_func


cpdef str to_string(object obj):
    """
    Returns a string version of an object.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, bytes):
        return obj.decode()
    elif callable(obj):
        # its a function callable returning a value
        try:
            return str(obj())
        except:
            pass
    return str(obj)

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

cpdef datetime.timedelta to_timedelta(object obj):
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
    dict: to_object,
    list: to_object,
    tuple: to_object
}

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
        new_dict[k] = parse_typing(field, val_type, v, encoder, False)
    return new_dict

cdef object _parse_list_type(
    object field,
    object T,
    object data,
    object encoder,
    object args
):
    cdef object arg_type = args[0]
    cdef list result = []

    if data is None:
        return []   # short-circuit

    if not isinstance(data, (list, tuple)):
        data = [data]

    # If it's a dataclass
    if is_dataclass(arg_type):
        for d in data:
            if is_dataclass(d):
                result.append(d)
            elif isinstance(d, dict):
                result.append(arg_type(**d))
            elif isinstance(d, (list, tuple)):
                result.append(arg_type(*d))
            else:
                result.append(arg_type(d))
        return result
    else:
        # General conversion
        for item in data:
            result.append(
                parse_typing(field, arg_type, item, encoder, False)
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
    elif T == str:
        return to_string(data)
    elif T == UUID:
        return to_uuid(data)
    elif is_dataclass(T):
        return _parse_dataclass_type(T, data)
    elif T == datetime.date:
        return to_date(data)
    elif T == datetime.datetime:
        return to_datetime(data)
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

    # print('FIELD > ', field)
    # print('T > ', T)
    # print('NAME > ', name)
    # print('DATA > ', data)
    # print('TYPE > ', type_args)

    if field.origin in {dict, Mapping} or name in {'Dict', 'Mapping'}:
        if isinstance(data, dict):
            if type_args:
                # e.g. Dict[K, V]
                return {k: _parse_type(field, type_args[1], v, None, False) for k, v in data.items()}
            return data

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

    # handle None, Optional, Union, etc.
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
            if is_dataclass(subT):
                for x in data:
                    result.append(_instantiate_dataclass(subT, x))
                return result
            else:
                # fallback
                return data
        except AttributeError:
            return data
    elif arg_type is not None and is_dataclass(arg_type):
        # build list of dataclasses
        for d in data:
            result.append(_instantiate_dataclass(arg_type, d))
        return result
    else:
        # parse each item
        for item in data:
            result.append(_parse_type(field, arg_type, item, encoder, False))
        return result

cdef object _instantiate_dataclass(object cls, object val):
    """
    Helper for instantiating a dataclass.
    """
    if is_dataclass(val):
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
    handle Optional or Union logic
    """
    cdef object non_none_arg
    cdef object t = args[0] if args else None
    cdef bint matched = False

    # e.g. Optional[T] is Union[T, NoneType]
    if origin == Union and type(None) in args:
        if data is None:
            return None
        non_none_arg = args[0] if args[1] is type(None) else args[1]
        return _parse_type(
            field,
            T=non_none_arg,
            data=data,
            encoder=encoder,
            as_objects=False
        )
    args = tuple(t for t in args if t is not type(None))
    for t in args:
        # let's validate all types on Union to be matched with Type of data
        if isinstance(data, t):
            matched = True
            break
    if not matched:
        raise ValueError(f"Invalid type for *{field.name}* with {type(data)}, expected {T}")
    try:
        if is_dataclass(t):
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
    cdef object errors = []
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
                return parse_typing(
                    field,
                    non_none_arg,
                    data,
                    encoder,
                    False
                )
        else:
            pass
    for arg_type in targs:
        try:
            if isinstance(data, list):
                result = _parse_list_type(field, arg_type, data, encoder, targs)
            else:
                # fallback to builtin parse
                result = parse_typing(
                    field,
                    arg_type,
                    data,
                    encoder,
                    False
                )
            return result
        except Exception as exc:
            errors.append(str(exc))

    # If we get here, all union attempts failed
    raise ValueError(f"Union parse failed for data={data}, errors={errors}")

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
    cdef object is_dc = is_dataclass(T)

    if data is None:
        return None

    if is_dataclass(T):
        result = _handle_dataclass_type(None, name, data, T, as_objects, None)
    # Field type shortcuts
    elif origin is dict and isinstance(data, dict):
        result = _parse_dict_type(field, T, data, encoder, targs)
    elif origin is list:
        result = _parse_list_type(field, T, data, encoder, targs)
    elif origin is not None:
        # other advanced generics
        result = data
    else:
        # fallback to builtin parse
        result = _parse_builtin_type(field, T, data, encoder)
    return result

cpdef object parse_typing(
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
    cdef object origin = field.origin
    cdef object targs = field.args
    cdef object name = getattr(T, '_name', None)  # T._name or None if not present
    cdef object sub = None     # for subtypes, local cache
    cdef object result = None
    cdef object is_dc = field.is_dc # is_dataclass(T)

    if not origin:
        origin = get_origin(T)
        targs = get_args(T)

    if data is None:
        return None

    if origin is Union and isinstance(data, list):
        return _parse_union_type(
            field,
            T,
            name,
            data,
            encoder,
            origin,
            targs
        )

    if is_dataclass(T):
        result = _handle_dataclass_type(None, name, data, T, as_objects, None)
    # Field type shortcuts
    elif field._type_category == 'typing':
        result = _parse_typing_type(
            field, T, name, data, encoder, origin, targs, as_objects
        )
    elif origin is dict and isinstance(data, dict):
        result = _parse_dict_type(field, T, data, encoder, targs)
    elif origin is list:
        result = _parse_list_type(field, T, data, encoder, targs)
    elif origin is not None:
        # other advanced generics
        result = data
    else:
        # fallback to builtin parse
        result = _parse_builtin_type(field, T, data, encoder)
    return result

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
    cdef object converter = TYPE_CONVERTERS.get(key) or TYPE_CONVERTERS.get(_type)
    cdef bint is_dc = field.is_dc if field else is_dataclass(_type)
    cdef object field_metadata = field.metadata if field else {}
    cdef str alias = field_metadata.get('alias')

    try:
        if value is None or is_dataclass(value):
            return value
        if isinstance(value, dict):
            try:
                return _type(**value)
            except TypeError:
                # Ensure keys are strings
                value = {str(k): v for k, v in value.items()}
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
        if isinstance(value, (list, tuple)):
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
            if isinstance(value, (int, str, UUID)):
                return value
            if is_dc:
                if not alias:
                    alias = name
                return _type(**{alias: value})
            else:
                return _type(value)
    except Exception as exc:
        raise ValueError(
            f"Invalid value for {_type}: {value}, error: {exc}"
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
        if is_dataclass(sub_type):
            key = (sub_type, name)
            converter = TYPE_CONVERTERS.get(key) or TYPE_CONVERTERS.get(_type)
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
    if is_callable(value):
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

cpdef dict process_attributes(object obj, list columns):
    """
    Process the attributes of a dataclass object.

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
    cdef bint is_dc = False
    cdef dict errors = {}
    cdef dict _typeinfo = {}

    for name, f in columns:
        try:
            value = getattr(obj, name)
            # Use the precomputed field type category:
            field_category = f._type_category

            if field_category == 'descriptor':
                # Handle descriptor-specific logic
                try:
                    value = f.__get__(obj, type(obj))  # Get the descriptor value
                    setattr(obj, name, value)
                except Exception as e:
                    errors[name] = f"Descriptor error in {name}: {e}"
                continue

            metadata = getattr(f, "metadata", {})
            _type = f.type
            _encoder = metadata.get('encoder')
            _default = f.default
            typeinfo = f.typeinfo # cached info (e.g., type_args, default_callable)
            is_dc = f.is_dc
            _default_callable = typeinfo.get('default_callable', False)

            if isinstance(_type, NewType):
                # change type if is a NewType object.
                _type = _type.__supertype__

            # Check if object is empty
            if is_empty(value) and not isinstance(value, list):
                if _type == str and value is not "":
                    value = f.default_factory if isinstance(_default, (_MISSING_TYPE)) else _default
                setattr(obj, name, value)
            if _default is not None:
                value = _handle_default_value(obj, name, value, _default, _default_callable)

            if f.parser is not None:
                # If a custom parser is attached, use it
                try:
                    new_val = f.parser(value)
                    setattr(obj, name, new_val)
                except Exception as ex:
                    errors[name] = f"Error parsing *{name}* = *{value}*, error: {ex}"
                    continue
            try:
                if field_category == 'primitive':
                    if (isinstance(value, str) and _type == str) or (isinstance(value, int) and _type == int):
                        # No conversion needed. The value remains as-is.
                        pass
                    else:
                        try:
                            value = parse_basic(_type, value, _encoder)
                        except ValueError as ex:
                            errors[name] = f"Error parsing {name}: {ex}"
                            continue
                elif field_category == 'type':
                    pass
                elif field_category == 'typing':
                    value = parse_typing(
                        f,
                        _type,
                        value,
                        _encoder,
                        as_objects
                    )
                elif field_category == 'dataclass':
                    if no_nesting is False:
                        if as_objects is True:
                            value = _handle_dataclass_type(f, name, value, _type, as_objects, obj)
                        else:
                            value = _handle_dataclass_type(f, name, value, _type, as_objects, None)
                elif isinstance(value, list) and typeinfo.get('type_args'):
                    if as_objects is True:
                        value = _handle_list_of_dataclasses(f, name, value, _type, obj)
                    else:
                        value = _handle_list_of_dataclasses(f, name, value, _type, None)
                else:
                    value = parse_typing(
                        f,
                        _type,
                        value,
                        _encoder,
                        as_objects
                    )
                setattr(obj, name, value)
                # then, call the validation process:
                if (error := _validation_(name, value, f, _type, meta, field_category, as_objects)):
                    errors[name] = error
            except ValueError as ex:
                if meta.strict is True:
                    raise
                else:
                    errors[name] = f"Wrong Value for {f.name}: {f.type}, error: {ex}"
                    continue
            except (TypeError, RuntimeError) as ex:
                errors[name] = f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                continue
        except ValueError as e:
            if meta.strict is True:
                raise
        except (TypeError, RuntimeError) as e:
            errors[name] = f"Error processing {name}: {e}"
            continue
    return errors


cdef list _validation_(
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
    val_type = type(value)
    if val_type == type or value == _type or is_empty(value):
        try:
            _field_checks_(f, name, value, meta)
            return []
        except (ValueError, TypeError):
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
                    if is_dataclass(t):
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
            elif is_dataclass(arg_type):
                if isinstance(data, list):
                    result = []
                    for d in data:
                        # is already a dataclass:
                        if is_dataclass(d):
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
                if is_dataclass(t):
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
                            if is_dataclass(arg):
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
