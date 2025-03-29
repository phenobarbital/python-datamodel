import uuid
from typing import List, Union
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError

DEFAULT_RECIPIENT = {
    "name": "Jesus Lara",
    "account": {
        "address": "jesuslarag@gmail.com",
        "phone": "+347777777"
    }
}

DEFAULT_MULTIPLE_ACCOUNTS = {
    "name": "Jesus Lara",
    "account": [
        {
            "provider": "email",
            "address": "jesuslarag@gmail.com"
        },
        {
            "provider": "sms",
            "phone": "+347777777"
        },
        {
            "provider": "whatsapp",
            "phone": "+347777777"
        },
        {
            "provider": "teams",
            "phone": "jlara@teams.com"
        }
    ]
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
    account: Union[Account, List[Account]]
    # account: List[Account]

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


def create_actor(payload):
    try:
        recipient = Actor(**payload)
        print(recipient)
        print('Account: ', recipient.account)
    except ValidationError as e:
        print(f"Validation Error: {e.payload}")
        return


if __name__ == "__main__":
    create_actor(DEFAULT_RECIPIENT)
    create_actor(DEFAULT_MULTIPLE_ACCOUNTS)
