# -*- coding: utf-8 -*-
"""DataModels.

DataModel is a reimplementation of dataclasses with true inheritance and composition.
"""
from .version import (
    __title__, __description__, __version__, __author__, __author_email__
)
from .base import Field, Column, BaseModel

__all__ = ('Field', 'Column', 'BaseModel', )
