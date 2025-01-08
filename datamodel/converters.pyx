# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
import re
from typing import get_args, get_origin, Union, Optional, List
from dataclasses import _MISSING_TYPE, _FIELDS, fields
import ciso8601
import orjson
from decimal import Decimal
from cpython cimport datetime
import pendulum
from pendulum.parsing.exceptions import ParserError
from uuid import UUID
import asyncpg.pgproto.pgproto as pgproto
from cpython.ref cimport PyObject
from .functions import is_empty, is_dataclass, is_iterable, is_primitive
from .validation import _validation


# Maps a type to a conversion callable
cdef dict TYPE_CONVERTERS = {}


cpdef object register_converter(object _type, object converter_func):
    """register_converter.

    Register a new converter function for a given type.
    """
    TYPE_CONVERTERS[_type] = converter_func


cdef str to_string(object obj):
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

cdef object to_uuid(object obj):
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
            return obj()
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
    if isinstance(obj, datetime.date):
        return obj
    elif isinstance(obj, str):
        try:
            return ciso8601.parse_datetime(obj).date()
        except ValueError:
            pass
    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")
    try:
        return datetime.datetime.fromisoformat(obj).date()
    except ValueError:
        pass
    try:
        return pendulum.parse(obj, strict=False).date()
    except (ValueError, TypeError, ParserError):
        raise ValueError(
            f"Can't convert invalid data *{obj}* to date"
        )

cpdef datetime.datetime to_datetime(object obj):
    """to_datetime.

    Returns obj converted to datetime.
    """
    if obj is None:
        return None
    if isinstance(obj, datetime.datetime):
        return obj
    elif obj == _MISSING_TYPE:
        return None
    elif isinstance(obj, str):
        try:
            return ciso8601.parse_datetime(obj)
        except ValueError:
            pass
    if isinstance(obj, (bytes, bytearray)):
        obj = obj.decode("ascii")
    try:
        return datetime.datetime.fromisoformat(obj)
    except ValueError:
        pass
    try:
        return pendulum.parse(obj, strict=False)
    except (ValueError, TypeError, ParserError):
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
        except (TypeError, ValueError):
            return None

TIMEDELTA_RE = re.compile(r"(-)?(\d{1,3}):(\d{1,2}):(\d{1,2})(?:.(\d{1,6}))?")

cpdef int _convert_second_fraction(s):
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


cdef object strtobool(str val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
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
        return False
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

cdef dict encoders = {
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

cdef object _parse_dict_type(object T, object data, object encoder, object args):
    cdef object val_type = args[1]
    cdef dict new_dict = {}
    for k, v in data.items():
        new_dict[k] = parse_typing(val_type, v, encoder)
    return new_dict

cdef object _parse_list_type(object T, object data, object encoder, object args):
    cdef object arg_type = args[0]
    cdef list result = []

    if data is None:
        return []   # short-circuit

    if not isinstance(data, (list, tuple)):
        data = [data]
        # raise ValueError(f"Expected list for {T} but got {type(data).__name__}")

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
            result.append(parse_typing(arg_type, item, encoder))
        return result

cdef object _parse_dataclass_type(object T, object data):
    if isinstance(data, dict):
        return T(**data)
    elif isinstance(data, (list, tuple)):
        return T(*data)
    else:
        return T(data)

cdef object _parse_builtin_type(object T, object data, object encoder):
    if encoder is not None:
        try:
            return encoder(data)
        except ValueError as e:
            raise ValueError(f"Error parsing type {T}, {e}")
    elif is_dataclass(T):
        return _parse_dataclass_type(T, data)
    else:
        # Try encoders dict:
        try:
            conv = encoders[T]
            return conv(data)
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
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error type {T}: {e}") from e

cpdef parse_type(object T, object data, object encoder = None, str field_type = None):
    cdef object origin = get_origin(T)
    cdef tuple args = None
    cdef str type_name = getattr(T, '_name', None)
    cdef object type_args = getattr(T, '__args__', None)

    if field_type == 'typing':
        args = None
        try:
            args = type_args
        except AttributeError:
            pass
        if type_name == 'Dict' and isinstance(data, dict):
            if args:
                return {k: parse_type(type_args[1], v) for k, v in data.items()}
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
                        converted_item = parse_type(arg_type, item, encoder)
                        result.append(converted_item)
                    return result
                return data
        elif type_name is None or type_name in ('Optional', 'Union'):
            # origin = get_origin(T)
            args = get_args(T)
            # Handling Optional types
            if origin == Union and type(None) in args:
                if data is None:
                    return None
                else:
                    non_none_arg = args[0] if args[1] is type(None) else args[1]
                    return parse_type(non_none_arg, data, encoder)
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
        return _parse_dict_type(T, data, encoder, args)
    elif origin is list:
        return _parse_list_type(T, data, encoder, args)
    elif origin is not None:
        # Other typing constructs can be handled here
        return data
    else:
        return _parse_builtin_type(T, data, encoder)

cdef bint is_callable(object value) nogil:
    """
    Check if `value` is callable by calling Python's callable(...)
    but reacquire the GIL inside.
    """
    with gil:
        return callable(value)

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
    # Using the encoders for basic types:
    try:
        return encoders[T](data)
    except KeyError:
        pass
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Encoder Error {T}: {e}"
        ) from e

    # function encoder:
    if encoder and is_callable(encoder):
        # using a function encoder:
        try:
            return encoder(data)
        except ValueError as e:
            raise ValueError(
                f"Error parsing type {T}, {e}"
            )

cdef object _parse_typing_type(
    object T,
    object name,
    object data,
    object encoder,
    object origin,
    object args,
    object as_objects=False,
):
    """
    Handle field_type='typing' scenario.
    """
    cdef tuple type_args = getattr(T, '__args__', ())

    if name == 'Dict' and isinstance(data, dict):
        if type_args:
            # e.g. Dict[K, V]
            return {k: parse_typing(type_args[1], v) for k, v in data.items()}
        return data

    if name == 'List':
        if not isinstance(data, (list, tuple)):
            data = [data]
        return _parse_list_typing(type_args, data, encoder, origin, args)

    # handle None, Optional, Union, etc.
    if name is None or name in ('Optional', 'Union'):
        return _parse_optional_union(T, data, encoder, origin, args)

    return data

cdef object _parse_list_typing(
    tuple type_args,
    object data,
    object encoder,
    object origin,
    object args,
    object as_objects=False
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
            result.append(parse_typing(arg_type, item, encoder))
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

cdef object _parse_optional_union(object T, object data, object encoder, object origin, object args):
    """
    handle Optional or Union logic
    """
    cdef object non_none_arg
    cdef object t = args[0] if args else None

    # e.g. Optional[T] is Union[T, NoneType]
    if origin == Union and type(None) in args:
        if data is None:
            return None
        non_none_arg = args[0] if args[1] is type(None) else args[1]
        return parse_typing(non_none_arg, data, encoder)
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
    object T,
    object name,
    object data,
    object encoder,
    object origin,
    object targs,
    str field_type=None
):
    """
    Attempt each type in the Union until one parses successfully
    or raise an error if all fail.
    """
    cdef object errors = []
    for arg_type in targs:
        try:
            if isinstance(data, list):
                result = _parse_list_type(arg_type, data, encoder, targs)
            else:
                # fallback to builtin parse
                result = parse_typing(arg_type, data, encoder, field_type=field_type)
            return result
        except Exception as exc:
            errors.append(str(exc))

    # If we get here, all union attempts failed
    raise ValueError(f"Union parse failed for data={data}, errors={errors}")


cpdef object parse_typing(
    object T,
    object data,
    object encoder=None,
    str field_type=None,
    object typing_args=None,
    object as_objects = False,
):
    """
    Parse a value to a typing type.
    """
    # local cdef variables:
    cdef object origin = None
    cdef object args = None
    cdef object name = getattr(T, '_name', None)  # T._name or None if not present
    cdef object sub = None     # for subtypes, local cache
    cdef object result = None

    if typing_args:
        origin, targs = typing_args.get(name, (get_origin(T), get_args(T)))
    else:
        origin = get_origin(T)
        targs = get_args(T)

    if data is None:
        return None

    if origin is Union and isinstance(data, list):
        return _parse_union_type(T, name, data, encoder, origin, targs, field_type)

    if is_dataclass(T):
        result = _handle_dataclass_type(name, data, T, as_objects)
    # Field type shortcuts
    elif field_type == 'typing':
        result = _parse_typing_type(T, name, data, encoder, origin, targs, as_objects)
    elif origin is dict and isinstance(data, dict):
        result = _parse_dict_type(T, data, encoder, targs)
    elif origin is list:
        result = _parse_list_type(T, data, encoder, targs)
    elif origin is not None:
        # other advanced generics
        result = data
    else:
        # fallback to builtin parse
        result = _parse_builtin_type(T, data, encoder)
    return result

cdef object _handle_dataclass_type(
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
    cdef bint is_dc = is_dataclass(_type)

    try:
        if value is None or is_dataclass(value):
            return value
        if isinstance(value, dict):
            return _type(**value)
        if isinstance(value, (list, tuple)):
            return _type(*value)
        else:
            # If a converter exists for this type, use it:
            if converter:
                return converter(name, value, _type, parent)
            if as_objects is True:
                return _type(**{name: value})
            if isinstance(value, (int, str, UUID)):
                return value
            if is_dc:
                return _type(**{name: value})
            else:
                return _type(value)
    except Exception as exc:
        raise ValueError(
            f"Invalid value for {_type}: {value}, error: {exc}"
        )

cdef object _handle_list_of_dataclasses(
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

cdef object _handle_default_value(object obj, str name, object value, object default_func):
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
    if is_callable(default_func) and value is None:
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
    """process_attributes.

    Process the attributes of a dataclass object.
    """
    cdef object new_val
    cdef object _encoder = None
    cdef object _default = None
    cdef object _type = None
    cdef object meta = obj.Meta
    cdef bint as_objects = meta.as_objects
    cdef bint no_nesting = meta.no_nesting
    cdef dict field_types = obj.__field_types__
    cdef dict typing_args = obj.__typing_args__
    cdef bint is_dc = False
    cdef dict errors = {}

    for name, f in columns:
        try:
            value = getattr(obj, name)
            metadata = f.metadata
            _type = f.type
            _encoder = metadata.get('encoder')
            _default = f.default

            # Check if object is empty
            if is_empty(value) and not isinstance(value, list):
                value = f.default_factory if isinstance(
                _default, (_MISSING_TYPE)) else _default
                setattr(obj, name, value)
            if _default is not None:
                value = _handle_default_value(obj, name, value, _default)
            # Use the precomputed field type category:
            field_category = field_types.get(name, 'complex')
            try:
                if field_category == 'primitive':
                    if isinstance(value, str) and _type == str:
                        continue  # short-circuit
                    if isinstance(value, int) and _type == int:
                        continue  # short-circuit
                    value = parse_basic(_type, value, _encoder)
                elif field_category == 'dataclass':
                    if no_nesting is False:
                        if as_objects is True:
                            value = _handle_dataclass_type(name, value, _type, as_objects, obj)
                        else:
                            value = _handle_dataclass_type(name, value, _type, as_objects, None)
                elif field_category == 'typing':
                    value = parse_typing(_type, value, _encoder, field_category, typing_args, as_objects)
                elif isinstance(value, list) and hasattr(_type, '__args__'):
                    if as_objects is True:
                        value = _handle_list_of_dataclasses(name, value, _type, obj)
                    else:
                        value = _handle_list_of_dataclasses(name, value, _type, None)
                else:
                    value = parse_typing(_type, value, _encoder, field_category, typing_args, as_objects)
                setattr(obj, name, value)
                # then, call the validation process:
                if (error := _validation_(name, value, f, _type, meta, field_category)):
                    errors[name] = error
            except (TypeError, ValueError, RuntimeError) as ex:
                errors[name] = f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                continue
        except (TypeError, ValueError, RuntimeError) as e:
            errors[name] = f"Error processing {name}: {e}"
            continue
    return errors


cdef list _validation_(
    str name,
    object value,
    object f,
    object _type,
    object meta,
    str field_category
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
        return _validation(f, name, value, _type, val_type, field_category)

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
    except KeyError:
        return
    # Nullable:
    try:
        if metadata.get('nullable', True) is False and meta.strict is True:
            raise ValueError(
                f":: *{name}* Cannot be null."
            )
    except KeyError:
        return
    return
