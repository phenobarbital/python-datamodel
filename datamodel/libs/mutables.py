import sys
from collections.abc import MutableMapping, Iterator, Iterable
from typing import Any, Optional, Union, Literal
from typing_extensions import TypedDict
from datamodel import Field

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec
P = ParamSpec("P")


class ClassDictConfig(TypedDict, total=False):
    """
    Configuration dictionary for ClassDict-based classes.
    `total=False` means all keys are optional.
    """
    extra: Literal['allow', 'ignore', 'forbid']
    validate_assignment: bool
    parse_values: bool


class ClassDict(dict, MutableMapping):
    """ClassDict.

    Mapping that works like both a simple Dictionary or a Mutable Object.
    """
    def __init__(self, *args: P.args, data: Optional[Union[tuple, dict]] = None, default: Any = None, **kwargs: P.kwargs):  # noqa
        self._columns: list = []
        self.mapping = {}
        self.default = default
        self.mapping.update(*args, **kwargs)
        self.update(data, **kwargs)

    def update(self, items: Optional[Iterable] = None, **kwargs): # pylint: disable=W0221 # noqa
        if isinstance(items, dict):
            for key, value in items.items():
                # self.mapping[key] = value
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
                    except KeyError:
                        pass
                # self.mapping[k] = v
                self.mapping[k] = v
        self._columns = list(self.mapping.keys())

    def __missing__(self, key):
        return self.default

    def items(self) -> zip:  # type: ignore
        return zip(self._columns, self.mapping)

    def keys(self) -> list:
        return self._columns

    def set(self, key, value) -> None:
        self.mapping[key] = value
        if key not in self._columns:
            self._columns.append(key)

    ### Section: Simple magic methods
    def __len__(self) -> int:
        return len(self.mapping)

    def __str__(self) -> str:
        return f"<{type(self).__name__}({self.mapping})>"

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self.mapping})>"

    def __contains__(self, key: str) -> bool:
        return key in self._columns

    def __delitem__(self, key) -> None:
        value = self[key]
        del self.mapping[key]
        self._columns.remove(key)
        self.pop(value, None)

    def __delattr__(self, name: str) -> None:
        value = self[name]
        del self.mapping[name]
        self._columns.remove(name)
        self.pop(value, None)

    def __setitem__(self, key, value):
        self.mapping[key] = value
        if key not in self._columns:
            self._columns.append(key)

    def __getitem__(self, key: Union[str, int]) -> Any:
        """
        Sequence-like operators
        """
        try:
            return self.mapping[key]
        except (KeyError, TypeError):
            return None

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

    def __iter__(self) -> Iterator:
        yield from self.mapping
