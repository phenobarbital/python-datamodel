from typing import Optional, List, Dict, Tuple, Set, Union, Any, FrozenSet
import uuid
from datetime import datetime
from dataclasses import is_dataclass
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class ContainerTypesModel(BaseModel):
    """Model with different container types"""
    class Meta:
        strict = True
        frozen = False

    # Bare container types (without type arguments)
    bare_list: list = Field(default_factory=list)
    bare_dict: dict = Field(default_factory=dict)
    bare_tuple: tuple = Field(default_factory=tuple)
    bare_set: set = Field(default_factory=set)

    # Typed container types
    typed_list: List[int] = Field(default_factory=list)
    typed_dict: Dict[str, str] = Field(default_factory=dict)
    typed_tuple: Tuple[str, ...] = Field(default_factory=tuple)
    typed_set: Set[str] = Field(default_factory=set)

    # Nested container types
    nested_list: List[List[int]] = Field(default_factory=list)
    nested_dict: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    # Union types with containers
    union_list: Union[List[int], str] = Field(default=None)
    union_list_str: Union[str, List[str]] = Field(default=None)
    union_dict: Union[Dict[str, int], int] = Field(default=None)
    union_set: Union[Set[str], str] = Field(default=None)

    # Optional container types
    optional_list: Optional[List[int]] = Field(default=None)
    optional_dict: Optional[Dict[str, int]] = Field(default=None)
    optional_set: Optional[Set[str]] = Field(default=None)

    # Empty containers - these should not fail
    empty_list: List[int] = Field(default_factory=list)
    empty_set: Set[str] = Field(default_factory=set)
    empty_dict: Dict[str, int] = Field(default_factory=dict)
    empty_tuple: Tuple[int, ...] = Field(default_factory=tuple)

    # FrozenSet (less common but should work)
    frozen_set: FrozenSet[str] = Field(default_factory=frozenset)


if __name__ == '__main__':
    # try:
    #     container = ContainerTypesModel(
    #         bare_list=["a", "b", 1, 2],
    #         bare_dict={"a": 1, "b": 2},
    #         bare_tuple=("x", "y", 1, 2),
    #         bare_set={"a", "b", "c"},

    #         typed_list=[1, 2, 3, 4],
    #         typed_dict={"a": "A", "b": "B"},
    #         typed_tuple=("x", "y", "z"),
    #         typed_set={"a", "b", "c"},

    #         nested_list=[[1, 2], [3, 4]],
    #         nested_dict={"a": {"x": 1, "y": 2}, "b": {"z": 3}},

    #         union_list=[1, 2, 3],
    #         union_list_str="Not a List",
    #         union_dict={"a": 1, "b": 2},
    #         union_set={"a", "b", "c"},

    #         optional_list=[1, 2, 3],
    #         optional_dict={"a": 1, "b": 2},
    #         optional_set={"a", "b", "c"},

    #         frozen_set=frozenset(["x", "y", "z"])
    #     )
    #     print(container)
    # except ValidationError as e:
    #     print(e.payload)
    try:
        model = ContainerTypesModel(
            nested_list=[[1, 2], [3, "4"]],  # Note "4" should convert to 4
            nested_dict={
                "a": {"x": 1, "y": "2"},  # Note "2" should convert to 2
                "b": {"z": 3}
            }
        )
        print(model)
    except ValidationError as e:
        print(e.payload)
