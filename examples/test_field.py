from typing import Optional
from dataclasses import dataclass
from datamodel.fields import Column, Field
from datamodel.types import default_dict, default_string

@dataclass
class Person:
    name: str = Field(required=True, factory=default_string, comment='Factory callable')
    first_name: str = Field(required=True, factory=default_string, comment='Factory callable')
    last_name: str = Field(required=True, default_factory=str, comment='Default Factory')
    age: int = Column(default=0)
    email: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default='')
    attributes: Optional[dict] = Column(default_factory=default_dict)


person = Person(name="Mary", age=30, email="mary@example.com", bio="A bio", attributes={"hair_color": "blonde"})
print('Mary > ', person)

age_field = Column(default=10)
person = Person(name="Bob", age=age_field)
print('Bob > ', person)

person = Person()
print('None > ', person)
