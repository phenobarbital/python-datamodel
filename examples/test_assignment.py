import uuid
from typing import List, Union
from datetime import datetime
from datamodel import BaseModel, Field, Column

DEFAULT_RECIPIENT = {
    "name": "Jesus Lara",
    "age": 45,
    "account": {
        "address": "jesuslarag@gmail.com",
        "phone": "+34692817379"
    }
}

def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Column(required=True, default='dummy')
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default='')
    phone: Union[str, list] = Column(required=False, default='')
    userid: str = Column(required=False, default='')

    def set_address(self, address: str):
        self.address = address

class Actor(BaseModel):
    """
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """
    userid: uuid.UUID = Field(required=False, primary_key=True, default=auto_uuid)
    name: str
    age: int = Field(required=False, default=0)
    signed: datetime = Field(required=False, default=datetime.now())
    account: Union[Account, List[Account]]

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'

    class Meta:
        validate_assignment = True

recipient = Actor(**DEFAULT_RECIPIENT)
print(recipient)
print(f'User ID : {recipient.userid}')
print(recipient.account)

# Assigment a new invalid value to age:
try:
    recipient.age = 'This is not a valid'
    print(recipient.age)
except TypeError as e:
    print(f'Error: {e}')

# Parsing on assignment:
recipient.age = '45'
recipient.signed = '2021-01-01 12:00:00'
print(type(recipient.age), type(recipient.signed))
