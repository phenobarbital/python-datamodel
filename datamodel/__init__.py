# -*- coding: utf-8 -*-
"""DataModels.

DataModel is a reimplementation of dataclasses with true inheritance and composition.
"""
from datamodel.fields import Field, Column
from .base import BaseModel
from .version import (
    __title__, __description__, __version__, __author__, __author_email__
)

__all__ = ('Field', 'Column', 'BaseModel', )
