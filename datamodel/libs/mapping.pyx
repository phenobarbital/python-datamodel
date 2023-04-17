# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=False, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
import sys
from typing import Optional, Union, Any
from datamodel import Field
from collections.abc import Iterator, Iterable
if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec
P = ParamSpec("P")


cdef class ClassDict(dict):

    def __cinit__(self, *args, data: Optional[dict]=None, default: Optional[Union[list,dict]]=None, **kwargs: P.kwargs):
        self.mapping = {}
        self._columns = []
        self.default = default
        self.mapping.update(*args, **kwargs)
        self.update(data, **kwargs)

    def update(self, items: Optional[dict]=None, **kwargs: P.kwargs):
        if isinstance(items, dict):
            for key, value in items.items():
                self.mapping[key] = value
        else:
            for k, v in kwargs.items():
                attr = getattr(self, k)
                if isinstance(attr, Field):
                    try:
                        fn = attr.default
                        if callable(fn):
                            v = fn(v)
                            setattr(self, k, v)
                        else:
                            setattr(self, k, fn)
                    except (TypeError, KeyError):
                        pass
                self.mapping[k] = v
        self._columns = list(self.mapping.keys())

    def __missing__(self, key):
        return self.default

    def __len__(self):
        return len(self.mapping)

    def __str__(self):
        return f"<{type(self).__name__}({self.mapping})>"

    def __repr__(self):
        return f"<{type(self).__name__}({self.mapping})>"

    def __contains__(self, key):
        return key in self._columns

    def __delitem__(self, key):
        if key in self.mapping:
            value = self.mapping.pop(key)
            self._columns.remove(key)
            self.pop(value, None)

    def __setitem__(self, key, value):
        self.mapping[key] = value
        if key not in self._columns:
            self._columns.append(key)

    def __getitem__(self, key):
        try:
            return self.mapping[key]
        except KeyError:
            return self.default

    def keys(self):
        return self.mapping.keys()

    def values(self):
        return self.mapping.values()

    def items(self):
        return self.mapping.items()

    def pop(self, key, default=None):
        try:
            value = self[key]
            del self[key]
            return value
        except KeyError:
            return default

    def clear(self):
        self.mapping.clear()
        self._columns = []

    def __iter__(self) -> Iterator:
        for value in self.mapping:
            yield value

    def __getattr__(self, attr: str) -> Any:
        """
        Attributes for dict keys
        """
        try:
            return self.__getitem__(attr)
        except KeyError as ex:
            raise KeyError(
                f"User Error: invalid field name {attr} on {self.mapping!r}"
            ) from ex
        except TypeError as ex:
            raise TypeError(
                f"User Error: invalid attribute value on {self.mapping!r} for {attr}"
            ) from ex

    def __delattr__(self, name: str) -> None:
        value = self[name]
        del self.mapping[name]
        self._columns.remove(name)
        self.pop(value, None)
