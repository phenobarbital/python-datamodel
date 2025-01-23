from datamodel import BaseModel, Field

class IntConversionDescriptor(Field):
    def __init__(self, *, default, **kwargs):
        self._default = default
        super().__init__(default=default, **kwargs)

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type):
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)

    def __set__(self, obj, value):
        setattr(obj, self._name, int(value))

class InventoryItem(BaseModel):
    quantity_on_hand: IntConversionDescriptor = IntConversionDescriptor(
        default=100.10,
        required=True,
        ui_meta={'label': 'Quantity on Hand'}
    )
    price_per_unit: IntConversionDescriptor = IntConversionDescriptor(
        default=50.75,
        required=False,
        ui_meta={'label': 'Price per Unit'}
    )

item = InventoryItem()
print(item.quantity_on_hand)  # 100
item.quantity_on_hand = 2.573   # __set__ converts to integer
print(item.quantity_on_hand)  # 2

print(item.price_per_unit)  # 50
item.price_per_unit = 99.99
print(item.price_per_unit)  # 99
