from typing import Any, Optional
import inspect
import logging
# Dataclass
from dataclasses import (
    _FIELD,
    dataclass,
    make_dataclass,
    _MISSING_TYPE
)
from enum import EnumMeta
from uuid import UUID
from orjson import OPT_INDENT_2
from .converters import parse_basic, parse_type, slugify_camelcase
from .fields import Field
from .types import JSON_TYPES, Text
from .validation import (
    _validation,
    is_callable,
    is_empty,
    is_dataclass,
    is_primitive
)
from .exceptions import ValidationError
from .parsers.encoders import json_encoder
from .abstract import ModelMeta, Meta
from .models import ModelMixin


def _get_type_info(_type, name, title):
    if _type.__module__ == 'typing':
        if inspect.isfunction(_type):
            if hasattr(_type, '__supertype__'):
                return _type.__supertype__
            raise ValueError(
                f"You're using bare Functions to type hint on {name} for: {title}"
            )
        if _type._name == 'List':
            return 'array'
        if _type._name == 'Dict':
            return 'object'
        try:
            return _type.__args__[0].__name__
        except (AttributeError, ValueError):
            return 'string'
    elif hasattr(_type, '__supertype__'):
        if type(_type) == type(Text):
            return 'text'
        if isinstance(_type.__supertype__, (str, int)):
            return 'string' if isinstance(_type.__supertype__, str) else 'integer'
    return JSON_TYPES.get(_type, 'string')


def _get_ref_info(_type, field):
    if isinstance(_type, EnumMeta):
        return {
            "type": "array",
            "enum_type": {
                "type": "string",
                "enum": list(map(lambda c: c.value, _type))
            }
        }
    elif isinstance(_type, ModelMeta):
        _schema = _type.schema(as_dict=True)
        columns = []
        if 'fk' not in field.metadata:
            ref = _schema.get('$id', f"/{_type.__name__}")
        else:
            columns = field.metadata.get('fk').split("|")
            _id, _value = columns
            ref = {
                "api": field.metadata.get('api', _schema['table']),
                "id": _id,
                "value": _value,
                "$ref": _schema.get('$id', f"/{_type.__name__}")
            }
        return {
            "type": "object",
            "schema": _schema,
            "$ref": ref,
            "columns": columns
        }
    elif 'api' in field.metadata:
        # reference information, no matter the type:
        try:
            columns = field.metadata.get('fk').split("|")
            _id, _value = columns
            _fields = {
                "id": _id,
                "value": _value,
            }
        except (TypeError, ValueError):
            _fields = {}
            columns = []
        ref = {
            "api": field.metadata.get('api'),
            **_fields
        }
        return {
            "type": "object",
            "$ref": ref,
            "columns": columns
        }
    return None


class BaseModel(ModelMixin, metaclass=ModelMeta):
    """
    BaseModel.
    Base Model for all DataModels.
    """
    Meta = Meta

    def __post_init__(self) -> None:
        """
        Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        errors = {}
        for name, f in self.__columns__.items():
            try:
                value = getattr(self, name)
                if (error := self._process_field_(name, value, f)):
                    errors[name] = error
            except RuntimeError as err:
                logging.exception(err)
        if errors:
            if self.Meta.strict is True:
                raise ValidationError(
                    f"""{self.modelName}: There are errors in Model. \
                        Hint: please check the "payload" attribute in the exception.""",
                    payload=errors
                )
            self.__errors__ = errors
            object.__setattr__(self, "__valid__", False)
        else:
            object.__setattr__(self, "__valid__", True)

    def _handle_default_value(self, value, f, name) -> Any:
        # Calculate default value
        if is_callable(value):
            if value.__module__ != 'typing':
                try:
                    new_val = value()
                except TypeError:
                    try:
                        new_val = f.default()
                    except TypeError:
                        new_val = None
                setattr(self, name, new_val)
        elif is_callable(f.default) and value is None:
            # Set the default value first
            try:
                new_val = f.default()
            except (AttributeError, RuntimeError):
                new_val = None
            setattr(self, name, new_val)
            value = new_val  # Return the new value
        elif not isinstance(f.default, _MISSING_TYPE) and value is None:
            setattr(self, name, f.default)
            value = f.default
        return value

    def _handle_dataclass_type(self, value, _type):
        try:
            if hasattr(self.Meta, 'no_nesting'):
                return value
            if value is None or is_dataclass(value):
                return value
            if isinstance(value, dict):
                return _type(**value)
            if isinstance(value, list):
                return _type(*value)
            return value if isinstance(value, (int, str, UUID)) else _type(value)
        except Exception as exc:
            raise ValueError(
                f"Invalid value for {_type}: {value}, error: {exc}"
            )

    def _handle_list_of_dataclasses(self, value, _type):
        try:
            sub_type = _type.__args__[0]
            if is_dataclass(sub_type):
                return [
                    sub_type(**item) if isinstance(item, dict) else item for item in value
                ]
        except AttributeError:
            pass
        return value

    def _process_field_(
        self,
        name: str, value: Any, f: Field
    ) -> Optional[dict[Any, Any]]:
        _type = f.type
        _encoder = f.metadata.get('encoder')
        new_val = value
        if is_empty(value):
            new_val = f.default_factory if isinstance(f.default, (_MISSING_TYPE)) else f.default
            setattr(self, name, new_val)

        if f.default is not None:
            value = self._handle_default_value(value, f, name)

        if is_primitive(_type):
            try:
                if value is not None:
                    new_val = parse_basic(f.type, value, _encoder)
                return self._validation_(name, new_val, f, _type)
            except (TypeError, ValueError) as ex:
                raise ValueError(
                    f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                ) from ex
        elif inspect.isclass(_type) and _type.__module__ == 'typing':
            new_val = parse_type(_type, value, _encoder)
            return self._validation_(name, new_val, f, _type)
        elif isinstance(value, list) and hasattr(_type, '__args__'):
            new_val = self._handle_list_of_dataclasses(value, _type)
            return self._validation_(name, new_val, f, _type)
        elif is_dataclass(_type):
            new_val = self._handle_dataclass_type(value, _type)
            return self._validation_(name, new_val, f, _type)
        else:
            try:
                new_val = parse_type(f.type, value, _encoder)
            except (TypeError, ValueError) as ex:
                raise ValueError(
                    f"Wrong Type for {f.name}: {f.type}, error: {ex}"
                ) from ex
            # Then validate the value
            return self._validation_(name, new_val, f, _type)

    def _field_checks_(self, f: Field, name: str, value: Any) -> None:
        # Validate Primary Key
        try:
            if f.metadata['primary'] is True:
                if 'db_default' in f.metadata:
                    pass
                else:
                    raise ValueError(
                        f"::{self.modelName}:: Missing Primary Key *{name}*"
                    )
        except KeyError:
            pass
        # Validate Required
        try:
            if f.metadata["required"] is True and self.Meta.strict is True:
                if 'db_default' in f.metadata:
                    return
                if value is not None:
                    return  # If default value is set, no need to raise an error
                raise ValueError(
                    f"::{self.modelName}:: Missing Required Field *{name}*"
                )
        except KeyError:
            return
        # Nullable:
        try:
            if f.metadata["nullable"] is False and self.Meta.strict is True:
                raise ValueError(
                    f"::{self.modelName}:: *{name}* Cannot be null."
                )
        except KeyError:
            return
        return

    def _validation_(
        self,
        name: str,
        value: Any,
        f: Field, _type: Any
    ) -> Optional[dict[Any, Any]]:
        """
        _validation_.
        TODO: cover validations as length, not_null, required, max, min, etc
        """
        val_type = type(value)
        # Set the current Value
        setattr(self, name, value)

        if val_type == type or value == _type or is_empty(value):
            try:
                self._field_checks_(f, name, value)
                return None
            except (ValueError, TypeError):
                raise
        else:
            # capturing other errors from validator:
            return _validation(f, name, value, _type, val_type)

    @classmethod
    def add_field(cls, name: str, value: Any = None) -> None:
        if cls.Meta.strict is True:
            raise TypeError(
                f'Cannot create a new field {name} on a Strict Model.'
            )
        if name != '__errors__':
            f = Field(required=False, default=value)
            f.name = name
            f.type = type(value)
            f._field_type = _FIELD
            cls.__columns__[name] = f
            cls.__dataclass_fields__[name] = f

    def create_field(self, name: str, value: Any) -> None:
        """create_field.
        create a new Field on Model (when strict is False).
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        Raises:
            TypeError: when try to create a new field on an Strict Model.
        """
        if self.Meta.strict is True:
            raise TypeError(
                f'Cannot create a new field {name} on a Strict Model.'
            )
        if name != '__errors__':
            f = Field(required=False, default=value)
            f.name = name
            f.type = type(value)
            f._field_type = _FIELD
            self.__columns__[name] = f
            self.__dataclass_fields__[name] = f
            setattr(self, name, value)

    def set(self, name: str, value: Any) -> None:
        """set.
        Alias for Create Field.
        Args:
            name (str): name of the field
            value (Any): value to be assigned.
        """
        if name not in self.__columns__:
            if name != '__errors__' and self.Meta.strict is False:
                self.create_field(name, value)
        else:
            setattr(self, name, value)

    def get_errors(self):
        return self.__errors__

    @classmethod
    def make_model(cls, name: str, schema: str = "public", fields: list = None):
        parent = inspect.getmro(cls)
        obj = make_dataclass(name, fields, bases=(parent[0],))
        m = Meta()
        m.name = name
        m.schema = schema
        m.app_label = schema
        obj.Meta = m
        return obj

    @classmethod
    def from_json(cls, obj: str, **kwargs) -> dataclass:
        try:
            decoder = cls.__encoder__(**kwargs)
            decoded = decoder.loads(obj)
            return cls(**decoded)
        except ValueError as e:
            raise RuntimeError(
                "DataModel: Invalid string (JSON) data for decoding: {e}"
            ) from e

    @classmethod
    def from_dict(cls, obj: dict) -> dataclass:
        try:
            return cls(**obj)
        except ValueError as e:
            raise RuntimeError(
                "DataModel: Invalid Dictionary data for decoding: {e}"
            ) from e

    @classmethod
    def model(cls, dialect: str = "json", **kwargs) -> Any:
        """model.

        Return the json-version of current Model.
        Returns:
            str: string (json) version of model.
        """
        result = None
        clsname = cls.__name__
        schema = cls.Meta.schema
        table = cls.Meta.name if cls.Meta.name else clsname.lower()
        columns = cls.columns(cls).items()
        if dialect == 'json':
            cols = {}
            for _, field in columns:
                key = field.name
                _type = field.type
                if _type.__module__ == 'typing':
                    # TODO: discover real value of typing
                    if _type._name == 'List':
                        t = 'array'
                    elif _type._name == 'Dict':
                        t = 'object'
                    else:
                        try:
                            t = _type.__args__[0]
                            t = t.__name__
                        except (AttributeError, ValueError):
                            t = 'object'
                else:
                    try:
                        t = JSON_TYPES[_type]
                    except KeyError:
                        t = 'object'
                cols[key] = {"name": key, "type": t}
            doc = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": f"/schemas/{table}",
                "name": clsname,
                "description": cls.__doc__.strip("\n").strip(),
                "additionalProperties": False,
                "table": table,
                "schema": schema,
                "type": "object",
                "properties": cols,
            }
            encoder = cls.__encoder__(**kwargs)
            result = encoder.dumps(doc, option=OPT_INDENT_2)
        return result

    @classmethod
    def sample(cls) -> dict:
        """sample.

        Get a dict (JSON) sample of this datamodel, based on default values.

        Returns:
            dict: _description_
        """
        columns = cls.get_columns().items()
        _fields = {}
        required = []
        for name, f in columns:
            if f.repr is False:
                continue
            _fields[name] = f.default
            try:
                if f.metadata["required"] is True:
                    required.append(name)
            except KeyError:
                pass
        return {
            "properties": _fields,
            "required": required
        }

    def _get_meta_value(self, key: str, fallback: Any = None, locale: Any = None):
        value = getattr(self.Meta, key, fallback)
        if locale is not None:
            value = locale(value)
        return value

    def _get_meta_values(
        self,
        key: dict,
        fallback: Any = None,
        locale: Any = None
    ):
        """
        _get_meta_values.

        Translates the entire dictionary of Meta values.
        """
        values = getattr(self.Meta, key, fallback)
        if locale is not None:
            for key, val in values.items():
                try:
                    values[key] = locale(val)
                except (KeyError, TypeError):
                    pass
        return values

    def _get_metadata(self, field, key: str, locale: Any = None):
        value = field.metadata.get(key, None)
        if locale is not None:
            value = locale(value)
        return value

    def _get_field_schema(
        self,
        type_info: str,
        field: object,
        description: str,
        locale: Any = None,
        **kwargs
    ) -> dict:
        return {
            "type": type_info,
            "nullable": field.metadata.get('nullable', False),
            "attrs": {
                "placeholder": description,
                "format": field.metadata.get('format', None),
            },
            "readOnly": field.metadata.get('readonly', False),
            **kwargs
        }

    @classmethod
    def schema(cls, as_dict=False, locale: Any = None):
        """Convert Model to JSON-Schema.

        Args:
            as_dict (bool, optional): if false, Returns JSON-schema as a JSON object.
            Defaults to False.

        Returns:
            _type_: JSON-Schema version of Model.
        """
        # description:
        description = cls._get_meta_value(
            cls,
            'description',
            fallback=cls.__doc__.strip("\n").strip(),
            locale=locale
        )
        title = cls._get_meta_value(
            cls,
            'title',
            fallback=cls.__name__,
            locale=locale
        )
        try:
            title = slugify_camelcase(title)
        except Exception:
            pass

        # Table Name:
        table = cls.Meta.name.lower() if cls.Meta.name else title.lower()
        endpoint = cls.Meta.endpoint
        schema = cls.Meta.schema
        columns = cls.get_columns().items()

        fields = {}
        required = []
        defs = {}

        # settings:
        settings = cls._get_meta_values(
            cls,
            'settings',
            fallback={},
            locale=locale
        )
        try:
            settings = {
                "settings": settings
            }
        except TypeError:
            settings = {}

        for name, field in columns:
            _type = field.type
            type_info = _get_type_info(_type, name, title)
            ref_info = _get_ref_info(_type, field)
            if ref_info:
                defs[name] = ref_info.pop('schema', None)
            else:
                ref_info = {}

            _metadata = field.metadata.copy()

            minimum = _metadata.pop('min', None)
            maximum = _metadata.pop('max', None)
            secret = _metadata.pop('secret', None)

            # custom endpoint for every field:
            custom_endpoint = _metadata.pop('endpoint', None)

            if field.metadata.get('required', False) or field.metadata.get('primary', False):
                required.append(name)

            # UI objects:
            ui_objects = {
                k.replace('_', ':'): v for k, v in _metadata.items() if k.startswith('ui_')
            }
            # schema_extra:
            schema_extra = _metadata.pop('schema_extra', {})
            meta_description = cls._get_metadata(
                cls,
                field,
                key='description',
                locale=locale
            )
            fields[name] = cls._get_field_schema(
                cls,
                type_info,
                field,
                description=meta_description,
                locale=locale,
                **ui_objects,
                **schema_extra,
                **ref_info
            )
            label = cls._get_metadata(cls, field, 'label', locale=locale)
            if label:
                fields[name]["label"] = label
            if meta_description:
                fields[name]["description"] = meta_description
            if custom_endpoint:
                fields[name]["endpoint"] = custom_endpoint

            if 'write_only' in field.metadata:
                fields[name]["writeOnly"] = _metadata.pop('write_only', False)

            if 'pattern' in field.metadata:
                fields[name]["attrs"]["pattern"] = _metadata.pop('pattern')

            if field.repr is False:
                fields[name]["attrs"]["visible"] = False

            _meta = {}
            _rejected = [
                'required',
                'nullable',
                'primary',
                'readonly',
                'label',
                'validator',
                'encoder',
                'decoder'
            ]
            for key, val in _metadata.items():
                if key not in _rejected:
                    _meta[key] = val

            if _meta:
                fields[name]["attrs"] = {
                    **fields[name]["attrs"],
                    **_meta
                }

            if field.default:
                d = field.default
                if is_callable(d):
                    fields[name]['default'] = f"fn:{d!r}"
                else:
                    fields[name]['default'] = f"{d!s}"

            if secret is not None:
                fields[name]['secret'] = secret

            if type_info == 'string':
                if minimum:
                    fields[name]['minLength'] = minimum
                if maximum:
                    fields[name]['maxLength'] = maximum
            else:
                if minimum:
                    fields[name]['minimum'] = minimum
                if maximum:
                    fields[name]['maximum'] = maximum

        endpoint_kwargs = {}
        if endpoint:
            endpoint_kwargs["endpoint"] = endpoint

        base_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"/schemas/{table}",
            **endpoint_kwargs,
            **settings,
            "additionalProperties": cls.Meta.strict,
            "title": title,
            "description": description,
            "type": "object",
            "table": table,
            "schema": schema,
            "properties": fields,
            "required": required,
        }

        if defs:
            base_schema["$defs"] = defs

        if as_dict is True:
            return base_schema
        else:
            return json_encoder(base_schema)
