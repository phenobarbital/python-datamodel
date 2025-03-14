from typing import List
from datetime import datetime
from dataclasses import is_dataclass
from datamodel import Model, BaseModel, Field
import pytest

# Base Class
class Animal(BaseModel):
    name: str
    weight: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)

# Derived Classes
class Snake(Animal):
    length: float

class Mammal(Animal):
    temp: float = Field(default=38.0)

class Felido(Mammal):
    claws: bool = Field(default=True)
    is_cat: bool = Field(default=True)

class Canido(Mammal):
    bark: bool = Field(default=True)
    is_dog: bool = Field(default=True)

# Further Specialization
class Tiger(Felido):
    height: float
    stripes: int

class Hiena(Felido):
    scavenger: bool = Field(default=True)

class Lycaon(Canido):
    scavenger: bool = Field(default=True)

class Elephant(Mammal):
    trunk_length: int

class Cetaceus(Mammal):
    fin_size: float
    water_type: str = Field(default="saltwater")  # Can be 'saltwater' or 'freshwater'

class Whale(Cetaceus):
    baleen: bool = Field(default=True)
    blowholes: int = Field(default=2)

class Dolphin(Cetaceus):
    speed: float
    intelligence_level: int

# Zoo Class
class Zoo(Model):
    animals: List[Animal]

animals = [
    Elephant(name="Eldor", trunk_length=176, weight=1200),
    Tiger(name="Roy", weight=405, height=389, stripes=10),
    Snake(name="Robin", length=210, weight=15),
    Whale(name="Moby", fin_size=2.5, weight=30000, baleen=True, blowholes=2),
    Dolphin(name="Flipper", fin_size=1.2, weight=150, speed=40.5, intelligence_level=9),
    Lycaon(name="Lycan", temp=37.5, bark=True, is_dog=False, scavenger=True),
    Hiena(name="Hyena", temp=37.5, claws=True, is_cat=False, scavenger=True),
]

def test_animal_hierarchy():
    # Verify all animals are dataclasses and inherit from the correct base
    assert all(is_dataclass(a) for a in animals)
    assert all(isinstance(a, Animal) for a in animals)
    # Ensure each subclass correctly inherits from its parents

def test_parents():
    assert issubclass(Tiger, Felido)
    assert issubclass(Felido, Mammal)
    assert issubclass(Mammal, Animal)
    assert issubclass(Snake, Animal)
    assert issubclass(Whale, Cetaceus)
    assert issubclass(Dolphin, Cetaceus)

def test_created_at_inheritance():
    # Ensure all child classes inherit created_at and it is initialized with a datetime
    for animal in animals:
        assert hasattr(animal, "created_at"), f"{animal.__class__.__name__} missing 'created_at'"
        assert isinstance(animal.created_at, datetime), f"'created_at' is not a datetime for {animal.name}"


def test_elephant_attributes():
    elephants = [a for a in animals if isinstance(a, Elephant)]
    assert len(elephants) == 1
    elephant = elephants[0]
    assert elephant.name == "Eldor"
    assert elephant.trunk_length == 176
    assert elephant.weight == 1200

def test_tiger_attributes():
    tigers = [a for a in animals if isinstance(a, Tiger)]
    assert len(tigers) == 1
    tiger = tigers[0]
    assert tiger.name == "Roy"
    assert tiger.height == 389
    assert tiger.stripes == 10
    assert tiger.temp == 38.0

def test_snake_attributes():
    snakes = [a for a in animals if isinstance(a, Snake)]
    assert len(snakes) == 1
    snake = snakes[0]
    assert snake.name == "Robin"
    assert snake.length == 210
    assert snake.weight == 15

def test_whale_attributes():
    whales = [a for a in animals if isinstance(a, Whale)]
    assert len(whales) == 1
    whale = whales[0]
    assert whale.name == "Moby"
    assert whale.fin_size == 2.5
    assert whale.weight == 30000
    assert whale.baleen is True
    assert whale.blowholes == 2
    assert whale.water_type == "saltwater"

def test_dolphin_attributes():
    dolphins = [a for a in animals if isinstance(a, Dolphin)]
    assert len(dolphins) == 1
    dolphin = dolphins[0]
    assert dolphin.name == "Flipper"
    assert dolphin.fin_size == 1.2
    assert dolphin.weight == 150
    assert dolphin.speed == 40.5
    assert dolphin.intelligence_level == 9
    assert dolphin.water_type == "saltwater"

def test_lycaon_attributes():
    lycaons = [a for a in animals if isinstance(a, Lycaon)]
    assert len(lycaons) == 1
    lycaon = lycaons[0]
    assert lycaon.name == "Lycan"
    assert lycaon.temp == 37.5
    assert lycaon.bark is True
    assert lycaon.is_dog is False
    assert lycaon.scavenger is True

def test_hiena_attributes():
    hienas = [a for a in animals if isinstance(a, Hiena)]
    assert len(hienas) == 1
    hiena = hienas[0]
    assert hiena.name == "Hyena"
    assert hiena.temp == 37.5
    assert hiena.claws is True
    assert hiena.is_cat is False
    assert hiena.scavenger is True


def test_zoo():
    # Test that all animals can be added to the Zoo
    zoo = Zoo(animals=animals)
    assert len(zoo.animals) == len(animals)
    assert all(isinstance(a, Animal) for a in zoo.animals)
    assert all(is_dataclass(a) for a in zoo.animals)

def test_zoo_counts():
    # Test that all animals can be added to the Zoo
    zoo = Zoo(animals=animals)
    assert is_dataclass(zoo)
    # Check specific animal counts
    assert len([a for a in zoo.animals if isinstance(a, Mammal)]) == 6
    assert len([a for a in zoo.animals if isinstance(a, Snake)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Lycaon)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Hiena)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Elephant)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Tiger)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Whale)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Dolphin)]) == 1
    assert len([a for a in zoo.animals if isinstance(a, Cetaceus)]) == 2

def test_zoo_attributes():
    # Test that all animals can be added to the Zoo
    zoo = Zoo(animals=animals)
    assert zoo.animals[0].name == "Eldor"
    assert zoo.animals[1].weight == 405
    assert zoo.animals[2].length == 210
    assert zoo.animals[3].fin_size == 2.5
    assert zoo.animals[4].speed == 40.5
    assert zoo.animals[5].temp == 37.5
    assert zoo.animals[6].scavenger is True
    # check if animal zero have created_at and is a datetime object:
    assert isinstance(zoo.animals[0].created_at, datetime)
