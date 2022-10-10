import inspect
from datamodel import BaseModel, Field

class HazelPortable(BaseModel):
    factory_id: int = Field(default=1)

    def write_portable(self, writer):
        for name, f in self.columns().items():
            _type = f.type
            value = getattr(self, f)
            print('WRITER ', _type, value)

    def read_portable(self, reader):
        for name, f in self.columns().items():
            _type = f.type
            print('READER', name, _type)

    def set_factory(self, fid: int = 1):
        self.factory_id = fid

    def get_factory_id(self):
        return self.factory_id

    def get_class_id(self):
        return self.factory_id

class Customer(HazelPortable):
    name: str
    age: int
    is_active: bool

print(inspect.getmro(Customer))

c1 = Customer(name='Hola', age=33, is_active=True)
c2 = Customer(name='Hola', age=33, is_active=True)

print('Is Instance: ', isinstance(c1, HazelPortable))
print('Is a Subclass: ', issubclass(Customer, HazelPortable))

print('EQUALITY :: ', c1 == c2)
