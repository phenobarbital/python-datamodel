from __future__ import annotations
import contextlib
from typing import Any, Dict
from enum import Enum, EnumMeta
# Dataclass
import inspect
from dataclasses import asdict as as_dict, dataclass, make_dataclass, _MISSING_TYPE
from operator import attrgetter
from orjson import OPT_INDENT_2
from datamodel.fields import fields
from .abstract import ModelMeta, Meta
from .fields import Field
from .parsers.encoders import json_encoder
from .converters import slugify_camelcase
from .types import JSON_TYPES, Text
from .functions import is_callable


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
        if type(_type) == type(Text):  # pylint: disable=C0123 # noqa
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


class ModelMixin:
    """Interface for shared methods on Model classes.
    """
    def __unicode__(self):
        return str(__class__)

    def columns(self):
        return self.__columns__

    @classmethod
    def get_columns(cls):
        return cls.__columns__

    @classmethod
    def get_column(cls, name: str) -> Field:
        try:
            return cls.__columns__[name]
        except KeyError as ex:
            raise AttributeError(
                f"{cls.__name__} has no column {name}"
            ) from ex

    def has_column(self, name: str) -> bool:
        return name in self.__columns__

    def list_columns(self) -> list[str]:
        return self.__fields__

    def get_fields(self):
        return self.__fields__

    def __contains__(self, key: str) -> bool:
        """__contains__. Check if key is in the columns of the Model."""
        return key in self.__columns__

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def reset_values(self):
        with contextlib.suppress(AttributeError):
            self.__values__ = {}

    def old_value(self, name: str) -> Any:
        """
        old_value.
        Get the old value of an attribute.
        Args:
            name (str): name of the attribute.
        Returns:
            Any: value of the attribute.
        """
        try:
            return self.__values__[name]
        except KeyError as ex:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from ex

    def column(self, name: str) -> Field:
        return self.__columns__[name]

    def __repr__(self) -> str:
        field_strs = []
        for field_name in self.__fields__:
            try:
                value = getattr(self, field_name)
            except AttributeError:
                # If this field doesn't exist on the instance, ignore it
                continue
            field_strs.append(f"{field_name}={value!r}")
        return f"{self.__class__.__name__}({', '.join(field_strs)})"

    def pop(self, key: str, default: Any = _MISSING_TYPE) -> Any:
        """
        A dict-like pop() method.
        Removes the value of `self.key` if it exists, otherwise returns `default`.
        """
        if key not in self.__columns__:
            if default is not _MISSING_TYPE:
                return default
            raise KeyError(f"{self.__class__.__name__} has no attribute {key}")

        # return the current value:
        value = getattr(self, key)
        setattr(self, key, None)
        if hasattr(self, '__values__') and key in self.__values__:
            del self.__values__[key]

        return value

    def remove_nulls(self, obj: Any) -> dict[str, Any]:
        """Recursively removes any fields with None values from the given object."""
        if isinstance(obj, list):
            return [self.remove_nulls(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                key: self.remove_nulls(value) for key, value in obj.items()
                if value is not None and value != {}
            }
        else:
            return obj

    def __convert_enums__(self, obj: Any) -> dict[str, Any]:
        """Recursively converts any Enum values to their value."""
        if isinstance(obj, list):
            return [self.__convert_enums__(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                key: self.__convert_enums__(value) for key, value in obj.items()
            }
        else:
            return obj.value if isinstance(obj, Enum) else obj

    def to_dict(
        self,
        remove_nulls: bool = False,
        convert_enums: bool = False,
        as_values: bool = False
    ) -> dict[str, Any]:
        if as_values:
            return self.__collapse_as_values__(remove_nulls, convert_enums, as_values)
        d = as_dict(self, dict_factory=dict)
        if convert_enums:
            d = self.__convert_enums__(d)
        if self.Meta.remove_nulls is True or remove_nulls:
            return self.remove_nulls(d)
        # 4) If as_values => convert sub-models to pk-value
        return d

    def __collapse_as_values__(
        self,
        remove_nulls: bool = False,
        convert_enums: bool = False,
        as_values: bool = False
    ) -> dict[str, Any]:
        """Recursively converts any BaseModel instances to their primary key value."""
        out = {}
        _fields = self.columns()
        for name, field in _fields.items():
            # datatype = field.type
            value = getattr(self, name)
            if value is None and remove_nulls:
                continue
            if isinstance(value, ModelMixin):
                if as_values:
                    try:
                        out[name] = getattr(value, name)
                    except AttributeError:
                        out[name] = value.to_json()
                else:
                    out[name] = value.__collapse_as_values__(
                        remove_nulls=remove_nulls,
                        convert_enums=convert_enums,
                        as_values=as_values
                    )
            # if it's a list, might contain submodels or scalars
            elif isinstance(value, list):
                if field.origin is list and field.args:
                    submodel_class = field.args[0]  # The type inside the list
                    if issubclass(
                        submodel_class, ModelMixin
                    ) and not hasattr(submodel_class, name):
                        out[name] = json_encoder(value)
                        continue
                items_out = []
                for item in value:
                    if isinstance(item, ModelMixin):
                        if as_values:
                            try:
                                items_out.append(getattr(item, name))
                            except AttributeError:
                                items_out.append(item.to_json())
                        else:
                            items_out.append(item.__collapse_as_values__(
                                remove_nulls=remove_nulls,
                                convert_enums=convert_enums,
                                as_values=as_values
                            ))
                    else:
                        items_out.append(item)
                out[name] = items_out
            else:
                out[name] = value
        if convert_enums:
            out = self.__convert_enums__(out)
        return out

    def json(self, **kwargs):
        encoder = self.__encoder__(**kwargs)
        return encoder(as_dict(self))

    to_json = json

    def is_valid(self) -> bool:
        """is_valid.

        returns True when current Model is valid under datatype validations.
        Returns:
            bool: True if current model is valid.
        """
        return bool(self.__valid__)

    def get(self, key: str, default=None):
        """
        A dict-like get() method.
        Returns the value of `self.key` if it exists, otherwise returns `default`.
        """
        return getattr(self, key) if hasattr(self, key) else default

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
    def _build_schema_basics(cls, locale: Any = None):
        """Build basic schema metadata such as title, description, etc."""
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
        # display_name:
        display_name = cls._get_meta_value(
            cls,
            'display_name',
            fallback=f"{title}_name".lower(),
            locale=locale
        )
        # Table Name:
        table = cls.Meta.name.lower() if cls.Meta.name else title.lower()
        endpoint = cls.Meta.endpoint
        schema = cls.Meta.schema
        return title, description, display_name, table, endpoint, schema

    @classmethod
    def _build_settings(cls, locale: Any = None) -> dict:
        """Build the settings part of the schema."""
        # settings:
        settings = cls._get_meta_values(
            cls,
            'settings',
            fallback={},
            locale=locale
        )
        if not isinstance(settings, dict):
            # Ensure settings is always a dict
            settings = {}
        return {"settings": settings}

    @classmethod
    def _build_fields(cls, title: str, locale: Any = None) -> dict:
        """Build the fields part of the schema."""
        _fields = {}
        required = []
        defs = {}

        # Get the columns of the Model.
        for name, field in cls.get_columns().items():
            field_schema, field_defs, field_required = cls._process_field_schema(
                name, field, locale, title
            )
            _fields[name] = field_schema
            if field_required:
                required.append(name)
            if field_defs:
                defs[name] = field_defs.get('schema')
        return _fields, required, defs

    @classmethod
    def _extract_field_basics(cls, name: str, field: Field, title: str):
        _type = field.type
        type_info = _get_type_info(_type, name, title)
        ref_info = _get_ref_info(_type, field) or {}
        field_defs = {}

        if 'schema' in ref_info:
            field_defs['schema'] = ref_info.pop('schema', None)

        return type_info, ref_info, field_defs

    @classmethod
    def _extract_and_filter_metadata(cls, field: Field, locale: Any):
        """Extract and filter metadata."""
        _metadata = field.metadata.copy()
        minimum = _metadata.pop('min', None)
        maximum = _metadata.pop('max', None)
        secret = _metadata.pop('secret', None)
        custom_endpoint = _metadata.pop('endpoint', None)

        field_required = field.metadata.get(
            'required', False
        ) or field.metadata.get('primary', False)

        ui_objects = {
            k.replace('_', ':'): v for k, v in _metadata.items() if k.startswith('ui_')
        }
        schema_extra = _metadata.pop('schema_extra', {})

        meta_description = cls._get_metadata(
            cls, field, key='description', locale=locale
        )

        return (
            _metadata,
            minimum,
            maximum,
            secret,
            custom_endpoint,
            field_required,
            ui_objects,
            schema_extra,
            meta_description
        )

    @classmethod
    def _apply_extra_metadata(cls, field_schema: dict, _metadata: dict):
        """Move non-rejected metadata keys into the 'attrs' dict."""
        _rejected = [
            'required', 'nullable', 'primary', 'readonly',
            'label', 'validator', 'encoder', 'decoder',
            'default_factory', 'type'
        ]

        if _meta := {k: v for k, v in _metadata.items() if k not in _rejected}:
            field_schema["attrs"] = {
                **field_schema["attrs"],
                **_meta
            }

    @classmethod
    def _apply_defaults_and_constraints(
        cls,
        field_schema: dict,
        field: Field,
        secret: Any,
        type_info: str,
        minimum: Any,
        maximum: Any
    ):
        """Handle default values, secret fields, and min/max constraints."""
        if field.default:
            if not isinstance(field.default, _MISSING_TYPE) and not callable(field.default):
                d = field.default
                field_schema['default'] = f"fn:{d!r}" if is_callable(d) else f"{d!s}"

        if secret is not None:
            field_schema['secret'] = secret

        # Handle length/size constraints
        if type_info == 'string':
            if minimum is not None:
                field_schema['minLength'] = minimum
            if maximum is not None:
                field_schema['maxLength'] = maximum
        else:
            if minimum is not None:
                field_schema['minimum'] = minimum
            if maximum is not None:
                field_schema['maximum'] = maximum

    @classmethod
    def _process_field_schema(
        cls,
        name: str,
        field: Field,
        locale: Any,
        title: str
    ) -> tuple:
        """Process the schema for a single field."""
        # Get the field type and description.

        type_info, ref_info, field_defs = cls._extract_field_basics(name, field, title)

        # Extract and handle metadata
        (
            _metadata,
            minimum,
            maximum,
            secret,
            custom_endpoint,
            field_required,
            ui_objects,
            schema_extra,
            meta_description
        ) = cls._extract_and_filter_metadata(
            field, locale
        )

        if 'schema' in ref_info:
            field_defs['schema'] = ref_info.pop('schema', None)

        # Build the basic field schema
        field_schema = cls._get_field_schema(
            cls,
            type_info,
            field,
            description=meta_description,
            locale=locale,
            **ui_objects,
            **schema_extra,
            **ref_info
        )

        # Handle primary/required keys
        if field.metadata.get('primary', False) is True:
            field_schema["primary_key"] = True
        if field_required:
            field_schema["required"] = True

        # Add label and description if available
        label = cls._get_metadata(cls, field, 'label', locale=locale)
        if label:
            field_schema["label"] = label
        if meta_description:
            field_schema["description"] = meta_description

        # Add custom endpoint
        if custom_endpoint:
            field_schema["endpoint"] = custom_endpoint

        # Handle write_only, pattern, visible attributes
        if 'write_only' in field.metadata:
            field_schema["writeOnly"] = _metadata.pop('write_only', False)

        if 'pattern' in field.metadata:
            field_schema["attrs"]["pattern"] = _metadata.pop('pattern')

        if field.repr is False:
            field_schema["attrs"]["visible"] = False

        # Remove some rejected keys and move others into attrs
        cls._apply_extra_metadata(field_schema, _metadata)

        # Handle default, secret, and constraints
        cls._apply_defaults_and_constraints(
            field_schema,
            field,
            secret,
            type_info,
            minimum,
            maximum
        )

        return field_schema, field_defs, field_required

    @classmethod
    def schema(cls, as_dict=False, locale: Any = None):
        """
        Convert the Model to a JSON-Schema representation.

        This method generates a JSON-Schema that describes the structure and constraints
        of the Model. It includes information about fields, their types,
        validation rules, and other metadata.

        Args:
            as_dict (bool, optional): If True,
                returns the schema as a Python dictionary.
                If False, returns the schema as a JSON-encoded string.
                Defaults to False.
            locale (Any, optional):
                The locale to use for internationalization of schema
                elements like descriptions and labels. Defaults to None.

        Returns:
            Union[dict, str]:
                The JSON-Schema representation of the Model. If as_dict is True,
                returns a Python dictionary. Otherwise, returns a JSON-encoded string.

        Note:
            This method caches the computed schema in the __computed_schema__ attribute
            of the class for subsequent calls.
        """
        # Check if schema is already computed and cached.
        if hasattr(cls, '__computed_schema__'):
            return cls.__computed_schema__ if as_dict else json_encoder(
                cls.__computed_schema__
            )

        # Build basic schema attributes (title, description, display_name, etc.)
        title, description, display_name, table, endpoint, schema = cls._build_schema_basics(locale)  # pylint: disable=C0301 # noqa
        settings = cls._build_settings(locale)
        endpoint_kwargs = {"endpoint": endpoint} if endpoint else {}

        # Build the fields part of the schema.
        _fields, required, defs = cls._build_fields(title, locale)

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
            "properties": _fields,
            "required": required,
            "display_name": display_name,
        }

        if defs:
            base_schema["$defs"] = defs

        # Cache the computed schema for subsequent calls
        cls.__computed_schema__ = base_schema

        return base_schema if as_dict else json_encoder(base_schema)

    def as_schema(self, top_level: bool = True) -> dict:
        """as_schema.
        Convert the Model instance to a JSON-LD schema representation.
        Args:
            top_level (bool, optional): If True, adds the @context to the schema.
        Returns:
            dict: JSON-LD schema representation of the Model instance.
        """
        data = {}
        # If top_level, add @context
        if top_level:
            data["@context"] = "https://schema.org/"

        # Determine the schema @type
        schema_type = getattr(self.Meta, 'schema_type', self.__class__.__name__)
        data["@type"] = schema_type

        for field_name, field_obj in self.__columns__.items():
            # Skip internal or error fields
            if field_name.startswith('__') or field_name == '__errors__':
                continue

            value = getattr(self, field_name)
            if isinstance(value, ModelMixin):
                data[field_name] = value.as_schema(top_level=False)
            else:
                data[field_name] = value

        return data

    @classmethod
    def make_model(cls, name: str, schema: str = "public", fields: list = None):
        parent = inspect.getmro(cls)
        obj = make_dataclass(name, fields, bases=(parent[0],))
        m = Meta()
        m.name = name
        m.schema = schema
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
        if hasattr(cls, '__computed_model__'):
            return cls.__computed_model__
        result = None
        clsname = cls.__name__
        schema = cls.Meta.schema
        table = cls.Meta.name or clsname.lower()
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
        cls.__computed_model__ = result
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

    @classmethod
    def from_jsonld(cls, data: Dict[str, Any]) -> "ModelMixin":
        """
        Create a model instance from a JSON-LD dictionary.

        Ignores @context and @type; attempts to parse all other top-level fields
        into the model’s constructor. If the JSON-LD has nested objects that
        correspond to other BaseModel fields, you may need additional logic
        to instantiate sub-models.
        """
        if not isinstance(data, dict):
            raise ValueError("JSON-LD input must be a dictionary.")
        # If present, remove the JSON-LD keys that are not actual model fields
        data.pop("@context", None)
        data.pop("@type", None)

    @classmethod
    def to_adaptive(cls, as_dict: bool = False, locale: Any = None):
        """
        Convert the Model to an Adaptive-Card compatible representation.

        This method generates an Adaptive-Card that describes the structure and constraints
        of the Model. It includes information about fields, their types,
        validation rules, and other metadata.

        Args:
            as_dict (bool, optional): If True,
                returns the schema as a Python dictionary.
                If False, returns the schema as a JSON-encoded string.
                Defaults to False.
            locale (Any, optional):
                The locale to use for internationalization of schema
                elements like descriptions and labels. Defaults to None.

        Returns:
            Union[dict, str]:
                The JSON-valid Adaptive-Card representation of the Model. If as_dict is True,
                returns a Python dictionary. Otherwise, returns a JSON-encoded string.

        Note:
            This method caches the computed schema in the __computed_schema__ attribute
            of the class for subsequent calls.
        """
        # Check if schema is already computed and cached.
        if hasattr(cls, '__computed_adaptive__'):
            return cls.__computed_adaptive__ if as_dict else json_encoder(
                cls.__computed_adaptive__
            )

        # Build basic schema attributes (title, description, display_name, etc.)
        title, description, display_name, table, endpoint, schema = cls._build_schema_basics(locale)  # pylint: disable=C0301 # noqa
        settings = cls._build_settings(locale)
        endpoint_kwargs = {"endpoint": endpoint} if endpoint else {}

        adaptive_card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.0",
            "body": [],
            "actions": []
        }
        card_body = adaptive_card["body"]
        card_actions = adaptive_card["actions"]

        # Adding the Title:
        card_body.append({
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "text": title or table
        })

        # Adding the Description:
        card_body.append({
            "type": "TextBlock",
            "text": description,
            "wrap": True
        })

        columns = cls.columns(cls).items()
        for name, field in columns:
            ui_help = cls._get_metadata(cls, field, 'ui_help', locale=None)
            placeholder = cls._get_metadata(cls, field, 'placeholder', locale=None)
            label = cls._get_metadata(cls, field, 'label', locale=None)
            title = cls._get_metadata(cls, field, 'title', locale=None)
            if not title:
                title = name.replace('_', ' ').title()
            ui_widget = field.metadata.get('ui_widget', None)
            style = field.metadata.get('style', None)
            is_required = field.metadata.get('required', False)

            field_type = field.type
            adaptive_input = None

            # Create Label TextBlock
            label_text = label or title  # Default label
            label_block = {
                "type": "TextBlock",
                "text": label_text,
                "wrap": True
            }
            card_body.append(label_block)

            common_input = {
                "id": name,
                "isRequired": is_required,
            }
            if field.repr is False:  # Using metadata['repr'] to set "isVisible"
                common_input["isVisible"] = False

            # Map field types to Adaptive Card Input types
            if field_type is str:
                adaptive_input = {
                    "type": "Input.Text",
                    "placeholder": ui_help or placeholder, # noqa
                }
                if ui_widget == 'textarea':
                    adaptive_input["isMultiline"] = True
                if style:  # e.g., email, url, password
                    adaptive_input["style"] = style

            elif field_type is int or field_type is float:
                adaptive_input = {
                    "type": "Input.Number",
                }

            elif isinstance(field_type, EnumMeta):
                adaptive_input = {
                    "type": "Input.ChoiceSet",
                    "choices": [
                        {"title": str(e.value), "value": str(e.value)} for e in field_type  # noqa
                    ]  # Convert Enum to choices
                }
                if field.default is not _MISSING_TYPE:
                    adaptive_input["value"] = str(field.default.value)

            elif field_type is bool:
                adaptive_input = {
                    "type": "Input.Toggle",
                    "title": label_text,  # Use label as title for Toggle
                    "valueOff": "false",  # Adaptive Cards convention for boolean false
                    "valueOn": "true",  # Adaptive Cards convention for boolean true
                    "value": "true" if field.default is True else "false"
                }
                # No need for separate Label TextBlock for Toggle as title is used.

            if adaptive_input:
                adaptive_input.update(common_input)
                card_body.append(adaptive_input)

        # Add Submit Action
        # Use Meta.submit or default to "OK"
        submit_action = {
            "type": "Action.Submit",
            "title": cls._get_meta_value(cls, 'submit', fallback='OK', locale=None)
        }
        card_actions.append(submit_action)

        # Cache the computed schema for subsequent calls
        cls.__computed_adaptive__ = adaptive_card
        return adaptive_card if as_dict else json_encoder(adaptive_card)

class Model(ModelMixin, metaclass=ModelMeta):
    """Model.

    Basic dataclass-based Model.
    """
    Meta = Meta

    def __post_init__(self) -> None:
        """
        Post init method.
        Useful for making Post-validations of Model.
        """
        self.__initialised__ = True
