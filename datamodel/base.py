from collections.abc import Callable
from typing import Any, Dict
# Dataclass
from dataclasses import (
    _FIELD,
)
from html import escape
from .converters import processing_fields, register_parser
from .fields import Field
from .exceptions import ValidationError
from .abstract import ModelMeta
from .models import ModelMixin


RendererFn = Callable[["BaseModel", bool], str]

HTML_RENDERERS: Dict[str, RendererFn] = {}

def register_renderer(schema_type: str):
    """
    Decorator to register a custom renderer function for a given schema_type.
    """
    def decorator(fn: RendererFn):
        HTML_RENDERERS[schema_type] = fn
        return fn
    return decorator


class BaseModel(ModelMixin, metaclass=ModelMeta):
    """
    BaseModel.
    Base Model for all DataModels.
    """

    def __post_init__(self) -> None:
        """
        Post init method.
        Fill fields with function-factory or calling validations
        """
        # checking if an attribute is already a dataclass:
        columns = list(self.__columns__.items())

        if errors := processing_fields(self, columns):
            if self.Meta.strict is True:
                raise ValidationError(
                    (
                        f"{self.modelName}: There are errors in Model.\n"
                        "Hint: please check the 'payload' attribute in the exception."
                    ),
                    payload=errors
                )
            object.__setattr__(self, '__errors__', errors)
            object.__setattr__(self, '__valid__', False)
        else:
            object.__setattr__(self, '__valid__', True)
            return

    @classmethod
    def register_parser(
        cls,
        target_type: Any,
        func: Callable,
        field_name: str = None
    ):
        key = (target_type, field_name) if field_name else target_type
        register_parser(key, func)

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
        if name in self.__columns__:
            setattr(self, name, value)
        elif name != '__errors__' and self.Meta.strict is False:
            self.create_field(name, value)

    def get_errors(self):
        return self.__errors__

    def to_html(self, top_level: bool = True) -> str:
        """to_html.
        Convert Model to HTML.

        Args:
            top_level (bool, optional): If True, adds the @context to the schema.
        """
        # 1) Determine the schema type from self.Meta or fallback to class name
        schema_type = getattr(self.Meta, 'schema_type', self.__class__.__name__)

        if schema_type in HTML_RENDERERS:
            return HTML_RENDERERS[schema_type](self, top_level)

        # 2) Container opening. For top-level objects, we specify:
        #    - vocab="https://schema.org/"
        #    - typeof="Recipe" (or other type)
        #    For nested objects, we might omit the 'vocab' attribute
        #    or rely on the parent's scope.
        if top_level:
            container_open = f'<div vocab="https://schema.org/" typeof="{escape(schema_type)}">'
        else:
            container_open = f'<div property="{escape(schema_type)}" typeof="{escape(schema_type)}">'

        # We'll accumulate our HTML pieces here
        pieces = [container_open]

        # 3) Iterate over each field in this model
        for field_name, value in self.__dict__.items():
            # Skip internal or error fields
            if field_name.startswith('_') or field_name == '__errors__':
                continue

            # Optionally skip if None
            if value is None:
                continue

            # 4) If value is a nested model, convert it to HTML as well
            if isinstance(value, BaseModel):
                nested_html = value.to_html(False)
                snippet = f'<div property="{escape(field_name)}">\n{nested_html}\n</div>'
                pieces.append(snippet)

            elif isinstance(value, list):
                # We might iterate and produce multiple lines
                for item in value:
                    if isinstance(item, BaseModel):
                        nested_html = item.to_html(False)
                        snippet = f'<div property="{escape(field_name)}">\n{nested_html}\n</div>'
                    else:
                        # If it's a simple scalar, just output a <span>
                        # e.g.: <span property="recipeIngredient">3 bananas</span>
                        val_escaped = escape(str(item))
                        snippet = f'<span property="{escape(field_name)}">{val_escaped}</span>'
                    pieces.append(snippet)
            else:
                # For simple scalars (str, int, etc.):
                # We might choose <span> or <meta> based on type.
                # We'll do something simple: a <span>
                val_escaped = escape(str(value))
                snippet = f'<span property="{escape(field_name)}">{val_escaped}</span>'
                pieces.append(snippet)

        # 4) Close the container
        pieces.append('</div>')
        return "\n".join(pieces)
