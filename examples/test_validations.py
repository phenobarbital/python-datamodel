from typing import Union, List
import uuid
from bson import ObjectId
from datetime import datetime
from datamodel import BaseModel, Column, Field
from datamodel.exceptions import ValidationError



def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

def def_age():
    return 18

def is_employee(obj) -> str:
    if obj in ('Y', 'F'):
        return obj
    elif obj is True:
        return 'Y'
    else:
        return 'F'

class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Column(required=True, default='dummy')
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default='')
    phone: Union[str, List[str]] = Column(required=False, default='')

    def set_address(self, address: str):
        self.address = address

class Actor(BaseModel):
    """
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """
    userid: uuid.UUID = Column(required=True, primary_key=True, default=auto_uuid)
    age: int = Column(default=def_age)
    name: str = Column(required=True)
    account: Union[Account, List[Account]]
    is_employee: str = Column(required=True, default='F', encoder=is_employee)
    created_at: datetime = Column(required=False, default=datetime.now)

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


user = {
    "name": "Jesus Lara",
    "is_employee": True,
    "account": [
        {
            "provider": "twilio",
            "phone": "+343317871"
        },
        {
            "provider": "email",
            "address": "jesuslara@jesuslara.com"
        },
        {
            "provider": "jabber",
            "address": "jesuslara@jesuslara.com"
        }
    ]
}

def to_objid(value):
    if isinstance(value, str):
        return ObjectId(value.encode('ascii'))
    return value

class Dataset(BaseModel):
    _id: ObjectId = Field(encoder=to_objid)
    name: str = Field(required=True)


if __name__ == '__main__':
    user = Actor(**user)
    print(
        f"User: ID: {user.userid}, Name: {user.name}, age: {user.age}, accounts: {user.account!r}, created: {user.created_at}"
    )
    print(f'Types: {type(user.created_at)}')
    try:
        # Test if name is required:
        missing_data = {
        "userid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "account": [
                {"provider": "twilio", "phone": "+343317871"},
            ]
        }
        user = Actor(**missing_data)
    except (ValueError, AttributeError) as ex:
        print(f"Error: {ex}", type(ex))
    except ValidationError as ex:
        print(f"Error: {ex}", type(ex))
        print(f"ValidationError: {ex.payload}")
    # Test Account for Invalid Data:
    invalid_data = {
        "userid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "Invalid User",
        "account": [
            {"provider": "twilio", "phone": {"phone": 343317871}},  # Expecting a string for `phone`
        ]
    }
    try:
        Account(**invalid_data["account"][0])
    except (ValueError, AttributeError) as ex:
        print(
            f"Error: {ex}", type(ex)
        )
    except ValidationError as ex:
        print(
            f"Error: {ex}", type(ex)
        )
        print(
            f"ValidationError: {ex.payload}"
        )
    # Test for Invalid Data:
    try:
        user = Actor(**invalid_data)
        print(user.account, type(user.account[0]['phone']))
    except (ValueError, AttributeError) as ex:
        print(
            f"Error: {ex}", type(ex)
        )
    except ValidationError as ex:
        print(
            f"Error: {ex}", type(ex)
        )
        print(
            f"ValidationError: {ex.payload}"
        )
    try:
        print('================================================================')
        dataset = Dataset(_id='123456789012', name="Test Dataset")
        print(dataset._id, dataset.name)
        print(' == Convert into JSON ===')
        data = dataset.to_json()
        print(data)
        print(' == Revert Back ===')
        d = Dataset(**dataset.to_dict())
        print(d._id, type(d._id))
    except ValidationError as ex:
        print(f"Error: {ex}", type(ex))
        print(f"ValidationError: {ex.payload}")
    except ValueError as ex:
        print(f"Error: {ex}", type(ex))
