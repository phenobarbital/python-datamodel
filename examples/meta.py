from datamodel.abstract import ModelMeta

class Person(metaclass=ModelMeta):
    id: int
    name: str
    age: int = 18

p = Person(id=1, name="John")
print(p.age) # Output: 18
print('Person > ', p)

u = Person(id=2, name='Mary', age=21)
print(u.age) # Output: 21
print('Person > ', u)
