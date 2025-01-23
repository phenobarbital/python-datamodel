from dataclasses import dataclass, field
from datamodel import BaseModel

class IntConversionDescriptor:
    def __init__(self, *, default):
        self._default = default

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, int(value))

@dataclass
class InventoryItem(BaseModel):
    quantity_on_hand: IntConversionDescriptor = IntConversionDescriptor(default=100.10)

item = InventoryItem()
print(item.quantity_on_hand)  # 100
item.quantity_on_hand = 2.573   # __set__ converts to integer
print(item.quantity_on_hand)  # 2
