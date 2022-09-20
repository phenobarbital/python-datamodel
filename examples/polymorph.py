"""
This example covers a basic polymorphism concept, avoid Data Ambiguity.
"""
from typing import List
from datamodel import BaseModel, Column

class Animal(BaseModel):
    name: str
    weight: int

class Snake(Animal):
    length: float

class Mammal(Animal):
    temp: float = Column(default=38.0)

class Tiger(Mammal):
    height: float

class Elephant(Mammal):
    trunk_length: int

class Zoo(BaseModel):
    animals: list

animals = [
    Elephant(name="Eldor", trunk_length=176),
    Tiger(name="Roy", weight=405, height=389),
    Snake(name='Robin', length=210)
]
zoo = Zoo(animals=animals)

print('ZOO: ', zoo)
for animal in zoo.animals:
    print(animal)
# print: ZOO: Zoo(animals=[Elephant(name='Eldor', weight=0, temp=38.0, trunk_length=176), Tiger(name='Roy', weight=405, temp=38.0, height=389.0), Snake(name='Robin', weight=0, length=210.0)])
