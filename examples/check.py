from __future__ import annotations
from datetime import datetime

_started = datetime.now()
import inspect
import types
from typing import (
    Optional,
    Union,
    Any
)
import logging
from collections.abc import Callable
# Dataclass
from dataclasses import (
    dataclass,
    is_dataclass,
    _FIELD,
    asdict,
    make_dataclass,
    _MISSING_TYPE
)
from orjson import OPT_INDENT_2
from datamodel.fields import Field
from datamodel.types import JSON_TYPES, DB_TYPES
from datamodel.converters import parse_type
from datamodel.validation import validator
from datamodel.parsers.encoders import DefaultEncoder

import re
from typing import Union
from dataclasses import is_dataclass, _MISSING_TYPE
# from distutils.util import strtobool
from decimal import Decimal
# # from cpython cimport datetime
from dateutil import parser
from uuid import UUID
# # from cpython.ref cimport PyObject
import orjson

print(f'Loaded at: {datetime.now() - _started}')


# def auto_now_add(*args, **kwargs):
#     return uuid.uuid4()

# def is_employee(obj) -> str:
#     if obj in ('Y', 'F'):
#         return obj
#     elif obj is True:
#         return 'Y'
#     else:
#         return 'F'

# class Contact(BaseModel):
#     account: str = ''
#     value: str = ''

# class User(BaseModel):
#     """
#     User Basic Structure
#     """
#     id: uuid.UUID = Column(primary_key=True, required=True, default=auto_now_add(), db_default='uuid_generate_v4()')
#     firstname: str
#     lastname: str
#     name: str = Column(required=True, default='John Doe')
#     age: int = Column(default=18, required=True)
#     salary: Decimal = Column(default=10.0)
#     in_time: time = Column(default='15:00')
#     out_time: time = Column(default='23:00')
#     birth: date = Column(required=False)
#     is_employee: str = Column(required=True, default='F', encoder=is_employee)
#     size: float
#     signup_ts: datetime = Column(default=datetime.now(), db_default='now()')
#     contacts: Contact = Column(required=False)

#     class Meta:
#         name = 'users'
#         schema = 'public'
#         driver = 'pg'
#         strict = False

# u = User()
# print(u.model(dialect='json'))

# ### creates a new user:
# jesus = User(
#     firstname='Jesus', lastname='Lara', age=43, salary=1500.25, size=185.28, birth='1978-10-23', in_time='11:00:00.000', out_time='23:59:00.000', is_employee=True
# )
# print(jesus)
# b = jesus.json()
# jlara = User.from_json(b)
# print(jlara)
