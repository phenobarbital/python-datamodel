from typing import List
from dataclasses import is_dataclass
from datamodel import Model, Field

class Animal(Model):
    name: str
    weight: int

class Snake(Animal):
    length: float

class Mammal(Animal):
    temp: float = Field(default=38.0)

class Tiger(Mammal):
    height: float
    stripes: int

class Elephant(Mammal):
    trunk_length: int

class Zoo(Model):
    animals: List[Animal]

animals = [
    Elephant(name="Eldor", trunk_length=176),
    Tiger(name="Roy", weight=405, height=389, stripes=10),
    Snake(name='Robin', length=210)
]

def test_animals():
    assert all(is_dataclass(a) for a in animals)
    assert all(isinstance(a, Animal) for a in animals)
    assert all(isinstance(a, Mammal) or isinstance(a, Snake) for a in animals)
    assert animals[0].trunk_length == 176
    assert animals[1].height == 389
    assert animals[2].length == 210

def test_tiger():
    tigers = [animal for animal in animals if isinstance(animal, Tiger)]
    assert len(tigers) == 1
    tiger = tigers[0]
    assert tiger.name == "Roy"
    assert tiger.weight == 405
    assert tiger.temp == 38.0
    assert tiger.height == 389
    assert tiger.stripes == 10
