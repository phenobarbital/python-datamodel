from typing import Optional, List, Union
from datamodel import BaseModel

print('=== Using Methods within Dataclass: ')


class InventoryItem(BaseModel):
    """Class for keeping track of an item in inventory."""
    name: str
    unit_price: float
    quantity: int = 0
    discount: Optional[int] = 0

    def total_cost(self) -> float:
        return self.unit_price * self.quantity

    @property
    def with_discount(self) -> float:
        return self.unit_price - float(self.discount)


grapes = InventoryItem(
    name='Grapes',
    unit_price=2.55
)
grapes.quantity = 8
print(f'Total for {grapes.name} is: ', grapes.total_cost())
grapes.discount = 0.18
print(f'Price of {grapes.name} with discount: {grapes.with_discount}')

print(':: Complex Model of Nested and Union Classes :: ')
print('=== Nested DataClasses: ')


class Foo(BaseModel):
    value: Union[List[int], int]


class Bar(BaseModel):
    foo: Union[Foo, List[Foo]]


f = Foo(value=[1, 2])
print('Foo > ', f, 'Value: ', f.value)
instance = Bar(foo=f)
print('Bar: > ', instance, instance.foo)
assert instance.is_valid() or 'Not Valid'
print('Valid: ', instance.is_valid())
assert instance == Bar(foo=Foo(value=[1, 2]))
print('EQ: ', instance == Bar(foo=Foo(value=[1, 2])))
