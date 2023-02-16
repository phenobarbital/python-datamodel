from dataclasses import dataclass, field
from datamodel import BaseModel, Column
from dataclasses import dataclass, field, asdict

class DynamicInit(type):
    def __new__(cls, clsname, bases, clsdict):
        fields = clsdict.get('__annotations__', {})
        for field_name in fields:
            if field_name not in clsdict:
                clsdict[field_name] = field(default=None)

        # Define a new __init__() method that calls the original __init__() method with updated field values
        def new_init(self, *args, **kwargs):
            updated_kwargs = {**asdict(self), **kwargs}
            super(cls, self).__init__(*args, **updated_kwargs)

        clsdict['__init__'] = new_init
        new_cls = super().__new__(cls, clsname, bases, clsdict)
        new_cls.__dataclass_fields__ = fields
        return new_cls

@dataclass
class Person(metaclass=DynamicInit):
    name: str
    age: int
    address: str = None
    hobbies: str = None

p = Person(name="John", age=30, address=None, hobbies="Reading", new_field="New Field")
print(asdict(p))  # Output: {'name': 'John', 'age': 30, 'address': None, 'hobbies': 'Reading', 'new_field': 'New Field'}



class Persona(BaseModel):
    name: str
    age: int
    address: str = None
    hobbies: str = None

    class Meta:
        strict = False
        frozen = False
        remove_nulls = True # Auto-remove nullable (with null value) fields

Persona.new_field = Column(default=None)
print(Persona)

p = Persona(name="John", age=30, address=None, hobbies="Reading", new_field="New Field")
print(p)
