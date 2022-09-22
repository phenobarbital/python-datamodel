# DataModel
DataModel is a simple library based on python +3.7 to use Dataclass-syntax for interacting with
Data, using the same syntax of Dataclass, users can write Python Objects
and work with Data in the same way, is a reimplementation of python Dataclasses supporting true inheritance (without decorators), true composition and other good features.

The key features are:
* **Easy to use**: No more using decorators, concerns abour re-ordering attributes or common problems with using dataclasses with inheritance.
* **Extensibility**: Can use other dataclasses, Data objects or primitives as data-types.
* **Fast**: DataModel is a replacement 100% full compatible with dataclasses, without any overhead.



## Requirements

Python 3.8+

## Installation

<div class="termy">

```console
$ pip install python-datamodel
---> 100%
Successfully installed datamodel
```


</div>

## Quickstart


```python

from datamodel import Field, BaseModel
from dataclasses import dataclass, fields, is_dataclass


# This pure Dataclass:
@dataclass
class Point:
    x: int = Field(default=0, min=0, max=10)
    y: int = Field(default=0, min=0, max=10)

point = Point(x=10, y=10)
print(point)
print(fields(point))
print('IS a Dataclass?: ', is_dataclass(point))

# Can be represented by BaseModel
class newPoint(BaseModel):
    x: int = Field(default=0, min=0, max=10)
    y: int = Field(default=0, min=0, max=10)

    def get_coordinate(self):
        return (self.x, self.y)

point = newPoint(x=10, y=10)
print(point)
print(fields(point))
print('IS a Dataclass?: ', is_dataclass(point))
print(point.get_coordinate())
```
## Supported types

DataModel support recursive transformation of fields, so you can easily work with nested dataclasses or complex types.

DataModel supports automatic conversion of:

- [datetime](https://docs.python.org/3/library/datetime.html#available-types)
objects. `datetime` objects are encoded to str exactly like orjson conversion, any str typed as datetime is decoded to datetime.
The same behavior is used to decoding time, date and timedelta objects.

- [UUID](https://docs.python.org/3/library/uuid.html#uuid.UUID) objects. They
are encoded as `str` (JSON string) and decoded back to uuid.UUID objects.

- [Decimal](https://docs.python.org/3/library/decimal.html) objects. They are
also encoded as `float` and decoded back to Decimal.

Also, "custom" encoders are supported.

```python

import uuid
from typing import (
    List,
    Optional,
    Union
)
from dataclasses import dataclass, field
from datamodel import BaseModel, Field

@dataclass
class Point:
    x: int = Field(default=0, min=0, max=10)
    y: int = Field(default=0, min=0, max=10)

class coordinate(BaseModel, intSum):
    latitude: float
    longitude: float

    def get_location(self) -> tuple:
        return (self.latitude, self.longitude)

def auto_uid():
    return uuid.uuid4()

def default_rect():
    return [0,0,0,0]

def valid_zipcode(field, value):
    return value > 1000

class Address(BaseModel):
    id: uuid.UUID = field(default_factory=auto_uid)
    street: str = Field(required=True)
    zipcode: int = Field(required=False, default=1010, validator=valid_zipcode)
    location: Optional[coordinate]
    box: List[Optional[Point]]
    rect: List[int] = Field(factory=default_rect)


addr = Address(street="Calle Mayor", location=(18.1, 22.1), zipcode=3021, box=[(2, 10), (4, 8)], rect=[1, 2, 3, 4])
print('IS a Dataclass?: ', is_dataclass(addr))

print(addr.location.get_location())
```
```console
# returns
Address(id=UUID('24b34dd5-8d35-4cfd-8916-7876b28cdae3'), street='Calle Mayor', zipcode=3021, location=coordinate(latitude=18.1, longitude=22.1), box=[Point(x=2, y=10), Point(x=4, y=8)], rect=[1, 2, 3, 4])
```

* Fast and convenience conversion from-to JSON (using orjson):

```python
import orjson

b = addr.json()
print(b)
```
```console
{"id":"24b34dd5-8d35-4cfd-8916-7876b28cdae3","street":"Calle Mayor","zipcode":3021,"location":{"latitude":18.1,"longitude":22.1}, "box":[{"x":2,"y":10},{"x":4,"y":8}],"rect":[1,2,3,4]}
```

```python
# and re-imported from json
new_addr = Address.from_json(b) # load directly from json string
# or using a dictionary decoded by orjson
data = orjson.loads(b)
new_addr = Address(**data)

```

## Inheritance

python-datamodel supports inheritance of classes.

```python
import uuid
from typing import Union, List
from dataclasses import dataclass, field
from datamodel import BaseModel, Column, Field


def auto_uid():
    return uuid.uuid4()

class User(BaseModel):
    id: uuid.UUID = field(default_factory=auto_uid)
    name: str
    first_name: str
    last_name: str


@dataclass
class Address:
    street: str
    city: str
    state: str
    zipcode: str
    country: Optional[str] = 'US'

    def __str__(self) -> str:
        """Provides pretty response of address"""
        lines = [self.street]
        lines.append(f"{self.city}, {self.zipcode} {self.state}")
        lines.append(f"{self.country}")
        return "\n".join(lines)

class Employee(User):
    """
    Base Employee.
    """
    role: str
    address: Address # composition of a dataclass inside of DataModel is possible.

# Supporting multiple inheritance and composition
# Wage Policies
class MonthlySalary(BaseModel):
    salary: Union[float, int]

    def calculate_payroll(self) -> Union[float, int]:
        return self.salary

class HourlySalary(BaseModel):
    salary: Union[float, int] = Field(default=0)
    hours_worked: Union[float, int] = Field(default=0)

    def calculate_payroll(self) -> Union[float, int]:
        return (self.hours_worked * self.salary)

# employee types
class Secretary(Employee, MonthlySalary):
    """Secretary.

    Person with montly salary policy and no commissions.
    """
    role: str = 'Secretary'

class FactoryWorker(Employee, HourlySalary):
    """
    FactoryWorker is an employee with hourly salary policy and no commissions.
    """
    role: str = 'Factory Worker'

class PayrollSystem:
    def calculate_payroll(self, employees: List[dataclass]) -> None:
        print('=== Calculating Payroll === ')
        for employee in employees:
            print(f"Payroll for employee {employee.id} - {employee.name}")
            print(f"- {employee.role} Amount: {employee.calculate_payroll()}")
            if employee.address:
                print('- Sent to:')
                print(employee.address)
            print("")

jane = Secretary(name='Jane Doe', first_name='Jane', last_name='Doe', salary=1500)
bob = FactoryWorker(name='Bob Doyle', first_name='Bob', last_name='Doyle', salary=15, hours_worked=40)
mitch = FactoryWorker(name='Mitch Brian', first_name='Mitch', last_name='Brian', salary=20, hours_worked=35)

payroll = PayrollSystem()
payroll.calculate_payroll([jane, bob, mitch])
```
A sample of output:
```
```console
=== Calculating Payroll ===
Payroll for employee 745a2623-d4d2-4da6-bf0a-1fa691bafd33 - Jane Doe
- Secretary Amount: 1500
- Sent to:
Rodeo Drive, Rd
Los Angeles, 31050 CA
US
```
## Contributing

First of all, thank you for being interested in contributing to this library.
I really appreciate you taking the time to work on this project.

- If you're just interested in getting into the code, a good place to start are
issues tagged as bugs.
- If introducing a new feature, especially one that modifies the public API,
consider submitting an issue for discussion before a PR. Please also take a look
at existing issues / PRs to see what you're proposing has  already been covered
before / exists.
- I like to follow the commit conventions documented [here](https://www.conventionalcommits.org/en/v1.0.0/#summary)

## License

This project is licensed under the terms of the BSD v3. license.
